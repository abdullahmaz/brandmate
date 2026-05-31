"""
Database service.

Every method takes a `client: Client` argument — the per-request Supabase
client that has been authenticated with the caller's JWT. Row Level
Security on `chats` and `messages` then filters rows by `auth.uid()`, so
this service does NOT pass user_id explicitly to filters. It also does
not own a long-lived client of its own; callers obtain one via
`supabase_client.client_for_user(access_token)`.

This is the same pattern Supabase recommends for FastAPI: never put user
data behind a global service_role client; always use the user's token.
"""

from typing import List, Optional
from datetime import datetime
import re

from supabase import Client

from database_models import (
    ChatCreate,
    ChatResponse,
    MessageCreate,
    MessageResponse,
    ChatWithMessages,
    MessageRole,
    MessageType,
)


def _parse_db_timestamp(value: str) -> datetime:
    """
    Parse ISO timestamp strings coming back from Supabase robustly across
    Python versions and minor format differences.

    Examples we've seen:
      - "2025-12-10T10:55:07.08128+00:00"
      - "2025-12-10T10:55:07.081280Z"
      - "2025-12-10T10:55:07.081280"
    """
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"

    timezone = ""
    for sep in ("+", "-"):
        idx = value.find(sep, 10)
        if idx != -1:
            timezone = value[idx:]
            value = value[:idx]
            break

    match = re.search(r"\.(\d+)$", value)
    if match:
        micros = match.group(1)
        if len(micros) < 6:
            micros = micros.ljust(6, "0")
        elif len(micros) > 6:
            micros = micros[:6]
        value = value[: match.start()] + f".{micros}"

    return datetime.fromisoformat(value + timezone)


def _chat_row_to_response(row: dict) -> ChatResponse:
    return ChatResponse(
        id=row["id"],
        title=row["title"],
        user_id=row["user_id"],
        created_at=_parse_db_timestamp(row["created_at"]),
        updated_at=_parse_db_timestamp(row["updated_at"]),
    )


def _message_row_to_response(row: dict) -> MessageResponse:
    return MessageResponse(
        id=row["id"],
        chat_id=row["chat_id"],
        role=MessageRole(row["role"]),
        content=row["content"],
        message_type=MessageType(row["message_type"]),
        s3_url=row["s3_url"],
        metadata=row["metadata"],
        created_at=_parse_db_timestamp(row["created_at"]),
    )


