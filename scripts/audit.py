#!/usr/bin/env python3
"""Reject unexpected tracked files and common secret formats before CI build."""
from pathlib import Path
import re
import subprocess
import argparse

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = 'config/public-files.txt'


def check_content(name, content):
    if b'\x00' in content:
        raise ValueError(f'Binary input is not allowed: {name}')
    text = content.decode('utf-8')
    patterns = [r'-----BEGIN (?:OPENSSH |RSA |EC |ENCRYPTED )?PRIVATE KEY-----',
                r'\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{20,}',
                r'\bgithub_pat_[A-Za-z0-9_]{20,}',
                r'\bssh-(?:ed25519|rsa)\s+[A-Za-z0-9+/]{30,}']
    if any(re.search(p, text) for p in patterns):
        raise ValueError(f'Credential/key material found in {name}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--working-tree', action='store_true',
                        help='Check reviewed files before staging; default checks exact index blobs')
    args = parser.parse_args()
    def read(name):
        if args.working_tree:
            p = ROOT / name
            if p.is_symlink():
                raise SystemExit(f'Symlink is not allowed: {name}')
            return p.read_bytes()
        return subprocess.check_output(['git', '-C', str(ROOT), 'show', ':' + name])
    allowed = set(read(MANIFEST).decode().splitlines())
    if not allowed or MANIFEST not in allowed or any(
            not n or Path(n).is_absolute() or '..' in Path(n).parts for n in allowed):
        raise SystemExit('Invalid publication allowlist')
    raw = subprocess.check_output(['git', '-C', str(ROOT), 'ls-files', '-z'])
    tracked = set(raw.decode().strip('\x00').split('\x00'))
    if not args.working_tree and tracked != allowed:
        raise SystemExit(f'Tracked-file allowlist mismatch: {sorted(tracked ^ allowed)}')
    if not args.working_tree:
        entries = subprocess.check_output(['git', '-C', str(ROOT), 'ls-files', '-s', '-z']).decode().split('\x00')
        if any(e and not e.startswith(('100644 ', '100755 ')) for e in entries):
            raise SystemExit('Only regular text files may be tracked')
    for name in sorted(allowed):
        content = read(name)
        if len(content) > 1024 * 1024:
            raise SystemExit(f'Unexpected input type or size: {name}')
        check_content(name, content)
    print(f'Publication audit passed: {len(allowed)} explicitly allowed text files')


if __name__ == '__main__':
    main()
