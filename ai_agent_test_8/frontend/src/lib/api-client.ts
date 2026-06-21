/**
 * Client-side API client.
 * All requests go through Next.js API routes (/api/*), never directly to the backend.
 * This keeps the backend URL hidden from the browser.
 */

import { useAuthStore } from "@/stores";

export class ApiError extends Error {
  constructor(
    public status: number,
    public message: string,
    public data?: unknown,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

interface RequestOptions extends Omit<RequestInit, "body"> {
  params?: Record<string, string>;
  body?: unknown;
}

// The proxy route that mints a fresh access token from the refresh cookie.
const REFRESH_ENDPOINT = "/auth/refresh";

// Shared in-flight refresh promise so a burst of concurrent 401s triggers only
// ONE refresh round-trip. Reset once the refresh settles.
let refreshPromise: Promise<boolean> | null = null;

/**
 * Attempt a single token refresh, de-duplicating concurrent callers.
 * Resolves true on success (cookies + in-memory access token updated), false
 * if the refresh itself failed (caller should surface the original 401).
 */
function refreshAccessToken(): Promise<boolean> {
  if (!refreshPromise) {
    refreshPromise = fetch(`/api${REFRESH_ENDPOINT}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
    })
      .then(async (res) => {
        if (!res.ok) return false;
        try {
          const data = (await res.json()) as { access_token?: string };
          if (data?.access_token) {
            // Keep the in-memory token (used for WS auth) in sync.
            useAuthStore.getState().setAccessToken(data.access_token);
          }
        } catch {
          // Body wasn't JSON — cookies were still rotated, treat as success.
        }
        return true;
      })
      .catch(() => false)
      .finally(() => {
        refreshPromise = null;
      });
  }
  return refreshPromise;
}

class ApiClient {
  private async request<T>(endpoint: string, options: RequestOptions = {}): Promise<T> {
    const { params, body, ...fetchOptions } = options;

    let url = `/api${endpoint}`;

    if (params) {
      const searchParams = new URLSearchParams(params);
      url += `?${searchParams.toString()}`;
    }

    const doFetch = () =>
      fetch(url, {
        ...fetchOptions,
        headers: {
          "Content-Type": "application/json",
          ...fetchOptions.headers,
        },
        body: body ? JSON.stringify(body) : undefined,
      });

    let response = await doFetch();

    // Transparent 401 recovery: refresh once, then retry the request once.
    // Never recurse into the refresh endpoint itself (would loop), and only
    // attempt this a single time per call.
    if (response.status === 401 && endpoint !== REFRESH_ENDPOINT) {
      const refreshed = await refreshAccessToken();
      if (refreshed) {
        response = await doFetch();
      }
    }

    if (!response.ok) {
      let errorData;
      try {
        errorData = await response.json();
      } catch {
        errorData = null;
      }
      throw new ApiError(
        response.status,
        errorData?.detail || errorData?.message || "Request failed",
        errorData,
      );
    }

    // Handle empty responses
    const text = await response.text();
    if (!text) {
      return null as T;
    }

    return JSON.parse(text);
  }

  get<T>(endpoint: string, options?: RequestOptions) {
    return this.request<T>(endpoint, { ...options, method: "GET" });
  }

  post<T>(endpoint: string, body?: unknown, options?: RequestOptions) {
    return this.request<T>(endpoint, { ...options, method: "POST", body });
  }

  put<T>(endpoint: string, body?: unknown, options?: RequestOptions) {
    return this.request<T>(endpoint, { ...options, method: "PUT", body });
  }

  patch<T>(endpoint: string, body?: unknown, options?: RequestOptions) {
    return this.request<T>(endpoint, { ...options, method: "PATCH", body });
  }

  delete<T>(endpoint: string, options?: RequestOptions) {
    return this.request<T>(endpoint, { ...options, method: "DELETE" });
  }
}

export const apiClient = new ApiClient();
