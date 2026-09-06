/**
 * 全局 PIXI 类型声明（CDN UMD 加载，不通过 npm 安装）
 * 仅声明项目实际使用的 API 子集，避免引入完整 @types/pixi.js
 */

// Cubism Core 全局
declare const Live2DCubismCore: any;

// pixi.js v6 全局
declare namespace PIXI {
  class Application {
    constructor(opts?: any);
    renderer: any;
    stage: Container;
    ticker: Ticker;
    view: HTMLCanvasElement;
    destroy(): void;
  }

  class Container {
    addChild<T extends DisplayObject>(...children: T[]): T;
    removeChildren(): DisplayObject[];
    destroy(): void;
    width: number;
    height: number;
    scale: ObservablePoint;
    position: Point;
    anchor?: ObservablePoint;
  }

  class DisplayObject {
    scale: ObservablePoint;
    position: Point;
    anchor?: ObservablePoint;
    visible: boolean;
    destroyed: boolean;
    destroy(): void;
  }

  class Point {
    x: number;
    y: number;
    set(x?: number, y?: number): void;
  }

  class ObservablePoint {
    x: number;
    y: number;
    set(x?: number, y?: number): void;
  }

  class Ticker {
    add(fn: (delta: number) => void): void;
    remove(fn: (delta: number) => void): void;
    started: boolean;
    start(): void;
    stop(): void;
    maxFPS: number;
  }

  namespace live2d {
    interface Model {
      internalModel: {
        coreModel: any;
        motionManager: any;
      };
      motion(name: string): void;
      expression(name: string): void;
      focus(x: number, y: number): void;
      autoUpdate: boolean;
      anchor: ObservablePoint;
      scale: ObservablePoint;
      position: Point;
      destroyed: boolean;
      textures: any[];
      update(...args: any[]): void;
      destroy(): void;
    }

    class Live2DModel extends DisplayObject {
      static from<M = Live2DModel>(src: string | object): Promise<M>;
      static registeredTags: any;
      motion(name: string): void;
      expression(name: string): void;
      focus(x: number, y: number): void;
      update(dt: number): void;
      autoUpdate: boolean;
      x: number;
      y: number;
      width: number;
      height: number;
      internalModel: {
        coreModel: any;
        motionManager: any;
        parameters: { params: { id: string; defaultValue: number; value: number }[]; setParamById(id: string, value: number): void };
      };
      gestures: any;
    }

    interface MotionPriority {
      NONE: number;
      IDLE: number;
      NORMAL: number;
      FORCE: number;
    }
  }

  const settings: any;
  const Loader: any;
}
