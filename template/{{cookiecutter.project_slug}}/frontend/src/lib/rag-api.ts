/**
 * RAG (Retrieval Augmented Generation) API client.
 */

import { apiClient, ApiError } from "./api-client";

export const RAG_API_ROUTES = {
  COLLECTIONS: "/v1/rag/collections",
  COLLECTIONS_INFO: (name: string) => `/v1/rag/collections/${name}/info`,
  COLLECTIONS_CREATE: (name: string) => `/v1/rag/collections/${name}`,
  COLLECTIONS_DELETE: (name: string) => `/v1/rag/collections/${name}`,
  COLLECTIONS_DOCUMENTS: (name: string) => `/v1/rag/collections/${name}/documents`,
  COLLECTIONS_DOCUMENT_DELETE: (name: string, documentId: string) =>
    `/v1/rag/collections/${name}/documents/${documentId}`,
  COLLECTIONS_INGEST: (name: string) => `/v1/rag/collections/${name}/ingest`,
  SEARCH: "/v1/rag/search",
} as const;

export interface RAGCollectionList {
  items: string[];
}

export interface RAGCollectionInfo {
  name: string;
  total_vectors: number;
  dim: number;
  indexing_status: string;
}

export interface RAGSearchRequest {
  query: string;
  collection_name?: string;
  collection_names?: string[];
  limit?: number;
  min_score?: number;
  filter?: string;
}

export interface RAGSearchResult {
  content: string;
  metadata: Record<string, unknown>;
  score: number;
  parent_doc_id: string;
}

export interface RAGSearchResponse {
  results: RAGSearchResult[];
}

export const isRagEnabled = (): boolean => {
  return process.env.NEXT_PUBLIC_RAG_ENABLED === "true";
};

export async function listCollections(): Promise<RAGCollectionList> {
  return apiClient.get<RAGCollectionList>(RAG_API_ROUTES.COLLECTIONS);
}

export async function getCollectionInfo(collectionName: string): Promise<RAGCollectionInfo> {
  return apiClient.get<RAGCollectionInfo>(RAG_API_ROUTES.COLLECTIONS_INFO(collectionName));
}

export async function createCollection(collectionName: string): Promise<{ message: string }> {
  return apiClient.post<{ message: string }>(RAG_API_ROUTES.COLLECTIONS_CREATE(collectionName));
}

export async function deleteCollection(collectionName: string): Promise<void> {
  return apiClient.delete(RAG_API_ROUTES.COLLECTIONS_DELETE(collectionName));
}

export async function deleteDocument(collectionName: string, documentId: string): Promise<void> {
  return apiClient.delete(RAG_API_ROUTES.COLLECTIONS_DOCUMENT_DELETE(collectionName, documentId));
}

export async function searchDocuments(request: RAGSearchRequest): Promise<RAGSearchResponse> {
  return apiClient.post<RAGSearchResponse>(RAG_API_ROUTES.SEARCH, request);
}

export interface RAGDocumentItem {
  document_id: string;
  filename: string;
  filesize: number;
  filetype: string;
  chunk_count: number;
  additional_info?: Record<string, unknown>;
}

export interface RAGDocumentList {
  items: RAGDocumentItem[];
  total: number;
}

export interface RAGIngestResult {
  id: string;
  status: string;
  document_id: string | null;
  filename: string;
  collection: string;
  message: string;
}

export interface RAGTrackedDocument {
  id: string;
  collection_name: string;
  filename: string;
  filesize: number;
  filetype: string;
  status: "processing" | "done" | "error";
  error_message: string | null;
  vector_document_id: string | null;
  chunk_count: number;
  has_file: boolean;
  created_at: string | null;
  completed_at: string | null;
}

export function getDocumentDownloadUrl(docId: string): string {
  return `/api/v1/rag/documents/${docId}/download`;
}

export async function downloadKBDocument(
  kbId: string,
  doc: { id: string; filename: string },
  mode: "download" | "view" = "download",
): Promise<void> {
  const res = await fetch(`/api/kb/${kbId}/documents/${doc.id}/download`);
  if (!res.ok) throw new Error(`Download failed: ${res.status}`);
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  if (mode === "view") {
    window.open(url, "_blank", "noopener,noreferrer");
    setTimeout(() => URL.revokeObjectURL(url), 60_000);
  } else {
    const a = document.createElement("a");
    a.href = url;
    a.download = doc.filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }
}

export interface RAGTrackedDocumentList {
  items: RAGTrackedDocument[];
  total: number;
}

export async function listTrackedDocuments(
  collectionName?: string,
): Promise<RAGTrackedDocumentList> {
  const params = collectionName ? `?collection_name=${encodeURIComponent(collectionName)}` : "";
  return apiClient.get<RAGTrackedDocumentList>(`/v1/rag/documents${params}`);
}

export async function deleteTrackedDocument(docId: string): Promise<void> {
  return apiClient.delete(`/v1/rag/documents/${docId}`);
}

export async function listDocuments(collectionName: string): Promise<RAGDocumentList> {
  return apiClient.get<RAGDocumentList>(RAG_API_ROUTES.COLLECTIONS_DOCUMENTS(collectionName));
}

