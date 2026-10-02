"""Run locally with an existing HELI-X installation; operates on a temp copy only."""
import importlib.util,json,shutil,subprocess,sys,tempfile
from pathlib import Path
repo=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(repo))
spec=importlib.util.spec_from_file_location('helix_patch',repo/'patch.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
source=Path(sys.argv[1]).resolve()
font=Path('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc')
with tempfile.TemporaryDirectory(prefix='helix-zh-integration-') as t:
    root=Path(t)/'HELI X with spaces';root.mkdir()
    for name in (m.MAIN,m.TRANSLATION,m.STYLES):
        p=root/name;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source/name,p)
    # Use the preserved clean files when validating extraction from the old local patch.
    for name in (m.LAUNCHER,m.SETTINGS,m.LANGUAGES):
        candidate=source/'localization/backup-original'/name
        p=root/name;p.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(candidate if candidate.exists() else source/name,p)
    originals={n:(root/n).read_bytes() for n in (m.LAUNCHER,m.SETTINGS,m.LANGUAGES)}
    m.install(root,font,2)
    m.verify_jar(root,root/m.STATE_DIR/'Chinese.jar')
    subprocess.run(['bash','-n',str(root/m.LAUNCHER)],check=True)
    first_backup=(root/m.STATE_DIR/'backup'/m.SETTINGS).read_bytes()
    m.install(root,font,2)
    assert (root/m.LAUNCHER).read_text().count(m.MARK_START)==1
    assert (root/m.STATE_DIR/'backup'/m.SETTINGS).read_bytes()==first_backup
    # The version guard must actually disable the overlay after a program update.
    guard=(root/m.STATE_DIR/'compatibility.sha256')
    assert subprocess.run(['sha256sum','--check','--status',str(guard)],cwd=root).returncode==0
    lib=root/m.MAIN;lib.write_bytes(lib.read_bytes()+b'changed')
    try:m.compatibility(root)
    except ValueError:pass
    else:raise AssertionError('incompatible version accepted')
    assert subprocess.run(['sha256sum','--check','--status',str(guard)],cwd=root).returncode!=0
    # Uninstall must work even after an update, and preserve unrelated user edits.
    p=root/m.SETTINGS;p.write_bytes(p.read_bytes().replace(b'</project>',b'<UserTest>keep</UserTest></project>'))
    m.uninstall(root)
    assert (root/m.LAUNCHER).read_bytes()==originals[m.LAUNCHER]
    assert (root/m.LANGUAGES).read_bytes()==originals[m.LANGUAGES]
    assert (root/m.SETTINGS).read_bytes()==originals[m.SETTINGS].replace(b'</project>',b'<UserTest>keep</UserTest></project>')
    assert not (root/m.FLAG).exists()
print('PASS: clean install, path with spaces, rebuild, backup retention, version guard, uninstall after upgrade, user-setting preservation')
