/**
 * 对话气泡
 * - 用户消息：右对齐，樱粉色
 * - 助手消息：左对齐，月光青/玻璃质感
 * - 流式消息带打字光标
 */
import { clsx } from "clsx";
import type { ChatMessage } from "@/types/chat";

interface ChatBubbleProps {
  message: ChatMessage;
}

export function ChatBubble({ message }: ChatBubbleProps) {
  const isUser = message.role === "user";
  const isStreaming = message.streaming;
  const isEmpty = !message.content && isStreaming;

  return (
    <div
      className={clsx(
        "flex w-full px-3",
        isUser ? "justify-end" : "justify-start",
      )}
    >
      <div
        className={clsx(
          "max-w-[78%] rounded-2xl px-3 py-2 text-[13px] leading-relaxed",
          "animate-float-up",
          isUser
            ? "bg-sakura-300/90 text-midnight-700 rounded-br-md"
            : "glass text-moonlight-100 rounded-bl-md",
        )}
      >
        {isEmpty ? (
          <span className="inline-flex gap-1 py-0.5">
            <span className="w-1.5 h-1.5 rounded-full bg-moonlight/60 animate-pulse-soft" />
            <span
              className="w-1.5 h-1.5 rounded-full bg-moonlight/60 animate-pulse-soft"
              style={{ animationDelay: "0.2s" }}
            />
            <span
              className="w-1.5 h-1.5 rounded-full bg-moonlight/60 animate-pulse-soft"
              style={{ animationDelay: "0.4s" }}
            />
          </span>
        ) : (
          <span className={clsx(isStreaming && "typing-cursor")}>
            {message.content}
          </span>
        )}
      </div>
    </div>
  );
}
