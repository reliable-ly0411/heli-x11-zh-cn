"""Private Windows fixture test: split roots, mocked registry, actual filesystem/runtime."""
from pathlib import Path
import json
import sys
import zipfile
from unittest.mock import patch

payload, fixture, base = map(Path, sys.argv[1:])
sys.path.insert(0, str(payload))
import windows_patch as w
import winreg

exe, data = base/'程序', base/'数据'
exe.mkdir(parents=True);data.mkdir()
with zipfile.ZipFile(fixture) as z:
    for name in z.namelist():
        target = (exe if name in w.LAUNCHERS else data)/name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(z.read(name))
originals = {p:p.read_bytes() for root in (exe,data) for p in root.rglob('*') if p.is_file()}
# Exercise registry selection logic without changing the machine's HELI-X installation.
class Key:
    def __enter__(self): return self
    def __exit__(self,*args): pass
with patch.object(winreg,'OpenKey',return_value=Key()), patch.object(winreg,'QueryValueEx',side_effect=lambda k,n:(str(data if n=='Path' else exe),winreg.REG_SZ)):
    assert w.resolve_roots(exe)==(data.resolve(),exe.resolve())
    assert w.resolve_roots(data)==(data.resolve(),exe.resolve())
    w.install(exe)
    w.core.verify_jar(data,data/w.STATE_DIR/'Chinese.jar',spec=w.spec())
    w.uninstall(data)
for p, original in originals.items(): assert p.read_bytes()==original,p
print('PASS split-root install/verify/uninstall and matching registry selection (registry mocked)')
