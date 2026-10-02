#!/usr/bin/env python3
"""Build and install the HELI-X 11 Chinese overlay from a local installation."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import struct
import sys
import tempfile
import zipfile

HERE = Path(__file__).resolve().parent
STATE_DIR = '.helix-zh-cn'
LAUNCHER = 'runHELI-X.sh'
SETTINGS = 'files/Application/ApplicationSettings.xml'
LANGUAGES = 'resources/miscellaneous/languages.txt'
FLAG = 'resources/miscellaneous/images/flag_zh.jpg'
MAIN = 'libs/HeliX/HeliX11.jar'
TRANSLATION = 'libs/HeliX/Translation.jar'
STYLES = 'libs/jme/styles.zip'
MARK_START = '# BEGIN HELI-X standalone Chinese patch'
MARK_END = '# END HELI-X standalone Chinese patch'
ANCHOR = 'CP="$CP:$JARPATH/HeliX/HeliX11.jar"'
OLD_CD = 'cd $( dirname $0 )'
NEW_CD = 'cd -- "$(dirname -- "$0")" || exit 1'
ZH_LINE = b'zh CN \\u7b80\\u4f53\\u4e2d\\u6587'


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def digest(data):
    return hashlib.sha256(data).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def compatibility(root):
    spec = read_json(HERE / 'data/compatibility.json')
    for name, expected in spec['sha256'].items():
        p = root / name
        require(p.is_file(), f'缺少文件：{p}')
        require(digest(p.read_bytes()) == expected,
                f'版本不兼容：{name}。此补丁仅适用于 HELI-X {spec["version"]} 的指定构建。')
    return spec


def ensure_stopped(root):
    # Only processes belonging to this exact installation are relevant.
    if not Path('/proc').is_dir():
        return
    for p in Path('/proc').glob('[0-9]*'):
        try:
            args = (p / 'cmdline').read_bytes().split(b'\0')
            if b'HELIX' in args and (p / 'cwd').resolve() == root:
                raise ValueError('请先关闭此目录中正在运行的 HELI-X。')
        except (OSError, RuntimeError):
            continue


def constants(b):
    """Return UTF-8 pool entries without interpreting or changing bytecode."""
    require(b[:4] == b'\xca\xfe\xba\xbe', '无效的 Java class')
    i, j = 10, 1
    count = struct.unpack('>H', b[8:10])[0]
    values = []
    sizes = {3:4, 4:4, 7:2, 8:2, 9:4, 10:4, 11:4, 12:4,
             15:3, 16:2, 17:4, 18:4, 19:2, 20:2}
    while j < count:
        start, tag = i, b[i]
        i += 1
        if tag == 1:
            size = struct.unpack('>H', b[i:i+2])[0]
            i += 2
            values.append((start, i+size, b[i:i+size].decode('utf-8', 'surrogateescape')))
            i += size
        elif tag in (5, 6):
            i += 8
            j += 1
        else:
            i += sizes[tag]
        j += 1
    return values, i


def replace_labels(original, mapping):
    entries, _ = constants(original)
    result, last, seen = bytearray(), 0, set()
    for start, end, text in entries:
        if text not in mapping:
            continue
        value = mapping[text].encode('utf-8')
        result += original[last:start] + b'\x01' + struct.pack('>H', len(value)) + value
        last = end
        seen.add(text)
    result += original[last:]
    require(seen == set(mapping), '固定界面标签与当前版本不匹配')
    return bytes(result)


def bundle_keys(root):
    with zipfile.ZipFile(root / TRANSLATION) as z:
        text = z.read('Translation/MessagesBundle_en_US.properties').decode('latin1')
    # This version has single-line key=value entries (escaped \\n stays in values).
    return {line.split('=', 1)[0] for line in text.splitlines()
            if line and not line.startswith(('#', '!')) and '=' in line}


def property_value(text):
    # Existing translation JSON uses literal \\n for intentional line breaks.
    text = text.replace('\\n', '\n')
    result = []
    for c in text:
        if c == '\\': result.append('\\\\')
        elif c == '\n': result.append('\\n')
        elif c == '\r': result.append('\\r')
        elif c == '\t': result.append('\\t')
        elif ord(c) > 127:
            raw = c.encode('utf-16-be')
            result.extend('\\u' + raw[i:i+2].hex() for i in range(0, len(raw), 2))
        else: result.append(c)
    return ''.join(result)


def payload():
    zh = read_json(HERE / 'data/zh-CN.json')
    labels = read_json(HERE / 'data/label-patches.json')
    return zh, labels


def build(root, output, font, font_index):
    spec = compatibility(root)
    require(font.is_file(), f'找不到字体：{font}；请安装 fonts-noto-cjk 或使用 --font。')
    zh, labels = payload()
    missing = bundle_keys(root) - zh.keys()
    require(not missing, f'缺少译文：{sorted(missing)}')
    chars = sorted({ord(c) for v in list(zh.values()) +
                    [v for d in labels.values() for v in d.values()] for c in v if ord(c) > 127}
                   | set(map(ord, '简体中文中文汉化')))
    properties = '\n'.join(k + '=' + property_value(v) for k, v in zh.items()) + '\n'
    output.mkdir(parents=True, exist_ok=True)
    from font_atlas import add_fonts
    with tempfile.TemporaryDirectory(prefix='helix-zh-build-') as tmp:
        jar = Path(tmp) / 'Chinese.jar'
        with zipfile.ZipFile(jar, 'w', zipfile.ZIP_DEFLATED) as z:
            for suffix in ('zh', 'zh_CN'):
                z.writestr(f'Translation/MessagesBundle_{suffix}.properties', properties)
            with zipfile.ZipFile(root / MAIN) as original:
                for name, mapping in labels.items():
                    z.writestr(name, replace_labels(original.read(name), mapping))
            fonts = add_fonts(z, root, chars, str(font), font_index)
        report = verify_jar(root, jar)
        shutil.copy2(jar, output / 'Chinese.jar')
    sums = ''.join(f'{h}  {n}\n' for n, h in spec['sha256'].items())
    (output / 'compatibility.sha256').write_text(sums, encoding='ascii')
    (output / 'font-report.json').write_text(json.dumps(fonts, indent=2) + '\n')
    (output / 'verification.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


def verify_jar(root, jar):
    compatibility(root)
    zh, labels = payload()
    chars = {ord(c) for v in list(zh.values()) + [v for m in labels.values() for v in m.values()]
             for c in v if ord(c) > 127}
    fonts = 0
    with zipfile.ZipFile(jar) as z, zipfile.ZipFile(root / MAIN) as original, \
            zipfile.ZipFile(root / STYLES) as styles:
        require(z.testzip() is None, 'JAR 完整性检查失败')
        resources = set(z.namelist()) | set(original.namelist()) | set(styles.namelist())
        expected = '\n'.join(k + '=' + property_value(v) for k,v in zh.items()) + '\n'
        require(z.read('Translation/MessagesBundle_zh_CN.properties').decode('ascii') == expected,
                '译文内容不匹配')
        for name in z.namelist():
            if not name.endswith('.fnt'): continue
            text = z.read(name).decode('utf-8')
            ids = set(map(int, re.findall(r'^char id=(-?\d+)', text, re.M)))
            require(chars <= ids, f'字体缺字：{name}')
            for image in re.findall(r'^page .*file="([^"]+)"', text, re.M):
                require(str(Path(name).parent / image) in resources, f'缺少图集：{image}')
            fonts += 1
        for name, changes in labels.items():
            before, after = original.read(name), z.read(name)
            old, end_old = constants(before)
            new, end_new = constants(after)
            require(before[:10] == after[:10] and before[end_old:] == after[end_new:],
                    f'程序指令发生变化：{name}')
            require(len(old) == len(new) and all(t == changes.get(s, s)
                    for (_, _, s), (_, _, t) in zip(old, new)), f'标签替换异常：{name}')
        require(fonts == 13, '字体资源数量异常')
    return {'version':'11.0.2681', 'bundleKeys':len(bundle_keys(root)),
            'translatedKeys':len(zh), 'fonts':fonts, 'displayClasses':len(labels),
            'fontCoverage':'PASS', 'classBytecodePreserved':'PASS', 'jarCRC':'PASS'}


def launcher_block():
    return f'''{MARK_START}
if [ -f "$PWD/{STATE_DIR}/Chinese.jar" ] && [ -f "$PWD/{STATE_DIR}/compatibility.sha256" ]; then
   if (cd "$PWD" && sha256sum --check --status "{STATE_DIR}/compatibility.sha256"); then
      CP="$PWD/{STATE_DIR}/Chinese.jar:$CP"
   else
      echo "HELI-X version changed; incompatible Chinese patch disabled." >&2
   fi
fi
{MARK_END}
'''


def get_tag(data, tag):
    m = re.search(rb'<' + tag.encode() + rb'>([^<]*)</' + tag.encode() + rb'>', data)
    require(m is not None, f'配置缺少 {tag}')
    return m.group(1).decode('utf-8')


def set_tag(data, tag, value):
    get_tag(data, tag)
    return re.sub(rb'<' + tag.encode() + rb'>[^<]*</' + tag.encode() + rb'>',
                  lambda _: f'<{tag}>{value}</{tag}>'.encode('utf-8'), data)


def atomic_write(path, data):
    mode = path.stat().st_mode & 0o777 if path.exists() else 0o644
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix='.helix-zh-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as f: f.write(data)
        os.chmod(tmp, mode)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp): os.unlink(tmp)


def apply_files(root, updates):
    originals = {name:(root/name).read_bytes() if (root/name).exists() else None for name in updates}
    done = []
    try:
        for name, data in updates.items():
            if data is None: (root/name).unlink(missing_ok=True)
            else: atomic_write(root/name, data)
            done.append(name)
    except Exception:
        for name in reversed(done):
            if originals[name] is None: (root/name).unlink(missing_ok=True)
            else: atomic_write(root/name, originals[name])
        raise


def install(root, font, font_index):
    compatibility(root)
    ensure_stopped(root)
    launcher = (root / LAUNCHER).read_text()
    require('localization/Chinese.jar' not in launcher,
            '检测到旧版手工补丁；请先关闭软件并运行旧版 localization/restore.py。')
    require(launcher.count(ANCHOR) == 1, '启动脚本结构不匹配，未修改任何文件。')
    state_dir = root / STATE_DIR
    state_file = state_dir / 'state.json'
    settings = (root / SETTINGS).read_bytes()
    languages = (root / LANGUAGES).read_bytes()
    if state_file.exists():
        state = read_json(state_file)
        require(state.get('format') == 1 and state.get('active'), '安装状态不匹配')
        require(launcher.count(launcher_block()) == 1, '汉化启动块被修改，请先恢复后再安装。')
    else:
        require(MARK_START not in launcher, '存在无状态记录的汉化启动块，请人工核对。')
        require(not state_dir.exists(), f'{STATE_DIR} 已存在但缺少安装状态，请先保留并移走该目录。')
        state = {'format':1, 'active':True,
                 'originalLanguage':get_tag(settings,'Language'),
                 'originalCountry':get_tag(settings,'Country'),
                 'cdChanged':OLD_CD in launcher,
                 'languageAdded':not re.search(rb'^zh\s+CN\b', languages, re.M)}
    new_launcher = launcher
    if MARK_START not in launcher:
        new_launcher = launcher.replace(ANCHOR + '\n', ANCHOR + '\n' + launcher_block())
    new_launcher = new_launcher.replace(OLD_CD, NEW_CD)
    require(launcher_block() in new_launcher, '无法插入启动块')
    new_languages = languages
    if state['languageAdded'] and not re.search(rb'^zh\s+CN\b', languages, re.M):
        new_languages += (b'' if languages.endswith(b'\n') else b'\n') + ZH_LINE + b'\n'
    new_settings = set_tag(set_tag(settings, 'Language', 'zh'), 'Country', 'CN')
    flag = (HERE/'assets/flag_zh.jpg').read_bytes()
    with tempfile.TemporaryDirectory(prefix='helix-zh-install-') as tmp:
        stage = Path(tmp)
        report = build(root, stage, font, font_index)
        updates = {LAUNCHER:new_launcher.encode(), SETTINGS:new_settings,
                   LANGUAGES:new_languages, FLAG:flag}
        for p in stage.iterdir(): updates[f'{STATE_DIR}/{p.name}'] = p.read_bytes()
        if not state_file.exists():
            backup = {}
            for n in (LAUNCHER,SETTINGS,LANGUAGES,FLAG):
                p = root/n
                backup[n] = digest(p.read_bytes()) if p.exists() else None
                if p.exists(): updates[f'{STATE_DIR}/backup/{n}'] = p.read_bytes()
            state['backup'] = backup
        state['flagSHA256'] = digest(flag)
        updates[f'{STATE_DIR}/state.json'] = (json.dumps(state,ensure_ascii=False,indent=2)+'\n').encode()
        apply_files(root, updates)
    print('安装成功。请运行原来的 runHELI-X.sh。')
    return report


def uninstall(root):
    ensure_stopped(root)
    state_dir = root/STATE_DIR
    state_file = state_dir/'state.json'
    require(state_file.is_file(), '未找到此安装器的状态记录，无需卸载。')
    state = read_json(state_file)
    require(state.get('active'), '补丁已停用。')
    launcher = (root/LAUNCHER).read_text()
    require(launcher.count(launcher_block()) == 1, '启动块被修改，请人工核对；未覆盖文件。')
    flag = root/FLAG
    require(flag.is_file() and digest(flag.read_bytes()) == state['flagSHA256'],
            '中文图标已被修改；未覆盖文件。')
    launcher = launcher.replace(launcher_block(), '')
    if state['cdChanged']: launcher = launcher.replace(NEW_CD, OLD_CD)
    settings = (root/SETTINGS).read_bytes()
    if get_tag(settings,'Language') == 'zh' and get_tag(settings,'Country') == 'CN':
        settings = set_tag(set_tag(settings,'Language',state['originalLanguage']),
                           'Country',state['originalCountry'])
    languages = (root/LANGUAGES).read_bytes()
    if state['languageAdded']:
        languages = re.sub(rb'^'+re.escape(ZH_LINE)+rb'\r?\n?', b'', languages, flags=re.M)
    old_flag = state_dir/'backup'/FLAG
    state['active'] = False
    updates = {LAUNCHER:launcher.encode(), SETTINGS:settings, LANGUAGES:languages,
               FLAG:old_flag.read_bytes() if old_flag.exists() else None,
               f'{STATE_DIR}/state.json':(json.dumps(state,ensure_ascii=False,indent=2)+'\n').encode()}
    apply_files(root, updates)
    print(f'汉化已停用；当前其他设置保留。原始备份仍在 {state_dir}/backup。')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['check','build','install','verify','uninstall'])
    parser.add_argument('--helix-dir', required=True, type=Path)
    parser.add_argument('--output', type=Path, default=HERE/'build')
    parser.add_argument('--font', type=Path,
                        default=Path('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'))
    parser.add_argument('--font-index', type=int, default=2, help='Noto CJK TTC 中简体中文为 2')
    args = parser.parse_args()
    root = args.helix_dir.expanduser().resolve()
    try:
        if args.command == 'check':
            spec = compatibility(root)
            print(f'兼容：HELI-X {spec["version"]}；三个输入文件 SHA-256 匹配。')
        elif args.command == 'build':
            print(json.dumps(build(root,args.output,args.font,args.font_index),indent=2))
        elif args.command == 'install':
            print(json.dumps(install(root,args.font,args.font_index),indent=2))
        elif args.command == 'verify':
            print(json.dumps(verify_jar(root,root/STATE_DIR/'Chinese.jar'),indent=2))
        else: uninstall(root)
    except (ValueError,OSError,KeyError,zipfile.BadZipFile,ImportError) as exc:
        print(f'错误：{exc}',file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
