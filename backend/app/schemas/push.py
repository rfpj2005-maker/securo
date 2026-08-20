from pydantic import BaseModel


class PushSubscribeKeys(BaseModel):
    p256dh: str
    auth: str


class PushSubscribeCreate(BaseModel):
    endpoint: str
    keys: PushSubscribeKeys
    user_agent: str | None = None


class PushUnsubscribe(BaseModel):
    endpoint: str


class PushVapidKey(BaseModel):
    public_key: str


class PushStatus(BaseModel):
    subscribed: bool
    device_count: int
