import {
  POLY_SPORTS_WS,
  parsePolySportMessage,
  type PolySportUpdate,
} from "@/core/polySportsFeed";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

/**
 * GET /api/sports/stream?league=fifwc
 *
 * Server-side proxy of Polymarket's public sports WebSocket as SSE.
 * Filters to one league prefix (default fifwc = World Cup). DRY_RUN read-only.
 */
export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const league = (searchParams.get("league") ?? "fifwc").toLowerCase();

  const encoder = new TextEncoder();
  let ws: WebSocket | null = null;
  let closed = false;

  const stream = new ReadableStream<Uint8Array>({
    start(controller) {
      const send = (event: string, data: unknown) => {
        if (closed) return;
        controller.enqueue(
          encoder.encode(`event: ${event}\ndata: ${JSON.stringify(data)}\n\n`),
        );
      };

      send("ready", { league, source: POLY_SPORTS_WS });

      try {
        ws = new WebSocket(POLY_SPORTS_WS);
      } catch (error) {
        send("error", {
          message: error instanceof Error ? error.message : "WebSocket failed",
        });
        controller.close();
        return;
      }

      ws.onopen = () => {
        send("connected", { at: new Date().toISOString() });
      };

      ws.onmessage = (message) => {
        const raw = String(message.data);
        if (raw === "ping") {
          ws?.send("pong");
          return;
        }
        const update = parsePolySportMessage(raw);
        if (!update) return;
        if (!update.slug.toLowerCase().startsWith(`${league}-`)) return;
        send("sport", update satisfies PolySportUpdate);
      };

      ws.onerror = () => {
        send("error", { message: "Sports WebSocket error" });
      };

      ws.onclose = () => {
        if (!closed) {
          send("closed", { at: new Date().toISOString() });
          controller.close();
        }
      };

      const abort = () => {
        closed = true;
        ws?.close();
        try {
          controller.close();
        } catch {
          /* already closed */
        }
      };

      request.signal.addEventListener("abort", abort);
    },
    cancel() {
      closed = true;
      ws?.close();
    },
  });

  return new Response(stream, {
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache, no-transform",
      Connection: "keep-alive",
    },
  });
}
