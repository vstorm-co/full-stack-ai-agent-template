{%- if cookiecutter.enable_ai_agent and cookiecutter.enable_conversation_persistence and cookiecutter.use_jwt %}
import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:{{ cookiecutter.backend_port }}";

export async function POST(request: NextRequest) {
  try {
    const accessToken = request.cookies.get("access_token")?.value;
    if (!accessToken) {
      return NextResponse.json({ detail: "Not authenticated" }, { status: 401 });
    }

    const formData = await request.formData();

    const response = await fetch(`${BACKEND_URL}/api/v1/files/upload`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${accessToken}`,
      },
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: "Upload failed" }));
      return NextResponse.json(error, { status: response.status });
    }

    const data = await response.json();
    return NextResponse.json(data, { status: 201 });
  } catch {
    return NextResponse.json({ detail: "Internal server error" }, { status: 500 });
  }
}
{%- else %}
// File upload not available (requires AI agent + conversation persistence + JWT)
export async function POST() {
  return new Response("Not implemented", { status: 501 });
}
{%- endif %}
