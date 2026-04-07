/**
 * SSE parser for POST-based streaming endpoints.
 *
 * We can't use EventSource (GET-only), so we use fetch + ReadableStream
 * and parse SSE frames manually.
 */

export type SSECallback = (event: string, data: unknown) => void;

export async function streamChat(
  message: string,
  conversationId: string | null,
  onEvent: SSECallback,
  signal?: AbortSignal
): Promise<void> {
  const res = await fetch("/api/v1/chat", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "text/event-stream",
    },
    body: JSON.stringify({
      message,
      conversation_id: conversationId,
    }),
    signal,
  });

  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`Chat request failed: ${res.status} ${text}`);
  }

  const reader = res.body?.getReader();
  if (!reader) throw new Error("No response body");

  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });

    // SSE frames are separated by double newlines
    const frames = buffer.split("\n\n");
    // Keep the last (possibly incomplete) frame in the buffer
    buffer = frames.pop() ?? "";

    for (const frame of frames) {
      if (!frame.trim()) continue;

      let eventName = "message";
      let dataStr = "";

      for (const line of frame.split("\n")) {
        if (line.startsWith("event: ")) {
          eventName = line.slice(7).trim();
        } else if (line.startsWith("data: ")) {
          dataStr += line.slice(6);
        } else if (line.startsWith("data:")) {
          dataStr += line.slice(5);
        }
      }

      if (dataStr) {
        try {
          const data = JSON.parse(dataStr);
          onEvent(eventName, data);
        } catch {
          // Non-JSON data, emit as raw string
          onEvent(eventName, dataStr);
        }
      }
    }
  }
}
