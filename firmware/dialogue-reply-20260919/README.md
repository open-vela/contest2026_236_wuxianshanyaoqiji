# 正式回复与播放结束修复固件

使用 qiji-chat-dialogue-reply.img，适配 Gemini-S1 + 2.8 寸 SPI 屏。

移除输入框、发送按钮、屏幕键盘；头部合并一行，录音按钮加高为 58px。保留 R2 媒体与 ROMFS 构建修复。新增 48kHz 双声道播放转换、写入超时和语音锁限时等待。修复录音阻塞读取及跨线程关闭导致无法结束录音的问题，增加停止和 ASR 分段耗时日志。本次新增：本地客户端只接收正式回复，设备 sink 正确处理 EOF，避免媒体服务断言退出。格式化烧录仍需重新配置网络与 Key。

阿里 ASR + 豆包拟人 LLM + Qwen Audio 3.1 TTS（龙安灵希）。

前版实机已确认识别正常、豆包返回；本次回调和 EOF 主机回归通过，新包完整对话仍待实机验收。

详见 source/docs/dialogue-reply-20260919.md；tools/restore_board_config.ps1 可恢复配置。镜像不含密钥。
