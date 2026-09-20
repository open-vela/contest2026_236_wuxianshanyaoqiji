# Gemini-S1 藤田琴音对话界面（v0.4.0）

角色行为、关系知识与来源见 [character/README.md](character/README.md)。旧版本的绮迹酱身份已停用；当前默认人设由知识卡生成，设备已有 SOUL 需要通过部署工具显式更新。角色迭代与测试记录见[本次说明](../../docs/kotone-persona-20260920.md)。

新增分层动画实现与安装入口：`tools/prepare_layered_ui.py`。使用 12 个活动部件和 4 个眼/嘴差分，支持呼吸、摆头、延迟发辫、眨眼、真实 PCM 音量嘴型；保留 8 张整图差分和缺资源回退。见[分层动画说明](../../docs/layered-ui-20260920.md)，尚待上板验收。

适配 Gemini-S1 的 2.8 寸 ILI9341 SPI 屏，以本次从官方比赛分支独立构建的 `nsh_minidisplay` 为显示基线。
当前界面为 240×320 竖屏：顶部 20px 小字状态轮播，右侧显示北京时间和版本号；中间 8 种动作位图、前景半透明对话、右下角浮动 44px 麦克风图标按钮，录音中显示停止方块；内外间距统一 8px，卡片圆角 16px、文本框圆角 8px。板上 ENTER 同样支持开始/结束录音，40ms 消抖、长按不连发。长回复在播放期间近似滚动，播放后可循环阅读。图片来源及边界见 ARTWORK.md。使用阿里 ASR / TTS，保留 ADB 文本诊断命令。
这不是离线大模型；没有联网或未配置服务时会显示错误，不生成假的 AI 回复。

## 当前验证边界

官方原样基线已编译、打包并校验；对话版本的构建状态见 `docs/official-clean-audit-20260919.md`。
2026-09-19 用户现场确认：对话包屏幕亮起，基本文本对话可用；语音未成功。尚未完成语音及长时间稳定性验收。屏幕输入框与键盘已移除，文本诊断可通过 ADB 输入。

## 构建依据与入口

官方来源：

- https://github.com/open-vela/vendor_allwinnertech/blob/dev-ai-contest-2026/README
- https://github.com/open-vela/packages_ai_agent/blob/dev-ai-contest-2026/defconfigs/gemini-s1/README.md
- https://github.com/open-vela/packages_ai_agent/blob/dev-ai-contest-2026/include/velaclaw/client.h

在独立同步完成的官方树中运行，本项目路径请按实际位置替换：

```sh
# 切换已有配置前，先按官方 build.sh 对原配置执行 distclean。
python3 /path/to/contest/tools/prepare_official_chat.py "$PWD"
bash packages/ai_agent/fix_gemini_s1.sh
# 官方音频补丁只在干净树执行一次；之后安装应用修复。
python3 /path/to/contest/tools/prepare_sprite_ui.py "$PWD"
./build.sh vendor/allwinnertech/boards/r528/r528s3-gemini-s1/configs/qiji_chat/ -j4

source build/envsetup.sh
cd vendor/allwinnertech/lichee
source envsetup.sh
lunch_nuttx r528s3-gemini-s1
pack
```

准备脚本使用官方 ILI9341 竖屏选项，同步适配 TPADC 触摸坐标，并增加应用、音频及 AI 所需选项。竖屏真机方向与点击效果待验收。
关闭 QuickApp 是为了避免板级 Make.defs 强制链接预编译媒体库，使官方音频源码补丁实际参与最终链接。
另外启用 `MBEDTLS_NET_C`、`PIPES`、`SYSTEM_POPEN`，对应 AI Agent 的 TLS 与网络管理源码依赖。

## 设备配置

烧录后关闭 PhoenixSuit，确认 `adb devices` 能识别设备。进入 `adb shell`。
以下命令中的占位符需要替换为自己的配置，不要把密钥提交到仓库。

保存并连接 Wi-Fi（重启时自动重连）：

```sh
qiji_config wifi "你的SSID" "你的Wi-Fi密码"
ifconfig wlan0
```

应用自启，**不要重复启动 `ai_agent`**。`qiji_config` 在 NSH 中调用已运行 Agent 的官方配置接口：

```sh
qiji_config status
qiji_config set_llm deepseek "你的模型API密钥"
qiji_config ask "你好，请做一句自我介绍"
```

实际模型预设可换成官方支持的 `mimo`、`qwen` 等；自定义接口沿用官方语法：

```sh
qiji_config set_llm "https://你的服务/v1/chat/completions" "模型名" "API密钥"
```

当前语音使用阿里云，北京 DashScope Key 用于 ASR 和 TTS：

```sh
qiji_config set_aliyun_asr "你的DashScope密钥"
qiji_config voice_status
```

凭据通过官方 config_store 保存到设备 `/data/ai_agent/config/`，固件中没有内置个人密钥。

## 验收顺序

1. 冷启动：屏幕显示界面；`ls /dev/lcd0 /dev/input0` 成功。
2. `qiji_config status` 显示服务已就绪，触摸按钮有响应。
3. 连网并配置模型后发送文本，屏幕显示真实模型回复。
4. 配置语音服务，点击说话后再点击结束，验证识别文字、模型回复和扬声器播放。
5. 断电重启后重复检查；没有服务配置时只验收亮屏，不宣称对话成功。

## 线程边界

只有 UI 任务调用 LVGL；工作线程执行录音、ASR、LLM 请求和 TTS。
Agent 回复回调只更新受互斥锁保护的文本，UI 定时器负责刷新屏幕。
Agent 完成初始化后通知界面开放输入，避免在消息总线未初始化时提交请求。

准备脚本已固化为安装本次成功构建经 savedefconfig 规范化的 qiji-chat.defconfig，并校验 BSP / AI Agent 提交号；不再随分支更新重新生成配置。
