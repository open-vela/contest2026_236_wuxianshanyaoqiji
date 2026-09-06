/**
 * 火山引擎语音二进制协议工具
 * ASR / TTS 共用的帧编解码
 *
 * 帧结构:
 *   [4B header][4B payload_size][payload]
 * header:
 *   byte0: (protocol_version << 4) | header_size_in_words
 *   byte1: (message_type << 4) | message_type_specific
 *   byte2: (serialization << 4) | compression
 *   byte3: reserved
 */

// —— 消息类型 ——
export const MSG_TYPE = {
  FULL_CLIENT_REQUEST: 0x01,
  AUDIO_ONLY_REQUEST: 0x02,
  FULL_SERVER_RESPONSE: 0x09,
  SERVER_ERROR: 0x0f,
} as const;

// —— 序列化方式 ——
export const SERIALIZATION = {
  NONE: 0x00,
  JSON: 0x01,
} as const;

// —— 压缩方式 ——
export const COMPRESSION = {
  NONE: 0x00,
  GZIP: 0x01,
} as const;

const PROTOCOL_VERSION = 0x01;
const HEADER_SIZE_WORDS = 0x01; // 4 bytes = 1 word

/** 构造客户端请求帧（JSON 配置） */
export function buildJsonFrame(jsonPayload: object): Buffer {
  const payload = Buffer.from(JSON.stringify(jsonPayload), "utf-8");
  const header = Buffer.alloc(4);
  header[0] = (PROTOCOL_VERSION << 4) | HEADER_SIZE_WORDS;
  header[1] = (MSG_TYPE.FULL_CLIENT_REQUEST << 4) | 0x00;
  header[2] = (SERIALIZATION.JSON << 4) | COMPRESSION.NONE;
  header[3] = 0x00;

  const sizeBuf = Buffer.alloc(4);
  sizeBuf.writeUInt32BE(payload.length + 4, 0); // payload + negative header size field

  // 负载大小后面还有 4 字节的 "payload size" 本身的大小（协议要求）
  // 实际上火山协议: header(4) + payload_size(4) + payload
  // payload_size 字段的值 = payload.length（不含 header 和 size 字段本身）
  sizeBuf.writeUInt32BE(payload.length, 0);

  return Buffer.concat([header, sizeBuf, payload]);
}

/** 构造音频帧（纯 PCM） */
export function buildAudioFrame(pcm: Buffer): Buffer {
  const header = Buffer.alloc(4);
  header[0] = (PROTOCOL_VERSION << 4) | HEADER_SIZE_WORDS;
  header[1] = (MSG_TYPE.AUDIO_ONLY_REQUEST << 4) | 0x00;
  header[2] = (SERIALIZATION.NONE << 4) | COMPRESSION.NONE;
  header[3] = 0x00;

  const sizeBuf = Buffer.alloc(4);
  sizeBuf.writeUInt32BE(pcm.length, 0);

  return Buffer.concat([header, sizeBuf, pcm]);
}

/** 解析服务器响应帧 */
export function parseServerFrame(data: Buffer): {
  messageType: number;
  serialization: number;
  compression: number;
  payload: Buffer;
} {
  if (data.length < 8) {
    throw new Error("Frame too short");
  }

  const messageType = (data[1] >> 4) & 0x0f;
  const serialization = (data[2] >> 4) & 0x0f;
  const compression = data[2] & 0x0f;
  const payloadSize = data.readUInt32BE(4);
  const payload = data.subarray(8, 8 + payloadSize);

  return { messageType, serialization, compression, payload };
}

/** base16 hex → Buffer */
export function hexToBuffer(hex: string): Buffer {
  return Buffer.from(hex, "hex");
}

/** Buffer → base16 hex */
export function bufferToHex(buf: Buffer): string {
  return buf.toString("hex");
}
