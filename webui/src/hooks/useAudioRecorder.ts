/**
 * 音频录制 Hook
 * - getUserMedia 采集麦克风
 * - ScriptProcessorNode 分帧 → Int16 PCM → base16
 * - 回调输出 PCM hex 块 + RMS 音量
 * - 兼容 OpenVela webview（不支持 AudioWorklet 时降级）
 */
import { useCallback, useEffect, useRef, useState } from "react";
import { float32ToInt16, rms, toBase16 } from "@/lib/audioUtils";

const SAMPLE_RATE = 16000; // 豆包 ASR 要求 16kHz
const CHUNK_SIZE = 4096;   // ScriptProcessor 缓冲

interface UseAudioRecorderOptions {
  onChunk: (hex: string) => void;
  onLevel?: (level: number) => void;
}

interface UseAudioRecorderReturn {
  recording: boolean;
  start: () => Promise<void>;
  stop: () => void;
  error: string | null;
}

export function useAudioRecorder(
  opts: UseAudioRecorderOptions,
): UseAudioRecorderReturn {
  const { onChunk, onLevel } = opts;
  const streamRef = useRef<MediaStream | null>(null);
  const ctxRef = useRef<AudioContext | null>(null);
  const processorRef = useRef<ScriptProcessorNode | null>(null);
  const sourceRef = useRef<MediaStreamAudioSourceNode | null>(null);
  const onChunkRef = useRef(onChunk);
  const onLevelRef = useRef(onLevel);
  const [recording, setRecording] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    onChunkRef.current = onChunk;
    onLevelRef.current = onLevel;
  }, [onChunk, onLevel]);

  const start = useCallback(async () => {
    try {
      setError(null);
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          sampleRate: SAMPLE_RATE,
          echoCancellation: true,
          noiseSuppression: true,
        },
      });
      streamRef.current = stream;

      const ctx = new (window.AudioContext ||
        (window as any).webkitAudioContext)({
        sampleRate: SAMPLE_RATE,
      });
      ctxRef.current = ctx;

      // 如果 webview 不允许指定采样率，用 ctx.sampleRate 重采样
      const actualRate = ctx.sampleRate;

      const source = ctx.createMediaStreamSource(stream);
      sourceRef.current = source;

      const processor = ctx.createScriptProcessor(CHUNK_SIZE, 1, 1);
      processorRef.current = processor;

      processor.onaudioprocess = (e) => {
        const input = e.inputBuffer.getChannelData(0);
        // RMS 音量
        const level = rms(input);
        onLevelRef.current?.(level);

        // 如果 ctx 采样率与目标不同，需要重采样（简易线性降采样）
        let pcm: Float32Array;
        if (actualRate !== SAMPLE_RATE) {
          const ratio = SAMPLE_RATE / actualRate;
          const newLen = Math.floor(input.length * ratio);
          pcm = new Float32Array(newLen);
          for (let i = 0; i < newLen; i++) {
            pcm[i] = input[Math.floor(i / ratio)];
          }
        } else {
          pcm = input;
        }

        const int16 = float32ToInt16(pcm);
        const hex = toBase16(int16);
        onChunkRef.current?.(hex);
      };

      source.connect(processor);
      processor.connect(ctx.destination); // 必须 connect 才会触发 onaudioprocess

      setRecording(true);
    } catch (e: any) {
      console.error("[Recorder] 启动失败:", e);
      setError(e?.message || "麦克风访问失败");
      throw e; // re-throw 让调用方感知失败
    }
  }, []);

  const stop = useCallback(() => {
    const processor = processorRef.current;
    const source = sourceRef.current;
    const ctx = ctxRef.current;
    const stream = streamRef.current;

    if (processor) {
      processor.disconnect();
      processor.onaudioprocess = null;
    }
    if (source) source.disconnect();
    if (stream) stream.getTracks().forEach((t) => t.stop());
    if (ctx && ctx.state !== "closed") ctx.close();

    processorRef.current = null;
    sourceRef.current = null;
    ctxRef.current = null;
    streamRef.current = null;
    setRecording(false);
  }, []);

  useEffect(() => {
    return () => {
      const processor = processorRef.current;
      const source = sourceRef.current;
      const ctx = ctxRef.current;
      const stream = streamRef.current;
      if (processor) processor.disconnect();
      if (source) source.disconnect();
      if (stream) stream.getTracks().forEach((t) => t.stop());
      if (ctx && ctx.state !== "closed") ctx.close();
    };
  }, []);

  return { recording, start, stop, error };
}
