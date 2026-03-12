{%- if cookiecutter.enable_conversation_persistence and cookiecutter.use_database %}
{% raw %}import { NextRequest, NextResponse } from "next/server";
import { backendFetch, BackendApiError } from "@/lib/server-api";

interface RouteParams {
  params: Promise<{ id: string }>;
}

export async function GET(request: NextRequest, { params }: RouteParams) {
  try {
    const accessToken = request.cookies.get("access_token")?.value;

    if (!accessToken) {
      return NextResponse.json({ detail: "Not authenticated" }, { status: 401 });
    }

    const { id } = await params;

    const data = await backendFetch(`/api/v1/conversations/${id}/messages`, {
      headers: {
        Authorization: `Bearer ${accessToken}`,
      },
    });

    return NextResponse.json(data);
  } catch (error) {
    if (error instanceof BackendApiError) {
      return NextResponse.json(
        { detail: error.message || "Failed to fetch messages" },
        { status: error.status }
      );
    }
    return NextResponse.json(
      { detail: "Internal server error" },
      { status: 500 }
    );
  }
}{% endraw %}
{%- else %}
// Conversation detail API route - not configured (enable_conversation_persistence is false)
export {};
{%- endif %}
