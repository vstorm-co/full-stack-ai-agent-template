import { NextResponse, type NextRequest } from "next/server";

import { BackendApiError, backendFetch } from "@/lib/server-api";

export async function GET(request: NextRequest) {
  const accessToken = request.cookies.get("access_token")?.value;
  if (!accessToken) {
    return NextResponse.json({ detail: "Not authenticated" }, { status: 401 });
  }
  try {
    const data = await backendFetch<{ items: unknown[]; total: number; truncated: boolean }>(
      "/api/v1/me/memory",
      { headers: { Authorization: `Bearer ${accessToken}` } },
    );
    return NextResponse.json(data);
  } catch (error) {
    if (error instanceof BackendApiError) {
      // Forward the backend's own message ("Agent memory is not enabled") rather
      // than the generic "Backend API error: <status>".
      const body = error.data as { error?: { code?: string; message?: string } } | null;
      return NextResponse.json(
        { detail: body?.error?.message ?? error.message, code: body?.error?.code },
        { status: error.status },
      );
    }
    return NextResponse.json({ detail: "Internal server error" }, { status: 500 });
  }
}
