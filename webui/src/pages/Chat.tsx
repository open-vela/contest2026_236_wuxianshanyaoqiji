/**
 * 主对话页面
 * - 全屏 Live2D 模型
 * - 顶部状态栏 + 设置入口
 * - 底部对话气泡浮层 + 录音按钮
 * - 整合 useChat 编排全流程
 */
import { useCallback, useRef } from "react";
import { Settings, Wifi, WifiOff } from "lucide-react";
import { useAppStore } from "@/store/appStore";
import { useChat } from "@/hooks/useChat";
import { Live2DStage } from "@/components/Live2DStage";
import { ChatBubble } from "@/components/ChatBubble";
import { StatusIndicator } from "@/components/StatusIndicator";
import { RecordButton } from "@/components/RecordButton";
import { SettingsDrawer } from "@/components/SettingsDrawer";

export function ChatPage() {
  const phase = useAppStore((s) => s.phase);
  const messages = useAppStore((s) => s.messages);
  const partialText = useAppStore((s) => s.partialText);
  const micLevel = useAppStore((s) => s.micLevel);
  const wsConnected = useAppStore((s) => s.wsConnected);
  const errorMsg = useAppStore((s) => s.errorMsg);
  const settingsOpen = useAppStore((s) => s.settingsOpen);
  const setSettingsOpen = useAppStore((s) => s.setSettingsOpen);
  const setError = useAppStore((s) => s.setError);
  const setPhase = useAppStore((s) => s.setPhase);

  // Live2D 口型同步函数引用
  const lipSyncRef = useRef<(v: number) => void>(() => {});
  const motionRef = useRef<{
    focus: (nx: number, ny: number) => void;
    playMotion: (g: string) => void;
    setExpression: (n: string) => void;
  } | null>(null);

  const handleLipSync = useCallback((v: number) => {
    lipSyncRef.current(v);
  }, []);

  // 对话编排
  const chat = useChat(
    handleLipSync,
    // 说话开始 → 播放动作
    () => motionRef.current?.playMotion("TapBody"),
    // 说话结束 → 回到待机
    () => motionRef.current?.playMotion("Idle"),
  );

  const handleRecordPress = useCallback(() => {
    if (phase === "listening") {
      chat.stopRecording();
    } else if (phase === "speaking") {
      // 打断播放
      lipSyncRef.current(0);
      setPhase("idle");
    } else if (phase === "idle" || phase === "error") {
      setError(null);
      chat.startRecording();
    }
  }, [phase, chat, setPhase, setError]);

  const handleLive2DReady = useCallback(
    (api: {
      focus: (nx: number, ny: number) => void;
      playMotion: (g: string) => void;
      setLipSync: (v: number) => void;
      setExpression: (n: string) => void;
    }) => {
      lipSyncRef.current = api.setLipSync;
      motionRef.current = {
        focus: api.focus,
        playMotion: api.playMotion,
        setExpression: api.setExpression,
      };
    },
    [],
  );

  // 最近 4 条消息（浮层显示）
  const recentMessages = messages.slice(-4);

  return (
    <div className="screen-portrait aurora-bg stardots font-body">
      {/* —— Live2D 舞台（全屏） —— */}
      <Live2DStage onReady={handleLive2DReady} />

      {/* —— 顶部状态栏 —— */}
      <div className="absolute top-0 left-0 right-0 z-20 flex items-center justify-between px-3 pt-2 pb-1">
        {/* 连接状态 */}
        <div className="flex items-center gap-1">
          {wsConnected ? (
            <Wifi className="w-3 h-3 text-moonlight-300" />
          ) : (
            <WifiOff className="w-3 h-3 text-sakura-400" />
          )}
          <span className="text-[9px] text-moonlight/50">
            {wsConnected ? "已连接" : "断开"}
          </span>
        </div>

        {/* 状态指示 */}
        <StatusIndicator phase={phase} partialText={partialText} />

        {/* 设置按钮 */}
        <button
          onClick={() => setSettingsOpen(true)}
          className="p-1.5 rounded-full hover:bg-moonlight/10 transition"
        >
          <Settings className="w-3.5 h-3.5 text-moonlight/60" />
        </button>
      </div>

      {/* —— 错误提示 —— */}
      {errorMsg && (
        <div className="absolute top-10 left-3 right-3 z-20 glass rounded-xl px-3 py-2 flex items-center justify-between animate-float-up">
          <p className="text-[11px] text-sakura-300 truncate">{errorMsg}</p>
          <button
            onClick={() => setError(null)}
            className="text-[10px] text-moonlight/50 ml-2 shrink-0"
          >
            ×
          </button>
        </div>
      )}

      {/* —— 对话气泡浮层 —— */}
      {recentMessages.length > 0 && (
        <div className="absolute bottom-20 left-0 right-0 z-10 px-1 space-y-1.5 max-h-[140px] overflow-y-auto no-scrollbar">
          {recentMessages.map((msg) => (
            <ChatBubble key={msg.id} message={msg} />
          ))}
        </div>
      )}

      {/* —— 底部录音按钮 —— */}
      <div className="absolute bottom-4 left-0 right-0 z-20 flex justify-center">
        <RecordButton
          phase={phase}
          micLevel={micLevel}
          recording={chat.recording}
          onPress={handleRecordPress}
        />
      </div>

      {/* —— 设置抽屉 —— */}
      <SettingsDrawer
        open={settingsOpen}
        onClose={() => setSettingsOpen(false)}
        onUpdate={chat.updateConfig}
      />
    </div>
  );
}
