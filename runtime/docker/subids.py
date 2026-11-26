"""Validate existing subordinate ID ranges; never edit account databases."""
from pathlib import Path
import pwd
import sys


def validate(text, account, uid, primary_ids=()):
    ranges = []
    for line in text.splitlines():
        if not line.strip() or line.lstrip().startswith('#'):
            continue
        owner, start, count = line.split(':')
        start, count = int(start), int(count)
        if start <= 0 or count <= 0 or start + count > 2**32:
            raise ValueError('Invalid subordinate range')
        ranges.append((start, start + count, owner))
    ranges.sort()
    if any(a[1] > b[0] for a, b in zip(ranges, ranges[1:])):
        raise ValueError('Overlapping subordinate ranges')
    selected = [(a, b) for a, b, owner in ranges if owner in (account, str(uid))]
    if not selected or max(b - a for a, b in selected) < 65536:
        raise ValueError('Target needs an existing subordinate range of at least 65536 IDs')
    if any(a <= n < b for a, b in selected for n in primary_ids):
        raise ValueError('Target subordinate range overlaps a real account/group ID')


if __name__ == '__main__':
    import grp
    name = sys.argv[1]
    user = pwd.getpwnam(name)
    validate(Path('/etc/subuid').read_text(), name, user.pw_uid,
             [p.pw_uid for p in pwd.getpwall()])
    validate(Path('/etc/subgid').read_text(), name, user.pw_uid,
             [g.gr_gid for g in grp.getgrall()])
    print('Existing subordinate UID/GID ranges validated')
