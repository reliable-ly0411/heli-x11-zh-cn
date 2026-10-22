# Windows x64 安装器构建

此目录构建**汉化补丁安装器**，不会捆绑 HELI-X。标准 Windows 10/11 的 .NET Framework 4.x 承载中文界面，隔离的 Python 运行时负责读取用户本机资源并生成覆盖包。运行安装器不需要网络或另装 Python。

## 构建

在含 Git 与 Python 3.10+ 的开发机器上执行：

```bash
python windows/prepare.py --cache ./build/windows-cache --output ./build/windows
```

依赖来源、固定版本、SHA-256 位于 `dependencies.json`。首次准备需要联网；文件已缓存且校验一致时可离线重建。不会调用系统 pip 或修改全局 Python。准备脚本可运行于 Linux 或 Windows。

将输出目录放到 Windows，使用系统编译器生成 EXE（示例在仓库根目录）：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\windows\build.ps1 -PreparedDirectory .\build\windows
```

`ExecutionPolicy Bypass` 仅用于本次构建进程，不修改系统策略。产物为 `setupHeli-X11-<VERSION>-win64-zh-CN.exe` 和 `SHA256SUMS`。

包内 `build-info.json` 记录源码提交、工作树是否干净、依赖与文件版本。正式发布使用干净提交构建，发布前校验 `VERSION`、标签、EXE 产品版本、文件版本和附件名一致。Windows 文件版本映射见仓库发布规范。内部 CLR 程序集标识固定为 `1.0.0.0`（不是对外发布版本），因为 CLR 程序集版本拒绝 `65535`；资源中的 FileVersion 与 ProductVersion 仍分别记录 PE 映射和完整 SemVer。

## 内容与许可

- 安装器源代码、译文、图标、兼容表和本地生成逻辑。
- Python 3.13.17 Windows embeddable package，完整 `LICENSE.txt` 随原包携带。
- Pillow 12.3.0 Windows wheel，完整 `.dist-info/licenses/` 及其库许可随 wheel 携带。
- 未修改的 Noto Sans CJK 2.004 字体，SIL Open Font License 1.1 见 `Noto-OFL.txt`。
- 不包含 HELI-X 本体、Java 运行时、预生成 `Chinese.jar`、激活信息或个人设置。

安装过程临时解压运行时，结束后尝试清理，不安装全局 Python、不注册字体。原始备份保留在数据目录 `.helix-zh-cn-windows/backup/`。安装器未做代码签名。

## 复验

Linux 通用回归：

```bash
python3 -m unittest discover -s tests -v
python3 tests/integration.py /path/to/linux/HELI-X11
```

Windows 集成测试要求一个**本机私有**的 ZIP：根目录包含匹配兼容表的三个原资源、四个官方 BAT、语言列表，以及合成的 `files/Application/ApplicationSettings.xml`（`Language=en`、`Country=US`、`UserSetting=keep`）。不要将此夹具上传仓库或 Release。

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tests\windows_installer.ps1 `
  -Installer "D:\build\setupHeli-X11-1.1.0-win64-zh-CN.exe" `
  -FixtureZip "D:\private\fixture.zip" -TestDirectory "D:\test-new-directory"
```

测试包含中文/空格/`&` 路径、写入失败回滚、安装/校验/重复安装、备份损坏保护、真实 PowerShell/BAT 启动保护、上游文件变动后拒绝、卸载后字节级恢复及保留其他设置。测试不会启动模拟器。

`--render-preview <PNG绝对路径>` 是维护用的安装器窗口绘制入口，可用于检查 Windows 字体和控件排版；它不能代替模拟器内中文画面的验证。
