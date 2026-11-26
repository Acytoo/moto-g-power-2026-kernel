"""Pack an lz4-legacy initramfs using this phone's original init_boot metadata."""
from pathlib import Path
import hashlib
import importlib.util
import json
import os
import struct
import subprocess
import sys
import tempfile

import argparse
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import boot_image
TOOLS = boot_image.TOOLS
HERE = None
avb = None
SOURCE = None
OUTPUT = None
os.umask(0o077)


def run(*args):
    return subprocess.run([str(x) for x in args], capture_output=True, text=True, check=True).stdout


def parse(p):
    return avb.Avb()._parse_image(avb.ImageHandler(str(p), read_only=True))


def pack(payload, name):
    assert name in ('magisk-restore', 'probe', 'chooser-dry', 'chooser-android-default', 'chooser-debian-default')
    data = payload.read_bytes(); assert data[:4] == b'\x02\x21\x4c\x18'
    source = SOURCE
    stock = source.read_bytes()
    ft, h, descs, size = parse(source)
    hashes = [d for d in descs if isinstance(d, avb.AvbHashDescriptor)]
    assert len(hashes) == 1 and hashes[0].partition_name == 'init_boot'
    baseline = hashes[0]
    assert size == 8388608 and h.algorithm_type == 0 and baseline.flags == 0
    assert struct.unpack_from('<I', stock, 40)[0] == 4
    props = [(d.key, d.value.decode()) for d in descs if isinstance(d, avb.AvbPropertyDescriptor)]
    out = HERE
    image = OUTPUT
    run(sys.executable, TOOLS / 'mkbootimg.py', '--header_version', '4', '--cmdline', '',
        '--ramdisk', payload, '--output', image)
    with image.open('r+b') as f: f.truncate(max(image.stat().st_size, baseline.image_size))
    args = [sys.executable, TOOLS / 'avbtool.py', 'add_hash_footer', '--image', image,
            '--partition_name', 'init_boot', '--partition_size', size, '--algorithm', 'NONE',
            '--hash_algorithm', baseline.hash_algorithm, '--salt', baseline.salt.hex(),
            '--rollback_index', h.rollback_index, '--rollback_index_location', h.rollback_index_location,
            '--flags', h.flags]
    for k, v in props: args += ['--prop', k + ':' + v]
    run(*args)
    d = image.read_bytes(); f, nh, nds, nsize = parse(image)
    nhashes = [x for x in nds if isinstance(x, avb.AvbHashDescriptor)]
    assert len(nhashes) == 1; hd = nhashes[0]
    assert nsize == size
    assert d[:12] + d[16:4096] == stock[:12] + stock[16:4096]
    assert struct.unpack_from('<I', d, 12)[0] == len(data)
    assert d[4096:4096 + len(data)] == data
    assert f.vbmeta_offset >= baseline.image_size and f.vbmeta_offset == f.original_image_size == hd.image_size
    assert not any(d[4096 + len(data):f.vbmeta_offset])
    assert f.vbmeta_offset + f.vbmeta_size < size - 64
    assert not any(d[f.vbmeta_offset + f.vbmeta_size:-64])
    assert hd.partition_name == 'init_boot' and hd.hash_algorithm == 'sha256' and hd.flags == baseline.flags
    assert hd.salt == baseline.salt and hd.digest == hashlib.sha256(hd.salt + d[:hd.image_size]).digest()
    assert [(x.key, x.value.decode()) for x in nds if isinstance(x, avb.AvbPropertyDescriptor)] == props
    for key in ('algorithm_type', 'rollback_index', 'rollback_index_location', 'flags'):
        assert getattr(nh, key) == getattr(h, key)
    with tempfile.TemporaryDirectory(dir=HERE) as temp:
        named = Path(temp) / 'init_boot.img'; named.symlink_to(image)
        verification = run(sys.executable, TOOLS / 'avbtool.py', 'verify_image', '--image', named)
    (out / (name + '.verification.txt')).write_text(verification)
    record = {'name': name, 'file': image.name, 'sha256': boot_image.sha(image), 'size': size,
              'ramdisk_sha256': boot_image.sha(payload), 'ramdisk_size': len(data),
              'vbmeta_offset': f.vbmeta_offset, 'original_descriptor_size': baseline.image_size,
              'verified': True, 'avb_algorithm': 'NONE', 'hardware_tested': False}
    image.with_suffix('.json').write_text(json.dumps(record, indent=2) + '\n')
    print('Validated', name, record['sha256'])


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--original', type=Path, required=True)
    p.add_argument('--ramdisk', type=Path, required=True)
    p.add_argument('--name', choices=['magisk-restore','probe','chooser-dry','chooser-android-default','chooser-debian-default'], required=True)
    p.add_argument('--output', type=Path, required=True)
    a=p.parse_args(); SOURCE=a.original.resolve(); OUTPUT=a.output.resolve(); HERE=OUTPUT.parent
    assert not OUTPUT.exists() and not OUTPUT.with_suffix('.json').exists()
    boot_image.configure(OUTPUT); avb=boot_image.avb
    pack(a.ramdisk.resolve(),a.name)
