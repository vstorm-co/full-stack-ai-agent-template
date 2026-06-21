import { NextRequest, NextResponse } from "next/server";
import { backendFetch, BackendApiError } from "@/lib/server-api";
import type { User } from "@/types";

const ACCESS_MAXAGE = 60 * 15; // 15 min
const REFRESH_MAXAGE = 60 * 60 * 24 * 7; // 7 days

const cookieOpts = (maxAge: number) =>
  ({
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax" as const,
    maxAge,
    path: "/",
  }) as const;

function fetchMe(token: string) {
  return backendFetch<User>("/api/v1/auth/me", {
    headers: { Authorization: `Bearer ${token}` },
  });
}

/**
 * Returns the current user AND echoes the access token so the client can use it
 * for WebSocket auth (Sec-WebSocket-Protocol). The access cookie is short-lived
 * (15 min); when it has expired we transparently refresh it using the 7-day
 * refresh cookie so the session — and the chat socket — stay alive across
 * reloads without forcing a re-login.
 */
export async function GET(request: NextRequest) {
  const accessToken = request.cookies.get("access_token")?.value;
  const refreshToken = request.cookies.get("refresh_token")?.value;

  if (accessToken) {
    try {
      const data = await fetchMe(accessToken);
      return NextResponse.json({ ...data, access_token: accessToken });
    } catch (error) {
      if (!(error instanceof BackendApiError) || error.status !== 401) {
        const status = error instanceof BackendApiError ? error.status : 500;
        return NextResponse.json({ detail: "Failed to get user" }, { status });
      }
      // 401 → fall through and try to refresh.
    }
  }

  if (!refreshToken) {
    return NextResponse.json({ detail: "Not authenticated" }, { status: 401 });
  }

  try {
    const refreshed = await backendFetch<{ access_token: string; refresh_token?: string }>(
      "/api/v1/auth/refresh",
      { method: "POST", body: JSON.stringify({ refresh_token: refreshToken }) },
    );
    const data = await fetchMe(refreshed.access_token);
    const response = NextResponse.json({ ...data, access_token: refreshed.access_token });
    response.cookies.set("access_token", refreshed.access_token, cookieOpts(ACCESS_MAXAGE));
    if (refreshed.refresh_token) {
      response.cookies.set("refresh_token", refreshed.refresh_token, cookieOpts(REFRESH_MAXAGE));
    }
    return response;
  } catch {
    // Refresh failed → truly logged out. Clear cookies.
    const response = NextResponse.json({ detail: "Not authenticated" }, { status: 401 });
    response.cookies.set("access_token", "", cookieOpts(0));
    response.cookies.set("refresh_token", "", cookieOpts(0));
    return response;
  }
}
