/**
 * File upload API client for chat attachments.
 */

import { ApiError } from "./api-client";

export interface FileUploadResponse {
  id: string;
  filename: string;
  mime_type: string;
  size: number;
  file_type: string;
}

export async function uploadFile(file: File): Promise<FileUploadResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch("/api/files/upload", {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Upload failed" }));
    throw new ApiError(response.status, error.detail || "Upload failed", error);
  }

  return response.json();
}

export function getFileUrl(fileId: string): string {
  return `/api/files/${fileId}`;
}
