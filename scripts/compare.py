#!/usr/bin/env python3
"""Compare control/variant BTF and kernel export CRCs. Hardware remains untested."""
import json
import subprocess
import sys
from pathlib import Path
from btf import BTF, section, compatible_members


def layout(image, name=None):
    args = ['pahole', '-F', 'btf']
    args += ['-C', name] if name else ['--sizes']
    r = subprocess.run([*args, str(image)], text=True, capture_output=True, check=True)
    if not r.stdout.strip():
        raise RuntimeError(f'No BTF layout output: {image}, {name}')
    return r.stdout


def sizes(text):
    result = {}
    for line in text.splitlines():
        fields = line.split()
        if len(fields) >= 3:
            result.setdefault(fields[0], set()).add(tuple(fields[1:3]))
    if not result:
        raise RuntimeError('No parsed structures')
    return result


def exports(path):
    result = {}
    for line in path.read_text().splitlines():
        fields = line.split()
        if len(fields) >= 3 and fields[2] == 'vmlinux':
            result[fields[1]] = fields[0]
    if not result:
        raise RuntimeError('No vmlinux exports')
    return result


def main(stock, linux, output):
    output.mkdir(parents=True, exist_ok=True)
    a = sizes(layout(stock / 'vmlinux'))
    b = sizes(layout(linux / 'vmlinux'))
    changed = sorted(k for k in a if k not in b or a[k] != b[k])
    types = ['task_struct', 'mm_struct', 'file', 'inode', 'super_block', 'dentry',
             'sk_buff', 'net_device', 'device', 'module', 'cred', 'signal_struct']
    old_btf, new_btf = BTF(section(stock / 'vmlinux')), BTF(section(linux / 'vmlinux'))
    members = [k for k in types if not compatible_members(old_btf, new_btf, k)]
    sa, sb = exports(stock / 'Module.symvers'), exports(linux / 'Module.symvers')
    crc_changes = sorted(k for k in sa if k not in sb or sa[k] != sb[k])
    report = dict(changed_or_removed_structure_sizes=changed,
                  changed_selected_member_layouts=members,
                  changed_or_removed_export_crcs=crc_changes,
                  added_kernel_exports=len(sb.keys() - sa.keys()),
                  vendor_modules_checked=False, hardware_tested=False,
                  flash_authorized=False)
    (output / 'comparison.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
    if changed or members or crc_changes:
        raise SystemExit('Compatibility differences require investigation; do not flash')
    print('Offline comparison passed. Local vendor-module checks and hardware tests are still required.')


if __name__ == '__main__':
    main(*(Path(x) for x in sys.argv[1:]))
