/**
 * WebSocket 对话编排器
 * 接收客户端音频/文本 → ASR → LLM → TTS → 回传
 *
 * 消息协议见 src/types/chat.ts
 */
import type { WebSocket as WsSocket } from "ws";
import type { ClientMessage, ServerMessage, RuntimeConfig } from "../../src/types/chat.js";
import { DEFAULT_CONFIG } from "../../src/types/chat.js";
import { createAsrSession } from "../services/doubaoASR.js";
import { streamChat, type LlmMessage } from "../services/doubaoLLM.js";
import { streamTts } from "../services/doubaoTTS.js";

// 每个连接的会话状态
interface SessionState {
  config: RuntimeConfig;
  history: LlmMessage[];     // LLM 上下文
  asrSession: { feedAudio: (hex: string) => void; finish: () => void } | null;
  busy: boolean;             // 是否正在处理一轮对话
}

function send(ws: WsSocket, msg: ServerMessage) {
  if (ws.readyState === ws.OPEN) {
    ws.send(JSON.stringify(msg));
  }
}

export function handleChatConnection(ws: WsSocket): void {
  const state: SessionState = {
    config: { ...DEFAULT_CONFIG },
    history: [],
    asrSession: null,
    busy: false,
  };

  console.log("[WS] 新对话连接");

  ws.on("message", async (raw: Buffer) => {
    let msg: ClientMessage;
    try {
      msg = JSON.parse(raw.toString());
    } catch {
      return;
    }

    switch (msg.type) {
      // —— 音频开始 ——
      case "audio-start": {
        console.log("[WS] 收到 audio-start");
        state.asrSession?.finish();
        state.asrSession = createAsrSession({
          onPartial: (text) => send(ws, { type: "asr-partial", text }),
          onFinal: (text) => {
            console.log("[WS] ASR final:", JSON.stringify(text));
            send(ws, { type: "asr-final", text });
            // 触发 LLM + TTS
            handleUserInput(ws, state, text).catch((e) => {
              console.error("[WS] 处理失败:", e);
              send(ws, { type: "error", message: String(e) });
            });
          },
          onError: (errMsg) => send(ws, { type: "error", message: errMsg }),
          onClose: () => {
            state.asrSession = null;
          },
        });
        break;
      }

      // —— 音频块 ——
      case "audio-chunk": {
        state.asrSession?.feedAudio(msg.data);
        break;
      }

      // —— 音频结束 ——
      case "audio-end": {
        console.log("[WS] 收到 audio-end, asrSession存在:", !!state.asrSession);
        state.asrSession?.finish();
        break;
      }

      // —— 文本输入 ——
      case "text-input": {
        console.log("[WS] 收到 text-input:", msg.text);
        handleUserInput(ws, state, msg.text).catch((e) => {
          console.error("[WS] 处理失败:", e);
          send(ws, { type: "error", message: String(e) });
        });
        break;
      }

      // —— 获取配置 ——
      case "config-get": {
        send(ws, { type: "config", payload: state.config });
        break;
      }

      // —— 更新配置 ——
      case "config-set": {
        state.config = { ...state.config, ...msg.payload };
        send(ws, { type: "config", payload: state.config });
        break;
      }
    }
  });

  ws.on("close", () => {
    state.asrSession?.finish();
    console.log("[WS] 连接关闭");
  });
}

/**
 * 处理用户输入：LLM → TTS
 */
async function handleUserInput(
  ws: WsSocket,
  state: SessionState,
  userText: string,
): Promise<void> {
  if (state.busy) {
    send(ws, { type: "error", message: "正在处理中，请稍候" });
    return;
  }
  if (!userText.trim()) return;

  state.busy = true;

  try {
    // —— LLM 阶段 ——
    send(ws, { type: "phase", phase: "thinking" });

    // 构建消息列表
    const messages: LlmMessage[] = [
      { role: "system", content: state.config.systemPrompt },
      ...state.history.slice(-10), // 最近 10 轮
      { role: "user", content: userText },
    ];

    let fullResponse = "";

    await streamChat(messages, state.config.llmModelId, {
      onDelta: (delta) => {
        fullResponse += delta;
        send(ws, { type: "llm-delta", text: delta });
      },
      onDone: (finalText) => {
        send(ws, { type: "llm-done", text: "" });
        // 更新历史
        state.history.push(
          { role: "user", content: userText },
          { role: "assistant", content: finalText || fullResponse },
        );
        // 限制历史长度
        if (state.history.length > 20) {
          state.history = state.history.slice(-20);
        }
      },
      onError: (errMsg) => {
        send(ws, { type: "error", message: errMsg });
      },
    });

    if (!fullResponse.trim()) {
      send(ws, { type: "phase", phase: "idle" });
      state.busy = false;
      return;
    }

    // —— TTS 阶段 ——
    send(ws, { type: "phase", phase: "speaking" });
    send(ws, { type: "tts-start" });

    await new Promise<void>((resolve) => {
      streamTts(fullResponse, state.config.ttsVoiceId, state.config.ttsSpeed, {
        onStart: () => {},
        onAudio: (hex, sampleRate) => {
          send(ws, { type: "tts-chunk", data: hex, sampleRate });
        },
        onEnd: () => {
          send(ws, { type: "tts-end" });
          send(ws, { type: "phase", phase: "idle" });
          resolve();
        },
        onError: (errMsg) => {
          send(ws, { type: "error", message: errMsg });
          send(ws, { type: "tts-end" });
          send(ws, { type: "phase", phase: "idle" });
          resolve();
        },
      });
    });
  } finally {
    state.busy = false;
  }
}
