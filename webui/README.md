> 网页为独立开发素材，不纳入本次固件。旧 WSL 构建脚本已移除，硬件成果见 ../docs/build-pack-guide.md。

# WebUI — R528 Gemini-S1 板端 Live2D 二次元语音对话界面

> 本目录是 2026 openvela AI 硬件开发者大赛参赛作品「无限闪耀队」的板端 Web 界面与 PC 网关代码。
> 部署目标：润芯微 Gemini-S1（全志 R528）开发板，2.8" SPI 竖屏 320×480，板载麦克风。

---

## 一、作品简介

面向 openvela AI 硬件大赛的板端二次元语音陪伴 demo。在 Gemini-S1 开发板的板端 webview 中渲染 Live2D 二次元角色（Haru），通过板载麦克风采集语音 → 网关代理豆包云端 ASR/LLM/TTS → 回传音频驱动 Live2D 口型同步，实现「听懂—思考—开口—口型同步」的实时对话体验。

- **核心链路**：板端 webview ↔ PC 网关（Node.js + WebSocket）↔ 豆包云端（火山引擎 ASR/LLM/TTS）
- **关键能力**：Live2D 渲染（pixi.js v6 + pixi-live2d-display + Cubism Core）、口型同步（AnalyserNode 取 RMS 驱动 ParamMouthOpenY）、眼神追踪、点击交互、流式对话
- **降级策略**：未配置豆包 API 凭证时自动切换至 mock 模式，便于 UI 调试

---

## 二、技术栈

| 层 | 技术 |
|----|------|
| 前端 | React 18 + TypeScript + Vite 6 + Tailwind CSS 3 |
| Live2D | pixi.js@6 + pixi-live2d-display@0.4 + Live2D Cubism Core |
| 图标 | lucide-react |
| 状态管理 | zustand |
| 网关 | Node.js + Express 4（静态资源 + REST）+ ws（WebSocket 流式代理）|
| 云端 | 火山引擎豆包（流式 ASR / Doubao LLM / 流式 TTS）|
| 板端 | OpenVela `nsh_minidisplay` 配置 + webview 组件 |

---

## 三、目录结构

```text
webui/
├── api/                       # PC 网关（Node.js 后端）
│   ├── app.ts                 # Express 应用（静态资源 + REST 路由）
│   ├── server.ts              # HTTP + WebSocket 服务入口（端口 3001）
│   ├── auth.ts                # 火山引擎签名工具
│   ├── doubaoASR.ts           # 豆包流式 ASR 封装
│   ├── doubaoLLM.ts           # 豆包 LLM（方舟 Ark）流式对话封装
│   ├── doubaoTTS.ts           # 豆包流式 TTS 封装
│   ├── doubaoProtocol.ts      # 豆包 WebSocket 二进制协议
│   ├── chatHandler.ts         # /ws/chat 对话编排器（ASR→LLM→TTS）
│   ├── routes/                # REST 路由
│   ├── services/              # 业务服务
│   └── ws/                    # WebSocket 处理器
├── src/                       # 板端前端（React）
│   ├── App.tsx                # 根组件（路由）
│   ├── main.tsx               # 入口
│   ├── index.css              # 全局样式 + Tailwind
│   ├── components/            # UI 组件
│   │   ├── Live2DStage.tsx    # Live2D 舞台（渲染 + 触摸眼神 + 点击动作）
│   │   ├── ChatBubble.tsx     # 对话气泡
│   │   ├── RecordButton.tsx   # 录音按钮（四态 + 呼吸光圈）
│   │   ├── StatusIndicator.tsx# 顶部状态条
│   │   ├── SettingsDrawer.tsx # 设置抽屉
│   │   └── Empty.tsx          # 空状态
│   ├── hooks/                 # 自定义 Hooks
│   │   ├── useLive2D.ts       # Live2D 模型加载与控制
│   │   ├── useChat.ts         # WebSocket 对话流管理
│   │   ├── useAudioRecorder.ts# 麦克风采集（getUserMedia + PCM 分片）
│   │   ├── useAudioPlayer.ts  # TTS 音频播放 + AnalyserNode 取音量
│   │   └── useTheme.ts        # 主题切换
│   ├── pages/
│   │   └── Chat.tsx           # 主对话页
│   ├── store/
│   │   └── appStore.ts        # zustand 全局状态
│   ├── lib/
│   │   ├── audioUtils.ts      # PCM 重采样、base16 编解码
│   │   ├── pixi.d.ts          # pixi-live2d-display 类型补充
│   │   └── utils.ts           # 通用工具（cn 类名合并等）
│   ├── types/
│   │   └── chat.ts            # 对话消息协议类型定义
│   └── assets/                # 静态资源
├── public/                    # 公共静态资源（favicon 等）
├── scripts/                   # WSL 编译/打包辅助脚本
│   ├── wsl-check.sh           # WSL 依赖检查
│   ├── wsl-repo-init.sh       # repo 初始化 + 同步（USTC 镜像）
│   # 固件构建入口已迁移到 ../docs/build-pack-guide.md
│   ├── wsl-check-lfs.sh       # LFS 指针文件检测与修复
│   # 使用官方 envsetup / lunch_nuttx / pack
│   # 旧固件拷贝脚本已移除，当前镜像按 SHA-256 核验
├── docs/                      # 项目文档
│   ├── PRD.md                 # 产品需求文档
│   ├── TechnicalArchitecture.md # 技术架构文档
│   └── BoardFlashingGuide.md  # 板端烧入与验证指南（含三确认流程）
├── firmware/                  # WSL 编译产物（不入 git，仅本地保留）
│   └── rtos_nuttx_r528s3-gemini-s1_uart0_128Mnand.img  # PhoenixSuit 烧入镜像
├── .env.example               # 环境变量模板（豆包 API 凭证）
├── .gitignore
├── eslint.config.js
├── index.html                 # Vite 入口 HTML
├── nodemon.json               # 后端开发热重载配置
├── package.json
├── pnpm-lock.yaml
├── postcss.config.js
├── tailwind.config.js
├── tsconfig.json
├── vercel.json                # Vercel 部署配置（可选）
└── vite.config.ts             # Vite 配置（含 /api 代理到 3001）
```

