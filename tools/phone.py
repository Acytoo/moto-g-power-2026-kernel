#!/usr/bin/env python3
"""Pinned SSH status and explicit boot-only operations for a private profile."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess


def sha(path):
    with Path(path).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def profile(path):
    path = Path(path).resolve()
    if path.stat().st_mode & 0o077:
        raise ValueError('Private profile must have mode 600 or stricter')
    data = json.loads(path.read_text())
    if 'REPLACE_WITH_' in json.dumps(data):
        raise ValueError('Complete the private profile first')
    if data['product'] != 'vegas' or data['sku'] != 'XT2617V' or data['slot'] not in ('a', 'b'):
        raise ValueError('Unsupported device profile')
    if not re.fullmatch(r'[A-Za-z0-9]+', data['serial']):
        raise ValueError('Invalid serial')
    if not re.fullmatch(r'[a-z_][a-z0-9_-]*', data['ssh_user']):
        raise ValueError('Invalid SSH user')
    for key in ('ssh_host', 'host_key_alias'):
        if not re.fullmatch(r'[A-Za-z0-9_.:-]+', data[key]) or data[key].startswith('-'):
            raise ValueError(f'Invalid {key}')
    if not 0 < int(data['ssh_port']) <= 65535 or data['boot_size'] != 67108864:
        raise ValueError('Invalid port/boot size')
    for key in ('identity_file', 'known_hosts_file', 'fastboot'):
        data[key] = str((path.parent / Path(data[key]).expanduser()).resolve())
    return data


def ssh_args(p):
    return ['ssh', '-F', '/dev/null', '-i', p['identity_file'], '-p', str(p['ssh_port']),
            '-o', 'IdentitiesOnly=yes', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=8',
            '-o', 'StrictHostKeyChecking=yes', '-o', 'GlobalKnownHostsFile=/dev/null',
            '-o', 'UserKnownHostsFile=' + p['known_hosts_file'],
            '-o', 'HostKeyAlias=' + p['host_key_alias'], p['ssh_user'] + '@' + p['ssh_host']]


def fb(p, *args):
    if sha(p['fastboot']) != p['fastboot_sha256']:
        raise ValueError('Fastboot binary digest differs from private profile')
    try:
        result = subprocess.run([p['fastboot'], '-s', p['serial'], *map(str, args)],
                                capture_output=True, text=True, timeout=120)
    except subprocess.TimeoutExpired as e:
        out = e.stderr or b''
        if isinstance(out, bytes):
            out = out.decode(errors='replace')
        raise RuntimeError('Fastboot timed out; no retry/reboot. ' + out.replace(p['serial'], '<device>')) from None
    out = (result.stdout + result.stderr).replace(p['serial'], '<device>')
    if result.returncode or re.search(r'\bFAILED\b', out):
        raise RuntimeError(out)
    return out


def gate(p):
    checks = dict(product=p['product'], sku=p['sku'], **{'current-slot': p['slot'],
                  'securestate': 'flashing_unlocked', 'is-userspace': 'no'})
    checks['partition-size:boot_' + p['slot']] = hex(p['boot_size'])
    for name, expected in checks.items():
        out = fb(p, 'getvar', name)
        values = re.findall(r'^(?:\(bootloader\)\s*)?' + re.escape(name) + r':\s*(.*?)\s*$', out, re.M)
        if len(values) != 1:
            raise ValueError(f'No unique {name}')
        actual = values[0]
        if name.startswith('partition-size:'):
            if int(actual, 16) != int(expected, 16):
                raise ValueError('Partition size mismatch')
        elif actual != expected:
            raise ValueError(f'Device gate failed: {name}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile', required=True)
    sub = parser.add_subparsers(dest='mode', required=True)
    sub.add_parser('status')
    sub.add_parser('fastboot-check')
    flash = sub.add_parser('flash-boot')
    flash.add_argument('--image', type=Path, required=True)
    flash.add_argument('--image-report', type=Path, required=True)
    flash.add_argument('--compat-report', type=Path, required=True)
    flash.add_argument('--restore-image', type=Path, required=True)
    flash.add_argument('--restore-sha256', required=True)
    restore = sub.add_parser('restore-boot')
    restore.add_argument('--image', type=Path, required=True)
    restore.add_argument('--sha256', required=True)
    args = parser.parse_args()
    p = profile(args.profile)
    if args.mode == 'status':
        command = ('id -un; uname -r; cat /etc/vegas/root-role; '
                   'findmnt -n -o SOURCE,FSTYPE /; systemctl is-system-running; '
                   'systemctl --user is-active docker; docker info --format '
                   "'{{.Architecture}} {{.Driver}} {{.CgroupVersion}}'")
        r = subprocess.run([*ssh_args(p), command], capture_output=True, text=True, timeout=45)
        print((r.stdout + r.stderr).replace(p['serial'], '<device>'), end='')
        raise SystemExit(r.returncode)
    if args.mode == 'flash-boot':
        report = json.loads(args.image_report.read_text())
        compat = json.loads(args.compat_report.read_text())
        if not compat['offline_checks_passed'] or compat['module_files'] != 399:
            raise ValueError('Vendor compatibility report did not pass')
        if report['kernel_Image_sha256'] != compat['Image_sha256'] or not report['avb_hash_verified']:
            raise ValueError('Image is not linked to the checked kernel')
        if sha(args.image) != report['sha256'] or report['size'] != p['boot_size']:
            raise ValueError('Image hash/size mismatch')
        if args.restore_image.stat().st_size != p['boot_size'] or sha(args.restore_image) != args.restore_sha256:
            raise ValueError('Saved restore image hash/size mismatch')
    elif args.mode == 'restore-boot':
        if sha(args.image) != args.sha256:
            raise ValueError('Restore image hash mismatch')
    if args.mode != 'fastboot-check' and args.image.stat().st_size != p['boot_size']:
        raise ValueError('Boot image partition size mismatch')
    gate(p)
    if args.mode == 'fastboot-check':
        print('Exact-device bootloader gates passed')
        return
    out = fb(p, 'flash', 'boot_' + p['slot'], args.image.resolve())
    if not re.search(r"Writing\s+'boot_" + p['slot'] + r"'.*?OKAY", out, re.S):
        raise RuntimeError('No confirmed boot-partition write; do not reboot blindly')
    print(out)
    print('Boot write confirmed. No erase, slot change or reboot was sent. Verify boot and readback next.')


if __name__ == '__main__':
    main()
