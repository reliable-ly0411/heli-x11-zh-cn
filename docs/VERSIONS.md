# 补丁版本与兼容契约

## 1.0.0：Linux 基线

标签 `v1.0.0` 固定提交 `e0888f13d29e773106703691813b369969c6d390`。
这是本仓第一个独立版本；此前仅有内容提交，没有版本标签或 Release。标签包含完整说明，不为加入版本文件改动该历史提交。

公共契约：

- Linux CLI：`patch.py check|build|install|verify|uninstall`。
- 选项：`--helix-dir`、`--output`、`--font`、`--font-index`。
- 翻译文件：`data/zh-CN.json` 的字符串键值映射、`data/label-patches.json` 的类名与显示字符串映射。
- Linux 安装状态：`.helix-zh-cn/state.json` 格式 1；未知上游文件哈希拒绝安装。
- 适配身份：HELI-X 11.0.2681 Linux，与补丁的独立版本号分开记录。

打标签前重新通过 4 项单元测试及 Linux 临时副本安装/恢复集成测试。

## 1.1.0-beta.1：Windows 安装器

在保留上述 Linux CLI、翻译格式和状态格式的基础上新增 Windows x64 安装器，因此选择次版本 `1.1.0`。Windows 实机模拟器界面及飞行功能尚未完成验收，使用 `-beta.1`，不作为正式稳定版。

新增接口：

- 双击 `setupHeli-X11-1.1.0-beta.1-win64-zh-CN.exe`，选择目录后安装、校验或卸载。
- 自动化入口：`--command check|install|verify|uninstall --helix-dir "目录" --log "日志文件"`；成功返回 0，操作失败返回 1，参数错误返回 2。
- Windows 独立状态：`.helix-zh-cn-windows/state.json` 格式 1，不读取或迁移 Linux 的安装状态。
- 官方分离目录布局：注册表 `HKLM\Software\HELI-X\HELI-X11\Settings` 中 `Path` 为数据目录，`ExePath` 为程序目录。所选目录必须与其中之一匹配才使用另一目录；否则按程序与数据同目录处理。
- Windows 上游身份：官方 11.0.2675 x64，三个原文件精确哈希见 `data/compatibility-windows.json`。未声明对自动更新后的其他构建兼容。

补丁不覆盖原版 JAR，不携带从 HELI-X 派生的预构建 JAR。Windows 安装器随包携带 Python、Pillow 和 Noto 字体，只在用户本机生成覆盖资源。
