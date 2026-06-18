import { NextRequest, NextResponse } from "next/server";
import { backendFetch } from "@/lib/server-api";

/**
 * Verify the request comes from an authenticated admin user.
 *
 * Calls the backend /api/v1/auth/me endpoint to validate the token
 * and check the user's role. Returns an error response if the user
 * is not authenticated or not an admin.
 */
export async function requireAdmin(
  request: NextRequest,
): Promise<{ error: NextResponse } | { accessToken: string }> {
  const accessToken = request.cookies.get("access_token")?.value;

  if (!accessToken) {
    return {
      error: NextResponse.json({ detail: "Not authenticated" }, { status: 401 }),
    };
  }

  try {
    const user = await backendFetch<{ role: string }>("/api/v1/auth/me", {
      headers: { Authorization: `Bearer ${accessToken}` },
    });

    if (user.role !== "admin") {
      return {
        error: NextResponse.json({ detail: "Forbidden" }, { status: 403 }),
      };
    }

    return { accessToken };
  } catch {
    return {
      error: NextResponse.json({ detail: "Not authenticated" }, { status: 401 }),
    };
  }
}
