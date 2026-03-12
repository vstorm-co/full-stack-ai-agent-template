{%- if cookiecutter.enable_rag and cookiecutter.use_frontend %}
{% raw %}import { NextRequest, NextResponse } from "next/server";
import { backendFetch, BackendApiError } from "@/lib/server-api";

interface RouteParams {
  params: Promise<{ name: string }>;
}

// GET /api/v1/rag/collections/:name/info - Get collection info
export async function GET(request: NextRequest, { params }: RouteParams) {
  try {
    const accessToken = request.cookies.get("access_token")?.value;

    if (!accessToken) {
      return NextResponse.json({ detail: "Not authenticated" }, { status: 401 });
    }

    const { name } = await params;

    const data = await backendFetch(`/api/v1/rag/collections/${name}/info`, {
      headers: {
        Authorization: `Bearer ${accessToken}`,
      },
    });

    return NextResponse.json(data);
  } catch (error) {
    if (error instanceof BackendApiError) {
      return NextResponse.json(
        { detail: error.message || "Failed to fetch collection info" },
        { status: error.status }
      );
    }
    return NextResponse.json(
      { detail: "Internal server error" },
      { status: 500 }
    );
  }
}

// DELETE /api/v1/rag/collections/:name - Delete collection
export async function DELETE(request: NextRequest, { params }: RouteParams) {
  try {
    const accessToken = request.cookies.get("access_token")?.value;

    if (!accessToken) {
      return NextResponse.json({ detail: "Not authenticated" }, { status: 401 });
    }

    const { name } = await params;

    await backendFetch(`/api/v1/rag/collections/${name}`, {
      method: "DELETE",
      headers: {
        Authorization: `Bearer ${accessToken}`,
      },
    });

    return new NextResponse(null, { status: 204 });
  } catch (error) {
    if (error instanceof BackendApiError) {
      return NextResponse.json(
        { detail: error.message || "Failed to delete collection" },
        { status: error.status }
      );
    }
    return NextResponse.json(
      { detail: "Internal server error" },
      { status: 500 }
    );
  }
}
{% endraw %}
{%- else %}
// RAG collection info route - not configured (enable_rag is false or frontend is disabled)
{%- endif %}
