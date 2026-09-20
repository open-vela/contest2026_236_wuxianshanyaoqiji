# 麦克风开启等待与播放格式修复固件

使用 qiji-chat-audio-unblock.img，适配 Gemini-S1 + 2.8 寸 SPI 屏。

移除输入框、发送按钮、屏幕键盘；头部合并一行，录音按钮加高为 58px。保留 R2 媒体与 ROMFS 构建修复。新增 48kHz 双声道播放转换、写入超时和语音锁限时等待。格式化烧录仍需重新配置网络与 Key。

阿里 ASR + 豆包拟人 LLM + Qwen Audio 3.1 TTS（龙安灵希）。

官方 PFW 解析器测试通过，修复包麦克风与扬声器尚待实机验收。

详见 source/docs/audio-unblock-20260919.md；tools/restore_board_config.ps1 可恢复配置。镜像不含密钥。
