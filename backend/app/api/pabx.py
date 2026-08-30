"""Amparar PABX (Nuvem JTi) call monitoring — company-wide, not
workspace-scoped, same reasoning as the camera/siprov integrations: any
member of a business workspace can view it, not just anyone with an
account on this install (see core/workspace_context.current_business_user
— this used to be current_active_user, which let unrelated personal
users see it too)."""
from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.workspace_context import current_business_user
from app.models.user import User
from app.services import pabx_service

router = APIRouter(prefix="/api/pabx", tags=["pabx"])


@router.get("/resumo")
async def get_resumo(
    dias: int = Query(7, ge=1, le=60),
    _user: User = Depends(current_business_user),
):
    try:
        return await pabx_service.resumo_chamadas(dias=dias)
    except pabx_service.NuvemJtiNotConfigured as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
