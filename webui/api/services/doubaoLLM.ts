/**
 * 豆包（火山引擎方舟）LLM 服务
 * OpenAI 兼容 SSE 流式
 *
 * 无凭证时降级为 mock 模式
 */

const ARK_URL = "https://ark.cn-beijing.volces.com/api/v3/chat/completions";

export interface LlmMessage {
  role: "system" | "user" | "assistant";
  content: string;
}

export interface LlmCallbacks {
  onDelta: (text: string) => void;
  onDone: (fullText: string) => void;
  onError: (msg: string) => void;
}

export function isLlmConfigured(): boolean {
  return !!process.env.DOUBAO_ARK_API_KEY;
}

/**
 * 流式调用豆包 LLM
 */
export async function streamChat(
  messages: LlmMessage[],
  modelId: string,
  callbacks: LlmCallbacks,
): Promise<void> {
  // —— Mock 模式 ——
  if (!isLlmConfigured()) {
    console.warn("[LLM] 未配置 ARK API Key，使用 mock 模式");
    const mockResponses = [
      "你好呀～我是小星，有什么可以帮你的吗？",
      "今天也要元气满满哦！",
      "嗯嗯，我在听呢，继续说吧～",
      "这个问题好有趣，让我想想…",
      "不要担心，一切都会好起来的！",
    ];
    const fullText = mockResponses[Math.floor(Math.random() * mockResponses.length)];
    // 逐字流式输出
    for (const char of fullText) {
      await new Promise((r) => setTimeout(r, 60));
      callbacks.onDelta(char);
    }
    callbacks.onDone(fullText);
    return;
  }

  // —— 真实模式 ——
  try {
    const apiKey = process.env.DOUBAO_ARK_API_KEY!;
    const res = await fetch(ARK_URL, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${apiKey}`,
      },
      body: JSON.stringify({
        model: modelId,
        messages,
        stream: true,
        max_tokens: 512,
        temperature: 0.7,
      }),
    });

    if (!res.ok) {
      const errText = await res.text();
      callbacks.onError(`LLM 请求失败 (${res.status}): ${errText}`);
      return;
    }

    if (!res.body) {
      callbacks.onError("LLM 响应体为空");
      return;
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    let fullText = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() || "";

      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed || !trimmed.startsWith("data:")) continue;
        const data = trimmed.slice(5).trim();
        if (data === "[DONE]") continue;

        try {
          const json = JSON.parse(data);
          const delta = json.choices?.[0]?.delta?.content || "";
          if (delta) {
            fullText += delta;
            callbacks.onDelta(delta);
          }
        } catch {
          // 跳过无法解析的行
        }
      }
    }

    callbacks.onDone(fullText);
  } catch (e: any) {
    callbacks.onError(`LLM 请求异常: ${e?.message || e}`);
  }
}
