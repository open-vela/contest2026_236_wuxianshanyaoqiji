/**
 * 音频播放 Hook
 * - 接收 TTS PCM base16 块队列
 * - 通过 AudioBufferSourceNode 顺序播放
 * - 播放期间计算 RMS → 驱动 Live2D 口型同步
 * - 播放结束回调
 */
import { useCallback, useEffect, useRef } from "react";
import { base16ToFloat32 } from "@/lib/audioUtils";

interface UseAudioPlayerOptions {
  onLipSync?: (value: number) => void;
  onPlaybackEnd?: () => void;
  onPlaybackStart?: () => void;
}

export function useAudioPlayer(opts: UseAudioPlayerOptions) {
  const { onLipSync, onPlaybackEnd, onPlaybackStart } = opts;
  const ctxRef = useRef<AudioContext | null>(null);
  const queueRef = useRef<Float32Array[]>([]);
  const playingRef = useRef(false);
  const sampleRateRef = useRef(24000);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const lipSyncTimerRef = useRef<number | null>(null);
  const onLipSyncRef = useRef(onLipSync);
  const onEndRef = useRef(onPlaybackEnd);
  const onStartRef = useRef(onPlaybackStart);

  useEffect(() => {
    onLipSyncRef.current = onLipSync;
    onEndRef.current = onPlaybackEnd;
    onStartRef.current = onPlaybackStart;
  }, [onLipSync, onPlaybackEnd, onPlaybackStart]);

  // 确保 AudioContext 存在
  const ensureCtx = useCallback(() => {
    if (!ctxRef.current || ctxRef.current.state === "closed") {
      ctxRef.current = new (window.AudioContext ||
        (window as any).webkitAudioContext)();
    }
    return ctxRef.current;
  }, []);

  // 播放队列中的下一块
  const playNext = useCallback(() => {
    const ctx = ctxRef.current;
    if (!ctx) return;

    const chunk = queueRef.current.shift();
    if (!chunk) {
      // 队列空了
      playingRef.current = false;
      onLipSyncRef.current?.(0);
      onEndRef.current?.();
      return;
    }

    const sr = sampleRateRef.current;
    const buffer = ctx.createBuffer(1, chunk.length, sr);
    buffer.copyToChannel(chunk, 0);

    const source = ctx.createBufferSource();
    source.buffer = buffer;
    source.connect(ctx.destination);
    // 也连接到 analyser（如果存在）
    if (analyserRef.current) {
      source.connect(analyserRef.current);
    }

    source.onended = () => {
      playNext();
    };

    source.start();
  }, []);

  /** 入队一块 TTS PCM（base16 hex） */
  const enqueue = useCallback(
    (hex: string, sampleRate: number) => {
      const ctx = ensureCtx();
      if (ctx.state === "suspended") ctx.resume();

      sampleRateRef.current = sampleRate;
      const samples = base16ToFloat32(hex);
      queueRef.current.push(samples);

      // 创建 analyser（仅第一次）
      if (!analyserRef.current) {
        analyserRef.current = ctx.createAnalyser();
        analyserRef.current.fftSize = 256;
        analyserRef.current.connect(ctx.destination);
      }

      if (!playingRef.current) {
        playingRef.current = true;
        onStartRef.current?.();
        // 启动口型同步采样循环
        const lipLoop = () => {
          const analyser = analyserRef.current;
          if (analyser && playingRef.current) {
            const data = new Uint8Array(analyser.frequencyBinCount);
            analyser.getByteTimeDomainData(data);
            // 计算 RMS（中心值 128）
            let sum = 0;
            for (let i = 0; i < data.length; i++) {
              const v = (data[i] - 128) / 128;
              sum += v * v;
            }
            const level = Math.sqrt(sum / data.length);
            // 放大口型灵敏度
            onLipSyncRef.current?.(Math.min(1, level * 3));
          }
          if (playingRef.current) {
            lipSyncTimerRef.current = requestAnimationFrame(lipLoop);
          }
        };
        lipSyncTimerRef.current = requestAnimationFrame(lipLoop);
        playNext();
      }
    },
    [ensureCtx, playNext],
  );

  /** 清空队列并停止 */
  const stop = useCallback(() => {
    queueRef.current = [];
    playingRef.current = false;
    onLipSyncRef.current?.(0);
    if (lipSyncTimerRef.current) {
      cancelAnimationFrame(lipSyncTimerRef.current);
      lipSyncTimerRef.current = null;
    }
  }, []);

  useEffect(() => {
    return () => {
      if (lipSyncTimerRef.current) cancelAnimationFrame(lipSyncTimerRef.current);
      const ctx = ctxRef.current;
      if (ctx && ctx.state !== "closed") ctx.close();
    };
  }, []);

  return { enqueue, stop };
}
