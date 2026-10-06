import { NextResponse, type NextRequest } from "next/server";

import { setAuthCookies } from "@/lib/auth-cookies";
import { BackendApiError, backendFetch } from "@/lib/server-api";

interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type?: string;
}

export async function POST(request: NextRequest) {
  try {
    const body = (await request.json()) as Record<string, unknown>;
    const data = await backendFetch<TokenResponse>("/api/v1/auth/magic-link/verify", {
      method: "POST",
      body: JSON.stringify(body),
    });

    const user = await backendFetch("/api/v1/auth/me", {
      headers: { Authorization: `Bearer ${data.access_token}` },
    });

    const response = NextResponse.json({
      user,
      access_token: data.access_token,
      message: "Sign-in successful",
    });

    setAuthCookies(response, {
      accessToken: data.access_token,
      refreshToken: data.refresh_token,
    });
    return response;
  } catch (error) {
    if (error instanceof BackendApiError) {
      return NextResponse.json({ detail: error.message }, { status: error.status });
    }
    return NextResponse.json({ detail: "Internal server error" }, { status: 500 });
  }
}
