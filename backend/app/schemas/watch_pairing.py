from pydantic import BaseModel, Field


class WatchPairStartResponse(BaseModel):
    code: str
    expires_in: int


class WatchPairRedeemRequest(BaseModel):
    code: str = Field(pattern=r"^\d{6}$")


class WatchPairTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
