# 2026-09-19 清理与成果固化

用户确认 qiji-chat.img 屏幕亮起、基本文本对话可用，语音未成功。
ADB 只读核验成功：NuttX dd92bcf4257，构建日期 Sep 19 2026 02:05:25；qiji_config status 返回 AI Agent ready。

## 已清理

- 移除旧 deploy/gemini-s1 叠加配置、自启片段及部署脚本，其显示初始化设置不同于本次官方小屏基线。
- 移除旧 wsl-build / wsl-pack / wsl-copy-fw / pack_full、修改 sst 的 fix_part、关闭媒体功能的 disable_quickapp。
- 移除项目根目录临时排查/修改脚本及旧链接补丁，保留本次 prepare_official_chat / verify_official_image。
- 移出 flash_tools 下历史 shell 脚本，避免继续使用旧 DDR、分区、启动块修改流程。
- 移出旧自制镜像及 LATEST_ANIME_VOICE 指针。保留原厂恢复镜像、设备备份、烧录工具和其他应用源码。
- 重写首页与构建指南；历史日志标为非操作指南；团队 manifest 的应用映射切换至 gemini_chat_minimal。

项目外备份：E:/Project/website/gemini-legacy-backup-20260919，逐文件清单和 SHA-256 见 removed-files.json。
没有删除或重置旧 WSL 源码树；本次使用独立官方树，后续也不得混用。

## 固化内容

固件哈希、实际配置、生成 defconfig、229 个仓库锁定 manifest、源码补丁、音频资源、自启配置、ELF、构建日志、用户验收状态及 ADB 记录。
成果 ZIP 包含最小应用源码和复现工具，内部 SHA256SUMS.json 校验每个文件，外部 .sha256 校验整个 ZIP。
本次没有重新编译或改写已通过用户验收的固件，也没有重新烧录。
语音仍未通过验收，不写成已完成。
