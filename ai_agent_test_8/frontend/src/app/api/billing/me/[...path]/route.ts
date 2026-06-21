import { NextRequest, NextResponse } from "next/server";

import { backendFetch, BackendApiError } from "@/lib/server-api";

interface RouteContext {
  params: Promise<{ path: string[] }>;
}

async function proxy(request: NextRequest, context: RouteContext, method: string) {
  try {
    const accessToken = request.cookies.get("access_token")?.value;
    if (!accessToken) {
      return NextResponse.json({ detail: "Not authenticated" }, { status: 401 });
    }

    const { path } = await context.params;
    const subpath = path.join("/");
    const qs = new URL(request.url).searchParams.toString();
    const url = `/api/v1/billing/me/${subpath}${qs ? `?${qs}` : ""}`;

    const init: RequestInit & { headers: Record<string, string> } = {
      method,
      headers: { Authorization: `Bearer ${accessToken}` },
    };

    if (method !== "GET" && method !== "DELETE") {
      const text = await request.text();
      if (text) {
        init.body = text;
        init.headers["Content-Type"] = "application/json";
      }
    }

    const data = await backendFetch(url, init);
    if (data === null || data === undefined) {
      return new NextResponse(null, { status: 204 });
    }
    return NextResponse.json(data);
  } catch (error) {
    if (error instanceof BackendApiError) {
      return NextResponse.json({ detail: error.message }, { status: error.status });
    }
    return NextResponse.json({ detail: "Internal server error" }, { status: 500 });
  }
}

export const GET = (request: NextRequest, context: RouteContext) => proxy(request, context, "GET");
export const POST = (request: NextRequest, context: RouteContext) =>
  proxy(request, context, "POST");
export const PATCH = (request: NextRequest, context: RouteContext) =>
  proxy(request, context, "PATCH");
export const PUT = (request: NextRequest, context: RouteContext) => proxy(request, context, "PUT");
export const DELETE = (request: NextRequest, context: RouteContext) =>
  proxy(request, context, "DELETE");
