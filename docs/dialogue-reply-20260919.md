# 识别后只回复“让我查一下”的修复

2026-09-19，设备已确认运行 capture-stop 包（构建时间 18:45:22），用户确认识别正常。实际日志中停止录音 9 ms、ASR finalize 36 ms，随后豆包拟人模型调用成功，2033 ms 返回 110 字节正式回答。上述时间来自一次实机操作，不代表平均延迟。

正式回答未显示的原因是官方 `agent_loop.c/send_working_status()` 在请求开始时向 `local_client` 发送“让我查一下…”等提示，而官方 `velaclaw_client_local.c/tap_callback()` 是一次性回调：第一条消息就清空回调。提示被界面当成答案朗读，约两秒后真正的答案仅进入同步回复缓存，界面收不到。

修复让 `local_client` 与官方已有的 voice/quickapp 通道一样跳过工作提示，保留界面自身的“正在等待模型回复”。正式回复仍走官方模型、会话历史、消息总线与客户端回调。没有过滤具体文案，也没有用固定回答替代模型。

同一次测试还发现朗读结束后 `mediad` 因 `ff_inlink_request_frame()` 的 `!li->status_in` 断言退出。官方最小播放图为 `abufsrc → volume → adevsink`；unlink 产生的 EOF 到达设备 sink 后，`adevsink_activate()` 没有确认结束状态就继续请求数据。修复先处理已排空输入的结束状态并停止 sink。下一次连接仍由官方 `audio_set_format_config()` 清除链路结束状态、重新配置；保留 FFmpeg 断言，未改为忽略异常。

## 验证

`tools/asr_host/test_dialogue_reply.py` 编译实际源码中的工作提示函数、完整本地客户端实现和设备 sink 激活函数，用桩模拟消息总线、音频队列及设备：

- 连续三次请求只由正式回答触发回调，CLI 进度提示仍保留。
- EOF 前先消费三帧音频，EOF 后不再请求结束的链路；覆盖三次重新连接、重复结束事件与错误传播。

主机测试通过。旧包实机已验证识别与豆包返回；新包正式回答显示、朗读和连续录音仍须烧录后验收，不能由主机测试推断成功。

### 烧录后 ADB 实测（20:04–20:05）

设备版本已核验为 `Sep 19 2026 19:50:54`。恢复阿里云、豆包配置并读回校验，断电重启后两个 Key 仍与已配置值一致。2F 自动连接获得 `192.168.5.158`，网关 ping 两次均成功（6–7 ms）。软件 reboot 曾进入全志 USB 烧录模式，用户关闭烧录工具并断电上电后恢复；没有将此过程记录为自动重启成功。

通过 `qiji_config ask` 连续提交两条测试文本，正式回复都进入 UI 共享状态，最终 `busy=0`、状态“可以继续对话”。豆包调用分别用时 889 ms、1274 ms；TTS 首块分别 585 ms、793 ms；朗读函数分别在 2730 ms、9820 ms 正常结束。第二轮结束后 `mediad` 仍存活，日志没有再次出现播放 EOF 断言。

这验证了新固件两轮文本请求、模型回复分发、TTS 数据及播放软件链路；没有远程确认扬声器实际听感，也没有替代用户的新固件麦克风端到端测试。冻结压缩包保留打包时的验收状态，本段为之后追加的现场记录。

## 构建与交付

在固定的官方源码树上执行 `python3 tools/prepare_dialogue_reply.py OFFICIAL_ROOT`，该入口依次应用此前的官方屏幕、网络、阿里语音、PCM 和停止录音修复，再应用本次两处修改。

继续使用官方 `build.sh vendor/allwinnertech/boards/r528/r528s3-gemini-s1/configs/qiji_chat/ -j4` 与 `pack`，核对最终镜像与 ROMFS。通用成果目录为 `firmware/dialogue-reply-20260919`，导出参数为 `--dialogue-reply`。本地 2F 调试包为 `qiji-chat-dialogue-reply-2f-debug.img`，交付入口为 `qiji-latest.img`。调试包仅含用户指定的网络配置，云端 Key 在烧录后单独恢复。
