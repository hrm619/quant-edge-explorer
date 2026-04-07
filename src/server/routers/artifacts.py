"""Artifact retrieval and management endpoints."""

from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Query

from explorer.history import repository as repo
from server.dependencies import get_history_conn
from server.schemas import ArtifactDetail, ArtifactFlagUpdate, ArtifactSummary

router = APIRouter(prefix="/api/v1", tags=["artifacts"])


@router.get("/artifacts", response_model=list[ArtifactSummary])
def list_artifacts(
    q: str | None = None,
    kind: str | None = None,
    quality_flag: str | None = None,
    conversation_id: str | None = None,
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
    conn: sqlite3.Connection = Depends(get_history_conn),
):
    return repo.list_artifacts(
        conn, q=q, kind=kind, quality_flag=quality_flag,
        conversation_id=conversation_id, limit=limit, offset=offset,
    )


@router.get("/artifacts/{artifact_id}", response_model=ArtifactDetail)
def get_artifact(
    artifact_id: str,
    conn: sqlite3.Connection = Depends(get_history_conn),
):
    result = repo.get_artifact(conn, artifact_id)
    if not result:
        raise HTTPException(status_code=404, detail="Artifact not found")
    return result


@router.patch("/artifacts/{artifact_id}", response_model=ArtifactDetail)
def update_artifact_flag(
    artifact_id: str,
    data: ArtifactFlagUpdate,
    conn: sqlite3.Connection = Depends(get_history_conn),
):
    try:
        result = repo.update_artifact_flag(conn, artifact_id, data.quality_flag)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not result:
        raise HTTPException(status_code=404, detail="Artifact not found")
    return result
