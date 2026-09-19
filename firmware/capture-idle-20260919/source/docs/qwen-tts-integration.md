# Qwen Audio 3.1 TTS 语音合成

2026-09-19：按用户指定接入 `qwen-audio-3.1-tts-flash`。默认官方系统女声 `longanlingxi_v3.1`（龙安灵希），风格为自然、亲切、轻快、略带笑意，情绪适度。

## 当前链路

阿里 Paraformer ASR → 豆包拟人模型 → 千问 TTS → Gemini-S1 PCM 播放。
语音识别和合成共用已保存的北京百炼 Key（`aliyun_asr_key`）；文字模型仍是用户此前选定的豆包，不在本次更换。文字输入和录音输入得到的回复都会朗读。

固定情绪指令由 TTS 根据文本执行，尚未实现逐轮模型情绪标签、嘴型同步或打断对话。

## 官方依据

- [模型说明](https://help.aliyun.com/zh/model-studio/qwen-audio-3-1-tts-flash)
- [模型专属音色列表](https://help.aliyun.com/zh/model-studio/qwen-audio-tts-voice-list)
- [WebSocket API](https://help.aliyun.com/zh/model-studio/cosyvoice-websocket-api)
- [客户端事件](https://help.aliyun.com/zh/model-studio/cosyvoice-client-events)
- [服务端事件](https://help.aliyun.com/zh/model-studio/cosyvoice-server-events)

使用现有北京域名 `dashscope.aliyuncs.com`，TLS 校验证书和域名。run-task → task-started → continue-task → finish-task → 接收 binary PCM / task-finished。没有混用 qwen3-tts-flash 的接口。

## 实现与验证

- 共用阿里 ASR 中的 WSS 传输，ASR/TTS 分别创建会话。修复官方流式 TTS 固定调用火山后端的问题。
- 二进制帧按不超过 16 KiB 分块接收，可处理较大帧、分片和跨帧 PCM 奇数字节，不把整个音频放进内存。
- 流式播放请求 24 kHz、单声道 PCM16，匹配官方实际播放参数；批量合成请求 16 kHz，匹配 voice_tts_synthesize 接口约定。
- 正确处理 media_player 短写，保留播放错误，发出 EOF 后等待播放完成再关闭，避免收完网络数据就截断句尾。等待使用单调时钟和期限。
- 默认选择 aliyun TTS，可切换音色/自然、开心、温柔风格并持久化。
- 电脑运行固件相同 C 代码，真实云端测试：自然样本 4.77 秒，首批 PCM 642 ms；温柔样本 4.93 秒，首批 PCM 1708 ms。均为单次结果，包含连接开销，不是板端延迟承诺。
- ASR 回归仍识别出“你好，我是启迹。今天天气怎么样？”。角色名同音字问题仍存在。
- 主机播放契约测试覆盖短写、EOF 完成、写入错误和取消；不等同硬件扬声器验收。
- 温柔样本第一次被 WSL DNS 解析阻塞，取消后重试通过；DNS 仍由系统解析器控制，TLS/网络读写有独立截止时间。

试听文件：`docs/assets/qwen-tts/lingxi-natural.wav`、`lingxi-gentle.wav`。这两段为本次模型生成的音频。

## 构建

在已经应用官方音频补丁的固定源码树执行，勿重复运行官方音频补丁：

```sh
python3 tools/prepare_aliyun_tts.py /home/vela/gemini-official-clean-20260919
cd /home/vela/gemini-official-clean-20260919
./build.sh vendor/allwinnertech/boards/r528/r528s3-gemini-s1/configs/qiji_chat/ -j4
source build/envsetup.sh
cd vendor/allwinnertech/lichee
source envsetup.sh
lunch_nuttx r528s3-gemini-s1
pack
```

仍为本机 WSL2/Ubuntu24.04 的实测构建，官方支持环境是 Ubuntu22.04。

## 上板

新镜像 `qiji-chat-qwen-tts.img`。成功保留 /data 时复用先前保存的阿里 Key，TTS 默认已选 aliyun；格式化升级后用 `tools/configure_gemini.ps1` 和 `tools/configure_aliyun.ps1` 重新配置。

```text
qiji_config tts_style natural
qiji_config tts_style cheerful
qiji_config tts_style gentle
qiji_config tts_voice longanlingxi_v3.1
qiji_config speak "你好，我是绮迹。"
qiji_config test_tts "你好。" /data/qiji-tts-test.pcm
```

后两条分别为直接播放和保存 16 kHz PCM 文件；`test_tts` 不播放。命令通过 ADB 非交互 shell 执行，交互 NSH 行长有限。完整配置读取不能依赖容易截断的 ADB 短输出。

当前新包尚未烧录，麦克风、扬声器和端到端语音对话仍待实机验证。本次向旧固件推送试听音频后 ADB 未结束响应，不能据传输进度判断已经播放。
