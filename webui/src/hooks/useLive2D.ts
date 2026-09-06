/**
 * Live2D 模型管理 Hook
 * - 创建 PIXI Application + Canvas
 * - 加载 Cubism 4 模型（Haru / Hiyori）
 * - 竖屏 320×480 自适应缩放
 * - 口型同步：每帧设置 ParamMouthOpenY
 * - 眼神追踪：focus(x, y)
 * - 待机动作循环
 */
import { useCallback, useEffect, useRef, useState } from "react";

// 板端目标分辨率
const SCREEN_W = 320;
const SCREEN_H = 480;

interface UseLive2DReturn {
  canvasRef: React.RefObject<HTMLCanvasElement>;
  modelReady: boolean;
  modelLoading: boolean;
  error: string | null;
  /** 眼神聚焦（归一化坐标 0~1） */
  focus: (nx: number, ny: number) => void;
  /** 播放动作组 */
  playMotion: (group: string) => void;
  /** 设置口型张开度 0~1 */
  setLipSync: (value: number) => void;
  /** 切换表情 */
  setExpression: (name: string) => void;
}

export function useLive2D(modelUrl: string): UseLive2DReturn {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const appRef = useRef<PIXI.Application | null>(null);
  const modelRef = useRef<PIXI.live2d.Live2DModel | null>(null);
  const lipValueRef = useRef(0);
  const targetLipRef = useRef(0);

  const [modelReady, setModelReady] = useState(false);
  const [modelLoading, setModelLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // —— 初始化 PIXI + 加载模型 ——
  useEffect(() => {
    let destroyed = false;
    const canvas = canvasRef.current;
    if (!canvas) return;

    // 等待 CDN 全局变量就绪
    const waitForGlobals = (): Promise<void> => {
      return new Promise((resolve, reject) => {
        let tries = 0;
        const check = () => {
          if (typeof PIXI !== "undefined" && (PIXI as any).live2d?.Live2DModel) {
            resolve();
          } else if (tries++ > 100) {
            reject(new Error("Live2D CDN 脚本加载超时"));
          } else {
            setTimeout(check, 50);
          }
        };
        check();
      });
    };

    (async () => {
      try {
        await waitForGlobals();
        if (destroyed) return;

        // 关闭 WebGL 失败时的报错弹窗
        (PIXI as any).settings.FAIL_IF_NOT_PERF = false;
        (PIXI as any).settings.RESOLUTION = window.devicePixelRatio || 1;

        const app = new PIXI.Application({
          view: canvas,
          width: SCREEN_W,
          height: SCREEN_H,
          backgroundAlpha: 0,
          antialias: true,
          autoStart: true,
          powerPreference: "low-power",
        });
        appRef.current = app;
        app.ticker.maxFPS = 30; // 板端性能预算

        // 加载模型
        const model = await PIXI.live2d.Live2DModel.from(modelUrl);
        if (destroyed) {
          model.destroy();
          return;
        }

        modelRef.current = model;
        app.stage.addChild(model);

        // 关闭自动更新，手动管理（口型同步需要）
        model.autoUpdate = false;

        // 自适应缩放：模型高度填满屏幕的 ~85%
        const scale = Math.min(
          SCREEN_W / model.width,
          SCREEN_H / model.height,
        ) * 0.85;
        model.scale.set(scale);

        // 锚点居中底部偏上
        model.anchor.set(0.5, 0.5);
        model.x = SCREEN_W / 2;
        model.y = SCREEN_H * 0.52;

        // 每帧手动更新 + 口型同步
        const tickFn = (delta: number) => {
          if (model.destroyed) return;
          // 平滑插值口型值
          lipValueRef.current += (targetLipRef.current - lipValueRef.current) * 0.3;
          // 在 update 前设置口型参数（动作通常不覆盖此参数）
          try {
            model.internalModel.coreModel.setParameterValueById(
              "ParamMouthOpenY",
              lipValueRef.current,
            );
          } catch {
            // 某些模型可能没有此参数
          }
          model.update(delta);
        };
        app.ticker.add(tickFn);

        setModelReady(true);
        setModelLoading(false);

        // 播放初始待机动作
        try {
          model.motion("Idle");
        } catch {
          // 忽略
        }
      } catch (e: any) {
        console.error("[Live2D] 加载失败:", e);
        setError(e?.message || "模型加载失败");
        setModelLoading(false);
      }
    })();

    return () => {
      destroyed = true;
      const app = appRef.current;
      const model = modelRef.current;
      if (model && !model.destroyed) model.destroy();
      if (app) app.destroy();
      appRef.current = null;
      modelRef.current = null;
    };
  }, [modelUrl]);

  // —— 眼神聚焦 ——
  const focus = useCallback((nx: number, ny: number) => {
    const model = modelRef.current;
    if (!model || model.destroyed) return;
    // nx, ny 是 0~1 归一化坐标，转为屏幕坐标
    model.focus(nx * SCREEN_W, ny * SCREEN_H);
  }, []);

  // —— 播放动作 ——
  const playMotion = useCallback((group: string) => {
    const model = modelRef.current;
    if (!model || model.destroyed) return;
    try {
      model.motion(group);
    } catch {
      // 忽略不存在的动作组
    }
  }, []);

  // —— 口型同步 ——
  const setLipSync = useCallback((value: number) => {
    targetLipRef.current = Math.max(0, Math.min(1, value));
  }, []);

  // —— 表情 ——
  const setExpression = useCallback((name: string) => {
    const model = modelRef.current;
    if (!model || model.destroyed) return;
    try {
      model.expression(name);
    } catch {
      // 忽略
    }
  }, []);

  return {
    canvasRef,
    modelReady,
    modelLoading,
    error,
    focus,
    playMotion,
    setLipSync,
    setExpression,
  };
}
