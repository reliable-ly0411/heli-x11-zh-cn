"""Prepare a pinned offline Windows payload; compile with build.ps1 on Windows."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import re
import shutil
import subprocess
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache', type=Path, default=ROOT/'build/windows-cache')
    parser.add_argument('--output', type=Path, default=ROOT/'build/windows')
    args = parser.parse_args()
    args.cache.mkdir(parents=True, exist_ok=True)
    args.output.mkdir(parents=True, exist_ok=True)
    lock = json.loads((ROOT/'windows/dependencies.json').read_text())
    version = (ROOT/'VERSION').read_text().strip()
    match = re.fullmatch(r'(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-beta\.([1-9]\d*))?', version)
    if not match: raise ValueError('Expected X.Y.Z or X.Y.Z-beta.N')
    fields = [int(v) for v in match.groups()[:3]] + [int(match[4]) if match[4] else 65535]
    if max(fields) > 65535 or (match[4] and fields[3] >= 65535): raise ValueError('Windows version fields out of range')
    files = {}
    for item in lock['files']:
        p = args.cache/item['filename']
        if not p.exists():
            print('Downloading', item['filename'], flush=True)
            with urllib.request.urlopen(item['url'], timeout=120) as response:
                p.write_bytes(response.read())
        if hashlib.sha256(p.read_bytes()).hexdigest() != item['sha256']:
            raise ValueError('Dependency checksum mismatch: '+p.name)
        files[p.name] = p
    sha = subprocess.check_output(['git','rev-parse','HEAD'], cwd=ROOT, text=True).strip()
    dirty = bool(subprocess.check_output(['git','status','--porcelain'], cwd=ROOT, text=True).strip())
    info = {'version':version, 'sourceCommit':sha, 'workingTreeDirty':dirty, 'target':'windows-x64',
            'python':lock['python'], 'pillow':lock['pillow'], 'font':lock['font'], 'fileVersion':'.'.join(map(str,fields))}
    payload = {}
    for name in ('python-embed.zip', 'pillow-12.3.0-cp313-cp313-win_amd64.whl'):
        with zipfile.ZipFile(files[name]) as archive:
            for entry in archive.infolist():
                if not entry.is_dir(): payload[entry.filename] = archive.read(entry)
    source_names = ['patch.py','windows_patch.py','font_atlas.py','VERSION','README.md','windows/guard.ps1','windows/Noto-OFL.txt',
        'data/compatibility-windows.json','data/zh-CN.json','data/label-patches.json','assets/flag_zh.jpg']
    for name in source_names: payload[name] = (ROOT/name).read_bytes()
    payload['fonts/NotoSansCJK-Regular.ttc'] = files['NotoSansCJK-Regular.ttc'].read_bytes()
    payload['build-info.json'] = (json.dumps(info, indent=2)+'\n').encode()
    # Keep deterministic entry order, timestamps, and compression for identical inputs.
    with zipfile.ZipFile(args.output/'payload.zip', 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for name, data in sorted(payload.items()):
            entry = zipfile.ZipInfo(name, (2020,1,1,0,0,0));entry.compress_type=zipfile.ZIP_DEFLATED
            z.writestr(entry, data)
    for name in ('Installer.cs','app.manifest','build.ps1'):
        shutil.copyfile(ROOT/'windows'/name, args.output/name)
    (args.output/'AssemblyInfo.cs').write_text('using System.Reflection;\n'
        f'[assembly: AssemblyTitle("HELI-X 11 Chinese Patch")]\n[assembly: AssemblyVersion("{info["fileVersion"]}")]\n'
        f'[assembly: AssemblyFileVersion("{info["fileVersion"]}")]\n[assembly: AssemblyInformationalVersion("{version}")]\n', encoding='utf-8')
    (args.output/'build-info.json').write_text(json.dumps(info,indent=2)+'\n', encoding='utf-8')
    print(json.dumps(info,indent=2))
    print('Prepared:', args.output)


if __name__=='__main__': main()
