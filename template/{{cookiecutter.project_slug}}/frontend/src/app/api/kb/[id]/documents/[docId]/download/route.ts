{% raw %}import { NextResponse, type NextRequest } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000";

interface RouteParams {
  params: Promise<{ id: string; docId: string }>;
}

export async function GET(request: NextRequest, { params }: RouteParams) {
  const accessToken = request.cookies.get("access_token")?.value;
  if (!accessToken) {
    return NextResponse.json({ detail: "Not authenticated" }, { status: 401 });
  }
  const { id, docId } = await params;
  try {
    const response = await fetch(
      `${BACKEND_URL}/api/v1/kb/${id}/documents/${docId}/download`,
      { headers: { Authorization: `Bearer ${accessToken}` } },
    );
    if (!response.ok) {
      return NextResponse.json({ detail: "File not found" }, { status: response.status });
    }
    const data = await response.arrayBuffer();
    const contentType = response.headers.get("content-type") || "application/octet-stream";
    const disposition = response.headers.get("content-disposition") || "";
    return new NextResponse(data, {
      headers: {
        "Content-Type": contentType,
        "Content-Disposition": disposition,
        "Cache-Control": "private, max-age=3600",
      },
    });
  } catch {
    return NextResponse.json({ detail: "Internal server error" }, { status: 500 });
  }
}
{% endraw %}
