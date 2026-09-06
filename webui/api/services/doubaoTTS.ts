/**
 * 豆包（火山引擎）流式 TTS 服务
 * WebSocket 二进制协议，返回 PCM 音频块
 *
 * 无凭证时降级为 mock 模式（生成静音 PCM）
 */
import WebSocket from "ws";
import {
  buildJsonFrame,
  parseServerFrame,
  bufferToHex,
  MSG_TYPE,
} from "./doubaoProtocol.js";

const TTS_URL = "wss://openspeech.bytedance.com/api/v1/tts/ws_binary";

export interface TtsCallbacks {
  onAudio: (hex: string, sampleRate: number) => void;
  onStart: () => void;
  onEnd: () => void;
  onError: (msg: string) => void;
}

export interface TtsConfig {
  appId: string;
  accessToken: string;
  cluster: string;
}

export function isTtsConfigured(): boolean {
  return !!(
    process.env.DOUBAO_APP_ID &&
    process.env.DOUBAO_ACCESS_TOKEN &&
    process.env.DOUBAO_TTS_CLUSTER
  );
}

export function getTtsConfig(): TtsConfig {
  return {
    appId: process.env.DOUBAO_APP_ID || "",
    accessToken: process.env.DOUBAO_ACCESS_TOKEN || "",
    cluster: process.env.DOUBAO_TTS_CLUSTER || "volcano_tts",
  };
}

/**
 * 流式合成语音
 * @param text 待合成文本
 * @param voiceId 音色 ID
 * @param speed 语速 0.5~2.0
 * @param callbacks 回调
 */
export function streamTts(
  text: string,
  voiceId: string,
  speed: number,
  callbacks: TtsCallbacks,
): void {
  const cfg = getTtsConfig();
  const sampleRate = 24000;

  // —— Mock 模式 ——
  if (!isTtsConfigured()) {
    console.warn("[TTS] 未配置凭证，使用 mock 模式");
    callbacks.onStart();
    // 生成 1 秒的近似静音 PCM（带微弱正弦波模拟口型）
    const durationMs = Math.min(3000, text.length * 200);
    const samples = Math.floor((sampleRate * durationMs) / 1000);
    const pcm = Buffer.alloc(samples * 2);
    for (let i = 0; i < samples; i++) {
      const t = i / sampleRate;
      const envelope = Math.sin((Math.PI * i) / samples); // 包络
      const wave = Math.sin(2 * Math.PI * 200 * t) * 0.05 * envelope;
      pcm.writeInt16LE(Math.floor(wave * 32767), i * 2);
    }
    // 分块发送（每 100ms）
    const chunkSize = Math.floor((sampleRate * 0.1) * 2); // 100ms worth of bytes
    let offset = 0;
    const sendChunk = () => {
      if (offset >= pcm.length) {
        callbacks.onEnd();
        return;
      }
      const chunk = pcm.subarray(offset, offset + chunkSize);
      callbacks.onAudio(bufferToHex(chunk), sampleRate);
      offset += chunkSize;
      setTimeout(sendChunk, 100);
    };
    sendChunk();
    return;
  }

  // —— 真实模式 ——
  const ws = new WebSocket(TTS_URL);
  let ended = false;

  ws.on("open", () => {
    const payload = {
      app: {
        appid: cfg.appId,
        token: cfg.accessToken,
        cluster: cfg.cluster,
      },
      user: { uid: "rivotek-board" },
      audio: {
        voice_type: voiceId,
        encoding: "pcm",
        rate: sampleRate,
        speed_ratio: speed,
      },
      request: {
        reqid: Date.now().toString(),
        text,
        operation: "submit",
      },
    };
    ws.send(buildJsonFrame(payload));
    callbacks.onStart();
  });

  ws.on("message", (data: Buffer) => {
    try {
      const frame = parseServerFrame(data);

      if (frame.messageType === MSG_TYPE.SERVER_ERROR) {
        const errMsg = frame.payload.toString("utf-8");
        callbacks.onError(`TTS 错误: ${errMsg}`);
        return;
      }

      if (frame.messageType === MSG_TYPE.FULL_SERVER_RESPONSE) {
        // JSON + 可选二进制音频
        // 火山 TTS 返回: [4B header][4B size][4B json_size][json][audio]
        let offset = 8; // skip header + size
        if (data.length > offset + 4) {
          const jsonSize = data.readUInt32BE(offset);
          offset += 4;
          const jsonStr = data.subarray(offset, offset + jsonSize).toString("utf-8");
          offset += jsonSize;
          const audioData = data.subarray(offset);

          try {
            const json = JSON.parse(jsonStr);
            if (json.code === 3000 && audioData.length > 0) {
              callbacks.onAudio(bufferToHex(audioData), sampleRate);
            }
            if (json.is_last) {
              if (!ended) {
                ended = true;
                callbacks.onEnd();
                ws.close();
              }
            }
          } catch {
            // 忽略 JSON 解析错误
          }
        }
      }
    } catch (e) {
      console.error("[TTS] 解析响应失败:", e);
    }
  });

  ws.on("error", (err) => {
    callbacks.onError(`TTS 连接错误: ${err.message}`);
  });

  ws.on("close", () => {
    if (!ended) {
      ended = true;
      callbacks.onEnd();
    }
  });
}
