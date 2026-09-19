# 按官方手册执行 Codex 日志归集

后续进展：已完成明确标注范围的手动兼容补采，见 [Codex 兼容补采说明](Codex兼容补采说明.md)。下文保留官方工具原样运行时的故障证据，不代表补采后的文件数量。

日期：2026-09-19。结果：官方采集器已安装，当前项目 Codex 日志仍未成功归集；不能作为通过项提交。

## 官方版本与执行

- 文档：[AI Coding 日志归集与提交手册](https://github.com/open-vela/docs/blob/dev-ai-contest-2026/zh-cn/contest_2026/ai_coding_log_guide.md)。
- 工具仓：`https://github.com/open-vela/.claude.git`。
- 实际使用比赛分支 `dev-ai-contest-2026`，提交 `10743591d1034480ecee7c8ffffe9bb251d4474d`。没有把默认 dev 分支当作比赛分支。
- Windows Git Bash 下执行官方 `onboarding/install.sh --team-id contest2026_236_wuxianshanyaoqiji --github-login gemhermit`，成功退出。
- 原有相关配置先备份。官方身份文件与共享核心已安装，jsonschema 已安装。Git Bash 缺少 python3 命令，以指向本机 Python 的启动包装运行安装程序。
- 安装器在 Windows 写出的 Claude 钩子路径使用 `/c/...`，本机已将其两处命令改为实际 Windows Python 和脚本绝对路径，未改官方采集核心。

## 实测阻塞

### 1. 当前项目不满足工作区检查

项目位于 `E:\Project\website\contest2026_236_wuxianshanyaoqiji`。从这里向上找不到 `.repo/`。真正的官方 repo 工作区位于 WSL 的 `/home/vela/gemini-official-clean-20260919`。

以真实会话 ID、真实 transcript 路径和当前工作目录调用官方采集核心，返回：

```text
not inside an openvela workspace (no .repo/ found); collection disabled for this session.
```

这是手册规定的工作区检查。没有新建空 `.repo`、伪造历史工作目录或修改原始会话来绕过它。

### 2. 安装脚本没有注册 Codex 钩子

官方 `install.sh` 自身的帮助明确列出 `~/.codex/hooks/` 不属于安装范围；实际运行也没有创建 `~/.codex/hooks.json`。安装输出中的共享核心可供 Codex 使用，不等于已完成 Codex 钩子注册。

### 3. 当前官方核心不能解析本机 Codex 格式

在本机只读元数据中找到与本项目工作目录匹配的 17 个 Codex 会话条目。采样当前会话时有 3,925 条原生记录，类型包括 `session_meta`、`event_msg`、`response_item`、`turn_context` 等。

官方 `snapshot_core.py` 的主流程不区分工具，统一调用 `expand_claude_event()`。把该函数用于采样会话，输出事件数量为 **0**。仅统计记录类型与数量，没有输出会话正文、工具参数、内部推理或系统指令，也没有修改原文件。

因此，即使补装钩子并解决工作区位置问题，当前核心仍不能导出该格式的有效记录。[OpenAI 官方钩子说明](https://developers.openai.com/zh-Hans/docs/hooks)也说明 transcript 格式不是稳定接口；钩子事件字段相似并不意味着会话文件格式相同。

### 4. 官方补采命令没有 Codex 选项

实际执行：

```text
export-session.py --backfill --source codex
```

返回参数错误。当前支持的 source 是 `all, claude, sqlite, opencode, mimocode, cursor`，不包含 codex；`--all` 也不会自动补采 Codex。

## 自检结果

- `verify-setup.sh`：9 项通过、1 项失败。失败项只搜索 Claude 配置中的 `contest-snapshot.sh` 字符串，而官方 Windows 安装分支使用直接 Python 命令，存在检查与安装逻辑不一致。此脚本本身也没有验证 Codex 钩子。
- `export-session.py --list`：`No sessions in staging`。
- `validate-log.py logs/`：检查到 0 个 JSONL 文件、0 个事件；不能据此认定日志有效。运行时需要 UTF-8 终端输出，否则 Windows GBK 编码会在打印错误符号时另报异常。

## 后续处理

需要官方补齐适配本机 Codex 原生记录的解析和补采功能，或确认允许使用经过审核的兼容转换器；未来会话还应在真实 openvela repo 工作区内启动，并完成 Codex 钩子配置及信任检查。

历史记录保留在本机。暂不将原生记录直接公开上传：其中可能包含凭据、内部推理和系统配置，不是当前官方格式。此记录可用于向组委会说明阻塞，尚未代用户发送问题报告。
