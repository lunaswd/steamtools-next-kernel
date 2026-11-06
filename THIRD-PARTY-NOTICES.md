# Source and third-party notices

This is the maintained OpenSteamTool kernel for SteamTools Next. The complete
kernel sources, build recipes and release scripts are in this repository.

- Maintenance repository: https://github.com/lunaswd/steamtools-next-kernel
- Original upstream: https://github.com/OpenSteam001/OpenSteamTool
- Baseline: OpenSteamTool 1.5.4.1, imported as commit `8122507`.
- Windows version-resource maintenance: commit `8f441fb`.
- Kernel license: GNU GPL version 3, reproduced in `LICENSE`. The upstream
  license text alone does not establish an additional "or later" grant.

Dependencies are pinned in `dependency-lock.json`. Binary release archives carry
their notices as flat `LICENSE-*.txt` files, including the bundled fmt notice.
The `steamtools-next-kernel-VERSION-source.zip` release asset includes the matching kernel
commit **and all downloaded dependency source trees** in `vendor/`, without Git
metadata, build caches or account data. A Git checkout fetches the same locked
dependencies; the source release uses its `vendor/` trees directly.

| Dependency | Revision | License |
|---|---|---|
| Lua | 5.5.0, archive SHA-256 in lock file | MIT |
| Microsoft Detours | 1dbd4ea281d73d478aa8d09a8b83fbd265f715f7 | MIT |
| Protocol Buffers | 3.15.3 / 983d115bd9f388468fd65d1e623b858eb12bc528 | BSD-3-Clause |
| spdlog (with bundled fmt) | 1.17.0 / 79524ddd08a4ec981b7fea76afd08ee05f83755d | MIT |
| toml++ | 3.4.0 / 30172438cee64926dc41fdd9c11fb3ba5b2ba9de | MIT |

The repository preserves the older maintained-source ZIP already published in
its original history. That legacy snapshot is not the current release asset.
Runtime compatibility with an individual Steam client or game requires separate
verification; a successful download, PE check, or matching hash is not such proof.

