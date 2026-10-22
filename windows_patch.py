"""Windows-specific installation adapter; Linux CLI/state format stay unchanged."""
import argparse
import base64
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import zipfile
import patch as core

HERE = Path(__file__).resolve().parent
STATE_DIR = '.helix-zh-cn-windows'
LAUNCHERS = ('runHELI-X.bat', 'runHELI-X_VR.bat', 'runHELI-X-local.bat', 'runHELI-X_VR-local.bat')
ANCHOR = b'set jars=%jars%;./libs/jSerial/jSerialComm-2.4.0.jar'
MARK = b'rem BEGIN HELI-X Chinese patch for Windows'
END = b'rem END HELI-X Chinese patch for Windows'


def spec():
    return core.read_json(HERE / 'data/compatibility-windows.json')


def resolve_roots(selected):
    """Match the selected root to the official two-directory registry layout."""
    selected = selected.resolve()
    if os.name == 'nt':
        import winreg
        for view in (winreg.KEY_WOW64_64KEY, winreg.KEY_WOW64_32KEY):
            try:
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r'Software\HELI-X\HELI-X11\Settings', 0, winreg.KEY_READ | view) as k:
                    data = Path(winreg.QueryValueEx(k, 'Path')[0]).resolve()
                    exe = Path(winreg.QueryValueEx(k, 'ExePath')[0]).resolve()
                if selected in (data, exe):
                    return data, exe
            except OSError:
                pass
    # Portable/test layout: the BAT launchers and libs live in the same directory.
    return selected, selected


def ensure_stopped(data, exe):
    if os.name != 'nt':
        return  # Cross-platform fixture tests only; production CLI requires Windows.
    env = dict(os.environ, HELIX_PATCH_DATA=str(data), HELIX_PATCH_EXE=str(exe))
    script = r'''$ErrorActionPreference='Stop'
$roots=@(($env:HELIX_PATCH_DATA.TrimEnd('\')+'\'),($env:HELIX_PATCH_EXE.TrimEnd('\')+'\'))
$names=@('java.exe','javaw.exe','HELI-X.exe','HELI-X_VR.exe')
foreach($p in (Get-CimInstance Win32_Process)) {
 if($names -contains $p.Name) {
  if(!$p.ExecutablePath -or !$p.CommandLine) { throw 'Cannot inspect a Java process. Close Java/HELI-X or run as administrator.' }
  foreach($root in $roots) {
   if($p.ExecutablePath.StartsWith($root,[StringComparison]::OrdinalIgnoreCase) -or $p.CommandLine.IndexOf($root,[StringComparison]::OrdinalIgnoreCase) -ge 0) { exit 3 }
  }
 }
}'''
    result = subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-EncodedCommand',
        base64.b64encode(script.encode('utf-16-le')).decode('ascii')], env=env,
        capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
    core.require(result.returncode == 0,
        '请先关闭此目录的 HELI-X。若仍失败，请关闭其他 Java 程序，或以管理员身份运行以检查进程。')


def block(newline):
    return newline.join((MARK,
        b'if exist ".\\.helix-zh-cn-windows\\guard.ps1" (',
        b'  powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File ".\\.helix-zh-cn-windows\\guard.ps1"',
        b'  if errorlevel 1 (',
        b'    echo HELI-X changed or patch check failed; Chinese patch disabled.',
        b'  ) else (',
        b'    set "jars=./.helix-zh-cn-windows/Chinese.jar;%jars%"',
        b'  )', b')', END)) + newline


def newline_of(content):
    return b'\r\n' if b'\r\n' in content else b'\n'


def patch_launcher(content):
    nl = newline_of(content)
    core.require(MARK not in content and END not in content, '检测到无状态记录的 Windows 汉化启动段。')
    core.require(b'Chinese.jar' not in content, '检测到其他汉化补丁，请先恢复原版启动脚本。')
    core.require(content.count(ANCHOR + nl) == 1, 'Windows 启动脚本结构不匹配。')
    # Keep all original bytes, including CRLF and update logic.
    result = content.replace(ANCHOR + nl, ANCHOR + nl + block(nl))
    return result


