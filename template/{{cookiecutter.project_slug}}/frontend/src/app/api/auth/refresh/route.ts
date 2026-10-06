import { NextRequest, NextResponse } from "next/server";
import { clearAuthCookies, setAuthCookies } from "@/lib/auth-cookies";
import { backendFetch, BackendApiError } from "@/lib/server-api";
import type { RefreshTokenResponse } from "@/types";

export async function POST(request: NextRequest) {
  try {
    const refreshToken = request.cookies.get("refresh_token")?.value;

    if (!refreshToken) {
      return NextResponse.json({ detail: "No refresh token" }, { status: 401 });
    }

    const data = await backendFetch<RefreshTokenResponse>("/api/v1/auth/refresh", {
      method: "POST",
      body: JSON.stringify({ refresh_token: refreshToken }),
    });

    const response = NextResponse.json({
      access_token: data.access_token,
      message: "Token refreshed",
    });

    // The refresh token is only re-set when the backend rotated it.
    setAuthCookies(response, {
      accessToken: data.access_token,
      refreshToken: data.refresh_token,
    });

    return response;
  } catch (error) {
    if (error instanceof BackendApiError) {
      const response = NextResponse.json({ detail: "Session expired" }, { status: 401 });

      clearAuthCookies(response);

      return response;
    }
    return NextResponse.json({ detail: "Internal server error" }, { status: 500 });
  }
}
