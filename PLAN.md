# Real-Time Messaging App — Project Plan

## Overview

A full-stack, real-time messaging application with a React frontend, Python FastAPI backend, and SQLite database. All messaging, user presence, and chat membership updates are communicated over WebSockets for a fully real-time experience.

---

## Tech Stack

| Layer      | Technology                        | Rationale                                                                 |
|------------|-----------------------------------|---------------------------------------------------------------------------|
| Frontend   | React (Vite + TypeScript)         | Fast dev server, strong typing, modern tooling                            |
| Backend    | Python FastAPI                    | Native async support, first-class WebSocket support, auto-generated docs  |
| Database   | SQLite (via SQLAlchemy + aiosqlite) | Zero-config, file-based, perfectly adequate for this scope               |
| Auth       | JWT (access tokens)               | Stateless, simple, works well with WebSocket auth via query params        |
| WebSockets | FastAPI WebSocket + native React `WebSocket` API | No extra libraries needed on either side              |

---

## Data Model

### Users
| Column          | Type    | Notes                     |
|-----------------|---------|---------------------------|
| id              | INTEGER | Primary key, autoincrement |
| username        | TEXT    | Unique, not null           |
| password_hash   | TEXT    | bcrypt hash                |
| created_at      | DATETIME| Default: now               |

### Chats
| Column      | Type    | Notes                        |
|-------------|---------|------------------------------|
| id          | INTEGER | Primary key, autoincrement    |
| name        | TEXT    | Chat display name             |
| creator_id  | INTEGER | FK → Users.id                 |
| created_at  | DATETIME| Default: now                  |

### ChatMembers (join table)
| Column   | Type    | Notes                           |
|----------|---------|---------------------------------|
| id       | INTEGER | Primary key, autoincrement       |
| chat_id  | INTEGER | FK → Chats.id                    |
| user_id  | INTEGER | FK → Users.id                    |
| joined_at| DATETIME| Default: now                     |

*Unique constraint on (chat_id, user_id)*

### Messages
| Column    | Type    | Notes                      |
|-----------|---------|----------------------------|
| id        | INTEGER | Primary key, autoincrement  |
| chat_id   | INTEGER | FK → Chats.id               |
| sender_id | INTEGER | FK → Users.id               |
| content   | TEXT    | Message body                |
| sent_at   | DATETIME| Default: now                |

---

## API Design

### REST Endpoints (HTTP)

These are used only for auth and initial data loading — not for real-time operations.

| Method | Path                  | Description                        | Auth Required |
|--------|-----------------------|------------------------------------|---------------|
| POST   | `/api/register`       | Create a new user account          | No            |
| POST   | `/api/login`          | Authenticate, returns JWT          | No            |
| GET    | `/api/me`             | Get current user info              | Yes           |
| GET    | `/api/chats`          | List chats the user belongs to     | Yes           |
| GET    | `/api/chats/{id}`     | Get chat details + members + messages | Yes        |
| GET    | `/api/users`          | Search/list users (for adding to chats) | Yes      |

### WebSocket Endpoint

**`/ws?token=<jwt>`**

A single multiplexed WebSocket connection per authenticated user. All real-time communication flows through this one connection.

#### Client → Server Messages

```jsonc
// Create a new chat
{ "type": "create_chat", "data": { "name": "My Chat" } }

// Send a message to a chat
{ "type": "send_message", "data": { "chat_id": 1, "content": "Hello!" } }

// Add a user to a chat (creator only)
{ "type": "add_user", "data": { "chat_id": 1, "user_id": 5 } }

// Remove a user from a chat (creator only)
{ "type": "remove_user", "data": { "chat_id": 1, "user_id": 5 } }
```

#### Server → Client Messages

```jsonc
// New message in a chat
{ "type": "new_message", "data": { "chat_id": 1, "message": { "id": 42, "sender_id": 3, "sender_username": "alice", "content": "Hello!", "sent_at": "..." } } }

// Chat created (sent to creator)
{ "type": "chat_created", "data": { "chat": { "id": 1, "name": "My Chat", "creator_id": 2 } } }

// User added to chat (broadcast to all chat members)
{ "type": "user_added", "data": { "chat_id": 1, "user": { "id": 5, "username": "bob" } } }

// User removed from chat (broadcast to all chat members)
{ "type": "user_removed", "data": { "chat_id": 1, "user_id": 5 } }

// You were added to a chat (sent to the added user)
{ "type": "added_to_chat", "data": { "chat": { "id": 1, "name": "My Chat", "creator_id": 2, "members": [...] } } }

// Presence update (broadcast to chat members)
{ "type": "presence_update", "data": { "chat_id": 1, "user_id": 3, "status": "online" | "offline" } }

// Error
{ "type": "error", "data": { "message": "Not authorized" } }
```

---

## Presence Tracking

