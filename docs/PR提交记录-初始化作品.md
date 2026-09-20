# GitHub 提交记录：初始化参赛作品 PR

> 本文件为 TraeWork 会话《OpenEVLA 二次元硬件初始化》的导出记录。
> 会话来源：`https://share.traecontent.cn/share/F2VXX68-WYTMVU`
> 整理时间：2026-09-09

## 背景
把本地初始化的参赛作品（62 文件，Live2D 语音对话 WebUI + 开发环境记录）提交到大赛专属仓 `open-vela/contest2026_236_wuxianshanyaoqiji` 的 `dev-ai-contest-2026` 分支。因专属仓规则强制「PR + CLA」，最终走 fork + PR 流程完成。

## 执行过程回顾

| 步骤 | 状态 |
|---|---|
| 本地提交初始化作品（62 文件 / +9978 行） | ✅ 本地提交 `4090293` |
| 直接 push 专属仓分支 | ❌ 被分支保护拦截（强制 PR + CLA） |
| Fork 专属仓 | ✅ `gemhermit/contest2026_236_wuxianshanyaoqiji` |
| 推送 `feat/init-workspace` 到 fork | ✅ |
| 创建 PR（fork → 专属仓） | ✅ PR #1 |
| 合并 PR | ✅ Merged |

## 关键要点

### 1. 为什么不能直接 push
专属仓配置了仓库级 ruleset，**push 到任何分支都要求先通过 `cla/signature` 状态检查**。
而 `cla/signature` 只在 PR 上产生 → 形成「push 要过 CLA → CLA 只在 PR → PR 要先 push」的鸡生蛋死循环，无法用 CLI 绕过。

### 2. 正确解法（组委会 README 第五节）
1. **Fork** 专属仓到自己账号
2. 在**自己的 fork** 里 push（不受专属仓分支保护限制）
3. 从 fork 向专属仓发起 PR
4. PR 上的 `cla/signature` 由 CLA bot 检查，签过 CLA 后自动通过
5. 审查后自行合入

### 3. 执行细节（浏览器自动化）
- GitHub 登录账号：**Gem Hermit**（邮箱 `xizhe.official@gmail.com`），fork 到 `gemhermit/contest2026_236_wuxianshanyaoqiji`
- PR 方向：`gemhermit:feat/init-workspace` → `open-vela:dev-ai-contest-2026`
- PR 标题/正文：按 `## Summary` 各点填写，未提交为 draft，未点击 Merge
- 过程中一次浏览器桥接快照超时(30s)，改用页面内 `browser_evaluate` 读取/填写表单完成

## 结果
- **PR #1**：[feat: 初始化参赛作品 - Live2D语音对话WebUI + 开发环境记录](https://github.com/open-vela/contest2026_236_wuxianshanyaoqiji/pull/1)（已合并）
- **状态**：Merged（合入 `open-vela:dev-ai-contest-2026`）
- **合并提交**：`9bd0bdb`
- **Checks**：✅ 2 checks passed（含 CLA signed）
- **改动**：+9,978 / −121，62 files

## 后续可选收尾
1. 同步本地：`git pull origin dev-ai-contest-2026`
2. 清理 fork 的 `feat/init-workspace` 临时分支（可选）
3. 继续开发（NFC 互动 / AI Passport）