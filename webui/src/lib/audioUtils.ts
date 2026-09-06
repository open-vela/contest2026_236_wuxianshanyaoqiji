/**
 * 音频处理工具
 * - Float32 ↔ Int16 PCM 转换
 * - base16 (hex) 编解码（用于 WebSocket 文本传输二进制 PCM）
 * - RMS 音量计算（用于口型同步）
 */

/** Float32Array → Int16Array PCM */
export function float32ToInt16(input: Float32Array): Int16Array {
  const out = new Int16Array(input.length);
  for (let i = 0; i < input.length; i++) {
    const s = Math.max(-1, Math.min(1, input[i]));
    out[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
  }
  return out;
}

/** Int16Array → Float32Array */
export function int16ToFloat32(input: Int16Array): Float32Array {
  const out = new Float32Array(input.length);
  for (let i = 0; i < input.length; i++) {
    out[i] = input[i] / 0x8000;
  }
  return out;
}

/** ArrayBuffer / Int16Array → base16 字符串 */
export function toBase16(data: ArrayBuffer | Int16Array | Uint8Array): string {
  const bytes = data instanceof Int16Array
    ? new Uint8Array(data.buffer, data.byteOffset, data.byteLength)
    : data instanceof Uint8Array
      ? data
      : new Uint8Array(data);
  let hex = "";
  for (let i = 0; i < bytes.length; i++) {
    hex += bytes[i].toString(16).padStart(2, "0");
  }
  return hex;
}

/** base16 字符串 → Uint8Array */
export function fromBase16(hex: string): Uint8Array {
  const clean = hex.length % 2 !== 0 ? "0" + hex : hex;
  const out = new Uint8Array(clean.length / 2);
  for (let i = 0; i < out.length; i++) {
    out[i] = parseInt(clean.substr(i * 2, 2), 16);
  }
  return out;
}

/** base16 字符串 → Int16Array PCM（小端） */
export function base16ToInt16(hex: string): Int16Array {
  const bytes = fromBase16(hex);
  return new Int16Array(bytes.buffer, bytes.byteOffset, bytes.byteLength / 2);
}

/** base16 字符串 → Float32Array PCM */
export function base16ToFloat32(hex: string): Float32Array {
  return int16ToFloat32(base16ToInt16(hex));
}

/** 计算 RMS 音量 (0~1) */
export function rms(samples: Float32Array): number {
  let sum = 0;
  for (let i = 0; i < samples.length; i++) {
    sum += samples[i] * samples[i];
  }
  return Math.sqrt(sum / samples.length);
}

/** 生成唯一 ID */
export function genId(): string {
  return Date.now().toString(36) + Math.random().toString(36).slice(2, 8);
}
