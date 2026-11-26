import { type NextRequest } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000";

export async function GET(request: NextRequest) {
  const accessToken = request.cookies.get("access_token")?.value;
  if (!accessToken) return new Response(null, { status: 401 });

  const upstream = await fetch(`${BACKEND_URL}/api/v1/rag/status/stream`, {
    headers: { Authorization: `Bearer ${accessToken}`, Accept: "text/event-stream" },
    cache: "no-store",
    signal: request.signal,
  });
  if (!upstream.ok) return new Response(null, { status: upstream.status });

  return new Response(upstream.body, {
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-store",
      "X-Accel-Buffering": "no",
    },
  });
}
