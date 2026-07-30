import { NextResponse, type NextRequest } from "next/server";

import { BackendApiError, backendFetch } from "@/lib/server-api";

// A memory file is addressed by the `path` query parameter, not a path segment,
// because a name already in the store may contain `/`. Params are forwarded
// verbatim.
function backendPath(request: NextRequest): string {
  const search = request.nextUrl.searchParams.toString();
  return `/api/v1/me/memory/file${search ? `?${search}` : ""}`;
}

// The backend's structured body carries the actionable message and error code
// (MEMORY_FILE_EXISTS vs MEMORY_VERSION_CONFLICT, an invalid file name);
// BackendApiError.message is only "Backend API error: <status>".
function errorResponse(error: unknown): NextResponse {
  if (error instanceof BackendApiError) {
    const body = error.data as { error?: { code?: string; message?: string } } | null;
    return NextResponse.json(
      { detail: body?.error?.message ?? error.message, code: body?.error?.code },
      { status: error.status },
    );
  }
  return NextResponse.json({ detail: "Internal server error" }, { status: 500 });
}

export async function GET(request: NextRequest) {
  const accessToken = request.cookies.get("access_token")?.value;
  if (!accessToken) {
    return NextResponse.json({ detail: "Not authenticated" }, { status: 401 });
  }
  try {
    const data = await backendFetch<unknown>(backendPath(request), {
      headers: { Authorization: `Bearer ${accessToken}` },
    });
    return NextResponse.json(data);
  } catch (error) {
    return errorResponse(error);
  }
}

export async function PUT(request: NextRequest) {
  const accessToken = request.cookies.get("access_token")?.value;
  if (!accessToken) {
    return NextResponse.json({ detail: "Not authenticated" }, { status: 401 });
  }
  let body: unknown;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ detail: "Invalid JSON body" }, { status: 400 });
  }
  try {
    const data = await backendFetch<unknown>(backendPath(request), {
      method: "PUT",
      body: JSON.stringify(body),
      headers: { Authorization: `Bearer ${accessToken}` },
    });
    return NextResponse.json(data);
  } catch (error) {
    return errorResponse(error);
  }
}

export async function DELETE(request: NextRequest) {
  const accessToken = request.cookies.get("access_token")?.value;
  if (!accessToken) {
    return NextResponse.json({ detail: "Not authenticated" }, { status: 401 });
  }
  try {
    await backendFetch<null>(backendPath(request), {
      method: "DELETE",
      headers: { Authorization: `Bearer ${accessToken}` },
    });
    return new NextResponse(null, { status: 204 });
  } catch (error) {
    return errorResponse(error);
  }
}
