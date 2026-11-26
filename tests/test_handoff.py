import importlib.util
import json
from pathlib import Path
import tempfile
import subprocess
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def load(name, rel):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class HandoffGuards(unittest.TestCase):
    def test_subordinate_range_collision_rejected(self):
        mod = load('subids', 'runtime/docker/subids.py')
        with self.assertRaises(ValueError):
            mod.validate('alice:100000:65536\nbob:120000:65536\n', 'alice', 1000)
        with self.assertRaises(ValueError):
            mod.validate('alice:100000:65536\n', 'alice', 1000, [100001])
        with self.assertRaises(ValueError):
            mod.validate('alice:100000:100\n', 'alice', 1000)
        mod.validate('alice:100000:65536\nbob:200000:65536\n', 'alice', 1000, [1000])

    def test_private_profile_rejects_templates_and_loose_permissions(self):
        mod = load('phone', 'tools/phone.py')
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)/'device.json'
            p.write_bytes((ROOT/'examples/device.example.json').read_bytes())
            p.chmod(0o644)
            with self.assertRaises(ValueError): mod.profile(p)
            p.chmod(0o600)
            with self.assertRaises(ValueError): mod.profile(p)

    def test_gate_rejects_wrong_slot_before_any_flash(self):
        mod = load('phone', 'tools/phone.py')
        calls = []
        def fake_fb(p, action, name):
            calls.append(action)
            return name + ': ' + {'product':'vegas','sku':'XT2617V','current-slot':'b'}[name]
        with patch.object(mod, 'fb', fake_fb), self.assertRaises(ValueError):
            mod.gate(dict(product='vegas',sku='XT2617V',slot='a',boot_size=67108864))
        self.assertEqual(calls, ['getvar']*3)

    def test_gate_rejects_duplicate_or_missing_identity(self):
        mod = load('phone', 'tools/phone.py')
        for output in ('', 'product: vegas\nproduct: vegas\n'):
            with patch.object(mod, 'fb', return_value=output), self.assertRaises(ValueError):
                mod.gate(dict(product='vegas',sku='XT2617V',slot='a',boot_size=67108864))

    def test_tool_download_digest_mismatch_fails(self):
        from io import BytesIO
        mod = load('fetchtools', 'tools/fetch-tools.py')
        with patch.object(mod.urllib.request, 'urlopen', return_value=BytesIO(b'wrong')), self.assertRaises(ValueError):
            mod.download(dict(url='https://example.invalid/tool',sha256='0'*64))

    def test_audit_checks_staged_blob_not_clean_working_copy(self):
        mod = load('audit', 'scripts/audit.py')
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root/'config').mkdir()
            (root/'config/public-files.txt').write_text('config/public-files.txt\npayload.txt\n')
            (root/'payload.txt').write_text('-----BEGIN ' + 'OPENSSH PRIVATE KEY-----')
            subprocess.run(['git','init','-q',tmp],check=True)
            subprocess.run(['git','-C',tmp,'add','config/public-files.txt','payload.txt'],check=True)
            (root/'payload.txt').write_text('clean working copy')
            with patch.object(mod,'ROOT',root), patch.object(sys,'argv',['audit']), self.assertRaises(ValueError):
                mod.main()


if __name__ == '__main__': unittest.main()
