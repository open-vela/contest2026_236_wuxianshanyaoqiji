/**
 * 录音按钮
 * - 待机：月光青圆形 + 麦克风图标
 * - 录音：樱粉脉冲 + 波纹扩散
 * - 思考/识别：加载圈
 * - 说话：停止按钮（可打断）
 */
import { clsx } from "clsx";
import { Mic, Square, Loader2 } from "lucide-react";
import type { ChatPhase } from "@/types/chat";

interface RecordButtonProps {
  phase: ChatPhase;
  micLevel: number;
  recording: boolean;
  onPress: () => void;
}

export function RecordButton({
  phase,
  micLevel,
  recording,
  onPress,
}: RecordButtonProps) {
  const isListening = phase === "listening";
  const isBusy = phase === "recognizing" || phase === "thinking";
  const isSpeaking = phase === "speaking";
  const disabled = isBusy;

  // 麦克风音量缩放
  const scale = 1 + Math.min(0.15, micLevel * 0.8);

  return (
    <div className="relative flex items-center justify-center">
      {/* 录音波纹 */}
      {isListening && (
        <>
          <span className="recording-ring" />
          <span
            className="recording-ring"
            style={{ animationDelay: "0.5s" }}
          />
        </>
      )}

      <button
        onClick={onPress}
        disabled={disabled}
        className={clsx(
          "relative z-10 flex items-center justify-center rounded-full",
          "transition-all duration-200 select-none",
          "w-14 h-14 active:scale-95",
          disabled && "opacity-50 cursor-not-allowed",
          isListening
            ? "bg-sakura-400 shadow-[0_0_24px_rgba(255,107,130,0.5)]"
            : isSpeaking
              ? "bg-sakura-500/80 shadow-[0_0_16px_rgba(255,107,130,0.3)]"
              : "bg-moonlight/90 shadow-[0_0_20px_rgba(142,230,224,0.3)]",
        )}
        style={isListening ? { transform: `scale(${scale})` } : undefined}
      >
        {isBusy ? (
          <Loader2 className="w-5 h-5 text-midnight-600 animate-spin" />
        ) : isListening ? (
          <Square className="w-4 h-4 text-midnight-600 fill-current" />
        ) : isSpeaking ? (
          <Square className="w-4 h-4 text-white fill-current" />
        ) : (
          <Mic className="w-5 h-5 text-midnight-600" />
        )}
      </button>
    </div>
  );
}
