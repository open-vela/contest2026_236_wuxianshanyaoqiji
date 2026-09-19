# Gemini-S1 官方干净基线排查（进行中）

## 目标与验收

用户确认：Gemini-S1 / R528，板载 2.8 寸 SPI 屏。先实现亮屏和基本对话。
必须完成源码构建、完整镜像打包、烧录、真机显示及对话验证后，才能宣称完成。
本记录不采用现有固件、项目补丁或旧构建脚本作为依据。

## 官方来源与隔离

- [官方板级说明](https://github.com/open-vela/vendor_allwinnertech/blob/dev-ai-contest-2026/boards/r528/r528s3-gemini-s1/README_zh-cn.md)：比赛分支 `dev-ai-contest-2026`，小屏配置 `nsh_minidisplay`，使用根目录 `build.sh` 的 Make 构建。
- [官方清单](https://github.com/open-vela/manifests/blob/dev-ai-contest-2026/openvela.xml)：清单提交 `8b8d8c17e66c327cac7ab3e97ae039d829635a37`。
- 本次核验的 BSP 官方分支提交：`1676386193f0e710121e710935f1757c0f34b662`，已通过远端 `git ls-remote` 核实。
- 新源码目录（WSL）：`/home/vela/gemini-official-clean-20260919`。
- 审核源码快照：`/home/vela/gemini-official-audit`，通过上述已核实提交的 `git archive` 导出。
- `repo init` 使用本机已有 Git 对象缓存作为 reference，仅加速传输，不复制旧工作区的修改或产物。
- 首次全量同步包含多个不相关架构的模拟器；已中止并改为同步全部源码及 Linux x86_64 ARM GCC、build-tools、CMake、tools，保留官方清单不变。

## 官方源码中已经确认的显示链

1. `chips/r528/r528_boot.c`：`r528_late_initialize()` 中 `CONFIG_LCD_FRAMEBUFFER` 优先于 `CONFIG_LCD` 分支。小屏 LCD 分支调用 `board_lcd_initialize()`，再通过 `lcddev_register(0)` 注册设备。
2. `chips/r528/drivers/rtos-hal/hal/source/disp2/soc/ili9341_lcd_spi.c`：复位 PD19，片选 PD10，时钟 PD11，MOSI PD12，MISO PD13，DC PD14，背光 PD20。`board_lcd_initialize()` 初始化 ILI9341 后把 PD20 配置为输出高电平。
3. 官方 `configs/nsh_minidisplay/defconfig` 启用 `CONFIG_LCD`、`CONFIG_LCD_DEV`、`CONFIG_LCD_ILI9341`、`CONFIG_LV_USE_NUTTX_LCD` 和 `CONFIG_LUNCHER_MINI_APP`。最终 `.config` 仍需验证，不能只检查 defconfig。
4. `src/etc/init.d/rcS` 在 `CONFIG_GEMINI_S1_NSH` 下包含 `rcS.nsh`。后者挂载 `/resource`、`/data`，启动 ADB，并在 `CONFIG_LUNCHER_MINI_APP` 下运行 `luncher_mini &`。
5. `apps/luncher_mini/luncher_mini.c` 明确设置 `info.fb_path = "/dev/lcd0"`，检查 `lv_nuttx_init()` 的 `result.disp`，之后创建桌面。仅启动内核不能证明 UI 已运行。
6. NAND 官方分区表把本次内核打包为 `nsh.fex`，另含 `res.fex` 和 `usrdata.fex`。不可将裸内核文件当作 PhoenixSuit 完整镜像。

以上是官方实现事实，尚不足以认定旧固件黑屏的具体根因。

### AI 示例配置的显示路径差异

官方 [AI Agent Gemini-S1 说明](https://github.com/open-vela/packages_ai_agent/blob/dev-ai-contest-2026/defconfigs/gemini-s1/README.md) 提供完整配置及音频补丁。
远端 AI Agent 分支当前提交为 `e65550f18759f086d7f544edcf17d1e31223244f`。
比较两份官方 defconfig，AI 示例另外启用了 `CONFIG_LCD_FRAMEBUFFER=y` 和 `CONFIG_LCD_EXTERNINIT=y`。
这会使 `r528_late_initialize()` 进入 `r528_disp_init()`，不进入后面的直接 LCD 初始化及 `lcddev_register(0)` 分支。
同时 `luncher_mini` 仍然在 `CONFIG_LV_USE_NUTTX_LCD` 下打开 `/dev/lcd0`。
因此不可未经核对直接覆盖整份 AI 配置；须检查最终配置、实际链接到的 framebuffer 实现和设备节点。
这是一项候选问题，并非已经证实的真机黑屏原因。

官方 AI 修复脚本涉及媒体 graph/criteria 以及 DMA、中间件、FFmpeg 补丁，应在需要语音时按官方说明逐项验证，不属于屏幕初始化修复。

## 当前环境与限制

- 当前 WSL Ubuntu 24.04，约 11 GiB RAM、4 GiB swap，4 个 CPU。
- 官方 Ubuntu 入门文档只声明支持 Ubuntu 22.04，且明确未支持 WSL；这是本次构建的环境偏差，需记录实际构建结果。
- 初次检查及随后检查的 `adb devices -l` 均为空，Windows 未检测到匹配的板卡 USB / 串口设备。烧录及屏幕验证待实物连接。
- 源码同步日志：`/home/vela/gemini-official-sync-targeted.log`。
- 原样小屏基线已成功编译并完成镜像完整性检查；尚未烧录、尚未验证对话。
- 后续 Windows 检查发现 `ROOT\\USB\\0001`，硬件 ID `USB\\VID_1f3a&PID_efe8`，服务 `usbUDisc`，ProblemCode 10。它是错误状态的根枚举驱动条目，不能据此断言物理 USB 烧录设备可通信。
- 用户说明开发板已连接，但当前烧入固件可能有问题。已请用户恢复确认能亮屏的官方包、退出 PhoenixSuit 并保持连接，以恢复设备调试通道；新固件仍独立源码构建。

## 已完成：官方原样基线构建及打包

- 官方 ARM GCC 13.4.0，使用 `build.sh .../configs/nsh_minidisplay/ -j4`，未修改 BSP 驱动源码。
- 首次源码编译完成，链接因正在下载的 `libquickapp.a` 仍为 LFS 指针而失败；下载完成后重试链接成功。
- ARM QuickApp 库 SHA-256：`34d2aad207edeccfc795b1fb7e08f329ab84c4f59eabdbd10677f0333d804768`，与官方 LFS 对象匹配。
- `vela.bin` / `nsh.fex` 为 7,345,072 字节，未超过官方 bootloader 分区的 16 MiB 容量。
- 最终配置确认为 `CONFIG_LCD_DEV=y`、`CONFIG_LCD_ILI9341_HARDWARE_SPI=y`、`CONFIG_LCD_ILI9341_IFACE0_LANDSCAPE=y`、`CONFIG_LCD_ILI9341_IFACE0_RGB565=y`、`CONFIG_GEMINI_S1_NSH=y`、`CONFIG_LUNCHER_MINI_APP=y`；没有开启 `CONFIG_LCD_FRAMEBUFFER` / `CONFIG_LCD_EXTERNINIT`。
- `savedefconfig` 自动移除了 9 项冗余或未生效的旧配置；该变化来自官方构建入口，并非手动裁剪。
- 按官方 README 执行 `source envsetup.sh; lunch_nuttx r528s3-gemini-s1; pack`，产生完整 IMAGEWTY 镜像。
- 官方脚本对 Gemini-S1 固定调用 `prepare_for_128Mnand()`，所以原始文件名含 `128Mnand`；这里未擅自按文件名改动官方分区表。
- `pack` 返回 1 的末尾原因是 `do_finish()` 最后一个可选 `.hooks/post-dragon` 文件存在性测试为假，虽然 Dragon 已报告成功。
- `boot0 checksum fail` 来自官方脚本无条件更新 SD 启动块的调用。NAND 容器实际使用 `boot0_nand.fex`；独立验证确认其 eGON 校验正确，`fes1.fex` 校验也正确。
- `ap.fex` 复制提示来自通用资源打包逻辑；此 NSH 分区使用 `nsh.fex`，已确认它完整出现在容器中。
- 构建仍有官方代码警告（蓝牙类型不一致、NAND memcpy 静态警告等）；编译成功不代表这些警告已完成运行时验证。

### 基线产物

目录：`firmware/official-clean-20260919/`。

- `official-nsh-minidisplay.img`：29,248,512 字节，SHA-256 `24f286127138f8f67b8167705fb830db7a2dfb2b0a17462ae4a1f6da1a43c4c4`。
- `baseline.config`、`baseline.elf`：配置及调试 ELF。
- `gemini-official-provenance.json`：实际同步仓库的提交号。
- `gemini-official-baseline-verification.json`：镜像与六个输入组件逐字节匹配、启动块校验报告。
- 构建链接及打包完整日志。

独立核验工具：`tools/verify_official_image.py`。报告明确 `hardware_verified=false`。

## 对话版本（已构建、打包并校验，待真机）

- 新应用 `app/gemini_chat_minimal`，使用官方 `/dev/lcd0` 后端、`/dev/input0` 触摸和 `velaclaw` / `voice_channel` API。
- 界面适配实际显示分辨率，显示识别文字和模型回复；录音、识别及朗读在工作线程执行，只有 UI 线程操作 LVGL。
- AI 初始化完成通知后才开放输入，避免初始化消息队列前发送请求。
- `tools/prepare_official_chat.py` 从官方 BSP 提交读取小屏配置，建立独立 `configs/qiji_chat`，保留原显示路径，关闭官方桌面自启，避免两个应用争用 LVGL。
- 官方 `packages/ai_agent/fix_gemini_s1.sh` 已执行，三个跨仓补丁均成功应用，没有跳过或失败。只在对话版本使用这些官方音频修复。
- Wi-Fi、模型、ASR/TTS 凭据尚待设备侧配置及实际联网验证，未编入任何密钥。

### 真实链接错误及修正

第一次对话构建的源码编译通过，链接阶段暴露三个依赖问题：

1. `mbedtls_net_*` 未定义。原始小屏 defconfig 明确关闭 `MBEDTLS_NET_C`，AI 的 TLS 及语音 WebSocket 源码直接调用这些接口。对话配置中启用它。
2. `popen` / `pclose` 未定义。AI Agent `src/infra/network_manager.c` 使用这些接口；根据官方 `apps/system/popen/Kconfig` 启用 `PIPES` 和 `SYSTEM_POPEN`。
3. `sws_*` 未定义。板级 `scripts/Make.defs` 在 `CONFIG_QUICKAPP=y` 时以 `--whole-archive` 强制链接 `liblibmedia.a` 等预编译库，导致媒体源码补丁不构成唯一实现且预编译库要求未启用的视频缩放依赖。参照官方 AI 示例关闭 QuickApp、UIKIT、feature、QuickJS 等不需要的组件，使用本次源码构建的媒体实现；无需修改显示驱动或强行添加不需要的视频功能。

第二次干净构建成功，`qiji_chat_main`、`qiji_config_main`、`qiji_chat_agent_ready`、mbedTLS 网络接口及 popen 均已在调试 ELF 中确认。
对话版 LCD、SPI、TPADC 配置集合与原样基线比较完全一致。
预处理后的开机脚本包含 `mediad &`、`qiji_chat &`、`ai_agent &`，不包含 `luncher_mini &`。

### 最终对话产物

- `firmware/official-clean-20260919/qiji-chat.img`：27,407,360 字节。
- SHA-256：`777e4e7f97a2dd1221c58fc60a06af8d05f4a7362295e3c5f560881a8201e393`。
- 内核 `nsh.fex`：5,503,488 字节，小于 16 MiB 分区。
- NAND/FES 启动块校验通过，六个输入组件均完整出现在 IMAGEWTY 镜像中。
- Windows 复制后的两份镜像 SHA-256 与 WSL 核验报告一致。
- `chat.config`、`chat.elf`、构建日志、打包日志和 vendor/agent/media/FFmpeg 补丁一起保存。
- 应用使用方法见 `app/gemini_chat_minimal/README.md`。

### 尚未完成的验收

最后一次 Windows 检查仍没有可通信的开发板 USB / ADB 设备（`adb devices -l` 为空，未检测到对应物理 USB VID）。
因此没有执行烧录，没有声称新固件已亮屏，也没有完成触摸、录音、扬声器或真实云端回复验证。
需要用户完成已请求的官方原包恢复并保持 USB 连接，之后继续设备日志采集、烧录及实测。
原固件黑屏的具体原因仍不能仅凭编译或配置差异下结论。

## 后续现场验收更新（2026-09-19）

用户确认本次 qiji-chat.img：屏幕亮起，基本文本对话可用，语音未成功。
此后电脑 ADB 已连接开发板，uname 返回 NuttX 0.0.0 dd92bcf4257 Sep 19 2026 02:05:25 arm nsh，qiji_config status 返回 AI Agent ready。
前文“尚未上板”是当时状态；原镜像核验报告保留为构建时证据，最新状态见 release.json。
未完成语音与长时间稳定性验收，未由此断定此前黑屏的唯一根因。
