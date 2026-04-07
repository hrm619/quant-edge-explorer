"""Pydantic request/response models for the API."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


# ---------------------------------------------------------------------------
# Chat
# ---------------------------------------------------------------------------


class ChatRequest(BaseModel):
    message: str
    conversation_id: str | None = None


# ---------------------------------------------------------------------------
# Conversations
# ---------------------------------------------------------------------------


class ConversationCreate(BaseModel):
    title: str | None = None


class ConversationUpdate(BaseModel):
    title: str | None = None
    starred: int | None = None
    archived_at: str | None = None


class ConversationSummary(BaseModel):
    id: str
    title: str | None
    created_at: str
    updated_at: str
    archived_at: str | None
    starred: int
    message_count: int


class ToolCallResponse(BaseModel):
    id: str
    tool_name: str
    tool_input: dict
    tool_result: str | None
    duration_ms: int | None
    status: str
    error_message: str | None
    created_at: str


class MessageResponse(BaseModel):
    id: str
    conversation_id: str
    role: str
    content: str
    phase: str | None
    created_at: str
    ordinal: int
    tool_calls: list[ToolCallResponse] = []


class ArtifactSummary(BaseModel):
    id: str
    tool_call_id: str
    conversation_id: str
    kind: str
    title: str | None
    quality_flag: str
    created_at: str


class ArtifactDetail(ArtifactSummary):
    spec: dict
    searchable_text: str


class ConversationDetail(ConversationSummary):
    messages: list[MessageResponse] = []
    artifacts: list[ArtifactSummary] = []
    annotations: list[AnnotationResponse] = []


# ---------------------------------------------------------------------------
# Artifacts
# ---------------------------------------------------------------------------


class ArtifactFlagUpdate(BaseModel):
    quality_flag: str


# ---------------------------------------------------------------------------
# Annotations
# ---------------------------------------------------------------------------


class AnnotationCreate(BaseModel):
    body: str


class AnnotationUpdate(BaseModel):
    body: str


class AnnotationResponse(BaseModel):
    id: str
    conversation_id: str
    body: str
    created_at: str
    updated_at: str


# Rebuild forward refs now that AnnotationResponse is defined
ConversationDetail.model_rebuild()
