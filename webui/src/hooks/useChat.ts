/**
 * 对话编排 Hook
 * - 管理 WebSocket 连接
 * - 协调录音 → ASR → LLM → TTS → 口型同步 全流程
 * - 文本输入模式（无麦克风时降级）
 *
 * 关键设计：所有回调用 ref 存储，WS 连接只建立一次，
 * 避免 React 渲染周期导致的重连循环。
 */
import { useCallback, useEffect, useRef } from "react";
import { useAppStore } from "@/store/appStore";
import { useAudioRecorder } from "./useAudioRecorder";
import { useAudioPlayer } from "./useAudioPlayer";
import { genId } from "@/lib/audioUtils";
import type { ClientMessage, ServerMessage, RuntimeConfig } from "@/types/chat";

function wsUrl(): string {
  if (import.meta.env.DEV) {
    return "ws://localhost:3001/ws/chat";
  }
  const proto = location.protocol === "https:" ? "wss:" : "ws:";
  return `${proto}//${location.host}/ws/chat`;
}

export function useChat(
  lipSyncSetter: (v: number) => void,
  onSpeakStart?: () => void,
  onSpeakEnd?: () => void,
) {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimer = useRef<number | null>(null);
  const phaseRef = useRef<string>("idle");
  const closedByUsRef = useRef(false);

  // 用 ref 存储所有需要访问的引用，避免依赖循环
  const store = useAppStore;
  const storeRef = useRef(store);
  storeRef.current = store;

  // lipSync / speak 回调用 ref
  const lipSyncRef = useRef(lipSyncSetter);
  lipSyncRef.current = lipSyncSetter;
  const onSpeakStartRef = useRef(onSpeakStart);
  onSpeakStartRef.current = onSpeakStart;
  const onSpeakEndRef = useRef(onSpeakEnd);
  onSpeakEndRef.current = onSpeakEnd;

  // —— 音频播放器（回调用 ref，对象本身不作为依赖） ——
  const player = useAudioPlayer({
    onLipSync: (v: number) => lipSyncRef.current(v),
    onPlaybackStart: () => onSpeakStartRef.current?.(),
    onPlaybackEnd: () => {
      onSpeakEndRef.current?.();
      lipSyncRef.current(0);
      storeRef.current.getState().setPhase("idle");
    },
  });
  // 把 player 方法存到 ref，这样 handleMessage 可以稳定引用
  const playerRef = useRef(player);
  playerRef.current = player;

  // —— 发送消息（稳定，无依赖） ——
  const send = useCallback((msg: ClientMessage) => {
    const ws = wsRef.current;
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(msg));
    }
  }, []);
  const sendRef = useRef(send);
  sendRef.current = send;

  // —— 音频录制 ——
  const recorder = useAudioRecorder({
    onChunk: (hex) => sendRef.current({ type: "audio-chunk", data: hex }),
    onLevel: (level) => storeRef.current.getState().setMicLevel(level),
  });
  const recorderRef = useRef(recorder);
  recorderRef.current = recorder;

  // —— 处理服务器消息（空依赖，通过 ref 访问一切） ——
  const handleMessage = useCallback((e: MessageEvent) => {
    let msg: ServerMessage;
    try {
      msg = JSON.parse(e.data);
    } catch {
      return;
    }

    const s = storeRef.current.getState();

    switch (msg.type) {
      case "asr-partial":
        s.setPartialText(msg.text);
        break;
      case "asr-final":
        s.setPartialText("");
        if (msg.text.trim()) {
          s.appendMessage({
            id: genId(),
            role: "user",
            content: msg.text,
            ts: Date.now(),
          });
        }
        break;
      case "llm-delta":
        if (phaseRef.current !== "thinking") {
          s.setPhase("thinking");
          phaseRef.current = "thinking";
        }
        {
          const msgs = storeRef.current.getState().messages;
          const last = msgs[msgs.length - 1];
          if (last && last.role === "assistant" && last.streaming) {
            s.updateLastAssistant(last.content + msg.text, true);
          } else {
            s.appendMessage({
              id: genId(),
              role: "assistant",
              content: msg.text,
              streaming: true,
              ts: Date.now(),
            });
          }
        }
        break;
      case "llm-done":
        {
          const msgs = storeRef.current.getState().messages;
          const last = msgs[msgs.length - 1];
          if (last && last.role === "assistant") {
            s.updateLastAssistant(
              (last.content || "") + (msg.text || ""),
              false,
            );
          } else if (msg.text) {
            s.appendMessage({
              id: genId(),
              role: "assistant",
              content: msg.text,
              ts: Date.now(),
            });
          }
        }
        break;
      case "tts-start":
        s.setPhase("speaking");
        phaseRef.current = "speaking";
        break;
      case "tts-chunk":
        playerRef.current.enqueue(msg.data, msg.sampleRate);
        break;
      case "tts-end":
        // 播放器会在队列空时触发 onPlaybackEnd
        break;
      case "phase":
        s.setPhase(msg.phase);
        phaseRef.current = msg.phase;
        break;
      case "error":
        s.setError(msg.message);
        s.setPhase("error");
        phaseRef.current = "error";
        break;
      case "config":
        s.setConfig(msg.payload);
        break;
    }
  }, []);

  // —— WebSocket 连接（空依赖，只建立一次） ——
  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;
    closedByUsRef.current = false;
    try {
      const ws = new WebSocket(wsUrl());
      wsRef.current = ws;

      ws.onopen = () => {
        const s = storeRef.current.getState();
        s.setWsConnected(true);
        s.setError(null);
        sendRef.current({ type: "config-get" });
      };

      ws.onmessage = handleMessage;

      ws.onclose = () => {
        storeRef.current.getState().setWsConnected(false);
        wsRef.current = null;
        // 自动重连（3 秒后），除非是我们主动关闭
        if (!closedByUsRef.current) {
          if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
          reconnectTimer.current = window.setTimeout(connect, 3000);
        }
      };

      ws.onerror = () => {
        storeRef.current.getState().setError("WebSocket 连接失败");
      };
    } catch (e) {
      console.error("[WS] 连接失败:", e);
    }
  }, [handleMessage]);

  useEffect(() => {
    connect();
    return () => {
      closedByUsRef.current = true;
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
      wsRef.current?.close();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // —— 开始录音 ——
  const startRecording = useCallback(async () => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      storeRef.current.getState().setError("未连接到服务器");
      return;
    }
    const s = storeRef.current.getState();

    // 先尝试启动录音（获取麦克风权限），失败则不进入 listening
    try {
      await recorderRef.current.start();
    } catch (e: any) {
      s.setError("麦克风启动失败：" + (e?.message || "请允许麦克风权限"));
      s.setPhase("error");
      phaseRef.current = "error";
      return;
    }

    // 录音启动成功，创建 assistant 占位消息 + 进入 listening
    s.appendMessage({
      id: genId(),
      role: "assistant",
      content: "",
      streaming: true,
      ts: Date.now(),
    });

    s.setPhase("listening");
    phaseRef.current = "listening";
    playerRef.current.stop(); // 停止当前播放
    sendRef.current({ type: "audio-start", sampleRate: 16000, channels: 1 });
  }, []);

  // —— 停止录音 ——
  const stopRecording = useCallback(() => {
    recorderRef.current.stop();
    sendRef.current({ type: "audio-end" });
    const s = storeRef.current.getState();
    s.setPhase("recognizing");
    phaseRef.current = "recognizing";
    s.setMicLevel(0);
  }, []);

  // —— 发送文本 ——
  const sendText = useCallback((text: string) => {
    if (!text.trim()) return;
    const s = storeRef.current.getState();
    s.appendMessage({
      id: genId(),
      role: "user",
      content: text,
      ts: Date.now(),
    });
    s.appendMessage({
      id: genId(),
      role: "assistant",
      content: "",
      streaming: true,
      ts: Date.now(),
    });
    s.setPhase("thinking");
    phaseRef.current = "thinking";
    sendRef.current({ type: "text-input", text });
  }, []);

  // —— 更新配置 ——
  const updateConfig = useCallback((partial: Partial<RuntimeConfig>) => {
    const s = storeRef.current.getState();
    s.setConfig(partial);
    sendRef.current({ type: "config-set", payload: partial });
  }, []);

  return {
    startRecording,
    stopRecording,
    sendText,
    updateConfig,
    recording: recorder.recording,
    recorderError: recorder.error,
  };
}
