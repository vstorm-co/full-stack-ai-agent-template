import { NextRequest, NextResponse } from "next/server";

import { clearAuthCookies } from "@/lib/auth-cookies";
import { backendFetch, BackendApiError } from "@/lib/server-api";

export async function POST(request: NextRequest) {
  const refreshToken = request.cookies.get("refresh_token")?.value;

  if (refreshToken) {
    try {
      await backendFetch("/api/v1/auth/logout", {
        method: "POST",
        body: JSON.stringify({ refresh_token: refreshToken }),
      });
    } catch (error) {
      // Ignore — we still want to clear the client cookies even if the
      // server-side invalidation fails (e.g. token already expired).
      if (!(error instanceof BackendApiError)) {
        console.error("Logout backend call failed:", error);
      }
    }
  }

  const response = NextResponse.json({ message: "Logged out successfully" });

  clearAuthCookies(response);

  return response;
}
