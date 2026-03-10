from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth import (
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)
from app.database import get_db
from app.models import Chat, ChatMember, Message, User
from app.schemas import (
    ChatDetailOut,
    ChatSummaryOut,
    MemberOut,
    MessageOut,
    TokenOut,
    UserCreate,
    UserLogin,
    UserOut,
)

router = APIRouter(prefix="/api")


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(body: UserCreate, db: Annotated[AsyncSession, Depends(get_db)]):
    existing = await db.execute(select(User).where(User.username == body.username))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already taken",
        )
    user = User(username=body.username, password_hash=hash_password(body.password))
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.post("/login", response_model=TokenOut)
async def login(body: UserLogin, db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(select(User).where(User.username == body.username))
    user = result.scalar_one_or_none()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )
    token = create_access_token(user.id)
    return TokenOut(access_token=token)


@router.get("/me", response_model=UserOut)
async def me(current_user: Annotated[User, Depends(get_current_user)]):
    return current_user


@router.get("/chats", response_model=list[ChatSummaryOut])
async def list_chats(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(
        select(Chat)
        .join(ChatMember, ChatMember.chat_id == Chat.id)
        .where(ChatMember.user_id == current_user.id)
        .order_by(Chat.created_at.desc())
    )
    return result.scalars().all()


@router.get("/chats/{chat_id}", response_model=ChatDetailOut)
async def get_chat(
    chat_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(
        select(Chat)
        .options(
            selectinload(Chat.members).selectinload(ChatMember.user),
            selectinload(Chat.messages).selectinload(Message.sender),
        )
        .where(Chat.id == chat_id)
    )
    chat = result.scalar_one_or_none()
    if not chat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat not found")

    is_member = any(m.user_id == current_user.id for m in chat.members)
    if not is_member:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a member of this chat")

    members = [
        MemberOut(id=m.user.id, username=m.user.username, online=False)
        for m in chat.members
    ]
    messages = [
        MessageOut(
            id=msg.id,
            chat_id=msg.chat_id,
            sender_id=msg.sender_id,
            sender_username=msg.sender.username,
            content=msg.content,
            sent_at=msg.sent_at,
        )
        for msg in sorted(chat.messages, key=lambda m: m.sent_at)
    ]

    return ChatDetailOut(
        id=chat.id,
        name=chat.name,
        creator_id=chat.creator_id,
        created_at=chat.created_at,
        members=members,
        messages=messages,
    )


@router.get("/users", response_model=list[UserOut])
async def list_users(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    q: str = Query(default="", description="Search by username prefix"),
):
    query = select(User)
    if q:
        query = query.where(User.username.ilike(f"{q}%"))
    query = query.where(User.id != current_user.id).limit(50)
    result = await db.execute(query)
    return result.scalars().all()