def validate(root):
    data, exe = resolve_roots(root)
    core.compatibility(data, spec())
    core.require(any((exe / n).is_file() for n in LAUNCHERS), '找不到官方 Windows BAT 启动脚本。请选择正确的程序目录。')
    core.require((data / core.SETTINGS).is_file(), '请先启动一次 HELI-X，正常退出后再安装汉化，以生成设置文件。')
    core.get_tag((data / core.SETTINGS).read_bytes(), 'Language')
    core.get_tag((data / core.SETTINGS).read_bytes(), 'Country')
    core.require((data / core.LANGUAGES).is_file(), '缺少语言列表。')
    return data, exe


def state_json(state):
    return (json.dumps(state, ensure_ascii=False, indent=2) + '\n').encode('utf-8')


def state_for(data, exe):
    state = core.read_json(data / STATE_DIR / 'state.json')
    core.require(state.get('format') == 1 and state.get('platform') == 'windows', 'Windows 补丁状态格式不匹配。')
    core.require(state.get('active'), '补丁已卸载。请保留备份并移走 .helix-zh-cn-windows 后再安装。')
    core.require(Path(state['exeRoot']).resolve() == exe, '程序目录已移动；请恢复原路径后卸载。')
    core.require(set(state['launchers']) <= set(LAUNCHERS) and state['launchers'], '启动器状态无效。')
    return state


def check_owned(data, exe, state):
    for name in state['launchers']:
        content = (exe / name).read_bytes()
        core.require(content.count(block(newline_of(content))) == 1, f'启动段被改动：{name}，未覆盖。')
    for name in (core.FLAG, f'{STATE_DIR}/guard.ps1', f'{STATE_DIR}/guard.json', f'{STATE_DIR}/Chinese.jar'):
        core.require((data / name).is_file() and core.digest((data / name).read_bytes()) == state['owned'][name],
                     f'补丁文件被改动：{name}，未覆盖。')
    for name, expected in state['backup'].items():
        core.require(name in (*LAUNCHERS, core.SETTINGS, core.LANGUAGES, core.FLAG), '备份名称无效。')
        if expected is not None:
            p = data / STATE_DIR / 'backup' / name
            core.require(p.is_file() and core.digest(p.read_bytes()) == expected, f'原始备份损坏：{name}。')


def install(selected):
    data, exe = validate(selected)
    ensure_stopped(data, exe)
    state_dir = data / STATE_DIR
    state_file = state_dir / 'state.json'
    settings = (data / core.SETTINGS).read_bytes()
    languages = (data / core.LANGUAGES).read_bytes()
    updates = {}
    if state_file.exists():
        state = state_for(data, exe)
        check_owned(data, exe, state)
    else:
        core.require(not state_dir.exists(), '补丁目录已存在但缺少状态记录，请保留并移走后重试。')
        state = {'format':1, 'platform':'windows', 'active':True, 'exeRoot':str(exe),
            'originalLanguage':core.get_tag(settings,'Language'), 'originalCountry':core.get_tag(settings,'Country'),
            'languageAdded':not re.search(rb'^zh\s+CN\b', languages, re.M), 'backup':{}, 'launchers':[]}
        for name in LAUNCHERS:
            if (exe / name).is_file():
                updates[exe / name] = patch_launcher((exe / name).read_bytes())
                state['launchers'].append(name)
        for name in (*state['launchers'], core.SETTINGS, core.LANGUAGES, core.FLAG):
            original = (exe if name in LAUNCHERS else data) / name
            state['backup'][name] = core.digest(original.read_bytes()) if original.exists() else None
            if original.exists():
                updates[state_dir / 'backup' / name] = original.read_bytes()
        # Store exact added separator so an originally unterminated list can be restored.
        state['languageSeparator'] = '' if languages.endswith(b'\n') else '\r\n'
    with tempfile.TemporaryDirectory(prefix='helix-win-build-') as tmp:
        stage = Path(tmp)
        report = core.build(data, stage, HERE / 'fonts/NotoSansCJK-Regular.ttc', 2, spec=spec())
        for p in stage.iterdir():
            updates[state_dir / p.name] = p.read_bytes()
        updates[state_dir / 'guard.ps1'] = (HERE / 'windows/guard.ps1').read_bytes()
        guard = dict(spec()['sha256'])
        guard[f'{STATE_DIR}/Chinese.jar'] = core.digest(updates[state_dir / 'Chinese.jar'])
        updates[state_dir / 'guard.json'] = state_json(guard)
        updates[data / core.FLAG] = (HERE / 'assets/flag_zh.jpg').read_bytes()
        state['owned'] = {n:core.digest(updates[data / n]) for n in
            (core.FLAG, f'{STATE_DIR}/guard.ps1', f'{STATE_DIR}/guard.json', f'{STATE_DIR}/Chinese.jar')}
        if state['languageAdded'] and not re.search(rb'^zh\s+CN\b', languages, re.M):
            languages += state['languageSeparator'].encode('ascii') + core.ZH_LINE + b'\r\n'
        updates[data / core.LANGUAGES] = languages
        updates[data / core.SETTINGS] = core.set_tag(core.set_tag(settings, 'Language', 'zh'), 'Country', 'CN')
        state['patchVersion'] = (HERE / 'VERSION').read_text().strip()
        updates[state_file] = state_json(state)
        try:
            core.apply_files(Path('.'), updates)
        except Exception:
            # apply_files restores bytes; remove only empty directories from a failed first install.
            if not state_file.exists() and state_dir.exists():
                for child in sorted(state_dir.rglob('*'), key=lambda p: len(p.parts), reverse=True):
                    if child.is_dir():
                        try: child.rmdir()
                        except OSError: pass
                try: state_dir.rmdir()
                except OSError: pass
            raise
    print('安装完成。请继续使用原来的 HELI-X 启动快捷方式或 BAT 文件。')
    print(f'程序目录：{exe}\n数据目录：{data}\n备份目录：{state_dir / "backup"}')
    return report