> 注：`node_modules/`、`dist/`、`.pnpm-store/` 不入仓，需在本地重新安装/构建。

---

## 四、架构概览

```text
┌──────────────────────────────┐         ┌──────────────────────────────┐         ┌─────────────────┐
│  Gemini-S1 开发板             │  Wi-Fi  │  PC / 笔记本                  │  HTTPS  │  豆包云端        │
│  (OpenVela + webview)         │◄───────►│  Node.js 网关 (Express + WS)  │◄───────►│  ASR/LLM/TTS    │
│                                │  WS     │  + 静态文件服务 (dist/)       │         │                 │
│  2.8" SPI 竖屏 320×480        │         │  端口: 3001                   │         │                 │
│  板载麦克风                    │         │  PC IP: 192.168.0.116         │         │                 │
└──────────────────────────────┘         └──────────────────────────────┘         └─────────────────┘
```

**对话流程**：
1. 板端 webview 通过 `getUserMedia` 采集麦克风 PCM → WebSocket 分片上行到网关 `/ws/chat`
2. 网关转发至豆包流式 ASR → 实时返回识别文本增量
3. 录音结束 → 识别文本送入豆包 LLM（带人设 system prompt）→ 流式返回回答
4. 回答文本送入豆包流式 TTS → 音频流回传 webview
5. webview 播放 TTS 音频，`AnalyserNode` 取音量驱动 Live2D `ParamMouthOpenY` 口型同步
6. 播报结束 → 回到待机态

---

## 五、WebSocket 消息协议

路径：`ws://<PC-IP>:3001/ws/chat`

### 客户端 → 网关

| type | 字段 | 说明 |
|------|------|------|
| `audio-start` | `sampleRate`, `channels` | 开始录音，初始化 ASR 会话 |
| `audio-chunk` | `data`（base16 PCM） | 音频分片 |
| `audio-end` | — | 结束录音，触发 LLM |
| `text-input` | `text` | 文本输入（跳过 ASR，直接送 LLM） |
| `config-get` | — | 拉取运行时配置 |
| `config-set` | `payload: Partial<RuntimeConfig>` | 更新运行时配置 |

### 网关 → 客户端

| type | 字段 | 说明 |
|------|------|------|
| `asr-partial` | `text` | ASR 增量文本 |
| `asr-final` | `text` | ASR 最终文本 |
| `llm-delta` | `text` | LLM 流式增量 |
| `llm-done` | `text` | LLM 完整文本 |
| `tts-start` | — | TTS 开始 |
| `tts-chunk` | `data`（base16 PCM）, `sampleRate` | TTS 音频分片 |
| `tts-end` | — | TTS 结束 |
| `phase` | `phase: ChatPhase` | 对话阶段切换 |
| `error` | `message`, `code?` | 错误通知 |
| `config` | `payload: RuntimeConfig` | 配置下发 |

---

## 六、快速开始

### 6.1 环境要求

- Node.js ≥ 18
- pnpm ≥ 10（`package.json` 已锁定 `pnpm@10.33.2`）
- 现代浏览器（需支持 WebGL + getUserMedia）

### 6.2 安装依赖

```bash
cd webui
pnpm install
```

### 6.3 配置豆包 API 凭证

复制 `.env.example` 为 `.env`，填入火山引擎豆包凭证：

```bash
cp .env.example .env
```

