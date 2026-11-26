"""Offline v4 boot packaging, preserving this firmware's header/footer metadata."""
import argparse, gzip, hashlib, importlib.util, json, os, struct, subprocess, sys, tempfile
from pathlib import Path
os.umask(0o077)
ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / 'work/tools'
HERE = None
avb = None

def configure(output):
    global avb, HERE
    HERE = Path(output).resolve().parent
    HERE.mkdir(parents=True, exist_ok=True)
    for name, record in json.loads((ROOT/'config/tools.json').read_text())['boot_tools'].items():
        if sha(TOOLS/name) != record['sha256']:
            raise ValueError('Boot-tool digest mismatch: ' + name)
    spec = importlib.util.spec_from_file_location('avbtool', TOOLS/'avbtool.py')
    avb = importlib.util.module_from_spec(spec); spec.loader.exec_module(avb)

def sha(path):
    with Path(path).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def run(*args):
    return subprocess.run([str(x) for x in args], check=True, capture_output=True, text=True).stdout


def parse(path):
    handler = avb.ImageHandler(str(path), read_only=True)
    return avb.Avb()._parse_image(handler)


def properties(descriptors):
    return [(d.key, d.value.decode()) for d in descriptors if isinstance(d, avb.AvbPropertyDescriptor)]


def hash_descriptor(descriptors):
    entries = [d for d in descriptors if isinstance(d, avb.AvbHashDescriptor) and d.partition_name == 'boot']
    assert len(entries) == 1, 'Expected exactly one boot hash descriptor'
    return entries[0]


def validate(image, payload, raw_kernel, original, original_footer, original_header, original_descriptors, preserve_original_trailer=False):
    data = image.read_bytes()
    footer, header, descriptors, size = parse(image)
    baseline = hash_descriptor(original_descriptors)
    desc = hash_descriptor(descriptors)
    assert size == len(original) == 67108864
    assert data[:8] == b'ANDROID!'
    # Every original header byte is preserved except the kernel length.
    assert data[:8] + data[12:4096] == original[:8] + original[12:4096]
    kernel_size = struct.unpack_from('<I', data, 8)[0]
    assert kernel_size == payload.stat().st_size
    assert data[4096:4096 + kernel_size] == payload.read_bytes()
    assert gzip.decompress(data[4096:4096 + kernel_size]) == raw_kernel.read_bytes()
    assert footer and footer.version_major == original_footer.version_major
    assert footer.version_minor == original_footer.version_minor
    assert footer.vbmeta_offset >= baseline.image_size
    assert footer.original_image_size == desc.image_size == footer.vbmeta_offset
    assert footer.vbmeta_offset % 4096 == 0
    assert 4096 + kernel_size <= desc.image_size
    assert footer.vbmeta_offset + footer.vbmeta_size <= size - 64
    payload_end = (4096 + kernel_size + 4095) // 4096 * 4096
    assert not any(data[4096 + kernel_size:payload_end])
    if preserve_original_trailer:
        assert data[payload_end:footer.vbmeta_offset] == original[payload_end:original_footer.vbmeta_offset]
    else:
        assert not any(data[payload_end:footer.vbmeta_offset])
    assert not any(data[footer.vbmeta_offset + footer.vbmeta_size:-64])
    assert desc.hash_algorithm == baseline.hash_algorithm == 'sha256'
    assert desc.flags == baseline.flags == 0
    assert desc.salt == baseline.salt
    assert hashlib.sha256(desc.salt + data[:desc.image_size]).digest() == desc.digest
    assert properties(descriptors) == properties(original_descriptors)
    assert len(descriptors) == len(original_descriptors)
    for attr in ('algorithm_type', 'rollback_index', 'rollback_index_location', 'flags',
                 'required_libavb_version_major', 'required_libavb_version_minor'):
        assert getattr(header, attr) == getattr(original_header, attr), attr
    assert header.algorithm_type == 0  # NONE, just like the original boot footer.
    # Independent official verifier validates the embedded AVB hash descriptor.
    # avbtool resolves the hash descriptor by partition name (boot.img).
    with tempfile.TemporaryDirectory(dir=HERE) as temporary:
        named_image = Path(temporary) / 'boot.img'
        named_image.symlink_to(image)
        output = run(sys.executable, TOOLS / 'avbtool.py', 'verify_image', '--image', named_image)
    (HERE / (image.stem + '.avb-verification.txt')).write_text(output)
    unpack_dir = HERE / 'unpacked' / image.stem
    run(sys.executable, TOOLS / 'unpack_bootimg.py', '--boot_img', image, '--out', unpack_dir)
    assert sha(unpack_dir / 'kernel') == sha(payload)
    return {'sha256': sha(image), 'size': size, 'kernel_gzip_sha256': sha(payload),
            'kernel_Image_sha256': sha(raw_kernel), 'header_version': 4,
            'ramdisk_size': 0, 'boot_signature_size': 0,
            'avb_algorithm': 'NONE', 'avb_hash_verified': True,
            'vbmeta_offset': footer.vbmeta_offset, 'hashed_image_size': desc.image_size,
            'original_header_preserved_except_kernel_size': True,
            'original_appended_signature_trailer_preserved': preserve_original_trailer,
            'original_avb_properties_preserved_including_duplicates': True,
            'matches_original_top_level_vbmeta_hash': desc.digest == baseline.digest}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--original',type=Path,required=True)
    p.add_argument('--kernel-dir',type=Path,required=True)
    p.add_argument('--compat-report',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args(); image=a.output.resolve()
    if image.exists() or image.with_suffix('.json').exists():
        raise ValueError('Output already exists')
    configure(image)
    report=json.loads(a.compat_report.read_text())
    assert report['offline_checks_passed'] and report['module_files']==399
    payload=a.kernel_dir/'Image.gz'; raw=a.kernel_dir/'Image'
    hashes={l.split()[1]:l.split()[0] for l in (a.kernel_dir/'SHA256SUMS').read_text().splitlines()}
    assert sha(payload)==hashes['Image.gz'] and sha(raw)==hashes['Image']==report['Image_sha256']
    original=a.original.read_bytes()
    footer,header,descriptors,size=parse(a.original)
    assert len(original)==size==67108864 and header.algorithm_type==0
    assert struct.unpack_from('<I',original,40)[0]==4
    assert struct.unpack_from('<I',original,12)[0]==0
    assert struct.unpack_from('<I',original,1580)[0]==0
    desc=hash_descriptor(descriptors)
    run(sys.executable,TOOLS/'mkbootimg.py','--header_version','4','--cmdline','',
        '--kernel',payload,'--output',image)
    with image.open('r+b') as f:f.truncate(max(image.stat().st_size,desc.image_size))
    args=[sys.executable,TOOLS/'avbtool.py','add_hash_footer','--image',image,
          '--partition_name','boot','--partition_size',str(size),'--hash_algorithm',desc.hash_algorithm,
          '--salt',desc.salt.hex(),'--algorithm','NONE','--rollback_index',str(header.rollback_index),
          '--rollback_index_location',str(header.rollback_index_location),'--flags',str(header.flags)]
    for k,v in properties(descriptors):args+=['--prop',k+':'+v]
    run(*args)
    result=validate(image,payload,raw,original,footer,header,descriptors)
    result['original_boot_sha256']=sha(a.original)
    image.with_suffix('.json').write_text(json.dumps(result,indent=2)+'\n')
    print('Offline boot image validated; no phone accessed:',result['sha256'])

if __name__=='__main__':main()
