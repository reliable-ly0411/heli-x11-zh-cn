# Windows 构建材料恢复索引

本页记录 1.1.0 候选制品的恢复入口和缓存保留规则。它不构成正式发布或新的验收结果；最终回放控制项及其他已知限制见[验收记录](release-1.1.0-validation.md)。仅补充文档，不改变版本、公共接口、标签或既有附件。

## 源码与制品

- 仓库：<https://github.com/reliable-ly0411/heli-x11-zh-cn>。
- 候选构建源码与流程提交：`fe18a5e9aeb1771d70eaa0bc1ca5119d693329cb`；工作树干净。
- 安装器：`setupHeli-X11-1.1.0-win64-zh-CN.exe`，34,115,072 字节。
- SHA-256：`f66dbd05a2ceaa6c353afbdff819f1888cbb404ceab00f23eea7ca575b555246`。
- 该安装器及 `SHA256SUMS` 保存在维护者可见的 GitHub 草稿中，尚未正式发布；本地保留目录为 `dist/1.1.0-release/`。
- 对应准备材料保存在 `build/windows-1.1.0-release/`：`build-info.json`、`Installer.cs`、`build.ps1`、`AssemblyInfo.cs`、`payload.zip`、`app.manifest`。缓存中的 `prepared-1.1.0-release.zip` 六项内容与该目录逐项 SHA-256 一致，可删除重复 ZIP。
- 已公开的 `v1.0.0`、`v1.1.0-beta.1` 标签和附件继续保留；此文档提交不参与上述候选 EXE 的构建。

## 重建入口

在独立的干净检出中使用上述源码提交，按照 [Windows 构建说明](../windows/README.md) 执行准备和编译。依赖版本、下载地址与摘要由 [`windows/dependencies.json`](../windows/dependencies.json) 固定。中文翻译、兼容表、字体生成、补丁程序、安装器及测试脚本均在 Git 历史内，无需保留多份准备 ZIP 才能恢复源码。

首次准备需要依赖缓存或联网下载。恢复源码并重新构建不保证 EXE 字节级相同；需要原制品时应使用已保留的 EXE 并核对上述摘要，不能用重建结果覆盖既有发布资产。

## 私有上游材料

Windows 上游为 HELI-X 11.0.2675。用于恢复原始测试资源的官方安装源单独保留，不上传本仓库：

- 原始来源：<https://www.heli-x.info/2675/setupHeli-X11_win64.exe>。
- 完整文件大小：449,604,287 字节。
- SHA-256：`87ac36b347fe31c00d4762a596a6b7fd64f5b0f3c141dfaea57f55c5cb75177b`。
- 原始输入身份仍以 [`data/compatibility-windows.json`](../data/compatibility-windows.json) 为准，不因重新下载或解包而修改兼容表。

完整官方安装源、解包工具、私有 `fixture.zip`、依赖缓存及必要辅助脚本保留在维护环境。解包目录与整合运行 ZIP 的 1,749 个文件逐项摘要一致；保留安装源和工具后，可移除这些可再生成副本。下载分片、未完成的下载和历史准备 ZIP 也不属于必需发布成果。删除前保存文件摘要清单，并把历史准备包中的小型源码与配置单独留存；目录名相似不能作为判断重复的依据。

私有夹具、模拟器、Java、模型、场景、激活信息、完整桌面截图与个人配置均不得上传公开仓库。界面验收材料应单独保留，不能用清理构建缓存的操作替代或声称完成 GUI 验收。
