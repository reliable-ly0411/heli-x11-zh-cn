"""Unit tests use synthetic class data and never require the simulator."""
import importlib.util
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch as mock_patch

spec = importlib.util.spec_from_file_location('helix_patch', Path(__file__).parents[1]/'patch.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class PatchTests(unittest.TestCase):
    def test_class_string_change_preserves_bytecode_and_other_keys(self):
        def utf(s):
            b=s.encode();return b'\x01'+struct.pack('>H',len(b))+b
        header=b'\xca\xfe\xba\xbe\x00\x00\x00\x3d\x00\x03'
        tail=b'\x00\x21\x00\x01UNTOUCHED_BYTECODE'
        source=header+utf('Dead Band')+utf('NickExpo')+tail
        changed=mod.replace_labels(source,{'Dead Band':'死区'})
        entries,end=mod.constants(changed)
        self.assertEqual([s for _,_,s in entries],['死区','NickExpo'])
        self.assertEqual(changed[end:],tail)
        with self.assertRaises(ValueError):mod.replace_labels(source,{'Missing':'缺少'})

    def test_properties_keep_line_breaks_and_escape_literals(self):
        self.assertEqual(mod.property_value('确定\\n下一步'),
                         '\\u786e\\u5b9a\\n\\u4e0b\\u4e00\\u6b65')
        self.assertEqual(mod.property_value('C:\\test'), 'C:\\\\test')

    def test_config_preserves_unrelated_fields_and_line_endings(self):
        source=b'<project>\r\n<Language>en</Language>\r\n<Country>US</Country>\r\n<Port>1234</Port>\r\n</project>'
        changed=mod.set_tag(mod.set_tag(source,'Language','zh'),'Country','CN')
        reverted=mod.set_tag(mod.set_tag(changed,'Language','en'),'Country','US')
        self.assertEqual(source,reverted)
        with self.assertRaises(ValueError):mod.set_tag(source,'Missing','x')

    def test_failed_write_rolls_back_earlier_changes(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);(root/'a').write_bytes(b'old');real=mod.atomic_write
            def fail(path,data):
                if path.name=='b':raise OSError('simulated disk failure')
                return real(path,data)
            with mock_patch.object(mod,'atomic_write',side_effect=fail):
                with self.assertRaises(OSError):mod.apply_files(root,{'a':b'new','b':b'new'})
            self.assertEqual((root/'a').read_bytes(),b'old')
            self.assertFalse((root/'b').exists())


if __name__=='__main__':unittest.main()
