# 妖气迹 · NFC 二次元互动终端（Microchip R528 / Gemini-S1）

> **队伍：236 无险山妖气迹**
> **赛道：AI 硬件产品创新**
> **目标硬件：微芯润 Gemini 开发板（openvela AI 硬件开发者大赛指定硬件，R528S3 / Cortex-A7）**

---

## 一、作品简介

一款基于 **openvela** + **微芯润 Gemini 开发板** 的二次元互动桌面终端。通过 **NFC 卡片互动** 触发本地动画/语音反馈，并结合 **AI Passport** 在对话中赋予角色「记忆与个性」——让二次元角色真正「认得你、记得住你们之间的事」。

一句话亮点：**刷一下 NFC，你的虚拟角色就会用带记忆的 AI 和你打招呼。**

---

## 二、选题方向

**AI 硬件产品创新**。

核心理由：
- 面向真实硬件（Gemini-S1 开发板），输出可烧录、可独立运行的固件。
- 结合 NFC（`RC522`/`PN532`）做低门槛实体交互，符合「二次元周边 + 智能硬件」的产品调性。
- 集成 AI Passport，把「一次性语音对话」升级为「有记忆、有身份、可持续」的角色陪伴体验。

---

## 三、目录结构

本仓用于存放超集 openvela 编译树之外的**作品代码**，并通过 manifest `<linkfile>` 软链进编译树对应位置。

```text
contest2026_236_wuxianshanyaoqiji/
├── app/                       # NuttX 原生应用（烧板运行）
│   └── hello_app/             #   → 软链至 packages/demos/contest2026_236_hello_app
├── quickapp/                  # QuickApp 应用（需 QuickApp 运行时）
│   └── hello_quickapp/        #   → 软链至 packages/apps/contest2026_236_hello_quickapp
├── board/                     # 板级适配（BSP）
│   └── contest_board/         #   → 软链至 vendor/openvela/boards/contest2026_236_board
├── docs/
│   └── development-notes.md   # 开发记录：环境搭建 / 源码同步 / 编译踩坑
├── logs/                      # AI Coding 日志（提交前导出）
├── contest2026_236_wuxianshanyaoqiji.xml  # 团队 manifest
└── openvela.xml               # openvela 工程 manifest
```

> 对应软链映射见 [contest2026_236_wuxianshanyaoqiji.xml](contest2026_236_wuxianshanyaoqiji.xml)：
> - `app/hello_app` → `packages/demos/contest2026_236_hello_app`
> - `quickapp/hello_quickapp` → `packages/apps/contest2026_236_hello_quickapp`
> - `board/contest_board` → `vendor/openvela/boards/contest2026_236_board`

---

## 四、运行方式

openvela 工程在 **WSL（Windows Subsystem for Linux, Ubuntu 24.04）** 中编译，统一通过 `build.sh` 作为入口，参数为 board config 路径。

### 0. 前置环境

- Windows + WSL2（Ubuntu 24.04）
- WSL 内安装：`repo`、`git`、`build-essential`、`cmake`、`python3`（详见 `docs/development-notes.md`）

### 1. 拉取源码（首次）

```bash
cd ~
repo init -u https://github.com/open-vela/contest2026_236_wuxianshanyaoqiji \
  -b dev-ai-contest-2026 -m contest2026_236_wuxianshanyaoqiji.xml
repo sync -c -j4
```

### 2. 编译 Gemini-S1 固件

```bash
cd ~/openvela
# 7 寸 MIPI 屏 NSH 基线：configs/nsh/
# 2.8 寸 SPI 屏：      configs/nsh_minidisplay/
./build.sh vendor/allwinnertech/boards/r528/r528s3-gemini-s1/configs/nsh/ -j8
```

> **注意**：本阶段按最小化方案，已在 `vendor/allwinnertech/boards/r528/r528s3-gemini-s1/configs/nsh/defconfig` 中关闭依赖 QuickApp 预编译库的 `CONFIG_MEDIA` / `CONFIG_FEATURE_FRAMEWORK`（原因是当前大赛分支 `libs_openvela_vela` 仓库未提供 `armv7a_cmake` 预编译库）。详见 `docs/development-notes.md`。

### 3. 产物

编译成功后生成：

```text
nuttx/vela.bin                                            # 可烧录二进制固件
nuttx/nuttx                                               # ELF 调试镜像
vendor/allwinnertech/lichee/board/r528s3/gemini-s1_nand/configs/nsh.fex
```

### 4. 打包 / 烧录

```bash
cd vendor/allwinnertech/lichee/
source envsetup.sh
lunch_nuttx          # 选择 r528s3-gemini-s1
pack                 # 打包出分区镜像
```

（使用 PhoenixSuit 或配套烧录工具将镜像烧入 Gemini-S1。）

---

## 五、AI Coding 使用说明

本项目全程借助 AI 辅助开发，主要用在以下环节：

- **需求拆解与创意展开**：从「二次元 + NFC + AI Passport」一句话需求逐步澄清为可落地的功能方案与产品形态。
- **环境搭建与排障**：WSL 损坏重建、repo 大仓同步、网络抖动、编译报错等均由 AI 协助定位并对症解决（详见 `docs/development-notes.md`）。
- **编译适配**：定位 QuickApp 预编译库缺失根因，决定本阶段以「最小 NSH 固件」先行落地。

完整对话日志见根目录 `logs/` 目录。

---

## 六、当前进度与规划

- [x] 本地编译环境搭建（WSL + openvela 全量源码同步）
- [x] Gemini-S1 `nsh` 目标编译出可烧录固件 `vela.bin`
- [ ] `pack` 打包最终镜像并完成真机烧录验证
- [ ] QuickApp 完整 UI（从官方获取 `armv7a_cmake` 预编译库后启用）
- [ ] NFC 互动模块（`RC522`/`PN532`）接入与动画/语音反馈
- [ ] AI Passport 接入，实现带记忆的角色对话

---

## 附：仓库命名规范

`contest2026_<编号>_<队伍名>` — `236` 号 / 队伍 `wuxianshanyaoqiji`。