[English](passport-companion.md)

# 琴音与小澄：双硬件伙伴

系统边界：Gemini-S1 运行 openvela / NuttX，AI Passport 运行 ESP-IDF 5.5.3 / FreeRTOS。Passport 是跨系统接入的配套终端，并未移植 openvela；双机模式由电脑协调云端文字生成。

这版给 FoloToy AI Passport 加入原创角色「小澄」，与 Gemini-S1 上现有的琴音联动。
协调服务读取现有 `SOUL.md` 和角色名称，沿用藤田琴音设定，不恢复旧“绮迹酱”人设。
**第一版需要同一局域网内的电脑运行协调服务**，尚未实现脱离电脑的 BLE/NFC 联动，也不在 Passport 上运行大模型。

## 已实现的行为

1. 两块硬件分别向服务报到，双方在线且就绪后，首次自动开聊。
2. 琴音、小澄轮流说 6 句短话，两块屏幕都显示当前发言。
3. 收到双方确认，且发言设备播放完成后，才开始下一句。角色间传文字，不通过麦克风识别另一块板的声音。
4. 最后单独调用模型，仅根据实际完成的对话生成总结：聊了什么、最多两条可选建议、一个留给主人确认的问题。琴音朗读，两屏保留。
5. 结束、断线、播放失败或用户停止后，不自动重开。长按 Passport 确认键可重新开始双板对话，上下键翻看文字。
6. 双板聊天中长按 Passport 确认键或按 Gemini ENTER 可停止本轮。Gemini 当前短句会播完，Passport 在下一次音频读写边界取消。已发出的云端请求不会撤回，但迟到的结果会丢弃。

记录只存在电脑服务内存中，重启后清空；不自动录音，不推测用户未提供的经历，也没有实现长期共享记忆。

小澄现采用原创银发未来风形象：蓝紫外套、细化眼睛、耳机和发饰。五张原尺寸 RGB565A8 图像存放在 Flash 中，支持呼吸、眨眼及 PCM 音量驱动口型。眼睛进一步优化了圆润眼型、虹膜层次和半闭眼过渡。可编辑 SVG 和转换工具见 `assets/xiaocheng-future-v1/README.zh_CN.md`；真实 LVGL 预览见 `docs/assets/duet/xiaocheng-eyes-preview.png` 和 `.gif`。琴音原有素材保持不变；HTML 中的简笔琴音仅用于说明交互。

2026-09-20 界面调整：人物按 1.875 倍直接放大绘制，顶部名称、状态及电量压成一行 12px 字体；取消底部翻页提示。对话和总结采用人物前方的半透明浮层，正文保留 16px 中文，发言者固定在浮层顶部，正文单独滚动。上下键功能保留，每次滚动一行；不使用需要额外整图缓冲的缩放变换。
新版预览见 `docs/assets/duet/xiaocheng-overlay-preview.png`，独立固件与验证记录位于 `firmware/passport-overlay-20260920`，旧版 `duet-20260920` 保留。

后续银发版保留上述顶部和文字布局，将人物替换为 240x280 插画。配网修复版已实测 USB 配置保存、Wi-Fi 获取地址及局域网服务报到；这一结果不代表银发插画版本已通过设备验收。

再后续的 `xiaocheng-0.2.1-refined-eyes` 已在 COM3 从 0x10000 更新应用，保留原 Wi-Fi 配置。启动 ELF 身份匹配，30 秒观察内未见崩溃，并重新接入协调服务；用户已确认实机显示和眨眼正常。记录见 `artifacts/passport-device/20260920-eyes-result.json`，固件见 `firmware/passport-eyes-20260920`。此版本的语音、双设备对话、按键滚动及长时间压力测试尚未验收。

## 文件与构建

| 路径 | 用途 |
| --- | --- |
| `app/passport_companion/main` | ESP-IDF 应用、角色界面、中文字体 |
| `tools/duet/server.py` | Python 标准库协调服务、独立人设、轮次与总结、模型和 TTS 接口 |
| `app/gemini_chat_minimal/qiji_duet.c` | Gemini 局域网客户端，复用原界面与语音工作线程 |
| `tools/duet/preview.html` | 可交互的脚本预览，也可只读查看真实服务状态 |
| `tools/passport_preview` | 使用固件同一份绘图代码与字体的主机渲染程序 |

Passport 使用官方提交 `855d2106547988e33128e27aadff4fe98351fe14`，ESP-IDF **5.5.3**，依赖按官方 lock 固定。
准备脚本保留 BSP、引脚与分区表，替换编译入口，禁用未使用的 BLE，将 LVGL 内存池设为 40KB，并启用大字体偏移。

