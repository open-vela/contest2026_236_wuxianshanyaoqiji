# 妖气迹 · Gemini-S1 最小对话终端

队伍：236 无险山妖气迹。硬件：Gemini-S1 / R528 + 2.8 寸 ILI9341 SPI 屏。

当前固件：[重复录音卡顿修复与绮迹人设](docs/capture-idle-20260919.md)，产物 `firmware/capture-idle-20260919`。采集源在录音结束后关闭，避免空闲时积压音频；加入原创偶像少女绮迹的中文聊天设定。主机回归通过，新包板端效果待验收。

前版[正式回复与播放结束修复](docs/dialogue-reply-20260919.md)已通过板端两轮文本对话与朗读软件链路，播放结束后媒体服务保持运行。

前版[停止录音修复](docs/capture-stop-20260919.md)已在板端确认识别成功，豆包也在约 2 秒内返回；本次继续修复后续回复显示与朗读链路。保留[麦克风开启等待与播放格式修复](docs/audio-unblock-20260919.md)。

角色试验：[原创分层角色动画](docs/avatar-iteration.md)，使用 LVGL 绘制，待新固件上板验收。

界面沿革：[语音优先界面与 ADB 检查](docs/voice-ui-20260919.md)。移除触屏输入框和键盘，头部合并一行，录音按钮加高到 58px；历史产物位于 `firmware/voice-ui-20260919`，请使用当前固件。

构建修复沿革：[烧录后 Wi-Fi 未连接与录音 -5](docs/voice-fix-20260919.md)。R2 修复增量构建漏更新 ROMFS，核对最终镜像内的自动联网脚本和媒体配置；已包含在当前固件中。通用镜像格式化烧录后使用 `tools/restore_board_config.ps1` 恢复配置。

语音链路：[千问语音合成与情绪控制](docs/qwen-tts-integration.md)。阿里识别 + 豆包拟人对话 + Qwen Audio 3.1 TTS 龙安灵希女声，保留 Wi-Fi 自动连接和原创 Q 版女性角色。

2026-09-19 用户现场确认：`qiji-chat.img` 烧录后屏幕亮起，基本文本对话可用；**语音未成功**。这不代表长时间稳定性或完整比赛功能已验收。

## 固定成果

- [固件、配置、ELF、补丁和日志](firmware/official-clean-20260919/README.md)
- [构建打包指南](docs/build-pack-guide.md)
- [最小应用与设备配置](app/gemini_chat_minimal/README.md)
- [官方源码排查记录](docs/official-clean-audit-20260919.md)
- [版本与成果清单](firmware/official-clean-20260919/release.json)

对话包 SHA-256：`777e4e7f97a2dd1221c58fc60a06af8d05f4a7362295e3c5f560881a8201e393`。

## 构建原则

固定官方仓库提交号，从官方 `nsh_minidisplay` 生成独立的 `qiji_chat` 配置。保留官方 LCD/SPI/触摸配置，使用 `/dev/lcd0`，不引入 `LCD_FRAMEBUFFER` / `LCD_EXTERNINIT`，不修改 DDR、启动链或分区表。

官方通用指南支持 Ubuntu 22.04，明确不支持 WSL / Docker。本次成果实际构建于 WSL2 + Ubuntu 24.04，这是实测记录，不是官方支持声明。

## 项目边界

当前应用为 `app/gemini_chat_minimal`。原二次元应用、网页、QuickApp 和模板源码保留作后续开发素材，不纳入本次固件成果。NFC、角色记忆仍是规划。

旧 framebuffer 叠加配置、手动分区修改、关闭媒体功能及屏蔽编译错误的构建入口已移除。历史日志仅供追溯，不能作为当前构建指南。
