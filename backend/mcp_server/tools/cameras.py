from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.services import camera_service
from mcp_server.auth import CallContext
from mcp_server.registry import tool


@tool(
    name="list_cameras",
    description=(
        "List all of Amparar's security cameras across every location (matriz, belvedere, "
        "varginha, centro) with live online/connected status. Does not return images — use this "
        "to answer 'how many cameras', 'is camera X online', or to find the location/name needed "
        "for list_camera_recordings. Tell the user to open the Câmeras page to actually watch the "
        "live feed or a recording — this tool can't show images/video in chat."
    ),
    parameters={"type": "object", "properties": {}, "additionalProperties": False},
    tags=["read", "cameras"],
)
async def list_cameras(*, session: AsyncSession, ctx: CallContext) -> dict[str, Any]:
    items = await camera_service.list_cameras()
    return {"items": items, "total": len(items)}


@tool(
    name="list_camera_recordings",
    description=(
        "List saved recordings for one camera, most recent first. location/camera_name come from "
        "list_cameras (the 'location' and 'name' fields)."
    ),
    parameters={
        "type": "object",
        "properties": {
            "location": {"type": "string", "description": "e.g. 'matriz', 'belvedere', 'varginha'"},
            "camera_name": {"type": "string", "description": "e.g. 'PVBelve02'"},
        },
        "required": ["location", "camera_name"],
        "additionalProperties": False,
    },
    tags=["read", "cameras"],
)
async def list_camera_recordings(
    *, session: AsyncSession, ctx: CallContext, location: str, camera_name: str
) -> dict[str, Any]:
    items = await camera_service.list_recordings(location, camera_name)
    return {"items": items, "total": len(items)}
