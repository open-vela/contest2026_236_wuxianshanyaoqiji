# 藤田琴音 v0.4.0 候选固件

qiji-chat-kotone.img：新增官方来源性格与人物关系知识卡、独立会话及括号动作过滤。保留分层动画、ENTER、Material 图标、朗读滚动与阿里语音链路。

板端编译、7 项主机回归、12 个云端角色探测、24 个图片资源与镜像完整性核验完成。云端原始回复曾出现括号动作，板端已加过滤；模型仍可能 OOC，不代表全剧情通过。设备未连接，尚未烧录或实机验收。通用镜像无 Wi-Fi 密码和云端 Key。

保留数据升级时，请运行 source/tools/deploy_kotone_persona.py 更新已有 SOUL；工具会备份并读回核对，不清除历史和 Key。详见 source/docs/kotone-persona-20260920.md。
