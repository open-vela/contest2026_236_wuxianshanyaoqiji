/**
 * Live2D 渲染舞台
 * - Canvas 容器
 * - 加载/错误状态显示
 * - 触摸眼神追踪
 * - 点击模型触发动作 + 随机表情
 */
import { useCallback, useEffect, useRef } from "react";
import { useLive2D } from "@/hooks/useLive2D";
import { useAppStore } from "@/store/appStore";

// 点击触发的动作组（Haru 标准动作）
const TAP_MOTIONS = ["TapBody", "FlickHead", "Shake"];
// 点击触发的随机表情（Haru 自带 F01~F08）
const TAP_EXPRESSIONS = ["F01", "F02", "F03", "F04", "F05", "F06", "F07", "F08"];

interface Live2DStageProps {
  onReady?: (api: {
    focus: (nx: number, ny: number) => void;
    playMotion: (g: string) => void;
    setLipSync: (v: number) => void;
    setExpression: (n: string) => void;
  }) => void;
}

export function Live2DStage({ onReady }: Live2DStageProps) {
  const config = useAppStore((s) => s.config);
  const live2d = useLive2D(config.live2dModelUrl);
  const containerRef = useRef<HTMLDivElement>(null);

  // 模型就绪后，把 API 暴露给父组件（只触发一次）
  const onReadyRef = useRef(onReady);
  onReadyRef.current = onReady;
  const exposedRef = useRef(false);
  useEffect(() => {
    if (live2d.modelReady && !exposedRef.current && onReadyRef.current) {
      exposedRef.current = true;
      onReadyRef.current({
        focus: live2d.focus,
        playMotion: live2d.playMotion,
        setLipSync: live2d.setLipSync,
        setExpression: live2d.setExpression,
      });
    }
  }, [live2d.modelReady, live2d.focus, live2d.playMotion, live2d.setLipSync, live2d.setExpression]);

  // 触摸眼神追踪
  const handleTouch = (e: React.TouchEvent) => {
    const rect = containerRef.current?.getBoundingClientRect();
    if (!rect) return;
    const touch = e.touches[0];
    if (!touch) return;
    const nx = (touch.clientX - rect.left) / rect.width;
    const ny = (touch.clientY - rect.top) / rect.height;
    live2d.focus(nx, ny);
  };

  // 记录 touchstart 起点，用于区分"点击"和"拖动/滑动"
  const touchStartRef = useRef<{ x: number; y: number; t: number } | null>(null);

  const handleTouchStartCapture = (e: React.TouchEvent) => {
    const t = e.touches[0];
    if (t) touchStartRef.current = { x: t.clientX, y: t.clientY, t: Date.now() };
  };

  // 触摸结束时若位移小且时间短，判定为点击 → 播放动作 + 表情
  const handleTouchEnd = (e: React.TouchEvent) => {
    const start = touchStartRef.current;
    touchStartRef.current = null;
    if (!start) return;
    const t = e.changedTouches[0];
    if (!t) return;
    const dx = t.clientX - start.x;
    const dy = t.clientY - start.y;
    const dist = Math.hypot(dx, dy);
    const dt = Date.now() - start.t;
    if (dist < 10 && dt < 500) {
      triggerTap();
    }
  };

  // 触发点击动作：随机动作 + 随机表情（300ms 防抖，避免触摸+鼠标双触发）
  const lastTapRef = useRef(0);
  const triggerTap = useCallback(() => {
    if (!live2d.modelReady) return;
    const now = Date.now();
    if (now - lastTapRef.current < 300) return;
    lastTapRef.current = now;
    const motion = TAP_MOTIONS[Math.floor(Math.random() * TAP_MOTIONS.length)];
    const expr = TAP_EXPRESSIONS[Math.floor(Math.random() * TAP_EXPRESSIONS.length)];
    live2d.playMotion(motion);
    live2d.setExpression(expr);
  }, [live2d.modelReady, live2d.playMotion, live2d.setExpression]);

  // 鼠标点击（PC 调试用）
  const handleClick = useCallback(() => {
    triggerTap();
  }, [triggerTap]);

  return (
    <div
      ref={containerRef}
      className="absolute inset-0 flex items-center justify-center"
      onTouchMove={handleTouch}
      onTouchStart={handleTouch}
      onTouchStartCapture={handleTouchStartCapture}
      onTouchEnd={handleTouchEnd}
      onClick={handleClick}
    >
      <canvas
        ref={live2d.canvasRef}
        width={320}
        height={480}
        className="w-full h-full"
      />

      {/* 加载中 */}
      {live2d.modelLoading && (
        <div className="absolute inset-0 flex flex-col items-center justify-center gap-3">
          <div className="w-10 h-10 rounded-full border-2 border-moonlight/30 border-t-moonlight animate-spin" />
          <p className="text-xs text-moonlight/70 font-display">加载模型中…</p>
        </div>
      )}

      {/* 错误 */}
      {live2d.error && (
        <div className="absolute inset-0 flex flex-col items-center justify-center gap-2 px-6 text-center">
          <p className="text-sm text-sakura-400 font-display">模型加载失败</p>
          <p className="text-[10px] text-moonlight/50 leading-relaxed">
            {live2d.error}
          </p>
        </div>
      )}
    </div>
  );
}
