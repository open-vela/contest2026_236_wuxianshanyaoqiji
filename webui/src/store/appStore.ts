/**
 * 全局状态管理（zustand）
 */
import { create } from "zustand";
import type { ChatMessage, ChatPhase, RuntimeConfig } from "@/types/chat";
import { DEFAULT_CONFIG } from "@/types/chat";

interface AppState {
  // —— 对话阶段 ——
  phase: ChatPhase;
  setPhase: (p: ChatPhase) => void;

  // —— 消息列表（最多保留 30 条） ——
  messages: ChatMessage[];
  appendMessage: (m: ChatMessage) => void;
  updateLastAssistant: (content: string, streaming?: boolean) => void;
  clearMessages: () => void;

  // —— ASR 实时识别文本 ——
  partialText: string;
  setPartialText: (t: string) => void;

  // —— 错误信息 ——
  errorMsg: string | null;
  setError: (msg: string | null) => void;

  // —— 配置 ——
  config: RuntimeConfig;
  setConfig: (c: Partial<RuntimeConfig>) => void;

  // —— 设置抽屉开关 ——
  settingsOpen: boolean;
  setSettingsOpen: (v: boolean) => void;

  // —— 连接状态 ——
  wsConnected: boolean;
  setWsConnected: (v: boolean) => void;

  // —— 音量（用于 UI 显示，0~1）——
  micLevel: number;
  setMicLevel: (v: number) => void;
}

export const useAppStore = create<AppState>((set) => ({
  phase: "idle",
  setPhase: (p) => set({ phase: p }),

  messages: [],
  appendMessage: (m) =>
    set((s) => ({
      messages: [...s.messages, m].slice(-30),
    })),
  updateLastAssistant: (content, streaming) =>
    set((s) => {
      const msgs = [...s.messages];
      // 找到最后一条 assistant 消息
      for (let i = msgs.length - 1; i >= 0; i--) {
        if (msgs[i].role === "assistant") {
          msgs[i] = { ...msgs[i], content, streaming };
          break;
        }
      }
      return { messages: msgs };
    }),
  clearMessages: () => set({ messages: [] }),

  partialText: "",
  setPartialText: (t) => set({ partialText: t }),

  errorMsg: null,
  setError: (msg) => set({ errorMsg: msg }),

  config: DEFAULT_CONFIG,
  setConfig: (c) => set((s) => ({ config: { ...s.config, ...c } })),

  settingsOpen: false,
  setSettingsOpen: (v) => set({ settingsOpen: v }),

  wsConnected: false,
  setWsConnected: (v) => set({ wsConnected: v }),

  micLevel: 0,
  setMicLevel: (v) => set({ micLevel: v }),
}));
