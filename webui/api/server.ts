/**
 * 本地开发服务器入口
 * - Express HTTP 服务
 * - WebSocket /ws/chat 对话流
 */
import { createServer } from "http";
import { WebSocketServer } from "ws";
import app from "./app.js";
import { handleChatConnection } from "./ws/chatHandler.js";

const PORT = Number(process.env.PORT) || 3001;
const HOST = process.env.HOST || "0.0.0.0";

const server = createServer(app);

// WebSocket 服务器 — 仅处理 /ws/chat 路径
const wss = new WebSocketServer({ server, path: "/ws/chat" });

wss.on("connection", (ws, req) => {
  console.log(`[WS] 连接来自 ${req.socket.remoteAddress}`);
  handleChatConnection(ws);
});

wss.on("error", (err) => {
  console.error("[WS] 服务器错误:", err);
});

server.listen(PORT, HOST, () => {
  console.log(`\n╔══════════════════════════════════════════╗`);
  console.log(`║  RivoTek 二次元对话服务已启动              ║`);
  console.log(`║  HTTP:  http://${HOST}:${PORT}            `);
  console.log(`║  WS:    ws://${HOST}:${PORT}/ws/chat      `);
  console.log(`╚══════════════════════════════════════════╝\n`);
});

/**
 * close server
 */
process.on("SIGTERM", () => {
  console.log("SIGTERM signal received");
  wss.close();
  server.close(() => {
    console.log("Server closed");
    process.exit(0);
  });
});

process.on("SIGINT", () => {
  console.log("SIGINT signal received");
  wss.close();
  server.close(() => {
    console.log("Server closed");
    process.exit(0);
  });
});

export default app;
