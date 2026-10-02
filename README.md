# HELI-X 11 简体中文汉化补丁

面向 **HELI-X 11.0.2681 Linux 版**的独立简体中文界面补丁。仓库用于分享和维护中文译文、中文位图字体生成代码，以及可备份、可校验、可卸载的部署工具。

仓库只提供补丁源文件。安装时读取你本机已有的 HELI-X 文件，生成中文覆盖包；不包含模拟器本体、Java 运行环境、模型、场景、激活码或个人配置。请先自行安装 [官方 HELI-X](https://www.heli-x.info/)。这是非官方社区汉化项目。

## 汉化范围

- 覆盖原英文语言包的 **1,272 个键**，另外增加中文语言名称，共 1,273 个条目。
- 补齐 **38 个界面类**的固定显示文字，包括舵量、指数、死区、前馈系数、语言选择和部分下载提示。
- 为 **13 组位图字体**补齐译文所需的中文与标点，保留原拉丁字符度量和行高，适配原按钮与窗口布局。
- 提供“选项 → 语言 → 简体中文”入口，安装后默认使用中文。

品牌、设备名、模型名、标准缩写和单位按原意保留；官方 PDF、许可正文、外部网站和模型作者说明不在此补丁的翻译范围内。部分非核心说明仍可能是英文。固定标签补丁始终显示中文；要完全恢复原始界面，请卸载补丁。

## 适配版本

目前仅验证 **Linux / HELI-X 11.0.2681**。部署前会同时校验主程序、语言包和字体资源的 SHA-256，具体值在 [`data/compatibility.json`](data/compatibility.json)。版本不同会拒绝安装。

Windows、macOS 以及其他 HELI-X 构建尚未适配。不要通过更改校验值强行安装；固定标签需要针对新版本重新核对。

## 部署方式

### 1. 准备依赖并下载仓库

Ubuntu / Debian：

```bash
sudo apt update
sudo apt install git python3 python3-pil fonts-noto-cjk

git clone https://github.com/reliable-ly0411/heli-x11-zh-cn.git
cd heli-x11-zh-cn
```

其他 Linux 发行版需要 Python 3.10+、Pillow 10.2+ 和 Noto Sans CJK 简体中文字体。也可在虚拟环境中安装 Python 依赖：

```bash
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -r requirements.txt
```

### 2. 检查版本

将下面的路径改为你自己的 HELI-X 安装目录。路径含空格也可以使用，请保留引号。

```bash
python3 patch.py check --helix-dir "$HOME/Downloads/HELI-X11"
```

### 3. 关闭 HELI-X 并安装

```bash
python3 patch.py install --helix-dir "$HOME/Downloads/HELI-X11"
python3 patch.py verify --helix-dir "$HOME/Downloads/HELI-X11"
```

**无需使用 sudo 运行安装脚本**，只需当前用户对 HELI-X 安装目录有写权限。生成字体通常需要数秒至数十秒。

默认字体路径：`/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc`，字体集合索引为 `2`（简体中文）。字体位置不同时可指定：

```bash
python3 patch.py install --helix-dir "/path/to/HELI-X11" \
  --font "/path/to/NotoSansCJK-Regular.ttc" --font-index 2
```

如使用独立的简体中文 TTF/OTF 字体文件，通常应指定 `--font-index 0`；使用其他字体后需自行检查文字排版。

### 4. 启动

```bash
bash "$HOME/Downloads/HELI-X11/runHELI-X.sh"
```

继续使用原来的 `runHELI-X.sh` 即可。通过其他方式直接调用 Java 可能绕过汉化加载步骤。

### 已安装早期手工版补丁的用户

如果启动脚本中已有 `localization/Chinese.jar`，新安装器会停止，以避免重复加载。请先关闭 HELI-X，在其目录执行早期补丁自带的恢复脚本：

```bash
cd "$HOME/Downloads/HELI-X11"
python3 localization/restore.py
```

然后回到本仓库，执行新的安装命令。此迁移只适用于带有上述恢复脚本的早期手工版；请保留旧备份。

## 安装器会修改什么

| 路径（相对于 HELI-X 目录） | 用途 |
| --- | --- |
| `.helix-zh-cn/Chinese.jar` | 安装时在本机生成的中文界面、字体与标签覆盖包 |
| `.helix-zh-cn/compatibility.sha256` | 启动时检查原版资源是否变化 |
| `.helix-zh-cn/backup/` | 首次安装前的文件备份，只保存在本机 |
| `.helix-zh-cn/state.json` | 用于重复安装和卸载的状态记录 |
| `runHELI-X.sh` | 插入带版本校验的覆盖包加载段；兼容含空格的安装路径 |
| `files/Application/ApplicationSettings.xml` | 只将语言与地区切换为 `zh` / `CN` |
| `resources/miscellaneous/languages.txt` | 加入中文语言入口 |
| `resources/miscellaneous/images/flag_zh.jpg` | 中文入口图标 |

原版 JAR 和字体压缩包不会被改写；控制器、飞行参数及其他配置不做调整。重复执行安装会更新补丁，但不会覆盖首次安装备份。

官方更新若替换了受校验的资源，启动器会自动停用不兼容的旧补丁，并在终端显示提示。重新适配前不会让旧界面代码覆盖新版。

## 卸载与恢复

关闭 HELI-X 后执行：

```bash
python3 patch.py uninstall --helix-dir "$HOME/Downloads/HELI-X11"
```

卸载会移除补丁加载段、撤回新增语言入口和图标。当前仍为中文时恢复安装前的语言；其他最新设置保持不变。原始备份与生成文件保留在 `.helix-zh-cn/`，不会被删除。

卸载后再次安装前，请先把 `.helix-zh-cn/` 移到另一个备份名称，以便新一轮安装单独保存当时的设置。

## 只构建，不安装

```bash
python3 patch.py build --helix-dir "/path/to/HELI-X11" --output ./build
```

此命令只读取模拟器目录，并在 `build/` 输出覆盖包和验证报告。构建产物依赖本机原版文件，默认被 Git 忽略，不随仓库发布。

## 翻译维护与验证

- [`data/zh-CN.json`](data/zh-CN.json)：可直接维护的中文译文。
- [`data/label-patches.json`](data/label-patches.json)：按界面类划分的固定标签白名单。
- [`patch.py`](patch.py)：版本检查、构建、安装、验证和卸载。
- [`font_atlas.py`](font_atlas.py)：本机扩展 BMFont 图集。

关键术语：Collective Pitch 为“总距”，Elevator/Nick 为“升降/俯仰”，Aileron/Roll 为“副翼/横滚”，Autorotation 为“熄火降落”，Expo 为“指数”，Dead Band 为“死区”。Promenade 为“绕机行走训练”，No Collective 为“锁高无总距训练”。训练功能释义参考 [HELI-X 11 官方手册](https://www.heli-x.info/help11/UsersManualV11.pdf)。

不依赖模拟器的单元测试：

```bash
python3 -m unittest discover -s tests -v
```

有本机原版文件时，可在临时副本上检查完整安装与恢复流程（不会修改传入的原目录）：

```bash
python3 tests/integration.py "/path/to/HELI-X11"
```

发布前已验证：全新安装、带空格路径、重复安装、备份保留、升级后自动停用、升级后卸载，以及保留安装后新增的其他配置。提取后构建的 JAR 内每一项内容均与原先实际检查过的本机补丁一致。此前在 1920×1018 窗口检查过菜单、控制器设置、智能按钮向导、飞行模式、悬停训练和语言选择页；未穷举所有窗口或真实遥控器功能。

## 第三方内容

本仓库不代表 HELI-X 官方，也不提供激活、授权绕过或完整软件分发。HELI-X 及其原版资源的权利属于各自权利人。安装器使用用户本机字体生成图集；Noto 字体的许可见其发行包。请遵守原软件及所用字体的许可条件。
