import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000";

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ name: string }> },
) {
  try {
    const { name } = await params;
    const accessToken = request.cookies.get("access_token")?.value;
    const headers: Record<string, string> = {};
    if (accessToken) {
      headers["Authorization"] = `Bearer ${accessToken}`;
    }

    const formData = await request.formData();
    const replace = request.nextUrl.searchParams.get("replace") === "true";
    const url = `${BACKEND_URL}/api/v1/rag/collections/${name}/ingest${replace ? "?replace=true" : ""}`;

    const response = await fetch(url, {
      method: "POST",
      headers,
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: "Ingestion failed" }));
      return NextResponse.json(error, { status: response.status });
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch {
    return NextResponse.json({ detail: "Internal server error" }, { status: 500 });
  }
}
