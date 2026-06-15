/**
 * Chat and AI Agent types.
 */

export type MessageRole = "user" | "assistant" | "system";
/** Rating values for message feedback. */
export enum RatingValue {
  LIKE = 1,
  DISLIKE = -1,
}

export type UserRating = RatingValue.LIKE | RatingValue.DISLIKE | null;

export interface ChatMessageFile {
  id: string;
  filename: string;
  mime_type: string;
  /** "image" | "pdf" | "docx" | "text" — derived from MIME on upload. */
  file_type: string;
}

export interface ChatMessage {
  id: string;
  role: MessageRole;
  content: string;
  timestamp: Date;
  toolCalls?: ToolCall[];
  isStreaming?: boolean;
  /** Group ID for related messages (e.g., CrewAI agent chain) */
  groupId?: string;
  /** IDs of attached files — kept for sending. Use ``files`` for rendering. */
  fileIds?: string[];
  /** Full file metadata for rendering attachments. */
  files?: ChatMessageFile[];
  /** Conversation ID for this message */
  conversationId?: string;
  /** True if message ID is a temporary nanoid, not yet replaced by server ID */
  isTemporaryId?: boolean;
  /** Current user's rating */
  user_rating?: UserRating;
  /** Aggregate rating counts */
  rating_count?: { likes: number; dislikes: number } | null;
  /** Reasoning trace from extended-thinking models. Rendered dimmed +
   *  collapsible above the final response. */
  thinking?: string;
  /** Ordered timeline of the assistant turn: reasoning, text and tool
   *  calls in the exact order they occurred. Rendered in sequence so a
   *  multi-step turn (think → tools → text → think → tools → text) shows
   *  correctly. ``content``/``thinking``/``toolCalls`` are kept in sync as
   *  flat aggregates for copy/persist/rating. */
  parts?: MessagePart[];
}

export interface ToolCall {
  id: string;
  name: string;
  args: Record<string, unknown>;
  result?: unknown;
  status: "pending" | "running" | "completed" | "error";
}

export type MessagePartType = "thinking" | "text" | "tool";

/** One ordered segment of an assistant turn. */
export interface MessagePart {
  id: string;
  type: MessagePartType;
  /** Text for "thinking"/"text" parts. */
  content?: string;
  /** Tool invocation for "tool" parts. */
  toolCall?: ToolCall;
}
{%- if cookiecutter.enable_charts %}

export type ChartType = "line" | "bar" | "pie" | "area" | "scatter";

export interface ChartSeries {
  key: string;
  label?: string | null;
  color?: string | null;
}

export interface ChartStyle {
  palette?: string[] | null;
  grid?: boolean;
  legend?: boolean;
  x_label?: string | null;
  y_label?: string | null;
  stacked?: boolean;
}

/** Structured chart payload produced by the agent's `create_chart` tool. */
export interface ChartSpec {
  kind: "chart";
  chart_type: ChartType;
  title: string;
  data: Array<Record<string, unknown>>;
  x_key: string;
  series: ChartSeries[];
  style: ChartStyle;
}
{%- endif %}
{%- if cookiecutter.enable_antv_charts %}

/** A single point on a `create_map` map. */
export interface MapMarker {
  lat: number;
  lng: number;
  label: string;
  description?: string | null;
  color?: string | null;
}

/** Structured map payload produced by the agent's `create_map` tool. */
export interface MapSpec {
  kind: "map";
  title: string;
  markers: MapMarker[];
  center?: [number, number] | null;
  zoom?: number | null;
}
{%- endif %}

// WebSocket event types from backend
export type WSEventType =
  // PydanticAI / LangChain / LangGraph events
  | "user_prompt"
  | "user_prompt_processed"
  | "model_request_start"
  | "part_start"
  | "text_delta"
  | "thinking_delta"
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
  | "ask_user"
{%- if cookiecutter.enable_deep_research %}
  // Deep research events
  | "todo_event"
  | "subagent_status"
  | "context_usage"
  | "context_compacted"
{%- endif %}
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

export interface AskUserQuestion {
  question: string;
  options: string[];
  /** Whether the user may type a free-form answer instead of picking an option. */
  allowCustom: boolean;
}

export interface AskUserAnswer {
  answer: string;
  skipped: boolean;
}

export interface AskUserEvent {
  type: "ask_user";
  data: {
    questions: { question: string; options: string[]; allow_custom: boolean }[];
  };
}
{%- if cookiecutter.enable_deep_research %}

export type ResearchTodoStatus = "pending" | "in_progress" | "completed" | "blocked";

export interface ResearchTodo {
  id: string;
  content: string;
  status: ResearchTodoStatus;
  active_form: string;
  parent_id: string | null;
  depends_on: string[];
}

export interface TodoEventFrame {
  type: "todo_event";
  data: {
    event_type: "created" | "updated" | "status_changed" | "completed" | "deleted";
    todo: ResearchTodo;
    previous: ResearchTodo | null;
    ts: string | null;
  };
}

export type SubagentTaskStatus =
  | "pending"
  | "running"
  | "waiting_for_answer"
  | "completed"
  | "failed"
  | "cancelled"
  | "retrying";

export interface SubagentStatus {
  task_id: string;
  subagent_name: string;
  description: string;
  status: SubagentTaskStatus;
  error: string | null;
}

export interface ContextUsage {
  pct: number;
  current: number;
  max: number;
}
{%- endif %}
