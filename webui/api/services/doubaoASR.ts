/**
 * 豆包（火山引擎）流式 ASR 服务
 * WebSocket 二进制协议，16kHz/16-bit/mono PCM
 *
 * 无凭证时自动降级为 mock 模式（回显固定文本）
 */
import WebSocket from "ws";
import {
  buildJsonFrame,
  buildAudioFrame,
  parseServerFrame,
  hexToBuffer,
  MSG_TYPE,
} from "./doubaoProtocol.js";

const ASR_URL = "wss://openspeech.bytedance.com/api/v1/asr";

export interface AsrCallbacks {
  onPartial: (text: string) => void;
  onFinal: (text: string) => void;
  onError: (msg: string) => void;
  onClose: () => void;
}

export interface AsrConfig {
  appId: string;
  accessToken: string;
  cluster: string;
}

export function isAsrConfigured(): boolean {
  return !!(
    process.env.DOUBAO_APP_ID &&
    process.env.DOUBAO_ACCESS_TOKEN &&
    process.env.DOUBAO_ASR_CLUSTER
  );
}

export function getAsrConfig(): AsrConfig {
  return {
    appId: process.env.DOUBAO_APP_ID || "",
    accessToken: process.env.DOUBAO_ACCESS_TOKEN || "",
    cluster: process.env.DOUBAO_ASR_CLUSTER || "volcengine_streaming_common",
  };
}

/**
 * 创建流式 ASR 会话
 * 返回控制器：feedAudio / finish
 */
export function createAsrSession(
  callbacks: AsrCallbacks,
): { feedAudio: (hex: string) => void; finish: () => void } {
  const cfg = getAsrConfig();

  // —— Mock 模式 ——
  if (!isAsrConfigured()) {
    console.warn("[ASR] 未配置凭证，使用 mock 模式（快速模拟）");
    let accumulated = "";
    let mockTimer: NodeJS.Timeout | null = null;
    const mockTexts = ["你好呀", "今天天气怎么样", "给我讲个故事", "你好，小星"];
    const mockText = mockTexts[Math.floor(Math.random() * mockTexts.length)];

    return {
      feedAudio: (_hex: string) => {
        // 模拟渐进式识别（60ms/字，快速反馈）
        if (mockTimer) clearTimeout(mockTimer);
        mockTimer = setTimeout(() => {
          accumulated = mockText.slice(0, accumulated.length + 1);
          callbacks.onPartial(accumulated);
        }, 60);
      },
      finish: () => {
        if (mockTimer) clearTimeout(mockTimer);
        // 立即给出完整文本
        callbacks.onFinal(mockText);
        callbacks.onClose();
      },
    };
  }

  // —— 真实模式 ——
  const ws = new WebSocket(ASR_URL);
  let configSent = false;
  let finished = false;

  ws.on("open", () => {
    const configPayload = {
      app: {
        appid: cfg.appId,
        token: cfg.accessToken,
        cluster: cfg.cluster,
      },
      user: { uid: "rivotek-board" },
      audio: {
        format: "pcm",
        rate: 16000,
        bits: 16,
        channel: 1,
        language: "zh-CN",
      },
      request: {
        reqid: Date.now().toString(),
        nbest: 1,
        sequence: -1,
      },
      additions: {
        with_speaker: false,
        end_window_size: 0,
      },
    };
    ws.send(buildJsonFrame(configPayload));
    configSent = true;
  });

  ws.on("message", (data: Buffer) => {
    try {
      const frame = parseServerFrame(data);
      if (frame.messageType === MSG_TYPE.SERVER_ERROR) {
        const errMsg = frame.payload.toString("utf-8");
        callbacks.onError(`ASR 错误: ${errMsg}`);
        return;
      }
      if (frame.serialization === 1) {
        // JSON 响应
        const json = JSON.parse(frame.payload.toString("utf-8"));
        const text = json.result?.[0]?.text || "";
        const isFinal = json.is_last === true;
        if (isFinal) {
          callbacks.onFinal(text);
        } else {
          callbacks.onPartial(text);
        }
      }
    } catch (e) {
      console.error("[ASR] 解析响应失败:", e);
    }
  });

  ws.on("error", (err) => {
    callbacks.onError(`ASR 连接错误: ${err.message}`);
  });

  ws.on("close", () => {
    callbacks.onClose();
  });

  return {
    feedAudio: (hex: string) => {
      if (!configSent || ws.readyState !== WebSocket.OPEN) return;
      const pcm = hexToBuffer(hex);
      ws.send(buildAudioFrame(pcm));
    },
    finish: () => {
      if (finished) return;
      finished = true;
      // 发送结束帧（空音频 + sequence=1）
      if (ws.readyState === WebSocket.OPEN) {
        const endFrame = buildAudioFrame(Buffer.alloc(0));
        ws.send(endFrame);
        setTimeout(() => {
          if (ws.readyState === WebSocket.OPEN) ws.close();
        }, 1000);
      }
    },
  };
}
