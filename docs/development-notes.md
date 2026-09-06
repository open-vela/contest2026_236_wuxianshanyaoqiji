# 开发记录：Gemini-S1 编译环境搭建与基础固件编译

> 队伍编号：236（无险山妖气迹）
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