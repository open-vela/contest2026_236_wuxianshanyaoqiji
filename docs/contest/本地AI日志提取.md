# 本地 AI 会话提取记录

检查日期：2026-09-19。只归集本项目，不上传或改写原始记录。

## 本机发现

| 客户端 | 发现内容 | 本次处理 |
| --- | --- | --- |
| TraeWork CN / 本机目录 TRAE SOLO CN | `C:\Users\zxz12\AppData\Roaming\TRAE SOLO CN\ModularData\ai-agent\database.db`，约 1.30 GB | 文件头不是标准 SQLite；只读 SQLite 打开失败，未解密、未修改，也未复制整个混合项目数据库 |
| Trae | `C:\Users\zxz12\AppData\Roaming\Trae\ModularData\ai-agent\database.db`，约 839 MB | 同样不能作为普通 SQLite 直接导出 |
| WorkBuddy | 本项目两份原生 JSONL，总计 8,038,271 字节 | 已逐字节复制，SHA-256 校验一致 |

TraeWork 与 WorkBuddy 是不同产品；本次成功提取的是 WorkBuddy，不能据此声称 TraeWork 会话已提取。

WorkBuddy 两份记录分别有 715 和 772 个事件；消息记录分别为用户 18 / 助手 128，以及用户 3 / 助手 44。会话创建日期为 9 月 13 日与 9 月 15 日，索引更新时间均到 9 月 18 日。这些计数不是有效开发工时。

私有备份目录：`artifacts/private-ai-logs/20260919T150059Z/`，内含原始 JSONL 和 `manifest.json`。目录已加入 Git 忽略并验证生效。原始记录中检测到疑似 Key，未在终端展示内容，不能直接作为公开材料上传。

再次提取可运行 `python tools/extract_local_ai_evidence.py`。脚本按项目工作目录精确选择 WorkBuddy 会话，检查 JSONL 格式、工作目录和复制哈希，只输出统计，不改变原始会话；它不是比赛官方格式转换器。

## Trae 客户端提取入口

1. **TraeCode / 旧 SOLO 模式：**官方 2026-03-26 更新说明支持导出历史对话。SOLO 在多任务面板导出，IDE 在历史对话旁的按钮导出。选择本项目真实历史会话，保留导出文件原样。
2. **TraeWork CN：**当前官方快速开始明确记载右击任务 → 分享 → 选择对话 → 生成图片并下载到本地；这可以保留可见对话佐证，但不等同于完整机器可读日志。若本机任务菜单另有“导出对话”，优先保留该原生导出文件。尚未确认本机 TraeWork 是否提供完整 JSON 导出。
3. 导出的本项目文件放入 `artifacts/private-ai-logs/trae-import/`，随后核对时间、轮次、工具调用是否完整，并计算 SHA-256。不要把包含账号信息的整库当作项目日志上传。

## 比赛接收边界

当前官方手册列出的工具是 Claude Code / AIoT-IDE、OpenCode、Codex；未列入 TraeWork 或 WorkBuddy。手册同时说明其他第三方工具的对话无法计入有效工时。因此原生导出可先作为开发过程补充证据，是否允许补充提交需要组委会确认，不能保证满足 AI Coding 日志评分项。

官方还明确禁止修改日志冒充原始内容。现有 `logs/gemhermit/2026-09-06/trae__dev-environment-and-build.md` 是人工摘要，已修正其“可转换为原始 JSONL”的表述。不会补造时间、思考过程、工具调用或统计。

## 官方依据

- [TraeCode 更新日志](https://docs.trae.cn/ide_changelog)
- [TraeWork 快速开始与分享对话](https://docs.trae.cn/work_trae-work-web-and-desktop-quickstart)
- [比赛 AI Coding 日志手册](https://github.com/open-vela/docs/blob/dev-ai-contest-2026/zh-cn/contest_2026/ai_coding_log_guide.md)
