/**
 * API response types.
 */

export interface ApiResponse<T> {
  data: T;
  message?: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

export interface HealthResponse {
  status: string;
  version?: string;
  database?: string;
}

export interface ErrorResponse {
  detail: string;
  status_code?: number;
}
