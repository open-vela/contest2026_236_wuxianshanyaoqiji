# logs/ — AI Coding 日志目录

存放你在开发中与 AI 工具的对话日志，和作品代码一并提交。

> 当前包含本项目 9 个 Codex Desktop 会话的兼容补采：1,766 个事件，经过凭据脱敏与未修改的官方格式校验。清单标为部分采集，自动采集尚未启用，比赛认可范围待确认。详见 [兼容补采说明](../docs/contest/Codex兼容补采说明.md)。历史 Markdown 为人工开发笔记，不是原始会话。

## 目录结构

```text
logs/
└── <github_login>/              # 你的 GitHub 用户名，一人一目录
    ├── manifest.json            # 会话清单
    └── <date>/                  # 日期 YYYY-MM-DD
        └── <tool>__<sid>.jsonl  # 一个会话一个文件（工具名与 session id 用 __ 连接）
```

- `<tool>`：`claude-code` / `opencode` / `codex` / `kiro`
- 每个 `.jsonl` 每行一个事件；本批由项目兼容解析器读取真实 Codex 原生记录，复用官方写出函数生成，附 `manifest.json`、原始来源哈希和采集范围说明，不冒充官方完整自动采集。

导出与提交的完整步骤、字段定义见[《AI Coding 日志归集与提交手册》](https://github.com/open-vela/docs/blob/dev-ai-contest-2026/zh-cn/contest_2026/ai_coding_log_guide.md)。
