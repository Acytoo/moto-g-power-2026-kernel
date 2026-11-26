#!/usr/bin/env python3
"""Fetch pinned public tools only; no phone access or system installation."""
import argparse
import base64
import hashlib
import io
import json
from pathlib import Path
import shutil
import tarfile
import tempfile
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
PINS = json.loads((ROOT / 'config/tools.json').read_text())


def download(entry):
    with urllib.request.urlopen(entry['url'], timeout=90) as response:
        data = response.read()
    if entry.get('encoding') == 'base64':
        data = base64.b64decode(data)
    if hashlib.sha256(data).hexdigest() != entry['sha256']:
        raise ValueError('Pinned public download checksum mismatch')
    return data


def write_same(path, data, mode=0o644):
    if path.exists():
        if path.is_symlink() or path.read_bytes() != data:
            raise ValueError(f'Existing tool differs: {path.name}')
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('xb') as f:
            f.write(data)
    path.chmod(mode)


def main(kind):
    tools = ROOT / 'work/tools'
    if kind == 'boot':
        for name, entry in PINS['boot_tools'].items():
            write_same(tools / name, download(entry))
    elif kind == 'fastboot':
        pin = PINS['fastboot']
        data = download(dict(url=pin['url'], sha256=pin['zip_sha256']))
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            binary = z.read('platform-tools/fastboot')
        if hashlib.sha256(binary).hexdigest() != pin['fastboot_sha256']:
            raise ValueError('Fastboot executable checksum mismatch')
        write_same(tools / 'fastboot-37.0.1', binary, 0o755)
    elif kind == 'upstream':
        target = ROOT / 'work/upstream'
        if target.exists():
            raise ValueError('work/upstream already exists; retain/review it rather than overwrite')
        raw = download(PINS['upstream'])
        target.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=target.parent) as tmp:
            with tarfile.open(fileobj=io.BytesIO(raw), mode='r:gz') as archive:
                archive.extractall(tmp, filter='data')
            contents = list(Path(tmp).iterdir())
            if len(contents) != 1 or not contents[0].is_dir():
                raise ValueError('Unexpected upstream archive layout')
            shutil.move(contents[0], target)
    print(f'Verified public {kind} inputs ready under work/')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('kind', choices=['boot', 'fastboot', 'upstream'])
    main(p.parse_args().kind)
