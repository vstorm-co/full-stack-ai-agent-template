import { NextResponse, type NextRequest } from "next/server";

import { BackendApiError, backendFetch } from "@/lib/server-api";

interface RouteParams {
  params: Promise<{ id: string }>;
}

export async function GET(request: NextRequest, { params }: RouteParams) {
  const accessToken = request.cookies.get("access_token")?.value;
  if (!accessToken) return NextResponse.json({ detail: "Not authenticated" }, { status: 401 });
  const { id } = await params;
  try {
    const data = await backendFetch("/api/v1/org/integrations/connectors", {
      headers: {
        Authorization: `Bearer ${accessToken}`,
        "X-Organization-Id": id,
      },
    });
    return NextResponse.json(data);
  } catch (error) {
    if (error instanceof BackendApiError)
      return NextResponse.json({ detail: error.message }, { status: error.status });
    return NextResponse.json({ detail: "Internal server error" }, { status: 500 });
  }
}
