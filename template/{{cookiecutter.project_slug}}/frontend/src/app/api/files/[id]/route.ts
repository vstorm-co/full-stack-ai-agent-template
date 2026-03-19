{%- if cookiecutter.enable_ai_agent and cookiecutter.enable_conversation_persistence and cookiecutter.use_jwt %}
import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:{{ cookiecutter.backend_port }}";

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;
    const accessToken = request.cookies.get("access_token")?.value;
    if (!accessToken) {
      return NextResponse.json({ detail: "Not authenticated" }, { status: 401 });
    }

    const response = await fetch(`${BACKEND_URL}/api/v1/files/${id}`, {
      headers: {
        Authorization: `Bearer ${accessToken}`,
      },
    });

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
{%- else %}
// File download not available
export async function GET() {
  return new Response("Not implemented", { status: 501 });
}
{%- endif %}
