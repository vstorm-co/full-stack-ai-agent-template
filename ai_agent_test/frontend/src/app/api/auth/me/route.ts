import { NextRequest, NextResponse } from "next/server";
import { backendFetch, BackendApiError } from "@/lib/server-api";
import type { User } from "@/types";

export async function GET(request: NextRequest) {
  try {
    const accessToken = request.cookies.get("access_token")?.value;

    if (!accessToken) {
      return NextResponse.json({ detail: "Not authenticated" }, { status: 401 });
    }

    const data = await backendFetch<User>("/api/v1/auth/me", {
      headers: {
        Authorization: `Bearer ${accessToken}`,
      },
    });

    // Return the access token alongside user data so the client can use it
    // for WebSocket auth via Sec-WebSocket-Protocol. Security tradeoff: this
    // exposes the httpOnly cookie to JS, same as the cross-origin WS needs.
    return NextResponse.json({ ...data, access_token: accessToken });
  } catch (error) {
    if (error instanceof BackendApiError) {
      if (error.status === 401) {
        // Token expired, try to refresh
        return NextResponse.json({ detail: "Token expired" }, { status: 401 });
      }
      return NextResponse.json({ detail: "Failed to get user" }, { status: error.status });
    }
    return NextResponse.json({ detail: "Internal server error" }, { status: 500 });
  }
}
