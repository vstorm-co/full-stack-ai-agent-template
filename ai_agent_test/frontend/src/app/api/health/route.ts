import { NextResponse } from "next/server";
import { backendFetch, BackendApiError } from "@/lib/server-api";
import type { HealthResponse } from "@/types";

export async function GET() {
  try {
    const data = await backendFetch<HealthResponse>("/api/v1/health");
    return NextResponse.json(data);
  } catch (error) {
    if (error instanceof BackendApiError) {
      return NextResponse.json({ detail: "Backend service unavailable" }, { status: error.status });
    }
    return NextResponse.json({ detail: "Internal server error" }, { status: 500 });
  }
}
