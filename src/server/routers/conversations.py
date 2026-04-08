"""Conversation CRUD endpoints."""

import sqlite3
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from explorer.history import repository as repo
from server.dependencies import get_history_conn
from server.schemas import (
    AnnotationCreate,
    AnnotationResponse,
    AnnotationUpdate,
    ConversationCreate,
    ConversationDetail,
    ConversationSummary,
    ConversationUpdate,
)

router = APIRouter(prefix="/api/v1", tags=["conversations"])

HistoryConn = Annotated[sqlite3.Connection, Depends(get_history_conn)]


@router.post("/conversations", response_model=ConversationSummary, status_code=201)
def create_conversation(
    body: ConversationCreate,
    conn: HistoryConn,
):
    return repo.create_conversation(conn, title=body.title)


@router.get("/conversations", response_model=list[ConversationSummary])
def list_conversations(
    conn: HistoryConn,
    archived: bool = False,
    starred: bool | None = None,
    q: str | None = None,
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
):
    return repo.list_conversations(
        conn, archived=archived, starred=starred, q=q, limit=limit, offset=offset,
    )


@router.get("/conversations/{conversation_id}", response_model=ConversationDetail)
def get_conversation(
    conversation_id: str,
    conn: HistoryConn,
):
    result = repo.get_conversation_with_messages(conn, conversation_id)
    if not result:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return result


@router.patch("/conversations/{conversation_id}", response_model=ConversationSummary)
def update_conversation(
    conversation_id: str,
    data: ConversationUpdate,
    conn: HistoryConn,
):
    # Only pass fields that were explicitly set
    kwargs = {}
    if data.title is not None:
        kwargs["title"] = data.title
    if data.starred is not None:
        kwargs["starred"] = data.starred
    if data.archived_at is not None:
        kwargs["archived_at"] = data.archived_at

    result = repo.update_conversation(conn, conversation_id, **kwargs)
    if not result:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return result


# ---------------------------------------------------------------------------
# Annotations
# ---------------------------------------------------------------------------


@router.post(
    "/conversations/{conversation_id}/annotations",
    response_model=AnnotationResponse,
    status_code=201,
)
def create_annotation(
    conversation_id: str,
    data: AnnotationCreate,
    conn: HistoryConn,
):
    conv = repo.get_conversation(conn, conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return repo.add_annotation(conn, conversation_id, data.body)


@router.patch("/annotations/{annotation_id}", response_model=AnnotationResponse)
def update_annotation(
    annotation_id: str,
    data: AnnotationUpdate,
    conn: HistoryConn,
):
    result = repo.update_annotation(conn, annotation_id, data.body)
    if not result:
        raise HTTPException(status_code=404, detail="Annotation not found")
    return result


@router.delete("/annotations/{annotation_id}", status_code=204)
def delete_annotation(
    annotation_id: str,
    conn: HistoryConn,
):
    if not repo.delete_annotation(conn, annotation_id):
        raise HTTPException(status_code=404, detail="Annotation not found")
