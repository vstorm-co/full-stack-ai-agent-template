export type KBScope = "personal" | "org" | "app";

export interface KnowledgeBase {
  id: string;
  organization_id: string | null;
  owner_user_id: string | null;
  name: string;
  description: string | null;
  scope: KBScope;
  collection_name: string;
  is_default: boolean;
  created_at: string;
  updated_at: string | null;
}

export interface KnowledgeBaseList {
  items: KnowledgeBase[];
  total: number;
}

export interface CreateKnowledgeBaseInput {
  name: string;
  description?: string;
  scope: KBScope;
}

/** A single document tracked in a KB's underlying vector collection. */
export interface KBDocument {
  id: string;
  collection_name: string;
  filename: string;
  filetype: string | null;
  filesize: number | null;
  status: "pending" | "processing" | "completed" | "failed" | string;
  error_message: string | null;
  vector_document_id: string | null;
  chunk_count: number;
  has_file: boolean;
  created_at: string;
  completed_at: string | null;
}

export interface KBDocumentList {
  items: KBDocument[];
  total: number;
}
