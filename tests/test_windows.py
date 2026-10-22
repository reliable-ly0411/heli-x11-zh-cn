import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import windows_patch as w


class WindowsTests(unittest.TestCase):
    def test_crlf_launcher_restores_exactly_and_rejects_double_patch(self):
        original=b'@echo off\r\n'+w.ANCHOR+b'\r\njava -classpath %jars% HELIX\r\n'
        changed=w.patch_launcher(original)
        self.assertEqual(changed.replace(w.block(b'\r\n'),b''), original)
        with self.assertRaises(ValueError): w.patch_launcher(changed)
        with self.assertRaises(ValueError): w.patch_launcher(b'custom launcher')

    def test_uninstall_rejects_damaged_backup(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);s=root/w.STATE_DIR;s.mkdir()
            launcher=b'prefix\r\n'+w.block(b'\r\n')+b'suffix\r\n'
            (root/w.LAUNCHERS[0]).write_bytes(launcher)
            owned={}
            for name in (w.core.FLAG, f'{w.STATE_DIR}/guard.ps1', f'{w.STATE_DIR}/guard.json', f'{w.STATE_DIR}/Chinese.jar'):
                p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b'owned');owned[name]=w.core.digest(b'owned')
            state={'launchers':[w.LAUNCHERS[0]], 'owned':owned, 'backup':{w.LAUNCHERS[0]:'bad'}}
            with self.assertRaisesRegex(ValueError,'备份损坏'):w.check_owned(root,root,state)
            self.assertEqual((root/w.LAUNCHERS[0]).read_bytes(),launcher)

if __name__=='__main__':unittest.main()
