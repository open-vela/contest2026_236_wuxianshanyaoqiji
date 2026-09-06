/**
 * 状态指示器
 * - 显示当前对话阶段
 * - 不同阶段不同颜色与动画
 */
import { clsx } from "clsx";
import type { ChatPhase } from "@/types/chat";

const PHASE_META: Record<ChatPhase, { label: string; color: string; dot: string }> = {
  idle: { label: "待机中", color: "text-moonlight/60", dot: "bg-moonlight/40" },
  listening: { label: "聆听中…", color: "text-sakura-300", dot: "bg-sakura-300" },
  recognizing: { label: "识别中…", color: "text-stardust-400", dot: "bg-stardust-400" },
  thinking: { label: "思考中…", color: "text-stardust-400", dot: "bg-stardust-400" },
  speaking: { label: "说话中…", color: "text-moonlight-300", dot: "bg-moonlight-300" },
  error: { label: "出错了", color: "text-sakura-400", dot: "bg-sakura-400" },
};

interface StatusIndicatorProps {
  phase: ChatPhase;
  partialText?: string;
}

export function StatusIndicator({ phase, partialText }: StatusIndicatorProps) {
  const meta = PHASE_META[phase] || PHASE_META.idle;
  const showPulse = phase === "listening" || phase === "thinking" || phase === "recognizing";

  return (
    <div className="flex flex-col items-center gap-1">
      <div className={clsx("flex items-center gap-1.5 text-[11px] font-display", meta.color)}>
        <span className="relative flex">
          {showPulse && (
            <span
              className={clsx("absolute inline-flex h-full w-full rounded-full opacity-60", meta.dot)}
              style={{ animation: "pulse-soft 1.5s ease-in-out infinite" }}
            />
          )}
          <span className={clsx("relative inline-flex w-1.5 h-1.5 rounded-full", meta.dot)} />
        </span>
        {meta.label}
      </div>
      {phase === "listening" && partialText && (
        <p className="text-[10px] text-moonlight/50 max-w-[260px] truncate text-center">
          {partialText}
        </p>
      )}
    </div>
  );
}
