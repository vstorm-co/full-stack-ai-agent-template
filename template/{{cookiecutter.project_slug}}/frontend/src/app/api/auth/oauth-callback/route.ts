import { NextRequest, NextResponse } from "next/server";

import { setAuthCookies } from "@/lib/auth-cookies";
import { backendFetch, BackendApiError } from "@/lib/server-api";

interface OAuthCallbackBody {
  access_token: string;
  refresh_token: string;
}

export async function POST(request: NextRequest) {
  try {
    const body = (await request.json()) as Partial<OAuthCallbackBody>;
    if (!body.access_token || !body.refresh_token) {
      return NextResponse.json({ detail: "Missing tokens" }, { status: 400 });
    }

    const user = await backendFetch("/api/v1/auth/me", {
      headers: { Authorization: `Bearer ${body.access_token}` },
    });

    const response = NextResponse.json({
      user,
      access_token: body.access_token,
      message: "Sign-in successful",
    });

    setAuthCookies(response, {
      accessToken: body.access_token,
      refreshToken: body.refresh_token,
    });
    return response;
  } catch (error) {
    if (error instanceof BackendApiError) {
      const detail = (error.data as { detail?: string })?.detail || "Sign-in failed";
      return NextResponse.json({ detail }, { status: error.status });
    }
    return NextResponse.json({ detail: "Internal server error" }, { status: 500 });
  }
}
