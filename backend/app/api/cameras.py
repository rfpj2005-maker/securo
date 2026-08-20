from __future__ import annotations

from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.responses import StreamingResponse

from app.core.auth import current_active_user
from app.models.user import User
from app.services import camera_service

router = APIRouter(prefix="/api/cameras", tags=["cameras"])


def _unavailable(exc: Exception) -> HTTPException:
    return HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Camera server unavailable: {exc}")


@router.get("", response_model=list[dict[str, Any]])
async def list_cameras(user: User = Depends(current_active_user)):
    try:
        return await camera_service.list_cameras()
    except camera_service.CameraApiNotConfigured as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except httpx.HTTPError as exc:
        raise _unavailable(exc) from exc


@router.get("/snapshot/{location}/{camera_id}")
async def snapshot(location: str, camera_id: str, user: User = Depends(current_active_user)):
    try:
        content, content_type = await camera_service.get_snapshot(location, camera_id)
    except camera_service.CameraApiNotConfigured as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except httpx.HTTPError as exc:
        raise _unavailable(exc) from exc
    return Response(content=content, media_type=content_type)


@router.get("/recordings/{location}/{camera_name}", response_model=list[dict[str, Any]])
async def recordings(location: str, camera_name: str, user: User = Depends(current_active_user)):
    try:
        return await camera_service.list_recordings(location, camera_name)
    except camera_service.CameraApiNotConfigured as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except httpx.HTTPError as exc:
        raise _unavailable(exc) from exc


@router.get("/recording/{location}/{camera_name}/{filename}")
async def recording(location: str, camera_name: str, filename: str, user: User = Depends(current_active_user)):
    try:
        content_type, content_length, stream = await camera_service.open_recording_stream(
            location, camera_name, filename
        )
    except camera_service.CameraApiNotConfigured as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except httpx.HTTPError as exc:
        raise _unavailable(exc) from exc
    headers = {"content-length": str(content_length)} if content_length is not None else {}
    return StreamingResponse(stream, media_type=content_type, headers=headers)
