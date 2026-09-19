# AI Coding 开发日志 — gemhermit（本次开发阶段）

> 会话工具：TRAE（AI IDE）
> 阶段：本地编译环境搭建 + openvela 源码同步 + Gemini-S1 首次固件编译
> 日期：2026-09-06
>
> 说明：本次 TRAE 会话暂无组委会官方日志归集工具，无法自动导出标准 `.jsonl`。
> 此处以人工整理的开发记录（`.md`）形式归档会话要点，不是原始会话。
> 不能将本摘要改写为 JSONL 冒充原始日志；需另行从客户端导出真实会话，并确认比赛接收范围。

---

## 一、会话目标

为「微芯润 Gemini-S1（R528）开发板」搭建可复现的本地编译环境，同步 openvela 全量源码，并编译出首个可烧录的固件，为后续「二次元 + NFC 互动 + AI Passport」功能开发打基础。

## 二、完成的工作

### 1. 编译环境搭建
- 通过 **WSL2 + Ubuntu 24.04** 提供 Linux 编译环境（曾因 WSL 发行版损坏 `ext4.vhdx` 丢失而重建）。
- 安装 `repo`、`git`、`build-essential`、`cmake`、`python3` 等编译依赖。

### 2. openvela 全量源码同步
- 使用团队专属 manifest 初始化工作区：`repo init -u .../contest2026_236_wuxianshanyaoqiji -b dev-ai-contest-2026 -m contest2026_236_wuxianshanyaoqiji.xml`
- 全量约 **35GB**（源码约 20GB + `.repo` 约 27GB）。
- 主要踩坑与对策（详见 `docs/development-notes.md`）：
  - `curl 56 GnuTLS recv error` → 调大 `http.postBuffer`、强制 HTTP/1.1、降并发、循环重试。
  - nuttx 仓库 checkout 不完整 → 单仓反复 `repo sync` 直至关键文件存在。

### 3. Gemini-S1 固件编译
- 目标：`vendor/allwinnertech/boards/r528/r528s3-gemini-s1/configs/nsh`（7 寸 MIPI 屏）。
- 编译入口：`./build.sh <board-config-path> -j8`。
- 首次编译失败根因：`MEDIA` / `FEATURE_FRAMEWORK` 框架依赖 QuickApp 头文件与宏，而 QuickApp 需链接 `libs_openvela_vela/armv7a_cmake` 预编译库，该库在当前大赛分支缺失（git-LFS 占位但仓库各分支无库文件）。
- 解决方案：在本机 defconfig 关闭 `CONFIG_MEDIA` 与 `CONFIG_FEATURE_FRAMEWORK`，编译出**最小 NSH 固件**（仍含 LVGL 图形、蓝牙、ffmpeg、libcxx，不含 QuickApp 运行时）。
- 结果：编译成功（`exit: 0`），产物 `nuttx/vela.bin`（约 7.2MB）、`nsh.fex` 已复制到 lichee 打包目录。

## 三、产物

| 产物 | 路径 | 说明 |
| ---- | ---- | ---- |
| `vela.bin` | `nuttx/vela.bin` | 可烧录二进制固件 |
| `nuttx` | `nuttx/nuttx` | ELF 调试镜像 |
| `nsh.fex` | `lichee/board/r528s3/gemini-s1_nand/configs/nsh.fex` | 打包用镜像产物 |

## 四、关键决策

1. **环境选型**：选择 Windows + WSL 而非原生 Linux，复用现有 Windows 主机。
2. **同步策略**：大仓同步优先大 buffer + 重试，而非一次性高并发。
3. **QuickApp 处置**：因官方预编译库缺失，本阶段先出「最小 NSH 固件」，保证有可烧录基线，后续再集成完整 QuickApp UI / NFC / AI Passport。

## 五、下一步（规划）

- `pack` 打包最终可烧录分区镜像。
- 获取 QuickApp `armv7a_cmake` 预编译库后启用完整 UI。
- 围绕「二次元 + NFC + AI Passport」开发具体功能并集成板端。

---

_本文档由 AI 会话整理自动归档于 logs/，详细技术过程见 `docs/development-notes.md`。_
