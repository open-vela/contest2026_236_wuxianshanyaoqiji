> 历史记录，不作为当前 Gemini-S1 固件构建入口。当前成果与复现流程见项目 docs/build-pack-guide.md；旧配置及脚本已停用。

# 开发记录：Gemini-S1 编译环境搭建与基础固件编译

> 队伍编号：236（无限闪耀绮迹）
> 赛道：AI 硬件产品创新
> 目标硬件：微芯润 Gemini 开发板（R528S3，Cortex-A7，openvela AI 硬件开发者大赛指定硬件）
> 文档更新：2026-09-06

本文档记录本项目在「本地编译环境搭建 + 源码同步 + 首次固件编译」阶段的完整工作，含具体命令、产物路径、遇到的问题与解决方案，便于复现与后续开发参考。

---

## 一、项目背景与目标

- 基于 **openvela**（NuttX 之上的开源 IoT/AI 软件平台）开发二次元互动硬件。
- 使用 **微芯润 Gemini 开发板（R528S3, Gemini-S1）**，是大赛指定硬件。
- 规划结合 **NFC 互动** 与 **AI Passport**（[folotoy/ai-passport](https://github.com/folotoy/ai-passport)）实现趣味互动功能。
- 本阶段目标：在本地（Windows + WSL）搭建可复现的编译环境，成功编译出 Gemini-S1 可烧录固件。

---

## 二、环境搭建

### 2.1 整体架构

| 组件 | 方案 |
| ---- | ---- |
| 宿主机 | Windows（PowerShell） |
| Linux 发行版 | WSL2 上的 Ubuntu 24.04 |
| 元工具 | `repo`（管理多 Git 仓库） |
| 编译工作区 | `~/openvela`（位于 WSL 内） |
| 工具链 | openvela 自带的 `prebuilts/gcc/linux-x86_64/arm-none-eabi` |

> 曾因 WSL Ubuntu 发行版损坏（`ext4.vhdx` 丢失）而重建：`wsl --unregister Ubuntu` 后重装 Ubuntu 24.04，并重新安装编译依赖（`repo`、`build-essential`、`cmake` 等）。

### 2.2 WSL 内安装 repo

```bash
# 拉取 repo 工具（作为普通用户保存到 ~/bin）
mkdir -p ~/bin
curl https://storage.googleapis.com/git-repo-downloads/repo -o ~/bin/repo
chmod a+x ~/bin/repo
# 将 ~/bin 加入 PATH
echo 'export PATH=$PATH:$HOME/bin' >> ~/.bashrc
```

### 2.3 安装编译依赖

```bash
sudo apt-get update
sudo apt-get install -y repo build-essential git cmake python3 python3-pip curl
```

---

## 三、源码同步

### 3.1 repo init

按组委会说明初始化工作区（团队专属 manifest）：

```bash
repo init -u https://github.com/open-vela/contest2026_236_wuxianshanyaoqiji \
  -b dev-ai-contest-2026 -m contest2026_236_wuxianshanyaoqiji.xml
```

工作区内 openvela 全量源码在外层，本团队仓位于 `contest2026_236_wuxianshanyaoqiji/`。

### 3.2 repo sync（踩坑较多）

全量源码约 **35GB**（同步后源码约 20GB + `.repo` 约 27GB），网络期间遇到的主要问题及对策：

| 症状 | 原因 | 解决 |
| ---- | ---- | ---- |
| `curl 56 GnuTLS recv error` | 大仓库网络不稳定 | 调大 git 缓冲 `git config --global http.postBuffer 1572864000` |
| HTTP/2 传输中断 | 与部分服务器握手机制不兼容 | 强制 HTTP/1.1 |
| 并发过高导致分片失败 | 网络抖动 | 降低并发 `repo sync -j2`，并多次重试 |
| nuttx 仓库 checkout 不完整（缺 `drivers/Kconfig` 等） | 中断残留 | 编写循环脚本反复 sync 该单仓直到关键文件存在 |

常用同步命令（网络优化参数）：

```bash
cd ~/openvela
export GIT_HTTP_LOW_SPEED_LIMIT=0
export GIT_HTTP_LOW_SPEED_TIME=999999
repo sync -j4 -c --prune --no-tags
```

---

## 四、编译目标与首次尝试

### 4.1 编译入口

openvela 统一通过 `build.sh` 编译，参数为 **board config 路径**：

```bash
./build.sh vendor/allwinnertech/boards/r528/r528s3-gemini-s1/configs/nsh/ -j8
```

Gemini-S1 提供多个配置：

| 配置 | 说明 |
| ---- | ---- |
| `configs/nsh/` | 7 寸 MIPI 屏，NSH 基线配置 |
| `configs/nsh_minidisplay/` | 2.8 寸 SPI 屏 |

> 板级目录：`vendor/allwinnertech/boards/r528/r528s3-gemini-s1/`

### 4.2 首次编译失败的根因

首次编译在 `apps` 侧失败，报两类错误：

1. `frameworks/multimedia/media/feature/audio_impl.c:816` —— `CONFIG_HAP_APP_PATH` 未定义
2. `frameworks/runtimes/feature/modules/fetch_impl.cpp:33` —— `fatal error: quickapp_inspector.h: No such file or directory`

排查结论：

- 这些 **MEDIA / FEATURE_FRAMEWORK** 框架代码硬编码依赖 **QuickApp** 的头文件与宏。
- QuickApp 启用时需要链接官方预编译库 `vendor/openvela/boards/vela/libs/armv7a_cmake/`（即 `libs_openvela_vela` 仓库）。
- 该仓库在 `dev-ai-contest-2026` 分支上**不含这些预编译库文件**（`.gitattributes` 中虽声明为 git-LFS，但各分支 `git ls-tree` 均无任何库文件，仅剩空壳），导致完整 QuickApp 固件无法链接。

> 备注：仓库内的提交 `a6c66430`（`vendor/allwinnertech` 仓库）描述了官方启用 QuickApp 的配置对（依赖 `libs_openvela_vela/armv7a_cmake` 下的 `libquickapp.a` 等）。当前大赛分支缺库，故本阶段选择最小化方案。

> **⚠️ 更正（2026-09-15）**：上面"MEDIA / FEATURE_FRAMEWORK **都**硬编码依赖 QuickApp 头文件"的表述不准确，把两个不同性质的问题捆在了一起。实测结论：
>
> - **FEATURE_FRAMEWORK 确实硬依赖 QuickJS** —— `frameworks/runtimes/feature/Kconfig` 里写明了 `depends on INTERPRETERS_QUICKJS`。关它是对的。
> - **MEDIA 并不依赖 QuickApp** —— `config MEDIA` 是 `tristate`，无任何 `select`/`depends on` 指向 QuickApp；`media/Make.defs` 只把它自己和 `pfw/` 加进构建，不含 `feature/`；当前树里 `media/pfw/` 已有 14 个成功编译的 `.o`。
> - 当时那个 `frameworks/multimedia/media/feature/audio_impl.c:816 HAP_APP_PATH 未定义` 报错，根因是同时开着 QuickJS 一簇：`media/feature/` 下全是 `.jidl`（`audio.jidl`/`record.jidl`/`session.jidl`），那是 media 框架**给 JS 运行时用的绑定层**，只在 JS 引擎开启时才参与构建。
> - **因此 `CONFIG_MEDIA` / `CONFIG_MEDIA_SERVER` 必须开启**，它正是 ai_agent 录音/播放路径的依赖（官方 `packages/ai_agent/defconfigs/gemini-s1/gemini-s1_defconfig` 中 `CONFIG_MEDIA=y` 且完全没有 `CONFIG_QUICKAPP`）。
>
> 完整依据与链接期症状速查见 [anime-voice-quickstart.md](anime-voice-quickstart.md) 第四节。

---

## 五、解决方案：编译最小 NSH 固件

在**本机 defconfig** 中关闭依赖 QuickApp 的高层框架，不动任何远程公共仓库：

```bash
DEF=vendor/allwinnertech/boards/r528/r528s3-gemini-s1/configs/nsh/defconfig
cp "$DEF" "$DEF.bak"            # 备份
# 关闭 MEDIA 及 FEATURE_FRAMEWORK 系列
sed -i 's/^CONFIG_MEDIA=y/# CONFIG_MEDIA is not set/' "$DEF"
...（同理关闭 MEDIA_SERVER、MEDIA_FOCUS、MEDIA_TOOL、FEATURE_FRAMEWORK）
```

最终 defconfig 中相关行变为：

```text
# CONFIG_QUICKAPP is not set
# CONFIG_MEDIA is not set
# CONFIG_FEATURE_FRAMEWORK is not set
```

> 该固件仍包含 **LVGL 图形、蓝牙、ffmpeg、libcxx** 等，仅不含 QuickApp 应用运行时，作为可烧录/可跑 NSH 的基础基线。

### 编译并生成固件

```bash
cd ~/openvela
./build.sh vendor/allwinnertech/boards/r528/r528s3-gemini-s1/configs/nsh/ -j8
```

编译成功，关键日志：

```text
Generating: nuttx.bin
copy from `nuttx' [elf32-littlearm] to `vela.bin' [binary]
Firmware is being converted: vela.bin
Copy nsh.fex to lichee board dir
=== exit:0 ===
```

### 产物清单

| 产物 | 路径 | 说明 |
| ---- | ---- | ---- |
| `vela.bin` | `nuttx/vela.bin`（约 7.2MB） | 可烧录二进制固件 |
| `nuttx` | `nuttx/nuttx` | ELF 调试镜像 |
| `nsh.fex` | `vendor/allwinnertech/lichee/board/r528s3/gemini-s1_nand/configs/nsh.fex` | 已复制到 lichee 打包目录 |

---

## 六、踩坑汇总（速查）

1. **WSL 发行版损坏** → 注销重装 Ubuntu 24.04 并重装依赖。
2. **repo sync 网络失败** → 调大 git buffer、强制 HTTP/1.1、降并发、循环重试。
3. **nuttx 仓库 checkout 不完整** → 单仓反复 sync 直至关键文件（`drivers/Kconfig`、`apps/Application.mk`）存在。
4. **QuickApp 预编译库缺失**（`libs_openvela_vela` 各分支均无库文件）→ 本阶段关闭 `MEDIA`/`FEATURE_FRAMEWORK`，编译最小 NSH 固件。

---

## 七、当前状态与下一步

### 已完成
- [x] 本地编译环境（WSL + Ubuntu + repo）搭建
- [x] openvela 全量源码同步
- [x] Gemini-S1 `nsh` 目标编译出可烧录固件 `vela.bin`

### 待办 / 可选方向
- [ ] `pack` 打包出最终可烧录分区镜像（`vendor/allwinnertech/lichee`：`lunch_nuttx` + `pack`）
- [ ] 如需完整 QuickApp UI 功能，从大赛官方获取 `armv7a_cmake` 预编译库后做源码级配置
- [ ] 围绕「二次元 + NFC 互动 + AI Passport」实现具体功能并集成设备端
- [ ] 按作品形态将代码放入 `contest2026_236_wuxianshanyaoqiji/app|quickapp|board` 对应子目录

---

## 附录：常用命令

```bash
# 进入编译工作区
cd ~/openvela

# 同步源码
repo sync -j4 -c --prune --no-tags

# 编译（含交互式配置修改）
./build.sh vendor/allwinnertech/boards/r528/r528s3-gemini-s1/configs/nsh/ menuconfig
./build.sh vendor/allwinnertech/boards/r528/r528s3-gemini-s1/configs/nsh/ -j8

# 清理后全新编译
./build.sh vendor/allwinnertech/boards/r528/r528s3-gemini-s1/configs/nsh/ distclean -j8
```

---

## 八、烧录阶段（2.8 寸 SPI 屏固件打包与烧录准备）

> **2026-09-15 更新**：本节记录的早期打包方式存在严重问题（DDR 参数被误改、nsh.fex 绑错分区），已按 GitHub 官方流程从头重建并全部查清修复。**最新完整流程、原理与踩坑分析见 [build-pack-guide.md](build-pack-guide.md)**，最终可用镜像为 `firmware/rtos_nuttx_r528s3-gemini-s1_uart0_official.img`（MD5 `e70379f56d36de6f02992c2594e5cadc`）。以下保留为历史过程记录。

> 本阶段目标：把 `nsh_minidisplay` 固件打包成 PhoenixSuit 可烧录镜像，并完成烧录前的排查与工具准备。
> 时间：2026-09-07 ~ 09-09

### 8.1 板子与 NAND 容量确认

- **板卡**：润芯微 Gemini-S1（全志 R528 双核 Cortex-A7，1.2GHz；RAM 128MB DDR3）
- **NAND FLASH**：**256MB SPI NAND**，型号 **Winbond W25N02KVZEIR（2Gbit）** ← 官方《硬件说明》确认
- 板载 2.8 寸 SPI 屏（ILI9341），也支持 7 寸 MIPI 大屏
- 判断历史的坑：此前 SDK `dummy_1=262144`、板端 MTD 到 ~122 曾误导为 128M；以官方文档为准是 **256MB**

### 8.2 编译连带排查（重要结论）

- `nsh_minidisplay` 首次编译实际**失败**（后台任务通知的 exit 0 是误报，查日志为链接失败）：
  - `ld: cannot find .../boards/vela/libs/armv7a_cmake/libquickapp.a` 等 8 个库
  - 根因：`vendor_openvela` 当前分支**根本没有这些 QuickApp 预编译库**（仅在 `.gitattributes` 声明 LFS 规则，`git ls-tree` 无该目录，`git lfs pull` 拉不到）。大赛分支 `libs_openvela_vela` checkout 失败被文档当作“不影响编译”而忽略，实际对需要 QuickApp 的 `nsh_minidisplay` 是致命的。
- **解决方案**（与 `nsh` 对齐）：关闭 QuickApp 框架
  - 修改 `configs/nsh_minidisplay/defconfig`：`MEDIA / FEATURE_FRAMEWORK / QUICKAPP / QUICKAPP_VAPP` 置为 not set，删除其 PRIORITY/STACKSIZE 子项（已备份 `.bak`）
  - 由此得到能驱动 ILI9341 SPI 屏的最小 NSH 固件：`vela.bin`（4.7MB）+ `nsh.fex`
- 说明：若需完整 QuickApp/WebView 能力，必须从官方获取 `armv7a_cmake` 预编译库（本分支无法编译/下拉）。

### 8.3 PhoenixSuit 镜像打包（三个根因的修复链）

1. **布局容量不匹配**：`tools/scripts/pack_img.sh` 对 `r528s3-gemini-s1` **硬编码 `prepare_for_128Mnand`**，与 256MB NAND 不符 → 把该分支改为 `prepare_for_256Mnand`。
2. **nsh 分区过小**：`update_mbr` 报 `dl file nsh.fex size too large / part_size = 2560`。修改 `board/r528s3/gemini-s1_nand/configs/sys_partition.fex`：
   - `sst`：2560 → **16384** 扇区（8MB，容纳 4.7MB 固件）
   - `usrdata`：425472 → 411648（净增补抵消，总量不变）
3. **dragon 工具无法运行**：`tools/tool/dragon` 是 32 位 ELF，系统缺 32 位动态加载器 → 安装 `libc6:i386 libstdc++6:i386` 后正常。

打包成功产出：
- 镜像：`out/r528s3/gemini-s1_nand/rtos_nuttx_r528s3-gemini-s1_uart0_256Mnand.img`（26,599,424 B ≈ 26.6MB）
- **MD5**：`60298e8309095cafa3f825ceb9f1ffdd`
- **SHA256**：`a20d359a08dde44c901404e466fd64e95238713656f2f52141929dca8da63dda`
- 已拷贝到 Windows：`firmware/rtos_nuttx_r528s3-gemini-s1_uart0_256Mnand.img`

### 8.4 官方文档与资料（已本地保存）

飞书 rivotek 官方文档（经 lark 授权拉取并本地化）：

| 文件 | 说明 |
|---|---|
| `official/Gemini-S1-开发板.md` | 板卡概述、特性、文档导航 |
| `official/软件烧录指南.md` | PhoenixSuit 烧录流程 |
| `official/硬件说明.md` | 核心规格（**含 256M NAND 铁证**）、接口定义 |

烧录工具已定位并解压到 `firmware/烧录工具/`：
- PhoenixSuit：`PhoenixSuit\AllwinnertechPhoeniSuitRelease20201225\PhoenixSuit.exe`（安装器 `PhoenixInstall.exe`）
- USB 驱动：`全志USB驱动\InstallUSBDrv.exe`（含 `UsbDriver\usbdrv.inf`）
- 原始包在 Chrome 默认下载目录：`E:\多用户共享文件\下载\`（`AllwinnertechPhoeniSuitRelease20201225.zip.zip`、`全志USB烧录驱动20201229.zip`）

### 8.5 烧录步骤（官方流程）

1. 装 USB 驱动：管理员运行 `InstallUSBDrv.exe`（Win11 代码10 → 设备管理器“通用串行总线控制器”从磁盘安装 `usbdrv.inf`）
2. 运行 `PhoenixSuit.exe` → 一键刷机 → 选择 `rtos_nuttx_r528s3-gemini-s1_uart0_256Mnand.img` → 选**全盘擦除升级**
3. 板进 FEL：Type-C 连电脑 → 按住 FEL → 按 RESET 复位 → 电脑出现 `USB Device (VID_1f3a_PID_efe8)` 后松开 FEL → 自动烧录
4. 烧完关闭 PhoenixSuit，板子自动重启进新固件

### 8.6 遗留/后续
- [ ] 实际烧录并验证 2.8 寸屏是否点亮、NSH 能否交互
- [ ] 若要做 webview / Live2D webui，需先从大赛官方补齐 QuickApp `armv7a_cmake` 预编译库并重新配置编译
- [ ] 围绕「二次元 + NFC 互动 + AI Passport」实现应用并集成
```