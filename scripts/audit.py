#!/usr/bin/env python3
"""Reject unexpected tracked files and common secret formats before CI build."""
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
ALLOWED = {
    '.gitignore', '.github/workflows/kernel.yml', 'README.md', 'NOTICE.md',
    'config/stock.config', 'config/linux.fragment', 'config/sources.env',
    'scripts/fetch.sh', 'scripts/build.sh', 'scripts/prepare.py', 'scripts/compare.py',
    'scripts/audit.py', 'tests/test_gates.py', 'scripts/btf.py',
    'config/containers.fragment', 'patches/sysvipc-kabi.patch',
}


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
    raw = subprocess.check_output(['git', '-C', str(ROOT), 'ls-files', '-z'])
    tracked = set(raw.decode().strip('\x00').split('\x00'))
    if tracked != ALLOWED:
        raise SystemExit(f'Tracked-file allowlist mismatch: {sorted(tracked ^ ALLOWED)}')
    for name in sorted(tracked):
        p = ROOT / name
        if p.is_symlink() or p.stat().st_size > 1024 * 1024:
            raise SystemExit(f'Unexpected input type or size: {name}')
        check_content(name, p.read_bytes())
    print(f'Publication audit passed: {len(tracked)} explicitly allowed text files; no phone captures')


if __name__ == '__main__':
    main()
