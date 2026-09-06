/**
 * 对话相关类型定义
 */

/** 对话阶段 */
export type ChatPhase =
  | "idle"          // 待机
  | "listening"     // 录音中
  | "recognizing"   // ASR 识别中
  | "thinking"      // LLM 推理中
  | "speaking"      // TTS 播放 + 口型同步
  | "error";        // 出错

/** 对话消息角色 */
export type MessageRole = "user" | "assistant" | "system";

/** 一条对话消息 */
export interface ChatMessage {
  id: string;
  role: MessageRole;
  content: string;
  /** 流式追加未完成时为 true */
  streaming?: boolean;
  /** 创建时间戳 */
  ts: number;
}

/** WebSocket 客户端 → 网关消息 */
export type ClientMessage =
  | { type: "audio-start"; sampleRate: number; channels: number }
  | { type: "audio-chunk"; data: string }   // base16 PCM
  | { type: "audio-end" }
  | { type: "text-input"; text: string }
  | { type: "config-get" }
  | { type: "config-set"; payload: Partial<RuntimeConfig> };

/** WebSocket 网关 → 客户端消息 */
export type ServerMessage =
  | { type: "asr-partial"; text: string }
  | { type: "asr-final"; text: string }
  | { type: "llm-delta"; text: string }
  | { type: "llm-done"; text: string }
  | { type: "tts-start" }
  | { type: "tts-chunk"; data: string; sampleRate: number }  // base16 PCM
  | { type: "tts-end" }
  | { type: "phase"; phase: ChatPhase }
  | { type: "error"; message: string; code?: string }
  | { type: "config"; payload: RuntimeConfig };

/** 运行时可配置项 */
export interface RuntimeConfig {
  /** 豆包 LLM 模型 ID */
  llmModelId: string;
  /** 豆包 TTS 音色 ID */
  ttsVoiceId: string;
  /** 说话速度 0~1 */
  ttsSpeed: number;
  /** Live2D 模型 URL */
  live2dModelUrl: string;
  /** 角色人设提示词 */
  systemPrompt: string;
}

/** 默认配置 */
export const DEFAULT_CONFIG: RuntimeConfig = {
  // 豆包 Seed 2.1 Turbo：轻量快速，适合板端低延迟对话
  llmModelId: "doubao-seed-2-1-turbo-260628",
  ttsVoiceId: "zh_female_qingxin",
  ttsSpeed: 0.9,
  live2dModelUrl:
    "https://cdn.jsdelivr.net/gh/guansss/pixi-live2d-display/test/assets/haru/haru_greeter_t03.model3.json",
  systemPrompt:
    "你是一个温柔的二次元少女助手，名叫小星。请用简短、俏皮、关心的语气回答问题，每次回答不超过两句话。永远用中文回答。",
};
