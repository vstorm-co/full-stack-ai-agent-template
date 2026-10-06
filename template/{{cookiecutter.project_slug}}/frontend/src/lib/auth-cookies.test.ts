import { describe, it, expect } from "vitest";
import { NextResponse } from "next/server";
import {
  ACCESS_TOKEN_MAX_AGE,
  REFRESH_TOKEN_MAX_AGE,
  clearAuthCookies,
  resolveCookieSecure,
  setAuthCookies,
} from "./auth-cookies";

describe("resolveCookieSecure", () => {
  it("follows NODE_ENV when COOKIE_SECURE is unset", () => {
    expect(resolveCookieSecure({ NODE_ENV: "production" })).toBe(true);
    expect(resolveCookieSecure({ NODE_ENV: "development" })).toBe(false);
    expect(resolveCookieSecure({})).toBe(false);
  });

  it("lets COOKIE_SECURE override NODE_ENV in both directions", () => {
    // The whole point of the flag: a production build served over plain HTTP
    // has to be able to turn Secure off, or the browser drops the cookie.
    expect(resolveCookieSecure({ COOKIE_SECURE: "false", NODE_ENV: "production" })).toBe(false);
    expect(resolveCookieSecure({ COOKIE_SECURE: "true", NODE_ENV: "development" })).toBe(true);
    expect(resolveCookieSecure({ COOKIE_SECURE: "FALSE", NODE_ENV: "production" })).toBe(false);
  });

  it("ignores a value it does not understand instead of guessing", () => {
    // A typo must not silently downgrade production to insecure cookies.
    expect(resolveCookieSecure({ COOKIE_SECURE: "0", NODE_ENV: "production" })).toBe(true);
    expect(resolveCookieSecure({ COOKIE_SECURE: "", NODE_ENV: "production" })).toBe(true);
    expect(resolveCookieSecure({ COOKIE_SECURE: "yes", NODE_ENV: "development" })).toBe(false);
  });
});

describe("setAuthCookies", () => {
  it("stores both tokens httpOnly, scoped to the whole site", () => {
    const response = NextResponse.json({});
    setAuthCookies(response, { accessToken: "access", refreshToken: "refresh" });

    const access = response.cookies.get("access_token");
    expect(access?.value).toBe("access");
    expect(access?.httpOnly).toBe(true);
    expect(access?.sameSite).toBe("lax");
    expect(access?.path).toBe("/");
    expect(access?.maxAge).toBe(ACCESS_TOKEN_MAX_AGE);

    const refresh = response.cookies.get("refresh_token");
    expect(refresh?.value).toBe("refresh");
    expect(refresh?.maxAge).toBe(REFRESH_TOKEN_MAX_AGE);
  });

  it("leaves the refresh cookie alone when the backend did not rotate it", () => {
    const response = NextResponse.json({});
    setAuthCookies(response, { accessToken: "access" });

    expect(response.cookies.get("access_token")?.value).toBe("access");
    expect(response.cookies.get("refresh_token")).toBeUndefined();
  });
});

describe("clearAuthCookies", () => {
  it("expires both cookies", () => {
    const response = NextResponse.json({});
    clearAuthCookies(response);

    expect(response.cookies.get("access_token")?.maxAge).toBe(0);
    expect(response.cookies.get("refresh_token")?.maxAge).toBe(0);
  });
});
