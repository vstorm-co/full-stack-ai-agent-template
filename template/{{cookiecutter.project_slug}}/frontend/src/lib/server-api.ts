/**
 * Server-side API client for calling the FastAPI backend.
 * This module is used by Next.js API routes to proxy requests.
 * IMPORTANT: This file should only be imported in server-side code (API routes, Server Components).
 */

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000";

export class BackendApiError extends Error {
  constructor(
    public status: number,
    public statusText: string,
    public data?: unknown
  ) {
    super(`Backend API error: ${status} ${statusText}`);
    this.name = "BackendApiError";
  }
}

interface RequestOptions extends RequestInit {
  params?: Record<string, string>;
}

/**
 * Make a request to the FastAPI backend.
 * This should only be called from Next.js API routes or Server Components.
 */
export async function backendFetch<T>(
  endpoint: string,
  options: RequestOptions = {}
): Promise<T> {
  const { params, body, ...fetchOptions } = options;

  let url = `${BACKEND_URL}${endpoint}`;

  if (params) {
    const searchParams = new URLSearchParams(params);
    url += `?${searchParams.toString()}`;
  }

  // Determine content type - don't set for FormData (browser will set with boundary)
  const headers: Record<string, string> = {};
  if (body instanceof FormData) {
    // Let the browser set Content-Type with the multipart boundary
  } else {
    headers["Content-Type"] = "application/json";
  }

  const response = await fetch(url, {
    ...fetchOptions,
    headers: {
      ...headers,
      ...fetchOptions.headers,
    },
    body,
  });

  if (!response.ok) {
    let errorData;
    try {
      errorData = await response.json();
    } catch {
      errorData = null;
    }
    throw new BackendApiError(response.status, response.statusText, errorData);
  }

  // Handle empty responses
  const text = await response.text();
  if (!text) {
    return null as T;
  }

  return JSON.parse(text);
}

/**
 * Forward authorization header from the incoming request to the backend.
 */
export function getAuthHeaders(
  authHeader: string | null
): Record<string, string> {
  if (!authHeader) {
    return {};
  }
  return { Authorization: authHeader };
}
