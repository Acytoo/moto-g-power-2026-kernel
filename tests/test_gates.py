import contextlib
import importlib.util
import io
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


def module(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts' / (name + '.py'))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


class Gates(unittest.TestCase):
    def test_missing_link_capabilities_remain_fatal(self):
        prepare = module('prepare')
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(io.StringIO()):
            p = Path(tmp)
            text = (ROOT / 'config/stock.config').read_text().replace(
                'CONFIG_CC_CAN_LINK=y', '# CONFIG_CC_CAN_LINK is not set')
            (p / 'config').write_text(text)
            with self.assertRaises(SystemExit):
                prepare.check('stock', p / 'config', p / 'report')

    def test_linux_acl_dependency_is_explicit_and_required(self):
        prepare = module('prepare')
        expected = prepare.config(ROOT / 'config/stock.config')
        expected.update(prepare.config(ROOT / 'config/linux.fragment'))
        self.assertEqual(expected['CONFIG_TMPFS_XATTR'], 'y')
        expected.pop('CONFIG_UNUSED_KSYMS_WHITELIST', None)
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(io.StringIO()):
            p = Path(tmp)
            (p / 'config').write_text('\n'.join(f'{k}={v}' for k, v in expected.items()))
            prepare.check('linux', p / 'config', p / 'report')
            expected['CONFIG_TMPFS_XATTR'] = 'n'
            (p / 'config').write_text('\n'.join(f'{k}={v}' for k, v in expected.items()))
            with self.assertRaises(SystemExit):
                prepare.check('linux', p / 'config', p / 'report')

    def test_stock_config_accepts_only_intended_features(self):
        prepare = module('prepare')
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(io.StringIO()):
            p = Path(tmp)
            prepare.check('stock', ROOT / 'config/stock.config', p / 'report')
            altered = (ROOT / 'config/stock.config').read_text().replace(
                '# CONFIG_FHANDLE is not set', 'CONFIG_FHANDLE=y')
            (p / 'config').write_text(altered)
            with self.assertRaises(SystemExit):
                prepare.check('stock', p / 'config', p / 'report')

    def test_missing_export_data_fails_closed(self):
        compare = module('compare')
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'Module.symvers'
            p.write_text('')
            with self.assertRaises(RuntimeError):
                compare.exports(p)

    def test_empty_btf_data_fails_closed(self):
        with self.assertRaises(RuntimeError):
            module('compare').sizes('')

    def test_private_key_rejected(self):
        payload = ('-----BEGIN ' + 'OPENSSH PRIVATE KEY-----').encode()
        with self.assertRaises(ValueError):
            module('audit').check_content('fixture.txt', payload)

    def test_binary_capture_rejected(self):
        with self.assertRaises(ValueError):
            module('audit').check_content('fixture.txt', b'capture\x00')


if __name__ == '__main__':
    unittest.main()
