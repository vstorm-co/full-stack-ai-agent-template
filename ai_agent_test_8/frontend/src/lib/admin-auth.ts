import { NextRequest, NextResponse } from "next/server";
import { backendFetch } from "@/lib/server-api";
import { isAppAdmin } from "@/lib/utils";

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

    if (!isAppAdmin(user)) {
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
