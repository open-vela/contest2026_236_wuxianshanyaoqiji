# “正在识别”长时间不结束

本次板上录音成功建立阿里流式 ASR 会话，并持续取得有声音峰值的 PCM。日志 18:28:49 开始录音，18:28:54 点击停止；18:30:47 仍为 busy=1，尚无 recording thread exit / ASR finish。这次等待发生在退出录音线程阶段，不能据此判断阿里模型识别速度慢。

官方 NuttX local socket 通过 FIFO 读取数据。原媒体客户端 accept 得到阻塞 socket；主线程先 shutdown/close，再 join 录音线程，未能让已进入 FIFO 的读取结束。源码现改为 SOCK_NONBLOCK，利用录音线程已有的 EAGAIN 重试与状态检查，在收到 STOPPING 后主动退出，再关闭 PCM socket，避免跨线程关闭竞态。适用于普通 stop 和 stop_with_text，也覆盖开始录音失败的清理顺序。

新增 capture stop requested / capture stopped / ASR finalize 日志，分开测量录音退出和云端最终识别时间。没有人为延迟识别，也没有降低云端质量参数。

回归测试直接编译本次媒体客户端 accept/read 函数及 voice_channel_stop_with_text，通过真实 Unix socket 模拟停止前没有新音频，验证 socket 非阻塞、线程先退出再关闭、进入 ASR finalize，连续三次停止成功，单次停止在主机小于 1 秒。该测试的 ASR 服务是桩，不代表真实云端延迟；板端 NuttX 录音结束与完整识别仍需烧录验收。

保留之前的播放格式、超时修复与简化界面。通用镜像 qiji-chat-capture-stop.img；指定网络的本地调试镜像 qiji-chat-capture-stop-2f-debug.img。新的代码不会改变板上当前已卡住的线程，需要烧入新镜像并重启。

本次检查还发现豆包 LLM Key 缺失，已用用户此前提供的 Key 恢复当前设备；格式化烧录后仍需通过 restore_board_config.ps1 恢复私有配置。

## 再次卡住时的设备版本核验

2026-09-19 再次通过 ADB 排查：设备 `uname -a` 和 `/proc/version` 都显示构建时间 `17:42:35`，对应冻结的 `voice-ui-20260919/chat.elf`。读取录音线程入口 `0x414be77c` 的前 48 字节，与该旧 ELF 的 PT_LOAD 段逐字节一致，与 `audio-unblock` 和 `capture-stop` 两个版本都不同。因此设备仍在运行旧代码，本次现象不能用来判断 capture-stop 修复是否有效。

设备日志 18:58:11 录音并取得 PCM，18:58:13 停止；此后录音线程仍等待信号量，没有新版本的 `capture stop requested`、`capture stopped` 或 `ASR finalize` 日志。状态为 busy=1、recording=0，符合旧版本卡在停止录音阶段的现象。

交付目录新增唯一推荐烧录入口 `qiji-latest.img`，内容与 `qiji-chat-capture-stop-2f-debug.img` 完全相同，SHA256 为 `a34de247e3d7eab3c05d9fd4231767a30fca125cd7ae4f37366e6741dc0925c1`，并附校验文件。没有重新构建或修改冻结成果。新镜像构建时间为 `18:45:22`；烧录后必须先核验板端版本，再恢复私有配置、校时并验证完整录音识别播放链路。