class DatabaseService:
    """Stateless. All state — auth context, connection — lives on the
    `client` passed into each method."""

    # ── chats ───────────────────────────────────────────────────────

    async def create_chat(
        self, client: Client, *, user_id: str, chat_data: ChatCreate
    ) -> ChatResponse:
        """Create a chat owned by `user_id`. The body of ChatCreate is
        trusted only for `title` — user_id always comes from the JWT."""
        try:
            now = datetime.utcnow().isoformat()
            result = client.table("chats").insert({
                "title": chat_data.title,
                "user_id": user_id,
                "created_at": now,
                "updated_at": now,
            }).execute()

            if not result.data:
                raise Exception("Failed to create chat")
            return _chat_row_to_response(result.data[0])
        except Exception as e:
            error_msg = str(e)
            if "RLS policy" in error_msg or "42501" in error_msg:
                print(f"RLS policy error creating chat: {e}")
                raise Exception(
                    "Database RLS policy blocking chat creation. "
                    "Check that the user JWT is being attached and the "
                    "policies in backend/migrations/001_user_auth.sql have run."
                )
            print(f"Error creating chat: {e}")
            raise Exception(f"Failed to create chat: {error_msg}")

    async def get_chat(self, client: Client, chat_id: str) -> Optional[ChatResponse]:
        """Get a chat by id. RLS scopes the result to the caller."""
        try:
            result = client.table("chats").select("*").eq("id", chat_id).execute()
            if not result.data:
                return None
            return _chat_row_to_response(result.data[0])
        except Exception as e:
            print(f"Error getting chat: {e}")
            return None

    async def get_chats(self, client: Client, limit: int = 50) -> List[ChatResponse]:
        """List chats. RLS scopes to the caller automatically."""
        try:
            result = (
                client.table("chats")
                .select("*")
                .order("updated_at", desc=True)
                .limit(limit)
                .execute()
            )
            return [_chat_row_to_response(row) for row in result.data]
        except Exception as e:
            print(f"Error getting chats: {e}")
            return []

    async def update_chat_title(self, client: Client, chat_id: str, title: str) -> bool:
        try:
            result = client.table("chats").update({
                "title": title,
                "updated_at": datetime.utcnow().isoformat(),
            }).eq("id", chat_id).execute()
            return bool(result.data)
        except Exception as e:
            print(f"Error updating chat title: {e}")
            return False

    async def delete_chat(self, client: Client, chat_id: str) -> bool:
        """Delete a chat (RLS scopes ownership) and its messages.
        Messages cascade is enforced by their own RLS policy via the
        parent chat, but we delete explicitly for clarity."""
        try:
            messages_result = (
                client.table("messages").delete().eq("chat_id", chat_id).execute()
            )
            print(
                f"Deleted {len(messages_result.data) if messages_result.data else 0} "
                f"messages for chat {chat_id}"
            )
            chat_result = client.table("chats").delete().eq("id", chat_id).execute()
            return bool(chat_result.data)
        except Exception as e:
            error_msg = str(e)
            if "RLS policy" in error_msg or "42501" in error_msg:
                print(f"RLS policy error deleting chat: {e}")
                raise Exception(
                    "Database RLS policy blocking chat deletion. The caller "
                    "may not own this chat."
                )
            print(f"Error deleting chat: {e}")
            raise Exception(f"Failed to delete chat: {error_msg}")

    # ── messages ────────────────────────────────────────────────────

    async def create_message(
        self, client: Client, message_data: MessageCreate
    ) -> MessageResponse:
        try:
            result = client.table("messages").insert({
                "chat_id": message_data.chat_id,
                "role": message_data.role.value,
                "content": message_data.content,
                "message_type": message_data.message_type.value,
                "s3_url": message_data.s3_url,
                "metadata": message_data.metadata,
                "created_at": datetime.utcnow().isoformat(),
            }).execute()

            if not result.data:
                raise Exception("Failed to create message")
            return _message_row_to_response(result.data[0])
        except Exception as e:
            error_msg = str(e)
            if "RLS policy" in error_msg or "42501" in error_msg:
                print(f"RLS policy error creating message: {e}")
                raise Exception(
                    "Database RLS policy blocking message creation. "
                    "The caller may not own the parent chat."
                )
            print(f"Error creating message: {e}")
            raise Exception(f"Failed to create message: {error_msg}")

    async def get_messages(
        self, client: Client, chat_id: str, limit: int = 100
    ) -> List[MessageResponse]:
        try:
            result = (
                client.table("messages")
                .select("*")
                .eq("chat_id", chat_id)
                .order("created_at", desc=False)
                .limit(limit)
                .execute()
            )
            return [_message_row_to_response(row) for row in result.data]
        except Exception as e:
            print(f"Error getting messages: {e}")
            return []

    async def get_chat_with_messages(
        self, client: Client, chat_id: str
    ) -> Optional[ChatWithMessages]:
        try:
            chat = await self.get_chat(client, chat_id)
            if not chat:
                return None
            messages = await self.get_messages(client, chat_id)
            return ChatWithMessages(
                id=chat.id,
                title=chat.title,
                user_id=chat.user_id,
                created_at=chat.created_at,
                updated_at=chat.updated_at,
                messages=messages,
            )
        except Exception as e:
            print(f"Error getting chat with messages: {e}")
            return None


# Global, stateless instance.
database_service = DatabaseService()
