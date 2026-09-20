# 录音 -5 与网络初始化修复固件

使用 qiji-chat-voice-fix-r2.img，适配 Gemini-S1 + 2.8 寸 SPI 屏。

修复增量构建遗漏 ROMFS 更新及媒体策略不匹配导致 mediad 退出、录音失败；NTP 放到联网后启动。格式化烧录仍需重新配置网络与 Key。

阿里 ASR + 豆包拟人 LLM + Qwen Audio 3.1 TTS（龙安灵希）。

官方 PFW 解析器测试通过，修复包麦克风与扬声器尚待实机验收。

详见 source/docs/voice-fix-20260919.md；tools/restore_board_config.ps1 可恢复配置。镜像不含密钥。
