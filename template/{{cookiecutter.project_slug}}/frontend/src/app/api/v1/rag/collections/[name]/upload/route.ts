{%- if cookiecutter.enable_rag and cookiecutter.use_frontend %}
{% raw %}import { NextRequest, NextResponse } from "next/server";
import { backendFetch, BackendApiError } from "@/lib/server-api";

interface RouteParams {
  params: Promise<{ name: string }>;
}

// POST /api/v1/rag/collections/:name/upload - Upload document to collection
export async function POST(request: NextRequest, { params }: RouteParams) {
  // Check if JWT auth is enabled via environment variable
  // (set NEXT_PUBLIC_AUTH_ENABLED=true to require auth, false or undefined to disable)
  const authEnabled = process.env.NEXT_PUBLIC_AUTH_ENABLED === "true";
  
  let accessToken: string | undefined;
  
  if (authEnabled) {
    accessToken = request.cookies.get("access_token")?.value;

    if (!accessToken) {
      return NextResponse.json({ detail: "Not authenticated" }, { status: 401 });
    }
  }

  try {
    const { name } = await params;

    // Get the file from the request
    const formData = await request.formData();
    const file = formData.get("file");

    if (!file) {
      return NextResponse.json({ detail: "No file provided" }, { status: 400 });
    }

    // Create a new FormData to forward to the backend
    const backendFormData = new FormData();
    backendFormData.append("file", file);

    // Only include Authorization header if we have a token
    const headers: Record<string, string> = {};
    if (accessToken) {
      headers["Authorization"] = `Bearer ${accessToken}`;
    }

    const data = await backendFetch(`/api/v1/rag/collections/${name}/upload`, {
      method: "POST",
      headers,
      // Don't set Content-Type, let the browser set it with the boundary
      body: backendFormData as unknown as BodyInit,
    });

    return NextResponse.json(data, { status: 202 });
  } catch (error) {
    if (error instanceof BackendApiError) {
      return NextResponse.json(
        { detail: error.message || "Failed to upload document" },
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
// RAG upload route - not configured (enable_rag is false or frontend is disabled)
{%- endif %}
