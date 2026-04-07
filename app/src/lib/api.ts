import type {
  ConversationSummary,
  ConversationDetail,
  ArtifactSummary,
  ArtifactDetail,
} from "./types";

class ApiError extends Error {
  constructor(
    public status: number,
    message: string
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 10_000);

  try {
    const res = await fetch(path, {
      ...init,
      signal: init?.signal ?? controller.signal,
    });
    if (!res.ok) {
      const body = await res.text().catch(() => "");
      throw new ApiError(res.status, body || res.statusText);
    }
    return (await res.json()) as T;
  } finally {
    clearTimeout(timeout);
  }
}

// ---------------------------------------------------------------------------
// Conversations
// ---------------------------------------------------------------------------

export async function fetchConversations(params?: {
  archived?: boolean;
  starred?: boolean;
  q?: string;
  limit?: number;
  offset?: number;
}): Promise<ConversationSummary[]> {
  const sp = new URLSearchParams();
  if (params?.archived !== undefined) sp.set("archived", String(params.archived));
  if (params?.starred !== undefined) sp.set("starred", String(params.starred));
  if (params?.q) sp.set("q", params.q);
  if (params?.limit !== undefined) sp.set("limit", String(params.limit));
  if (params?.offset !== undefined) sp.set("offset", String(params.offset));
  const qs = sp.toString();
  return request<ConversationSummary[]>(`/api/v1/conversations${qs ? `?${qs}` : ""}`);
}

export async function fetchConversation(id: string): Promise<ConversationDetail> {
  return request<ConversationDetail>(`/api/v1/conversations/${id}`);
}

export async function createConversation(title?: string): Promise<ConversationSummary> {
  return request<ConversationSummary>("/api/v1/conversations", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title }),
  });
}

export async function updateConversation(
  id: string,
  data: { title?: string; starred?: number; archived_at?: string | null }
): Promise<ConversationSummary> {
  return request<ConversationSummary>(`/api/v1/conversations/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
}

// ---------------------------------------------------------------------------
// Artifacts
// ---------------------------------------------------------------------------

export async function fetchArtifacts(params?: {
  q?: string;
  kind?: string;
  quality_flag?: string;
  conversation_id?: string;
  limit?: number;
  offset?: number;
}): Promise<ArtifactSummary[]> {
  const sp = new URLSearchParams();
  if (params?.q) sp.set("q", params.q);
  if (params?.kind) sp.set("kind", params.kind);
  if (params?.quality_flag) sp.set("quality_flag", params.quality_flag);
  if (params?.conversation_id) sp.set("conversation_id", params.conversation_id);
  if (params?.limit !== undefined) sp.set("limit", String(params.limit));
  if (params?.offset !== undefined) sp.set("offset", String(params.offset));
  const qs = sp.toString();
  return request<ArtifactSummary[]>(`/api/v1/artifacts${qs ? `?${qs}` : ""}`);
}

export async function fetchArtifact(id: string): Promise<ArtifactDetail> {
  return request<ArtifactDetail>(`/api/v1/artifacts/${id}`);
}

export async function updateArtifactFlag(
  id: string,
  quality_flag: string
): Promise<ArtifactDetail> {
  return request<ArtifactDetail>(`/api/v1/artifacts/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ quality_flag }),
  });
}

// ---------------------------------------------------------------------------
// Health
// ---------------------------------------------------------------------------

export async function checkHealth(): Promise<{ status: string }> {
  return request<{ status: string }>("/health");
}
