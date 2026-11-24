#!/usr/bin/env python3
"""Prepare the public symbol whitelist; reject unexplained config changes."""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def config(path):
    result = {}
    for line in Path(path).read_text().splitlines():
        if line.startswith('CONFIG_') and '=' in line:
            key, value = line.split('=', 1)
            result[key] = value
        elif m := re.fullmatch(r'# (CONFIG_\w+) is not set', line):
            result[m[1]] = 'n'
    return result


def symbols():
    source = ROOT / 'work/common'
    text = (source / 'build.config.gki.aarch64').read_text()
    primary = re.search(r'^KMI_SYMBOL_LIST=(\S+)$', text, re.M)
    additional = re.search(r'ADDITIONAL_KMI_SYMBOL_LISTS="(.*?)"', text, re.S)
    if not primary or not additional:
        raise SystemExit('Cannot determine the upstream GKI symbol lists')
    names = set()
    for rel in [primary[1], *additional[1].split()]:
        for line in (source / rel).read_text().splitlines():
            line = line.split('#', 1)[0].strip()
            if not line or line.startswith('['):
                continue
            if not re.fullmatch(r'[A-Za-z_][A-Za-z_0-9]*', line):
                raise SystemExit(f'Unexpected whitelist entry in {rel}')
            names.add(line)
    if len(names) < 100:
        raise SystemExit('Unexpectedly small symbol whitelist')
    (ROOT / 'work/abi_symbollist.raw').write_text('\n'.join(sorted(names)) + '\n')
    print(f'Prepared {len(names)} upstream symbol names')


def check(variant, actual, report):
    expected = config(ROOT / 'config/stock.config')
    if variant == 'linux':
        expected.update(config(ROOT / 'config/linux.fragment'))
    elif variant != 'stock':
        raise SystemExit('Unknown variant')
    found = config(actual)
    # Compiler/binutils/pahole version fields reflect the CI tool environment.
    metadata = {'CONFIG_CC_VERSION_TEXT', 'CONFIG_CLANG_VERSION', 'CONFIG_LLD_VERSION',
                'CONFIG_AS_VERSION', 'CONFIG_LD_VERSION', 'CONFIG_GCC_VERSION',
                'CONFIG_PAHOLE_VERSION'}
    # Linux no longer needs the trim whitelist once trimming is disabled.
    if variant == 'linux':
        expected.pop('CONFIG_UNUSED_KSYMS_WHITELIST', None)
        found.pop('CONFIG_UNUSED_KSYMS_WHITELIST', None)
    differences = {k: (expected.get(k, 'n'), found.get(k, 'n'))
                   for k in expected.keys() | found.keys()
                   if expected.get(k, 'n') != found.get(k, 'n')}
    lines = [f'{k}: expected={a}, actual={b}' for k, (a, b) in sorted(differences.items())]
    Path(report).write_text('\n'.join(lines) + '\n')
    for line in lines:
        print(line)
    unexpected = set(differences) - metadata
    if unexpected:
        for key in sorted(unexpected):
            a, b = differences[key]
            message = f'{key}: expected={a}, actual={b}'.replace('%', '%25').replace('\r', '%0D').replace('\n', '%0A')
            print(f'::error title=Unexpected configuration drift::{message}')
        raise SystemExit('Unexplained configuration drift: ' + ', '.join(sorted(unexpected)))
    print('Configuration matches expected features (tool version differences reported separately)')


if __name__ == '__main__':
    if sys.argv[1:] == ['symbols']:
        symbols()
    elif len(sys.argv) == 5 and sys.argv[1] == 'check':
        check(sys.argv[2], sys.argv[3], sys.argv[4])
    else:
        raise SystemExit('Usage: prepare.py symbols | check stock|linux CONFIG REPORT')
