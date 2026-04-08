// ---------------------------------------------------------------------------
// REST API response types (mirrors src/server/schemas.py)
// ---------------------------------------------------------------------------

export interface ConversationSummary {
  id: string;
  title: string | null;
  created_at: string;
  updated_at: string;
  archived_at: string | null;
  starred: number;
  message_count: number;
}

export interface ToolCallResponse {
  id: string;
  tool_name: string;
  tool_input: Record<string, unknown>;
  tool_result: string | null;
  duration_ms: number | null;
  status: string;
  error_message: string | null;
  created_at: string;
}

export interface MessageResponse {
  id: string;
  conversation_id: string;
  role: "user" | "assistant" | "system";
  content: string;
  phase: "planning" | "execution" | null;
  created_at: string;
  ordinal: number;
  tool_calls: ToolCallResponse[];
}

export interface AnnotationResponse {
  id: string;
  conversation_id: string;
  body: string;
  created_at: string;
  updated_at: string;
}

export interface ArtifactSummary {
  id: string;
  tool_call_id: string;
  conversation_id: string;
  kind: "table" | "chart" | "citation_set";
  title: string | null;
  quality_flag: "unflagged" | "trusted" | "untrusted";
  created_at: string;
}

export interface ArtifactDetail extends ArtifactSummary {
  spec: Record<string, unknown>;
  searchable_text: string;
}

export interface ConversationDetail extends ConversationSummary {
  messages: MessageResponse[];
  artifacts: ArtifactDetail[];
  annotations: AnnotationResponse[];
}

// ---------------------------------------------------------------------------
// SSE event data types (mirrors chat.py SSE protocol)
// ---------------------------------------------------------------------------

export interface SSEConversationEvent {
  conversation_id: string;
}

export interface SSEPhaseEvent {
  phase: "planning" | "execution";
}

export interface SSEPlanEvent {
  text: string;
}

export interface SSEToolCallStartEvent {
  id: string;
  name: string;
  input: Record<string, unknown>;
}

export interface SSEToolCallEndEvent {
  id: string;
  name: string;
  status: "success" | "error";
  duration_ms: number;
  row_count?: number;
}

export interface SSEArtifactEvent {
  id: string;
  kind: "table" | "chart" | "citation_set";
  title: string | null;
  spec: Record<string, unknown>;
}

export interface SSETextDeltaEvent {
  text: string;
}

export interface SSEDoneEvent {
  conversation_id: string;
  message_id: string;
}

export interface SSETitleUpdatedEvent {
  conversation_id: string;
  title: string;
}

export interface SSEErrorEvent {
  message: string;
  tool_call_id?: string;
}

// ---------------------------------------------------------------------------
// UI state types
// ---------------------------------------------------------------------------

export type Phase = "idle" | "planning" | "execution";

export interface StreamingToolCall {
  id: string;
  name: string;
  input: Record<string, unknown>;
  status?: "success" | "error";
  duration_ms?: number;
  row_count?: number;
}

export interface StreamingArtifact {
  id: string;
  tool_call_id: string;
  kind: "table" | "chart" | "citation_set";
  title: string | null;
  spec: Record<string, unknown>;
}
