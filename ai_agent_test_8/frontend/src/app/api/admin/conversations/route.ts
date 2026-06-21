import { NextRequest, NextResponse } from "next/server";
import { backendFetch, BackendApiError } from "@/lib/server-api";
import { requireAdmin } from "@/lib/admin-auth";

export async function GET(request: NextRequest) {
  try {
    const adminCheck = await requireAdmin(request);
    if ("error" in adminCheck) return adminCheck.error;
    const { accessToken } = adminCheck;

    // Forward query params to backend admin endpoint. Use /api/v1/admin/conversations
    // (admin_conversations router) — it returns AdminConversationList with user_email
    // and supports user_id filtering, unlike the legacy /api/v1/conversations/admin-list.
    const searchParams = request.nextUrl.searchParams;
    const params = new URLSearchParams();
    const forward = ["skip", "limit", "search", "user_id", "status", "sort_by", "sort_dir"];
    for (const key of forward) {
      const v = searchParams.get(key);
      if (v) params.set(key, v);
    }

    const qs = params.toString();
    const url = `/api/v1/admin/conversations${qs ? `?${qs}` : ""}`;

    const data = await backendFetch(url, {
      headers: {
        Authorization: `Bearer ${accessToken}`,
      },
    });

    return NextResponse.json(data);
  } catch (error) {
    if (error instanceof BackendApiError) {
      return NextResponse.json(
        { detail: error.message || "Failed to fetch conversations" },
        { status: error.status },
      );
    }
    return NextResponse.json({ detail: "Internal server error" }, { status: 500 });
  }
}
