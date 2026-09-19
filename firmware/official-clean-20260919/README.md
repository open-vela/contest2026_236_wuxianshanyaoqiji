# Gemini-S1 固定成果 · 2026-09-19

硬件：Gemini-S1 / R528 + 2.8 寸 ILI9341 SPI 屏。

用户现场确认：qiji-chat.img 已上板，屏幕亮起，基本文本对话可用；**语音未成功**。
ADB 只读核验：NuttX dd92bcf4257，qiji_config status 返回 AI Agent ready。
官方桌面基线包仅完成构建与镜像校验，未收到它单独的上板验收反馈。

| 镜像 | SHA-256 |
| --- | --- |
| qiji-chat.img | 777e4e7f97a2dd1221c58fc60a06af8d05f4a7362295e3c5f560881a8201e393 |
| official-nsh-minidisplay.img | 24f286127138f8f67b8167705fb830db7a2dfb2b0a17462ae4a1f6da1a43c4c4 |

这是基于官方源码构建的完整 PhoenixSuit 镜像，不代表官方发布或认证的二进制。
本次实际构建环境为 WSL2 + Ubuntu 24.04；官方通用文档支持 Ubuntu 22.04，不支持 WSL/Docker。

release.json 记录当前验收；原 verification.json 的 hardware_verified=false 是构建时记录，保留不篡改。
source-lock.xml 固定已检出仓库提交号；另附配置、ELF、补丁、媒体资源及日志。
复现见 ../../docs/build-pack-guide.md，设备配置见 ../../app/gemini_chat_minimal/README.md。
语音问题及长时间稳定性仍需继续验证。
