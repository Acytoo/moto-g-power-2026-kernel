"""Read named BTF member offsets, including promoted anonymous union members.

Only the documented SYSVIPC use of task_struct reserve slots may add members.
Existing member types, bit widths, offsets, and overall size must stay identical.
"""
import struct
from pathlib import Path


def section(path):
    data = Path(path).read_bytes()
    if data[:4] != b'\x7fELF':
        return data
    if data[4:6] != b'\x02\x01':
        raise ValueError('Expected little-endian ELF64')
    offset = struct.unpack_from('<Q', data, 40)[0]
    size, count, strings = struct.unpack_from('<HHH', data, 58)
    headers = [struct.unpack_from('<IIQQQQIIQQ', data, offset + i * size) for i in range(count)]
    sh = headers[strings]
    names = data[sh[4]:sh[4] + sh[5]]
    for h in headers:
        if names[h[0]:].split(b'\0', 1)[0] == b'.BTF':
            return data[h[4]:h[4] + h[5]]
    raise ValueError('Missing .BTF')


class BTF:
    def __init__(self, data):
        magic, version, flags, hdr, toff, tlen, soff, slen = struct.unpack_from('<HBBIIIII', data)
        if magic != 0xeb9f or version != 1 or flags:
            raise ValueError('Unsupported BTF header')
        strings = data[hdr + soff:hdr + soff + slen]
        self.types = [dict(kind=0, name='void', value=0)]
        name = lambda off: strings[off:strings.index(b'\0', off)].decode()
        pos, end = hdr + toff, hdr + toff + tlen
        extra_sizes = {1: 4, 2: 0, 3: 12, 4: 12, 5: 12, 6: 8, 7: 0,
                       8: 0, 9: 0, 10: 0, 11: 0, 12: 0, 13: 8, 14: 4,
                       15: 12, 16: 0, 17: 4, 18: 0, 19: 12}
        while pos < end:
            noff, info, value = struct.unpack_from('<III', data, pos)
            kind, count, kflag = (info >> 24) & 31, info & 65535, info >> 31
            pos += 12
            if kind not in extra_sizes:
                raise ValueError(f'Unknown BTF kind {kind}')
            length = extra_sizes[kind] * (count if kind in (4, 5, 6, 13, 15, 19) else 1)
            t = dict(kind=kind, name=name(noff), value=value)
            if kind in (4, 5):
                t['members'] = []
                for i in range(count):
                    n, typ, off = struct.unpack_from('<III', data, pos + i * 12)
                    t['members'].append((name(n), typ, off & 0xffffff if kflag else off,
                                         off >> 24 if kflag else 0))
            if kind == 3:
                t['array'] = struct.unpack_from('<III', data, pos)
            if kind == 1:
                t['encoding'] = struct.unpack_from('<I', data, pos)[0]
            self.types.append(t)
            pos += length
        if pos != end:
            raise ValueError('Invalid BTF length')

    def signature(self, tid, seen=()):
        if tid in seen:
            return ('recursive',)
        t = self.types[tid]
        k = t['kind']
        if k in (0, 1, 6, 7, 16, 19):
            return k, t['name'], t['value'], t.get('encoding')
        if k in (2, 8, 9, 10, 11, 18):
            return k, t['name'], self.signature(t['value'], (*seen, tid))
        if k == 3:
            elem, _, count = t['array']
            return k, count, self.signature(elem, (*seen, tid))
        if k in (4, 5):
            if t['name']:
                return k, t['name'], t['value']
            return k, t['value'], tuple(sorted(self.members(tid).items()))
        # Function-pointer prototype definitions are also covered by export CRCs.
        if k == 13:
            return ('function', self.signature(t['value'], (*seen, tid)))
        return k, t['name']

    def members(self, tid, offset=0):
        result = {}
        for name, typ, off, bits in self.types[tid]['members']:
            if name:
                if name in result:
                    raise ValueError('Duplicate BTF member')
                result[name] = (offset + off, bits, self.signature(typ))
            elif self.types[typ]['kind'] in (4, 5):
                nested = self.members(typ, offset + off)
                if result.keys() & nested.keys():
                    raise ValueError('Duplicate promoted BTF member')
                result.update(nested)
        return result

    def named(self, name):
        matches = [i for i, t in enumerate(self.types)
                   if t['kind'] == 4 and t['name'] == name]
        if len(matches) != 1:
            raise ValueError(f'Expected one struct {name}, found {len(matches)}')
        return self.members(matches[0])


def compatible_members(old, new, name):
    a, b = old.named(name), new.named(name)
    if any(b.get(n) != value for n, value in a.items()):
        return False
    added = b.keys() - a.keys()
    if not added:
        return True
    if name != 'task_struct' or added != {'sysvsem', 'sysvshm'}:
        return False
    # Constrain both added members to exactly the reviewed 24-byte reserve area.
    first = a['android_kabi_reserved6'][0]
    second = a['android_kabi_reserved7'][0]
    third = a['android_kabi_reserved8'][0]
    return (second == first + 64 and third == second + 64
            and b['sysvsem'] == (first, 0, (4, 'sysv_sem', 8))
            and b['sysvshm'] == (second, 0, (4, 'sysv_shm', 16)))
