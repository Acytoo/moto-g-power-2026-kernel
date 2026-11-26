"""Offline comparison against private captures; no uploads or phone access."""
import argparse,hashlib,importlib.util,json,struct,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def module_exports(sec):
    table, strings = sec['.symtab'], sec['.strtab']
    result = set()
    for pos in range(0, len(table), 24):
        name_offset, info, _, index, _, _ = struct.unpack_from('<IBBHQQ', table, pos)
        # Kernel EXPORT_SYMBOL uses assembler labels (STT_NOTYPE), not only
        # C objects. Exclude section/function symbols and undefined entries.
        if info & 15 not in (0, 1) or not index:
            continue
        name = strings[name_offset:strings.index(b'\0', name_offset)].decode()
        if name.startswith('__ksymtab_'):
            result.add(name[len('__ksymtab_'):])
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--capture-root',type=Path,required=True)
    p.add_argument('--capture-manifest',type=Path,required=True)
    p.add_argument('--original-btf',type=Path,required=True)
    p.add_argument('--baseline-symvers',type=Path,required=True)
    p.add_argument('--candidate',type=Path,required=True)
    p.add_argument('--panel-module',type=Path)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    from btf import BTF,section,compatible_members
    compare=load('compare',ROOT/'scripts/compare.py')
    elf=load('modcrc',ROOT/'work/upstream/linux/tools/modcrc.py')
    hashes=json.loads(a.capture_manifest.read_text())
    assert len(hashes)==399,'Expected the complete 399-file vendor capture set for this firmware'
    imports={}; provided=set()
    for rel,h in hashes.items():
        path=(a.capture_root/rel).resolve()
        assert path.is_relative_to(a.capture_root.resolve()) and sha(path)==h
        sec=elf.sections(path); assert sec.get('__versions')
        imports[rel]=list(elf.versions(sec['__versions']))
        provided.update(module_exports(sec))
    exports=compare.exports(a.candidate/'Module.symvers')
    original=compare.exports(a.baseline_symvers)
    checked=module_provided=0; missing=[]; mismatch=[]
    for rel,requirements in imports.items():
        for name,crc in requirements:
            if name in exports:
                checked+=1
                if int(exports[name],16)!=crc:mismatch.append([rel,name])
            elif name in provided:module_provided+=1
            else:missing.append([rel,name])
    panel_count=0
    if a.panel_module:
        for name,crc in elf.versions(elf.sections(a.panel_module)['__versions']):
            panel_count+=1
            if name not in exports or int(exports[name],16)!=crc:mismatch.append(['panel',name])
        assert panel_count>0
    collisions=sorted((exports.keys()-original.keys())&provided)
    old_sizes=compare.sizes(compare.layout(a.original_btf))
    new_sizes=compare.sizes(compare.layout(a.candidate/'vmlinux'))
    common=old_sizes.keys()&new_sizes.keys()
    sizes=sorted(t for t in common if old_sizes[t]!=new_sizes[t])
    old,new=BTF(section(a.original_btf)),BTF(section(a.candidate/'vmlinux'))
    critical=['task_struct','mm_struct','file','inode','super_block','dentry','sk_buff',
              'net_device','device','module','cred','signal_struct','nsproxy',
              'pid_namespace','user_namespace','ipc_namespace','drm_panel']
    layouts=[t for t in critical if not compatible_members(old,new,t)]
    result=dict(module_files=len(imports),kernel_imports_checked=checked,
                imports_provided_by_original_modules=module_provided,
                panel_module_imports_checked=panel_count,crc_mismatches=mismatch,
                missing_imports=missing,new_kernel_exports_colliding_with_vendor_modules=collisions,
                common_struct_names_checked=len(common),changed_common_structure_sizes=sizes,
                changed_critical_member_layouts=layouts,Image_sha256=sha(a.candidate/'Image'),
                offline_checks_passed=not any([mismatch,missing,collisions,sizes,layouts]),
                hardware_tested=False)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(result,indent=2)+'\n'); a.output.chmod(0o600)
    print('Offline compatibility:', 'PASS' if result['offline_checks_passed'] else 'FAIL')
    if not result['offline_checks_passed']:raise SystemExit(1)

if __name__=='__main__':main()