```sh
python tools/duet/build_font.py
python tools/prepare_passport_companion.py /path/to/dedicated-ai-passport-checkout
cd /path/to/dedicated-ai-passport-checkout
. /path/to/esp-idf-v5.5.3/export.sh
./tools/validate.sh
```

字体生成需要 Node/npm、Python fontTools 与网络。Noto Sans SC 实例化为 500 字重，使用 lv_font_conv 1.5.3 转为 16px / 2bpp，存放在 Flash。
另生成 12px 状态字体子集，字符清单来自界面、设备状态及桌面角色名称，记录在 `assets/xiaocheng-font/status-characters.txt`；修改固定提示或角色名称后，使用 `python tools/duet/build_font.py --status-only` 更新。
许可证见 `assets/xiaocheng-font/OFL.txt`，实际字符范围和源文件哈希见 `coverage.json`。
服务会拒绝字体不支持的模型输出，不用隐藏方框来掩盖缺字。源字体更新须核对记录的哈希。

Gemini 继续使用[现有固定构建流程](build-pack-guide.md)和已准备的官方树，联动客户端不修改板级驱动或分区。

## 先看效果

打开 `tools/duet/preview.html`，点击「播放脚本效果」；不会调用模型或假装已连接实物。
也可运行脚本模式服务及测试：

```sh
python tools/duet/server.py --demo
python -m unittest discover -s tools/duet -p test_server.py -v
```

测试覆盖实际 HTTP 握手、6 句对话与总结、鉴权、重复/过期确认、取消、断线、播放超时/失败和模型异常。实时模式出错不会偷偷改播脚本。

使用固件绘图代码生成预览：

```sh
cmake -S tools/passport_preview -B /tmp/xiaocheng-preview -DLVGL_SOURCE=/path/to/lvgl
cmake --build /tmp/xiaocheng-preview -j4
mkdir -p docs/assets/duet/frames
/tmp/xiaocheng-preview/passport_preview docs/assets/duet/frames
```

渲染程序检查 20,976 个基本汉字及一个故意缺失的字符。生成的动图见 `docs/assets/duet/xiaocheng-firmware-preview.gif`。
这是**主机渲染，不是实物拍照或上板通过记录**。

## 实时联动配置

### Passport 自己录音聊天

语音接入版中，中间确认键短按开始录音，再短按结束并发送；识别、生成或播放时短按取消。请等屏幕显示正在录音后再说话。录音采用 16kHz、16bit、单声道 PCM，最长二十秒，每次上传 1KB，不在设备上缓存整段录音。上传长时间阻塞或录音不完整会明确失败。长按确认键仍用于双板对话开始/停止，上下键滚动。单人语音会停止双板对话，并暂时将 Passport 标为不可参与，直到再次长按进入双板模式。录音、播放和采样率切换共用互斥锁。

`gemini_bridge.py` 直接调用现有 `tools/asr_host`，复用 Gemini 的 `qiji_aliyun_asr.c` 中 Paraformer 识别和千问 3.1 合成。文字模型复用 Gemini 保存的地址、模型名和密钥，小澄保留独立人设。Windows 默认通过 WSL Ubuntu 调用 `/home/vela/qiji-asr-host/qiji_asr_host`；可用 JSON 参数数组 `DUET_GEMINI_COMMAND` 覆盖命令，Linux 可用 `DUET_GEMINI_HELPER` 指定程序。密钥经标准输入传入，临时 PCM 用完删除。电脑内存只保留最近六轮已成功播放的对话。

Gemini 通过 ADB 连接后，可以导入其现有云端配置：

```sh
python tools/duet/configure_cloud.py --from-gemini
```

没有 Gemini 时，不带参数运行 `configure_cloud.py`，在本机交互填写接口和密钥，密钥不回显。配置只保存到已被 Git 忽略的电脑本地 `cloud.json`，不进入固件。停止旧服务后运行：

```sh
python tools/duet/run_live.py --model character
python -m unittest discover -s tools/duet -p 'test_*.py' -v
```

`--model character` 使用 `doubao-seed-character-260628`；`--model turbo` 使用 `doubao-seed-2-1-turbo-260628`。省略参数则沿用本地配置的模型。两个模型均已用真实接口调用验证，当前默认启用拟人模型。阿里云识别和合成复用 Gemini 的实现，不要求 Gemini 硬件在线。

2026-09-20 真实 HTTP 链路已通过合成语音测试：分块上传 → 识别 → 豆包回复 → 合成 → 音频下载约 7.2 秒。记录位于 `artifacts/passport-device/20260920-voice-http-cloud-test.json`。这不代表实机麦克风或扬声器验收。可手动运行 `python tools/duet/check_live_voice.py` 重测；会调用真实付费接口并停止当前双板对话，不会录音、播放或将测试对话加入用户历史。WSL 调用已限制 DNS 重试和 Linux 子进程时间，避免 DNS 隧道卡住后遗留进程。

