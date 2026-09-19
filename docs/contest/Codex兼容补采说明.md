# Codex Desktop 兼容补采说明

2026-09-19 手动补采快照：9 个会话，1,766 个事件（用户 69、助手可见消息 329、工具事件 1,368），131 处脱敏。未修改的官方 `validate-log.py` 返回 0：9 个文件、1,766 个事件，ALL OK。

这是**项目自行实现的兼容补采**，不是官方采集器自动产生的完整记录；结构校验通过不代表组委会已认可有效工时或完整性。历史记录位于 `.repo` 工作区之外，清单中保留了原工作目录与这一限制。

## 来源与真实性

从本机 Codex 只读会话索引中，按本项目工作目录精确匹配到 17 个条目。读取原生 JSONL，不修改原文件。只有属于选定会话 ID、匹配项目路径、原生来源为 `vscode` 的消息段才参与导出；没有可用匹配事件的 8 个条目被跳过，没有为其补造内容。

本批会话原始客户端为 Codex Desktop，原生 source 为 `vscode`。因此在官方已有枚举内标为 `vscode_extension_partial`，健康状态为 `degraded`；每个会话附有明确的部分采集说明，`capture_method` 为 `manual-native-visible-backfill`。

导出保留原事件时间戳、消息文本和工具调用 ID，并标注每条事件的原文件行号。每个会话清单保存原始快照 SHA-256、字节数、导出 SHA-256、遗漏类型统计及脱敏次数。不会用本次导出时间代替原消息时间，不生成虚构模型、Token 消耗或工时。

同一原生文件中的 `response_item` 与 `event_msg` 可能重复描述同一消息；只取前者。不同会话的历史可能因分叉而重叠，不把会话数或事件数等同于独立开发工时。

## 采集边界

包括可见用户/助手文本、成对的函数与自定义工具调用及结果。排除系统/开发者指令、内部推理、会话压缩摘要、非选定会话段、未配对工具结果及图片/音频等非文本字段。

凭据在写出阶段按规则脱敏；原生文件保持原样。导出后再次扫描已知 Key 形式、GitHub Token 与调试网络密码，未发现匹配，并逐文件复核导出哈希。扫描不能代替全面人工隐私审核。

## 工具与复现

- `tools/collect_codex_native.py`：项目范围明确授权的手动兼容导出；每次必须使用新的输出目录，禁止覆盖既有快照。
- `tools/test_collect_codex_native.py`：7 项测试覆盖私有内容排除、项目与会话边界、子智能体排除、工具调用对应关系、损坏/未完成记录和二进制字段。
- 官方工具仓 `open-vela/.claude`，比赛分支提交 `10743591d1034480ecee7c8ffffe9bb251d4474d`。复用其 `append_events()` 和脱敏写出逻辑，使用其原样 Schema 与校验器；没有改宽校验规则。

在 Windows 中运行（替换本机路径）：

```powershell
python tools/collect_codex_native.py --project PROJECT_PATH --collector COLLECTOR_SKILL_PATH --output NEW_PRIVATE_OUTPUT --github-login YOUR_LOGIN --redaction-file PRIVATE_RULES_JSON
python tools/test_collect_codex_native.py
python COLLECTOR_SKILL_PATH/tools/validate-log.py NEW_PRIVATE_OUTPUT/logs
```

私有脱敏规则 JSON 是含 `pattern` / `replacement` 字段的数组；不要把其中的真实密码提交到仓库。只有完成格式校验和敏感信息检查后，才把导出的 `logs/<login>/` 放入项目。为保持哈希和 JSONL 原始字节，Git 禁止对日志作自动换行转换。

## 尚未完成

自动采集钩子仍未启用；官方解析器尚不能直接解析此原生格式，未来自动采集还需官方适配及真实 openvela 工作区。本次补采不改变 `.repo` 自动采集检查，也不伪造历史 cwd。是否计入比赛的 AI Coding 评分由组委会决定。
