# 绮迹 · 原创角色语音陪伴终端

2026 首届 openvela AI 硬件开发者大赛，AI 硬件产品创新方向。绮迹面向学习、工作间隙的短对话：点击大按钮说话，原创 Q 版少女接收语音、生成回答并朗读，减少在小屏上打字的负担。

项目使用 openvela / NuttX、LVGL、官方 ai_agent 和媒体服务。角色由 LVGL 分层图形绘制，**不是 Live2D/Cubism**。作品仍是开发板原型，尚未完成外壳与量产设计。

## 参赛入口与验收状态

- [作品介绍](docs/contest/作品介绍.md)；[4 分钟演示与验收清单](docs/contest/演示与验收.md)；[预提交说明](docs/contest/预提交说明.md)。
- [可复用的 Gemini 语音排障 Skill](skills/gemini-voice-diagnosis/SKILL.md)。
- 最新候选版本：`capture-idle-20260919`，板端标识 **Sep 19 2026 20:26:48**。源码、回归与镜像已验证，最新版板端多轮录音和人设效果待验收。
- 小屏和语音识别已在早先版本由用户确认；前版完成了两轮板端文本回复与播放软件流程。各版证据不可合并宣称最新版全链路通过。
- 本版为草稿预提交，尚未正式合入；`logs/` 仍需补充按官方工具导出的真实 Codex 会话。

当前累计准备入口为 `tools/prepare_qiji_persona.py`，在固定官方树及基础音频补丁上运行，再按下方指南构建。历史累计补丁不要与准备脚本重复叠加。

PowerShell 7 中运行 `./tools/restore_board_config.ps1` 恢复网络和 Key；如果 Wi-Fi 已连接，使用 `-KeepWifi` 保留连接。工具优先选择 SDK ADB，支持 `-AdbPath` / `-Serial`。

`python tools/board_acceptance.py` 做只读预检；加 `--exercise --rounds 3 --idle-seconds 30` 才会实际录音、调用云端并测试多轮。JSON 中 `complete` 只说明脚本完成，还须核对每轮结果；扬声器听感和识别准确性需要人工确认。

通用镜像 SHA256：`30052058d730c71fa351865e34b1bae08a1328c15ca127f7ee7ced83e62d7e92`。本地 `qiji-latest.img` 含调试网络配置，不作为公开提交镜像。新增项目代码采用 Apache-2.0，第三方组件保留原许可证；公共仓补丁仍须按官方提交指南整理独立 PR。

## 工程沿革与复现资料

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