- The backend maintains an in-memory dictionary mapping `user_id → WebSocket connection`.
- When a user connects via WebSocket, they are marked **online** and a `presence_update` is broadcast to all chats they belong to.
- When a user disconnects, they are marked **offline** and the same broadcast occurs.
- When a client requests chat details (via REST), the response includes each member's current online/offline status derived from this in-memory map.

---

## Project Structure

```
agent-coded-messaging-app/
├── PLAN.md
├── backend/
│   ├── requirements.txt
│   ├── app/
│   │   ├── main.py              # FastAPI app, startup/shutdown, CORS
│   │   ├── config.py            # Settings (secret key, DB URL, etc.)
│   │   ├── database.py          # SQLAlchemy async engine + session
│   │   ├── models.py            # SQLAlchemy ORM models
│   │   ├── schemas.py           # Pydantic request/response schemas
│   │   ├── auth.py              # JWT creation/verification, password hashing
│   │   ├── routes/
│   │   │   ├── http.py          # REST endpoints (register, login, chats, etc.)
│   │   │   └── ws.py            # WebSocket endpoint + message dispatcher
│   │   └── manager.py           # ConnectionManager: tracks connections, broadcasts
│   └── messaging.db             # SQLite database file (gitignored)
├── frontend/
│   ├── package.json
│   ├── vite.config.ts
│   ├── index.html
│   ├── src/
│   │   ├── main.tsx             # React entry point
│   │   ├── App.tsx              # Top-level routing
│   │   ├── api.ts               # HTTP helper (fetch wrapper with JWT)
│   │   ├── ws.ts                # WebSocket connection manager (singleton)
│   │   ├── context/
│   │   │   └── AuthContext.tsx   # Auth state (token, current user)
│   │   ├── pages/
│   │   │   ├── LoginPage.tsx
│   │   │   ├── RegisterPage.tsx
│   │   │   └── ChatPage.tsx     # Main chat UI
│   │   └── components/
│   │       ├── ChatList.tsx      # Sidebar: list of chats
│   │       ├── ChatWindow.tsx    # Message list + input for active chat
│   │       ├── MemberList.tsx    # Members sidebar with online/offline indicators
│   │       └── AddUserModal.tsx  # Modal for chat creator to add users
│   └── public/
└── .gitignore
```

---

## Implementation Phases

### Phase 1: Backend Foundation
1. Set up FastAPI project structure with SQLAlchemy + aiosqlite.
2. Define ORM models and create DB initialization logic.
3. Implement user registration and login (JWT).
4. Implement REST endpoints for chat listing and details.

### Phase 2: WebSocket Infrastructure
1. Build `ConnectionManager` class to track active WebSocket connections per user.
2. Implement the `/ws` endpoint with JWT authentication via query param.
3. Implement message dispatching: parse incoming JSON, route to handler functions.
4. Implement `send_message` handler — persist to DB, broadcast to chat members.

### Phase 3: Chat Management over WebSocket
1. Implement `create_chat` handler — create chat + add creator as member.
2. Implement `add_user` / `remove_user` handlers with creator-only authorization.
3. Broadcast membership changes to all connected chat members in real time.

### Phase 4: Presence System
1. On WebSocket connect: mark user online, broadcast to their chats.
2. On WebSocket disconnect: mark user offline, broadcast to their chats.
3. Include presence data in chat detail REST responses.

### Phase 5: Frontend — Auth & Routing
1. Scaffold React app with Vite + TypeScript.
2. Build login and registration pages.
3. Implement `AuthContext` for JWT storage and current-user state.
4. Set up routing (login, register, main chat view).

### Phase 6: Frontend — Chat UI & WebSocket Integration
1. Build WebSocket singleton that connects on login, reconnects on drop.
2. Build chat list sidebar, chat window, and message input.
3. Wire incoming WebSocket messages to React state updates.
4. Build member list with online/offline status indicators.
5. Build "Add User" modal (visible only to chat creator).

### Phase 7: Polish & Edge Cases
1. Handle WebSocket reconnection with exponential backoff.
2. Scroll-to-bottom behavior on new messages.
3. Error toasts for failed operations.
4. Loading states and empty states.

---

## Key Design Decisions

1. **Single WebSocket connection per user** — simpler than per-chat connections; the server multiplexes messages by `chat_id`.
2. **SQLite** — no external database process to manage; perfect for a project of this scope. Easily swappable for PostgreSQL later via SQLAlchemy.
3. **JWT via query param for WebSocket auth** — browsers' WebSocket API doesn't support custom headers, so the token is passed as `?token=<jwt>` on the connection URL.
4. **In-memory presence** — no need for Redis at this scale. The `ConnectionManager` holds a `dict[int, WebSocket]` which naturally represents who is online.
5. **Creator-only chat administration** — `add_user` and `remove_user` handlers check `chat.creator_id == requesting_user.id` before proceeding.
