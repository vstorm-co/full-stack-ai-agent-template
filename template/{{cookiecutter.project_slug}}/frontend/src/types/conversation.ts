import { RatingValue, type ChatMessageFile, type UserRating } from "./chat";

export interface Conversation {
  id: string;
  user_id?: string;
  title?: string;
  created_at: string;
  updated_at: string;
  is_archived: boolean;
  is_demo: boolean;
  active_knowledge_base_ids?: string[];
}

export interface ConversationMessage {
  id: string;
  conversation_id: string;
  role: "user" | "assistant" | "system";
  content: string;
  created_at: string;
  model_name?: string;
  tokens_used?: number;
  tool_calls?: ConversationToolCall[];
  files?: ChatMessageFile[];
  user_rating?: UserRating;
  rating_count?: { likes: number; dislikes: number } | null;
}

export interface ConversationToolCall {
  id: string;
  message_id: string;
  tool_call_id: string;
  tool_name: string;
  args: Record<string, unknown>;
  result?: string;
  status: "pending" | "running" | "completed" | "failed";
  started_at: string;
  completed_at?: string;
  duration_ms?: number;
}

export interface ConversationListResponse {
  items: Conversation[];
  total: number;
}

export interface ConversationWithMessages extends Conversation {
  messages: ConversationMessage[];
}
/**
 * Message rating types.
 */

export interface MessageRating {
  id: string;
  message_id: string;
  user_id: string;
  rating: RatingValue;
  comment: string | null;
  created_at: string;
  updated_at: string;
}

export interface MessageRatingWithDetails extends MessageRating {
  message_content: string | null;
  message_role: string | null;
  conversation_id: string | null;
  user_email: string | null;
  user_name: string | null;
}

export interface MessageRatingListResponse {
  items: MessageRatingWithDetails[];
  total: number;
}

export interface RatingSummary {
  total_ratings: number;
  like_count: number;
  dislike_count: number;
  average_rating: number;
  with_comments: number;
  ratings_by_day: Array<{ date: string; likes: number; dislikes: number }>;
}

export interface ConversationShare {
  id: string;
  conversation_id: string;
  shared_by: string;
  shared_with?: string;
  share_token?: string;
  permission: "view" | "edit";
  shared_with_email?: string;
  shared_by_email?: string;
  created_at: string;
}

export interface ConversationShareListResponse {
  items: ConversationShare[];
  total: number;
}

export interface AdminConversation {
  id: string;
  user_id?: string;
  title?: string;
  is_archived: boolean;
  is_demo: boolean;
  message_count: number;
  user_email?: string;
  created_at: string;
  updated_at?: string;
}

export interface AdminConversationListResponse {
  items: AdminConversation[];
  total: number;
}

export interface AdminUser {
  id: string;
  email: string;
  full_name?: string;
  role?: string;
  is_active: boolean;
  is_app_admin?: boolean;
  conversation_count: number;
  created_at: string;
}

export interface AdminUserListResponse {
  items: AdminUser[];
  total: number;
}
