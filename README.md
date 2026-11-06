# SteamTools Next Kernel

SteamTools Next 的独立 Windows x64 内核维护仓库：
[github.com/lunaswd/steamtools-next-kernel](https://github.com/lunaswd/steamtools-next-kernel)。

本仓库直接包含 OpenSteamTool **1.5.4.1** 的完整展开源码、构建脚本、依赖锁定信息和许可证，
不是只有一个源码压缩包的占位仓库。原始上游说明保留在 `README_UPSTREAM.md`、`README_EN.md`
和 `README_ES.md`，来源与第三方依赖见 `THIRD-PARTY-NOTICES.md`。

## 发布与下载安装

SteamTools Next 从此仓库的 **Releases** 获取安装包，不要求用户选择本地内核产物目录。
每个正式发布包含：

- `kernel-release.json`：版本、来源提交、平台、安装 ZIP 名称/大小/SHA-256，以及每个文件的大小与 SHA-256。
- `steamtools-next-kernel-VERSION-windows-x64.zip`：平铺的 Windows x64 DLL、配置样本、构建来源和全部第三方许可证。
- `steamtools-next-kernel-VERSION-source.zip`：同一来源提交的完整内核源码、脚本及 `vendor/` 内完整依赖源码。
- `release-SHA256SUMS.txt`：以上资产的 SHA-256 校验。

下载器先检查发布元数据，再下载并校验安装 ZIP 和逐文件清单、x64 PE、构建版本与来源提交。
正式包不自动安装到 Steam；SteamTools Next 的事务式安装器负责备份、入口二选一、写入与回滚。
`version.dll` 与 `version.dll.disabled` 的字节相同，实际启用哪个入口由安装器管理。

## 从 Git 源码构建

需要 Windows x64、Visual Studio 2022/2026 C++ 工具链、CMake >= 3.20、Ninja、Git 和 Python >= 3.10。
在 x64 Native Tools / Developer PowerShell 终端中执行：

```powershell
git clone https://github.com/lunaswd/steamtools-next-kernel.git
cd steamtools-next-kernel
python -m unittest discover -s scripts -p 'test_*.py' -v
.\scripts\build-kernel.ps1 -Configuration Release
python scripts/package_kernel.py --release-tag v1.5.4.1
```

`build-release/Release/` 是 DLL 输出，`build-release/kernel-build.json` 是构建来源记录，
`dist/` 是发布资产。脚本要求先提交源码变更，避免把旧 DLL 标记为新源码的构建结果。
可以传 `-BuildDirectory`、`-DependencyDirectory` 复用符合锁定 commit 的缓存。
依赖 CMake recipes 固定到具体 Git commit；Lua 的 HTTPS tar 包固定 SHA-256，保持 TLS 验证。

## 从完整源码发布包离线重建

解压 `steamtools-next-kernel-VERSION-source.zip` 后，所有依赖源码已在 `vendor/`；
CMake 自动优先使用这些来源，不需要重新从第三方下载依赖：

```powershell
cmake -S src -B build -G "Ninja Multi-Config"
cmake --build build --config Release --parallel
```

`SOURCE_INFO.json` 记录来源提交与依赖锁。可重现的是输入、依赖和打包过程；
不同 MSVC/CMake 版本的输出不承诺逐字节相同。ZIP 打包使用固定排序、时间戳与压缩级别，
相同文件输入及 Python/zlib 环境得到相同资产哈希。

## 自动发布

`.github/workflows/main.yml` 在推送 `vVERSION` tag 时构建，也支持对已存在 tag 的手动执行。
它构建带 Windows 版本资源的 Release DLL，校验来源与哈希，上传二进制、完整源码和发布清单。
发布文件不自动覆盖已有同名资产；修订发布应更新源码版本并使用新 tag。
旧源码快照 `OpenSteamTool-1.5.4.1-maintained-source.zip` 保留以维护既有历史，不作为新安装来源。

## 许可与验证范围

内核许可全文见 `LICENSE`（GNU GPL version 3）；完整 corresponding source 与第三方许可证随每次发布提供。
文件下载成功、安装成功、PE/哈希/版本一致不等于已经验证 Steam 或特定游戏运行兼容。
升级前保留安装器备份；Steam 运行时先关闭客户端再替换内核。
