# OpenEVLA 二次元硬件初始化

> 2026-09-20 校注：队伍编号 236，正式队名为“无限闪耀绮迹”。下文为原始对话留档，其中早期队名转写不准确，以此校注为准。

[TraeWork](https://www.trae.cn/ide/download?auto=1&product_type=work&utm_source=content&utm_medium=session_share_download&utm_campaign=try_traework&utm_content=artifact_marker)

September 9, 2026·Content is AI-generated and may not be fully accurate

openevla的比赛初始仓库 你看看 我想做二次元这些的硬件 看看怎么初始化一下

07 26, 14:40

TraeWork

Worked for 14s

Thought

我先看一下当前目录的情况。

Browsed 1 folder

这看起来是 openvela (RTOS) 的比赛初始仓库。让我读一下 README 和 XML 文件，了解一下项目结构。

Read 3 files

我已经看完仓库了。这是 **2026 openvela AI 硬件开发者大赛** 的样例/模板仓库（队伍编号 236「无限山妖气姬」），不是 openvela 主仓库本身。

## 仓库现状

里面**只有 3 个示例骨架** ，没有任何 openvela 源码：

| 内容 | 你的仓路径 | 映射到 openvela 编译树 |
|---|---|---|
| 应用 | `app/hello_app/` | `packages/demos/contest2026_236_hello_app` |
| 快应用 | `quickapp/hello_quickapp/` | `packages/apps/contest2026_236_hello_quickapp` |
| 板级 | `board/contest_board/` | `vendor/openvela/boards/contest2026_236_board` |

XML manifest 里列了 openvela 全量子项目（nuttx、apps、packages、vendor 等），但要靠 `repo init` 拉取。

## 初始化步骤（Windows）

先确认两件事，再决定怎么往下走：

1. **赛道** ：你说想做「二次元这些的硬件」——属于「**AI 硬件产品创新** 」赛道吧？作品形态大概是个带屏/语音/动画的智能小设备。

2. **目标板** ：是跑模拟器（`prebuilts/emulator/windows-x86_64`），还是要烧到真板（比如 `vendor/espressif` ESP32-S3、`vendor/sifli` SF32LB52、`vendor/xiaomi/vela/pyxis`）？

### 一次性拉取 + 编译

Bash

```
1
2
3
4
5
6
7
8
9
```
```
# 1) 安装 repo 工具（Windows 推荐用 Git Bash 或 WSL）
curl https://storage.googleapis.com/git-repo-downloads/repo > repo
python repo init -u https://github.com/open-vela/contest2026_236_wuxianshanyaoqiji \
 -b dev-ai-contest-2026 -m contest2026_236_wuxianshanyaoqiji.xml
python repo sync -c -j8

# 2) 编译（以模拟器为例，赛题推荐跑这个） cd ..
./build.sh vendor/openvela/boards/emulator -j8
```
## 关于「二次元硬件」

openvela 里现成能用的素材/中间件（你不用从零造轮子）：

- **图形** ：LVGL（`apps/graphics/lvgl/lvgl`）+ ThorVG 矢量渲染（`external/thorvg`）+ Lottie 动画（`external/rlottie`）

- **资源解码** ：libwebp / libpng / libjpeg-turbo / freetype（中日韩字体）

- **AI** ：百炼 SDK（`external/bailian_sdk`）、TFLite-Micro、CMSIS-NN

- **快应用** ：自带 quickapp 框架，能写带皮肤的 UI

## 想让我接着做什么？

请你确认/选择一下，我再动手：

- 你想做的是**快应用（手表/手环 UI）** 、**普通 C 应用 + LVGL** ，还是**新硬件适配** ？

- 目标开发板/模拟器是哪个？

- 需不需要我先帮你把 `hello_app` / `hello_quickapp` / `contest_board` 这三个示例跑通（验证编译链路），再开始做二次元主题？

我是想是开发板 然后有啥可以好的创意

09 05, 23:48

TraeWork

Worked for 7m 14s

Thought

好想法 👍 你要用**真开发板** 做 AI 硬件 + 二次元主题。openvela 的强项正好是：RTOS 实时系统 + 快应用 UI + AI 接入（百炼/TFLite）+ 现成的图形库（LVGL/ThorVG/Lottie 动画）。

下面给你几个能落地、且切中「二次元」的创意，分几类：

## 一、桌面陪伴类（观众缘最好，评委爱看）

1. **二次元 AI 语音管家「电子婆娘/虚拟守护」**  — 小摆件带屏 + 麦克风 + 喇叭。喊名字唤醒，二次元小人用 Lottie 动画/呼吸灯回应，能闲聊、报天气、讲故事。核心卖点：**表情状态机 + 情感语音** 。

2. **手办智能底座**  — 普通手办放上去，底座屏幕显示专属台词/LIVE 背景，按钮/Voice 触发动画全屏和呼吸灯联动。

## 二、可穿戴类（openvela 最擅长的赛道）

1. **二次元智能手环/手表（像素精灵桌宠）**  — 屏上养一只像素二次元精灵，走步喂它、聊天、换皮肤。用 Sifli SF32LB52 或现成 watch 板。

2. **痛T发光徽章 / 发饰**  — 表情随蓝牙开关、触摸变化的可穿戴小屏。

## 三、炫技类（硬件 + 视觉冲击）

1. **全息投影二次元精灵（Pepper's Ghost）**  — LED 屏 + 倒金字塔亚克力，次元壁打破呈现在空中，旁边 AI 对话互为呼应。

2. **点头娃娃/摇头公仔**  — 舵机 + 传感器，二次元角色对你的话点头摇头，情绪可视化。

我个人**最推荐组合** ：ESP32-S3 开发板（便宜、好买、都能买到）+ 一块 1.8\~2.4 寸 LCD + 麦克风/喇叭 →「**二次元 AI 语音桌宠** 」。理由：成本低、演示强、AI 语音 + 表情动画双亮点，代码也多在你自己仓里（openvela 里现成 LVGL + AI SDK）。

先帮我定个方向，我再给你出详细方案（硬件清单 + 仓内目录怎么搭

Asked user

你手上有**微芯润 Gemini 开发板（大赛指定硬件）** ，还想结合 **NFC 互动 + AI Passport** 。我先查一下这块板的规格，确认它的 MCU/屏/NFC 能力，好给你靠谱方案。

Searched 10 web pages

查清楚了。你这是 **全志 R528（润芯微 Gemini-S1）** ——官方兼容性认证的首款板：

- 双核 Cortex-A7 + **HiFi4 DSP** 、WiFi/BLE、**LCD 显示** 、**音频 I/O**

- 首款过 openvela 5.2 官方认证，厂商已有现成适配（`vendor/allwinnertech`）

- 定位智能屏/音响/语音助手，非常适合二次元桌宠

板子本身**不带 NFC** ，但预算内加一个 **RC522 / PN532 模块** （十几到几十元，走 SPI/UART）即可。这样 NFC + 二次元 + AI 就能串起来。

## 创意方案：NFC 集卡 × 二次元 AI 互动桌宠「次元契约」

**核心一句话** ：做一叠二次元角色 NFC 卡牌，往 Gemini-S1 桌宠上「哔——」一贴，屏幕立刻变身该角色、触发专属动画、AI 用该角色的人设跟你对话。

### 玩法交互

- **集卡** ：每张 NFC 卡 = 一个二次元角色（磁卡/亚克力滴胶卡，嘉立创打样代金券可用）

- **贴卡识别** ：贴上 → 手机/R522 读到角色 ID → 屏幕播放变身动画 + 呼吸灯变色

- **AI 对话** ：唤起百炼/大模型，用该角色的语气人设接话（TS 快应用或 LVGL C 应用）

- **记忆** ：卡上有 UID，可存好感度/每日打卡，桌面养角色

- **对战/收集解锁** ：多张卡组合触发特殊剧情

### 为什么能打（评委视角）

- **「NFC 卡」是便宜、可量产、有收藏感的实体周边** ，视觉和情怀十足

- 落到「AI 人设对话」这个 openvela AI 赛道核心能力上，能演示、能讲故事

- Gemini-S1 全栈都用上：屏(LCD)+声音(HiFi4 DSP)+WiFi/BLE(AI接入)+GPIO(NFC)

在动手写代码/搭目录前，我得先搞清楚你说的 **「AI Passport」**  具体是啥，好把方案接上它。

Asked user

我去看下这个 repo 是什么。

Searched 1 web page

I'll read the full repo output to understand what this project is.

Read 1 file

明白了，这两个硬件我理清楚了：

| 设备 | 芯片/能力 | 角色 |
|---|---|---|
| **润芯微 Gemini-S1** | 全志 R528：双核 A7 + HiFi4 DSP、LCD、音频 Mic/SPK、WiFi/BLE | 你大赛的主控终端（openvela），做「桌宠/音箱」 |
| **FoloToy AI Passport** | ESP32-C3：240×320 LCD(LVGL)、3 按键、ES8311 语音、BLE、电池 | 随身「可穿戴 AI」，做「个人 AI 身份/电子宠物」 |
| **NFC 模块/卡** | RC522/PN532，接在 Gemini-S1 上 | 二次元集卡，交互触发 |

## 整合创意：「次元契约 · 双端 AI 联动」

**一句话** ：一套二次元 NFC 角色卡，刷向 Gemini-S1 桌宠「契约启动」，屏幕变身该角色并以其人设 AI 对话；同时你随身戴的 **AI Passport**  亮起同款表情、同步这段「契约记忆」，出门它也认得你、会接续剧情。形成「**家中主控 + 随身 AI + 实物卡牌** 」三件套闭环，故事性和可演示性都强。

### 具体怎么串

- **NFC 触发** ：贴二次元角色卡 → Gemini-S1 识别卡 UID → 播放变身动画 + 换人设（百炼/通义接入）

- **AI Passport 联动** ：通过 **BLE**  与 Gemini-S1 互通，同步角色/好感度/NFC 契约数据到随身设备

- **情感展示** ：AI Passport 屏上二次元表情、语音回应；Gemini 桌宠承担重活的对话与服务

- **记忆与成长** ：NFC 卡存 UID，积分好感度、解锁剧情（NVS/文件持久化）

### 这条路线对评委的好处在哪

- **双硬件都用上** ，展示「多端联动」，不只是一块屏幕

- NFC 实体卡 = 有收藏感的周边，现场演示直观（贴卡就变身）

- 落到 openvela **AI 人设对话 + 多设备协同** 核心，能讲完整产品故事

在动手前确认一下范围，我好决定是先给你**详细方案/初始化仓库** ，还是先规划：

Asked user

好，先给你一份**创意可行性评估 + 技术方案** ，重点把「哪些容易、哪些坑、怎么绕」讲清楚，再决定投入。

## 一、总体判断

创意「NFC 集卡 × Gemini 桌宠 × AI Passport 随身联动」**成立且有差异化** ，但**落地关键不在 AI，而在「NFC 驱动」和「双端 BLE 互通」这两块系统层工作** 。这两块决定成败，AI 反而是最省力的部分。

## 二、分模块可行性

| 模块 | 依赖 | 难度 | 风险点 / 对策 |
|---|---|---|---|
| **AI 人设对话** （ASR→LLM→TTS） | openvela AI 子系统 + 百炼 SDK | ⭐ 低 | openvela 原生支持百炼/通义，Gemini 带 WiFi+Mic+SPK，链路现成 |
| **二次元动画/UI** （变身、表情） | LVGL + ThorVG/Lottie | ⭐ 低 | 有现成图形库；注意内存/资源放 Flash |
| **数据持久化** （好感度、契约档案） | nuttx FS（littlefs/fatfs）+ NVS | ⭐ 低 | 直接可用 |
| **NFC 读卡** | RC522(SPI)/PN532(UART) + openvela 驱动 | ⭐⭐⭐ 中高 | **openvela 大概率没有现成 MFRC522 驱动** ，需写个用户态 SPI 驱动。RC522 协议公开且成熟，可行；PN532 走串口协议更简单，可选 |
| **Gemini ↔ Passport BLE 互通** | 双边蓝牙协议栈 | ⭐⭐⭐⭐ 高 | Gemini 端 openvela 有 BLE 栈；**Passport(ESP32-C3/ESP-IDF) 目前只做「不可连接广播」demo** ，要做成可连的外设、外加人设，两边都要改，**是目前最大风险点** |
| **硬件采购** | NFC 模块 20\~40 元 | ⭐ 低 | RC522 几块钱、PN532 三四十，预算内 |

## 三、两个关键风险（必须先接受再动手）

**1. NFC 驱动要自己写** openvela 侧没有封装好的「刷 NFC 卡」现成接口，需要实现 `SPI + GPIO 中断 → 读卡 UID → 查角色表 → 触发状态机`。 这属于「新硬件外设接入」，正好可以走\*\*「新硬件适配」的加分维度\*\*，做好了反而是亮点。建议选 **RC522(MFRC522)** ：芯片文档全、示例多，SPI 驱动代码量可控（几百行）。

**2. 双端 BLE 协调是硬骨头** Passport 的蓝牙当前只是「广播存在(不可连)」，要变成「连上来联动」需要：

- Passport(ESP-IDF)：改造成可连接 GATT Server，暴露「角色/好感度/状态」特征

- Gemini-S1(openvela + 蓝牙框架)：实现 GATT Client 去连它

📌 **合规提醒** ：大赛要求「依托 openvela」。所以**Gemini-S1(openvela) 必须是系统中心 + 主交互** ，Passport 只当「被 openvela 驱动的 BLE 随身屏/附件」，AI 全部跑在 openvela 侧。Passport 本身跑 ESP-IDF 没关系，但不能是「第二个独立 openvela 系统」。

## 四、推荐 MVP 技术方案（先跑通，再玩花活）

Plain Text

```
1
2
3
4
5
6
7
8
9
10
11
12
13
14
```
```
二次元NFC角色卡(实体)
 │ 贴卡
┌─────────────────────────▼──────────────────────────┐
│ Gemini-S1 (R528 / openvela) ✔本系统中心 │
│ │ 用户态RC522驱动 → 读UID → 角色状态机 │
│ ├─ LVGL: 变身动画 / 表情 / 契约UI │
│ ├─ 百炼: 角色人设 ASR→LLM→TTS (WiFi) │
│ └─ 好感度/档案: littlefs 持久化 │
└───────────────┬─────────────────────────────────────┘
 │ BLE (GATT) 同步角色/状态
┌───────────────▼─────────────────────────────────────┐
│ AI Passport (ESP32-C3 / ESP-IDF) ✔可穿戴附件 │
│ LCD 表情/语音 / 亮灯 / 随身携带 │
└─────────────────────────────────────────────────────┘
```
**开发顺序（把最难的放前面验证）** ：

1. 先打通「**Gemini + RC522 读到卡 UID** 」（验证 NFC 可行性）

2. 再做「**读卡 → LVGL 变身 + AI 人设对话** 」（核心演示，不依赖 Passport）

3. 最后才做「**BLE 双端同步** 」（增量加分项）

## 五、现在需要你定的两件事

1. **Gemini-S1 的 openvela 编译环境** 你搭好了吗？（`repo init` + `build.sh` 能否出镜像、刷到板上跑起来）——这块不通，后面都白搭。

2. **Passport 定位** ：你打算让它成为正赛作品的一部分，还是只当参考硬件？我建议**先做单机桌宠（第1、2步），BLE 联动作为冲刺加分项** ，把风险高的排到最后。

要不要我先把 **NFC(RC522) + 变身 + AI 对话** 这块的具体实现方案（openvela 用户态驱动怎么写、目录怎么在 `app/` 下搭）细化出来？还是你先去把 Gemini-S1 烧录跑通，我们再看下一步。

本地编译环境先按照说明完成搭建

09 06, 12:09

TraeWork

Worked for 4h 31m

Thought

本地搭建开始前，先确认你 Windows 上哪些工具就绪（openvela 构建一般走 WSL/Linux 或原生符号链，Windows 需要先看环境）。

Ran 2 commands

工具基本就绪：git 2.49 ✓、Python 3.13.9 ✓、WSL2 带 Ubuntu（当前停止）✓、`repo` 未装 ✗。

openvela 标准构建走 **Linux/WSL** （prebuilts 以 linux-x86_64 为主），你这台是 AMD64 + WSL Ubuntu，路线确定：**用 WSL Ubuntu 建环境** 。

先确认当前目录的性质（它应该是团队仓、而非 openvela 工作区根），再决定在哪执行 repo init。

Ran 1 command

当前目录就是**团队仓** （手动 `git clone`），父目录里已有别的项目（还看到有个 `rfid` 和 `gem`，先不管）。要建 openvela 工作区，得在**独立的干净目录** 里做，且**在 WSL 里用 Linux 原生文件系统** 构建（`/mnt/e` 挂着 Windows 盘会暴慢）。

我来规划这次的搭建步骤

Updated todo

启动 WSL Ubuntu 并检查基础环境。

Ran 1 command

WSL Ubuntu 的磁盘镜像（ext4.vhdx）报 `FILE_NOT_FOUND`——发行版注册了但 vhdx 缺失，无法挂载。先定位一下。

Ran 2 commands

找到根因了：**Ubuntu 的 `ext4.vhdx` 磁盘文件丢失** （LocalState 目录是空的），发行版只是残留注册信息，无法挂载，所以启动失败。这不是配置问题，是发行版损坏，需要重建。

三个方案，需要你定一下（重建会重新下载 Ubuntu，大概 **10 分钟 + 约 2\~4GB 下载** ，C 盘要有空余

Asked user

重建 Ubuntu。先注销损坏的发行版，再重新安装

Ran 1 command

注销成功（现在 WSL 里没有任何发行版了）。开始重新安装 Ubuntu（用 `--no-launch` 避免交互式用户名设置，稍后以 root 进入再创建用户）。下载约 2\~4GB，放后台执行。

Ran 1 command

I'll wait for the install to complete.

Read 1 file

日志还空，检查安装进展（是否已出现 Ubuntu 发行版）。

Ran 1 command

WSL 进程在跑（说明安装进行中），但发行版还未注册。稍等它下载完成

Ran 2 commands

I'll wait longer for the Ubuntu download, which can take a few minutes

Ran 1 command

安装卡住了（收进store间格GUI，3分钟无输出、未注册任何发行版）。不再干等这个路子，停掉它，改用**手动导入 Ubuntu 镜像** ——完全可脚本化，还能把虚拟盘放到指定位置。

先结束挂起的安装进程

Ran 1 command

挂起的安装已终止（后台任务也显示失败 exit 1 确认了）。改用**手动导入 Ubuntu 24.04 rootfs** 。先看磁盘空间，确定放哪。

Ran 1 command

C 盘剩 156GB、E 盘剩 388GB。我把 WSL 虚拟盘和 openvela 工作区都放 **E 盘** ，避免占用 C 盘系统空间。

先下载 Ubuntu 24.04 rootfs 镜像

Ran 1 command

404，换用 Ubuntu 官方 **WSL 专用镜像** （wsl 目录）。

Ran 1 command

直接列目录找真实文件名。

Searched 1 web page

`current/` 下没有 rootfs tar。列一下 minimal 发行版目录找真实的 root tar 文件名

Searched 1 web page

Found it. The correct file is `ubuntu-24.04-minimal-cloudimg-amd64-root.tar.xz`. Downloading it.

Ran 1 command

镜像下载完成（112MB）。导入为 WSL 发行版（虚拟盘放 E 盘

Ran 1 command

导入成功，Ubuntu 已注册运行于 WSL2。以 root 进入测试能否正常启动

Ran 1 command

WSL Ubuntu 24.04.4 启动正常（4 核，虚拟盘 956G 可用，放 E 盘）。环境重建完成。

Updated todo

在 WSL 里更新 apt 源并安装默认工具（同时探测到 github/googleapis 的连通性，判断 repo 工具下载要不要用镜像）。

Ran 1 command

网络全通（github 200、repo 源 200），无需镜像，apt 也正常。现在装 repo 工具、编译依赖，并创建一个普通用户 `vela`（openvela 构建不推荐 root）作为默认用户

Ran 1 command

repo 工具和各编译依赖装好了。创建用户 `vela` 并设为默认启动用户，然后重启 WSL 生效

Ran 2 commands

输出乱码了，直接查当前默认用户。

Ran 1 command

默认用户已切换为 `vela`。现在创建 openvela 工作区并执行 `repo init`（指向团队 manifest）。

Ran 1 command

PATH 继承了 Windows 变量（含空格/中文），`export` 触发词法报错。避免改 PATH，直接用完整路径调用 repo 工具重试。

Ran 1 command

`repo init` 成功，工作区已在 `/home/vela/openvela`。进入 `repo sync`，这会拉取 openvela 全量源码（**几个 GB，耗时较长** ，放后台跑

Ran 1 command, Updated todo

I'll check on the sync progress shortly. Let me wait and monitor the output log

Ran 1 command

sync 刚开始。输出被 `tail` 缓冲，只有结束时才回显。我改从工作区增长量来监控进度

Ran 1 command

同步进行中（已 0.57GB / 8 个子项目）。全量源码较大，继续等并监控

Ran 1 command

团队仓 `contest2026_236_wuxianshanyaoqiji` 已克隆进来，现 1.47GB。继续等待同步完成

Ran 1 command

增速放缓（1.58GB，可能在下大体积 prebuilt 二进制）。确认 sync 进程还活着

Ran 1 command

46 个 git 进程在跑，sync 正常进行中（并行克隆多个仓库）。继续等待

Ran 1 command

大小增长慢（可能正在下大体积 prebuilt 工具链）。继续等待，拉长间隔

Ran 1 command

进度加快（3.47GB，tests/ 也出来了）。继续等待同步完成

Ran 1 command

监控命令被转入后台了。直接查 sync 主任务日志

Ran 2 commands

10.07GB，主要仓库已下来大半（nuttx 还没就位，31 个进程仍在拉取）。继续等待

Ran 2 commands

11.64GB，nuttx 等大仓库还在拉。继续等

Ran 2 commands

14.47GB，nuttx 目录开始就位。继续等待收尾

Ran 2 commands

监控备份在跑，直接查当前状态。

Ran 1 command

19GB，各总目录已齐，git 进程只剩 10 个，接近收尾。等它跑完

Ran 2 commands

sync 主体完成（19GB），但有 **12 个项目因瞬时网络抖动（TLS recv error）没拉成功** ，