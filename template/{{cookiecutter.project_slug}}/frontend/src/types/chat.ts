/**
 * Chat and AI Agent types.
 */

export type MessageRole = "user" | "assistant" | "system";

export interface ChatMessage {
  id: string;
  role: MessageRole;
  content: string;
  timestamp: Date;
  toolCalls?: ToolCall[];
  isStreaming?: boolean;
  /** Group ID for related messages (e.g., CrewAI agent chain) */
  groupId?: string;
  /** IDs of attached files (images, documents) */
  fileIds?: string[];
}

export interface ToolCall {
  id: string;
  name: string;
  args: Record<string, unknown>;
  result?: unknown;
  status: "pending" | "running" | "completed" | "error";
}

// WebSocket event types from backend
export type WSEventType =
  // PydanticAI / LangChain / LangGraph events
  | "user_prompt"
  | "user_prompt_processed"
  | "model_request_start"
  | "part_start"
  | "text_delta"
  | "tool_call_delta"
  | "call_tools_start"
  | "tool_call"
  | "tool_result"
  | "final_result_start"
  | "final_result"
  | "complete"
  | "error"
  | "conversation_created"
  | "message_saved"
  // DeepAgents Human-in-the-Loop event
  | "tool_approval_required"
  // CrewAI-specific events
  | "crew_start"
  | "crew_started"
  | "crew_complete"
  | "agent_started"
  | "agent_completed"
  | "task_started"
  | "task_completed"
  | "tool_started"
  | "tool_finished"
  | "llm_started"
  | "llm_completed";

export interface WSEvent {
  type: WSEventType;
  data?: unknown;
  timestamp?: string;
}

export interface TextDeltaEvent {
  type: "text_delta";
  data: {
    delta: string;
  };
}

export interface ToolCallEvent {
  type: "tool_call";
  data: {
    tool_name: string;
    args: Record<string, unknown>;
  };
}

export interface ToolResultEvent {
  type: "tool_result";
  data: {
    tool_name: string;
    result: unknown;
  };
}

export interface FinalResultEvent {
  type: "final_result";
  data: {
    output: string;
    tool_events: ToolCall[];
  };
}

export interface ChatState {
  messages: ChatMessage[];
  isConnected: boolean;
  isProcessing: boolean;
}

// Human-in-the-Loop (HITL) types for DeepAgents
export interface ActionRequest {
  id: string;
  tool_name: string;
  args: Record<string, unknown>;
}

export interface ReviewConfig {
  tool_name: string;
  /** Whether to allow editing the tool arguments */
  allow_edit?: boolean;
  /** Maximum time to wait for decision (seconds) */
  timeout?: number;
}

export interface PendingApproval {
  actionRequests: ActionRequest[];
  reviewConfigs: ReviewConfig[];
}

export type DecisionType = "approve" | "edit" | "reject";

export interface Decision {
  type: DecisionType;
  editedAction?: {
    id: string;
    tool_name: string;
    args: Record<string, unknown>;
  };
}

export interface ToolApprovalRequiredEvent {
  type: "tool_approval_required";
  data: {
    action_requests: ActionRequest[];
    review_configs: ReviewConfig[];
  };
}