`--demo` 模式会拒绝录音 AI 请求，不伪造识别结果或回复。必须分别实测麦克风录音、真实识别、模型回复及扬声器发声，才算完整链路验收。这版仍需要电脑，但不需要另一块硬件。

仅在本机环境变量中配置，不写入源码：

| 变量 | 含义 |
| --- | --- |
| `DUET_LLM_URL` | HTTPS chat-completions 地址，例如用户自己的豆包接口 |
| `DUET_LLM_MODEL` | 接口支持的模型或部署名称 |
| `DUET_LLM_KEY` | 模型 Key |
| `DASHSCOPE_API_KEY` | 小澄语音使用的北京地域百炼 Key |
| `DUET_TOKEN` | 双设备共用的局域网配对码，使用 32 位随机十六进制字符 |

```sh
python tools/duet/server.py --host 0.0.0.0
```

琴音使用设备现有 TTS 后端和音色；小澄的双机语音现复用 `gemini_bridge.py` 的单人语音路径，调用现有 `qwen-audio-3.1-tts-flash` C 后端，向设备发送经长度校验的 24kHz PCM16。2026-09-20 联调中旧 `qwen3-tts-flash` 路径返回 HTTP 400 / Arrearage，而现有 3.1 路径实测可用，因此已统一路径；旧 `DUET_XIAOCHENG_VOICE` 配置不再使用。这不是失败后的预录音降级，两台音色仍需现场比较。
`--text-only` 明确关闭双方语音，用于测试通信；`--manual` 关闭首次自动开聊。云端调用需要真实凭据与额度，脚本测试不代表云端验收。

两设备须能访问电脑的局域网 IPv4 地址和 TCP 8765 端口。默认仅监听本机，接实物时须加 `--host 0.0.0.0`。
板间原型协议为带配对码的明文 HTTP，仅面向可信局域网；云端请求使用 HTTPS，云端 Key 不下发到 Passport。

获得烧录授权并安装新固件后，配置 Passport：

```sh
python -m pip install pyserial
python tools/duet/configure_passport.py --port COM3 --host http://COMPUTER_LAN_IP:8765
```

工具交互读取 Wi-Fi 和配对码，密码不回显，仅写应用自己的 `qiji_duet` NVS 命名空间，成功后重启。
若设备初始化 NVS 失败，程序不会自动擦除原有数据。

USB 配置接收端会保留分段到达的 JSON，直到收到换行才解析；串口暂时没有数据时不会丢弃半条配置。超过 639 字节或包含 NUL 的整条输入会被拒绝，下一行可重新配置。回归测试位于 `tools/duet/test_config_line.c`。

安装 Gemini 联动版后，在其命令行配置：

```text
qiji_config duet COMPUTER_LAN_IP 8765 PAIRING_TOKEN
qiji_config duet_off
```

第一条启用，第二条关闭；本机命令和配置历史需妥善保管。停止后可长按 Passport 确认键重开，或带配对码调用 `POST /v1/start`。
实时模式的 start 请求可带不超过 160 字的用户话题 `topic`。

## 实物验收边界

行距微调版 `xiaocheng-0.3.1-spacing` 将对白每行步长从 31 px 缩至 20 px，上下键与自动滚动同步调整。人物、16 px 正文字号、对话框位置及语音逻辑保持一致。实际 LVGL 预览见 `docs/assets/duet/xiaocheng-spacing-preview.png`；这张图是主机渲染。

2026-09-20 已经用户授权，将 `xiaocheng-0.3-voice` 应用镜像烧入 COM3 的 `0x10000`，写入校验通过。分区表与此前眼睛优化版一致，NVS 未写入，设备沿用原 Wi-Fi 配置并恢复协调服务心跳。启动日志中的 ELF 标识与归档一致；30 秒内未发现崩溃。用户已确认中键录音、识别文字和语音回答正常；中途取消与长时间压力测试未验收。详见 `artifacts/passport-device/20260920-voice-result.json`。

编译、主机测试、实物测试分别记录在版本记录中。USB 枚举已找到 COM3 上的 ESP32-C3 原生 USB 设备，但这不等于中文、显示、音频或两板联动通过。

Passport 合并镜像从 0x0 烧录，将替换现有固件；填充区可能重置 NVS/PHY 数据，不能承诺保留出厂名片。应针对具体镜像取得授权，不以整片擦除作为常规前提。

待实测：屏幕方向/颜色、中文可读性、按键翻页、联网与播音时空闲堆及最大连续块、双方声音不重叠、真实播放结束判定、连续 10 轮无重启、断线/停止、两屏最终总结以及音色区分。
本版不包含 BLE/NFC、脱离协调服务运行、语音插话换题或持久共享记忆。