```ini
DOUBAO_APP_ID=               # 火山引擎语音 App ID
DOUBAO_ACCESS_TOKEN=         # 火山引擎语音 Access Token
DOUBAO_ASR_CLUSTER=volcengine_streaming_common
DOUBAO_TTS_CLUSTER=volcano_tts
DOUBAO_ARK_API_KEY=          # 方舟 LLM API Key
PORT=3001
```

> 未配置凭证时自动降级为 mock 模式：ASR 返回固定文本、LLM 返回回声、TTS 不发声，便于纯 UI 调试。

### 6.4 启动开发服务器

```bash
pnpm dev
```

该命令同时启动：
- Vite 前端开发服务器（默认 `http://localhost:5173`，已配置 `/api` 代理到 3001）
- Node.js 后端网关（`http://localhost:3001`）

### 6.5 单独启动

```bash
# 仅前端
pnpm client:dev

# 仅后端（带热重载）
pnpm server:dev
```

### 6.6 构建生产版本

```bash
pnpm build
```

构建产物在 `dist/` 目录，由网关 `api/app.ts` 通过 Express 静态服务托管。

### 6.7 启动生产网关

```powershell
# Windows PowerShell
$env:NODE_ENV="production"; $env:HOST="0.0.0.0"; node --import tsx api/server.ts
```

网关监听 `0.0.0.0:3001`，板端访问 `http://<PC-IP>:3001/`。

健康检查：`http://localhost:3001/api/health`

---

## 七、板端部署

板端固件编译、打包、烧入的完整流程见 [docs/BoardFlashingGuide.md](docs/BoardFlashingGuide.md)，此处仅列关键步骤：

1. **固件构建**：按 `../docs/build-pack-guide.md` 操作。
2. **打包**：使用官方 `pack` 入口并核验镜像。
3. **烧入三确认**：MD5 校验 → FEL 模式设置 → 工具版本检查
4. **板端配置**：通过 NSH 串口配置 Wi-Fi，`webview http://<PC-IP>:3001/`

固件产物（已验证 MD5：`de7aa55366730d3a7b7b95a2deb63def`）：
- `firmware/rtos_nuttx_r528s3-gemini-s1_uart0_128Mnand.img`（29.2MB，PhoenixSuit 烧入镜像）
- `firmware/vela.bin`（7.3MB，精简运行固件）

---

## 八、开发约定

### 8.1 屏幕适配

板端 webview 固定 **320×480 竖屏**，所有布局以该分辨率为基准。开发时可用 Chrome 设备模拟（自定义 320×480）。

### 8.2 Live2D 模型

默认使用 Haru greeter 模型（CDN 加载）。如板端无法访问外网 CDN，需将模型文件下载到本地由网关托管。

- 点击模型触发随机动作（TapBody/FlickHead/Shake）+ 随机表情（F01~F08）
- 触摸屏幕驱动眼神追踪
- TTS 播放时通过 `AnalyserNode` 实时取 RMS 驱动 `ParamMouthOpenY` 实现口型同步

### 8.3 烧入三确认（硬约束）

烧入过程必须执行三确认，缺一不可：
1. **MD5 校验**：确认固件完整未损坏
2. **FEL 模式**：确认跳线/按键设置正确，PC 识别到 USB 设备
3. **工具版本**：确认 PhoenixSuit 与 USB 驱动已安装

### 8.4 代码风格

- ESLint + TypeScript 严格模式
- 路径别名 `@/` 指向 `src/`
- 提交前运行 `pnpm lint` 和 `pnpm check`

---

## 九、常用命令速查

```bash
# 开发
pnpm dev              # 同时启动前后端
pnpm client:dev       # 仅前端
pnpm server:dev       # 仅后端（热重载）

# 构建
pnpm build            # tsc + vite build
pnpm check            # TypeScript 类型检查（不产出）
pnpm lint             # ESLint

# 生产
node --import tsx api/server.ts   # 启动生产网关
```

---

## 十、故障排查

| 现象 | 排查方向 |
|------|----------|
| webview 白屏 | 检查 Wi-Fi 连接、PC 网关是否运行、防火墙是否放行 3001 端口 |
| Live2D 不显示 | 检查 WebGL 支持、CDN 可达性；必要时本地托管模型 |
| 麦克风无声音 | 确认板载麦克风在固件中启用、`getUserMedia` 可用 |
| WebSocket 连接失败 | 确认网关监听 `0.0.0.0`（非仅 localhost）、WS URL 指向 PC IP |
| ASR/TTS 报错 | 检查 `.env` 豆包凭证是否正确、是否降级为 mock 模式 |
| LLM 响应慢 | 检查网络延迟、考虑切换更轻量的模型（如 doubao-seed-2-1-turbo）|

更多烧入相关问题见 [docs/BoardFlashingGuide.md](docs/BoardFlashingGuide.md) 的「故障排查」章节。