export async function ingestFile(
  collectionName: string,
  file: File,
  replace = false,
): Promise<RAGIngestResult> {
  const formData = new FormData();
  formData.append("file", file);

  const url = `/api${RAG_API_ROUTES.COLLECTIONS_INGEST(collectionName)}${replace ? "?replace=true" : ""}`;
  const response = await fetch(url, {
    method: "POST",
    body: formData,
    credentials: "include",
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Upload failed" }));
    throw new ApiError(response.status, error.detail || "Ingestion failed", error);
  }

  return response.json();
}

export interface SyncSourceCreate {
  name: string;
  connector_type: string;
  /** Omit to create an org-level integration not yet assigned to a KB. */
  collection_name?: string | null;
  config: Record<string, unknown>;
  sync_mode?: string;
  schedule_minutes?: number | null;
}

export interface SyncSourceClone {
  collection_name: string;
  name?: string;
}

export interface SyncSourceRead {
  id: string;
  organization_id: string | null;
  name: string;
  connector_type: string;
  /** null = org-level integration, not yet assigned to a KB */
  collection_name: string | null;
  config: Record<string, unknown>;
  sync_mode: string;
  schedule_minutes: number | null;
  is_active: boolean;
  last_sync_at: string | null;
  last_sync_status: string | null;
  last_error: string | null;
  created_at: string | null;
}

export interface SyncSourceList {
  items: SyncSourceRead[];
  total: number;
}

export interface ConnectorConfigField {
  type: string;
  required: boolean;
  label: string;
  help?: string;
  default?: unknown;
  secret?: boolean;
}

export interface ConnectorInfo {
  type: string;
  name: string;
  config_schema: Record<string, ConnectorConfigField>;
  enabled: boolean;
}

export interface ConnectorList {
  items: ConnectorInfo[];
}

export interface RAGSyncLog {
  id: string;
  source: string;
  collection_name: string;
  status: string;
  mode: string;
  total_files: number;
  ingested: number;
  updated: number;
  skipped: number;
  failed: number;
  error_message: string | null;
  started_at: string | null;
  completed_at: string | null;
}

export interface RAGSyncLogList {
  items: RAGSyncLog[];
  total: number;
}

export async function listSyncLogs(collectionName?: string, limit = 20): Promise<RAGSyncLogList> {
  const params = new URLSearchParams();
  if (collectionName) params.set("collection_name", collectionName);
  params.set("limit", String(limit));
  return apiClient.get<RAGSyncLogList>(`/v1/rag/sync/logs?${params}`);
}

/** Fetch logs for a specific sync source under a KB. */
export async function listKBSyncSourceLogs(
  kbId: string,
  sourceId: string,
  limit = 20,
): Promise<RAGSyncLogList> {
  return apiClient.get<RAGSyncLogList>(`/kb/${kbId}/sync-sources/${sourceId}/logs?limit=${limit}`);
}

/** Fetch logs for a specific org integration. */
export async function listOrgIntegrationLogs(
  orgId: string,
  sourceId: string,
  limit = 20,
): Promise<RAGSyncLogList> {
  return apiClient.get<RAGSyncLogList>(
    `/orgs/${orgId}/integrations/${sourceId}/logs?limit=${limit}`,
  );
}

export async function triggerSync(
  collectionName: string,
  mode: string,
  path: string,
): Promise<{ id: string; status: string; message: string }> {
  return apiClient.post("/v1/rag/sync/local", { collection_name: collectionName, mode, path });
}

export async function cancelSync(syncId: string): Promise<{ message: string }> {
  return apiClient.delete(`/v1/rag/sync/${syncId}`);
}

export async function listSyncSources(collectionName?: string): Promise<SyncSourceList> {
  const params = collectionName ? `?collection_name=${encodeURIComponent(collectionName)}` : "";
  return apiClient.get<SyncSourceList>(`/v1/rag/sync/sources${params}`);
}

export async function createSyncSource(data: SyncSourceCreate): Promise<SyncSourceRead> {
  return apiClient.post<SyncSourceRead>("/v1/rag/sync/sources", data);
}

export async function cloneSyncSource(
  sourceId: string,
  data: SyncSourceClone,
): Promise<SyncSourceRead> {
  return apiClient.post<SyncSourceRead>(`/v1/rag/sync/sources/${sourceId}/clone`, data);
}

export async function updateSyncSource(
  sourceId: string,
  data: Partial<SyncSourceCreate>,
): Promise<SyncSourceRead> {
  return apiClient.patch<SyncSourceRead>(`/v1/rag/sync/sources/${sourceId}`, data);
}

export async function deleteSyncSource(sourceId: string): Promise<void> {
  return apiClient.delete(`/v1/rag/sync/sources/${sourceId}`);
}

export async function triggerSyncSource(
  sourceId: string,
): Promise<{ id: string; status: string; message: string }> {
  return apiClient.post(`/v1/rag/sync/sources/${sourceId}/trigger`);
}

export async function listConnectors(): Promise<ConnectorList> {
  return apiClient.get<ConnectorList>("/v1/rag/sync/connectors");
}