def uninstall(selected):
    data, exe = resolve_roots(selected)
    ensure_stopped(data, exe)
    state = state_for(data, exe)
    check_owned(data, exe, state)
    updates = {}
    for name in state['launchers']:
        content = (exe / name).read_bytes()
        updates[exe / name] = content.replace(block(newline_of(content)), b'')
    settings = (data / core.SETTINGS).read_bytes()
    if core.get_tag(settings, 'Language') == 'zh' and core.get_tag(settings, 'Country') == 'CN':
        settings = core.set_tag(core.set_tag(settings,'Language',state['originalLanguage']), 'Country',state['originalCountry'])
    updates[data / core.SETTINGS] = settings
    languages = (data / core.LANGUAGES).read_bytes()
    if state['languageAdded']:
        added = state['languageSeparator'].encode('ascii') + core.ZH_LINE + b'\r\n'
        if added in languages: languages = languages.replace(added, b'', 1)
        else: languages = re.sub(rb'^'+re.escape(core.ZH_LINE)+rb'\r?\n?', b'', languages, flags=re.M)
    updates[data / core.LANGUAGES] = languages
    updates[data / core.FLAG] = ((data / STATE_DIR / 'backup' / core.FLAG).read_bytes()
        if state['backup'][core.FLAG] is not None else None)
    state['active'] = False
    updates[data / STATE_DIR / 'state.json'] = state_json(state)
    core.apply_files(Path('.'), updates)
    print(f'汉化已卸载；其他设置保留。备份仍在 {data / STATE_DIR / "backup"}。')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['check','install','verify','uninstall'])
    parser.add_argument('--helix-dir', required=True, type=Path)
    args = parser.parse_args()
    try:
        core.require(os.name == 'nt', '此入口仅用于 Windows；Linux 请使用 patch.py。')
        selected = args.helix_dir.resolve()
        if args.command == 'check':
            data, exe = validate(selected)
            print(f'兼容：HELI-X {spec()["version"]} Windows x64\n程序目录：{exe}\n数据目录：{data}')
        elif args.command == 'install': print(json.dumps(install(selected), ensure_ascii=False, indent=2))
        elif args.command == 'uninstall': uninstall(selected)
        else:
            data, exe = validate(selected)
            check_owned(data, exe, state_for(data, exe))
            print(json.dumps(core.verify_jar(data, data / STATE_DIR / 'Chinese.jar', spec=spec()), indent=2))
        return 0
    except (OSError, ValueError, KeyError, ImportError, zipfile.BadZipFile) as e:
        print(f'操作未完成：{e}', file=sys.stderr)
        return 1


if __name__ == '__main__': sys.exit(main())
