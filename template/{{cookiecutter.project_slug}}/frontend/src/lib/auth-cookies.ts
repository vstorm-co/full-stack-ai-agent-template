/**
 * Auth cookie handling shared by every `/api/auth/*` route handler.
 *
 * The browser silently discards a `Secure` cookie sent from an insecure origin.
 * A deployment served over plain HTTP — a LAN IP, a bare Docker host, a tunnel
 * without TLS — therefore accepts the login response and then sends no cookie
 * back on any request after it, so `/api/auth/me` answers 401 forever, the
 * access token is never refreshed and the chat socket never authenticates.
 *
 * `COOKIE_SECURE` makes that flag explicit: unset follows `NODE_ENV`, `false`
 * opts a trusted-network HTTP deployment out, `true` forces it on (e.g. a dev
 * server behind an HTTPS proxy). Anything else falls back to the `NODE_ENV`
 * default rather than guessing, so a typo cannot downgrade production.
 */
import type { NextResponse } from "next/server";

export const ACCESS_TOKEN_MAX_AGE = 60 * 15; // 15 minutes
export const REFRESH_TOKEN_MAX_AGE = 60 * 60 * 24 * 7; // 7 days

/** Exported for the unit test — the module-level value is read once at startup. */
export function resolveCookieSecure(env: { COOKIE_SECURE?: string; NODE_ENV?: string }): boolean {
  switch (env.COOKIE_SECURE?.toLowerCase()) {
    case "false":
      return false;
    case "true":
      return true;
    default:
      return env.NODE_ENV === "production";
  }
}

const COOKIE_SECURE = resolveCookieSecure(process.env);

const cookieOptions = (maxAge: number) =>
  ({
    httpOnly: true,
    secure: COOKIE_SECURE,
    sameSite: "lax",
    maxAge,
    path: "/",
  }) as const;

interface AuthTokens {
  accessToken: string;
  /** Only set when the backend issued (or rotated) one. */
  refreshToken?: string;
}

/** Store the session tokens as httpOnly cookies on an outgoing response. */
export function setAuthCookies(response: NextResponse, { accessToken, refreshToken }: AuthTokens) {
  response.cookies.set("access_token", accessToken, cookieOptions(ACCESS_TOKEN_MAX_AGE));
  if (refreshToken) {
    response.cookies.set("refresh_token", refreshToken, cookieOptions(REFRESH_TOKEN_MAX_AGE));
  }
}

/** Expire both session cookies — logout, or a refresh token the backend rejected. */
export function clearAuthCookies(response: NextResponse) {
  response.cookies.set("access_token", "", cookieOptions(0));
  response.cookies.set("refresh_token", "", cookieOptions(0));
}
