/**
 * Express API 应用
 * - REST 路由
 * - 静态文件服务（生产环境）
 * - WebSocket 升级处理（在 server.ts 中挂载）
 */
import express, {
  type Request,
  type Response,
  type NextFunction,
} from "express";
import cors from "cors";
import path from "path";
import dotenv from "dotenv";
import { fileURLToPath } from "url";
import authRoutes from "./routes/auth.js";
import { isAsrConfigured } from "./services/doubaoASR.js";
import { isLlmConfigured } from "./services/doubaoLLM.js";
import { isTtsConfigured } from "./services/doubaoTTS.js";

// for esm mode
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// load env
dotenv.config();

const app: express.Application = express();

app.use(cors());
app.use(express.json({ limit: "10mb" }));
app.use(express.urlencoded({ extended: true, limit: "10mb" }));

/**
 * API Routes
 */
app.use("/api/auth", authRoutes);

/**
 * 健康检查 + 服务状态
 */
app.use("/api/health", (_req: Request, res: Response): void => {
  res.status(200).json({
    success: true,
    message: "ok",
    services: {
      asr: isAsrConfigured() ? "configured" : "mock",
      llm: isLlmConfigured() ? "configured" : "mock",
      tts: isTtsConfigured() ? "configured" : "mock",
    },
  });
});

/**
 * 生产环境：静态文件服务（板端部署用）
 */
if (process.env.NODE_ENV === "production") {
  const distPath = path.resolve(__dirname, "../dist");
  app.use(express.static(distPath));
  app.get("*", (_req: Request, res: Response): void => {
    res.sendFile(path.join(distPath, "index.html"));
  });
}

/**
 * error handler middleware
 */
app.use((error: Error, _req: Request, res: Response, _next: NextFunction) => {
  console.error("[API] 错误:", error.message);
  res.status(500).json({
    success: false,
    error: "Server internal error",
  });
});

export default app;
