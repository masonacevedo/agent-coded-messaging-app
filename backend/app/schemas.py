from datetime import datetime

from pydantic import BaseModel


class UserCreate(BaseModel):
    username: str
    password: str


class UserLogin(BaseModel):
    username: str
    password: str


class UserOut(BaseModel):
    id: int
    username: str
    created_at: datetime

    model_config = {"from_attributes": True}


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class MemberOut(BaseModel):
    id: int
    username: str
    online: bool = False

    model_config = {"from_attributes": True}


class MessageOut(BaseModel):
    id: int
    chat_id: int
    sender_id: int
    sender_username: str
    content: str
    sent_at: datetime


class ChatSummaryOut(BaseModel):
    id: int
    name: str
    creator_id: int
    created_at: datetime

    model_config = {"from_attributes": True}


class ChatDetailOut(BaseModel):
    id: int
    name: str
    creator_id: int
    created_at: datetime
    members: list[MemberOut]
    messages: list[MessageOut]
