from typing import List, Optional
from datetime import datetime
import re
from .supabase_client import supabase_client
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
    Parse ISO timestamp strings coming back from Supabase in a way that is
    robust across Python versions and minor format differences.

    Examples of values we've seen:
      - "2025-12-10T10:55:07.08128+00:00"
      - "2025-12-10T10:55:07.081280Z"
      - "2025-12-10T10:55:07.081280"
    
    Python < 3.13 requires exactly 6 digits for microseconds, so we normalize them.
    """
    # Normalize trailing "Z" to "+00:00" (UTC) if present
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"

    # Extract timezone if present
    timezone = ""
    tz_separators = ["+", "-"]
    for sep in tz_separators:
        idx = value.find(sep, 10)
        if idx != -1:
            timezone = value[idx:]
            value = value[:idx]
            break

    # Normalize microseconds to exactly 6 digits (pad or truncate)
    # Pattern: matches .{1-9 digits} after seconds
    pattern = r'\.(\d+)$'
    match = re.search(pattern, value)
    
    if match:
        microseconds = match.group(1)
        # Pad to 6 digits or truncate to 6 digits
        if len(microseconds) < 6:
            microseconds = microseconds.ljust(6, '0')
        elif len(microseconds) > 6:
            microseconds = microseconds[:6]
        value = value[:match.start()] + f'.{microseconds}'

    return datetime.fromisoformat(value + timezone)


class DatabaseService:
    def __init__(self):
        try:
            self.client = supabase_client.get_client()
        except Exception as e:
            print(f"Database service not available: {e}")
            self.client = None
    
    async def create_chat(self, chat_data: ChatCreate) -> ChatResponse:
        """Create a new chat"""
        if not self.client:
            raise Exception("Database not available")
            
        try:
            result = self.client.table("chats").insert({
                "title": chat_data.title,
                "user_id": chat_data.user_id,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }).execute()
            
            if result.data:
                chat = result.data[0]
                return ChatResponse(
                    id=chat["id"],
                    title=chat["title"],
                    user_id=chat["user_id"],
                    created_at=_parse_db_timestamp(chat["created_at"]),
                    updated_at=_parse_db_timestamp(chat["updated_at"]),
                )
            else:
                raise Exception("Failed to create chat")
                
        except Exception as e:
            error_msg = str(e)
            if "RLS policy" in error_msg or "42501" in error_msg:
                print(f"RLS policy error creating chat: {e}")
                raise Exception("Database RLS policy blocking chat creation. Please check your Supabase RLS settings.")
            else:
                print(f"Error creating chat: {e}")
                raise Exception(f"Failed to create chat: {error_msg}")
    
    async def get_chat(self, chat_id: str) -> Optional[ChatResponse]:
        """Get a chat by ID"""
        try:
            result = self.client.table("chats").select("*").eq("id", chat_id).execute()
            
            if result.data:
                chat = result.data[0]
                return ChatResponse(
                    id=chat["id"],
                    title=chat["title"],
                    user_id=chat["user_id"],
                    created_at=_parse_db_timestamp(chat["created_at"]),
                    updated_at=_parse_db_timestamp(chat["updated_at"]),
                )
            return None
            
        except Exception as e:
            print(f"Error getting chat: {e}")
            return None
    
    async def get_chats(self, user_id: Optional[str] = None, limit: int = 50) -> List[ChatResponse]:
        """Get all chats, optionally filtered by user_id"""
        if not self.client:
            print("Database not available, returning empty chat list")
            return []
            
        try:
            query = self.client.table("chats").select("*").order("updated_at", desc=True).limit(limit)
            
            if user_id:
                query = query.eq("user_id", user_id)
            
            result = query.execute()
            
            chats = []
            for chat in result.data:
                chats.append(
                    ChatResponse(
                        id=chat["id"],
                        title=chat["title"],
                        user_id=chat["user_id"],
                        created_at=_parse_db_timestamp(chat["created_at"]),
                        updated_at=_parse_db_timestamp(chat["updated_at"]),
                    )
                )
            
            return chats
            
        except Exception as e:
            print(f"Error getting chats: {e}")
            return []
    
    async def create_message(self, message_data: MessageCreate) -> MessageResponse:
        """Create a new message"""
        if not self.client:
            raise Exception("Database not available")
            
        try:
            result = self.client.table("messages").insert({
                "chat_id": message_data.chat_id,
                "role": message_data.role.value,
                "content": message_data.content,
                "message_type": message_data.message_type.value,
                "s3_url": message_data.s3_url,
                "metadata": message_data.metadata,
                "created_at": datetime.utcnow().isoformat()
            }).execute()
            
            if result.data:
                message = result.data[0]
                return MessageResponse(
                    id=message["id"],
                    chat_id=message["chat_id"],
                    role=MessageRole(message["role"]),
                    content=message["content"],
                    message_type=MessageType(message["message_type"]),
                    s3_url=message["s3_url"],
                    metadata=message["metadata"],
                    created_at=_parse_db_timestamp(message["created_at"]),
                )
            else:
                raise Exception("Failed to create message")
                
        except Exception as e:
            error_msg = str(e)
            if "RLS policy" in error_msg or "42501" in error_msg:
                print(f"RLS policy error creating message: {e}")
                raise Exception("Database RLS policy blocking message creation. Please check your Supabase RLS settings.")
            else:
                print(f"Error creating message: {e}")
                raise Exception(f"Failed to create message: {error_msg}")
    
    async def get_messages(self, chat_id: str, limit: int = 100) -> List[MessageResponse]:
        """Get messages for a chat"""
        try:
            result = (
                self.client.table("messages")
                .select("*")
                .eq("chat_id", chat_id)
                .order("created_at", desc=False)
                .limit(limit)
                .execute()
            )
            
            messages = []
            for message in result.data:
                messages.append(
                    MessageResponse(
                        id=message["id"],
                        chat_id=message["chat_id"],
                        role=MessageRole(message["role"]),
                        content=message["content"],
                        message_type=MessageType(message["message_type"]),
                        s3_url=message["s3_url"],
                        metadata=message["metadata"],
                        created_at=_parse_db_timestamp(message["created_at"]),
                    )
                )
            
            return messages
            
        except Exception as e:
            print(f"Error getting messages: {e}")
            return []
    
    async def get_chat_with_messages(self, chat_id: str) -> Optional[ChatWithMessages]:
        """Get a chat with all its messages"""
        try:
            chat = await self.get_chat(chat_id)
            if not chat:
                return None
            
            messages = await self.get_messages(chat_id)
            
            return ChatWithMessages(
                id=chat.id,
                title=chat.title,
                user_id=chat.user_id,
                created_at=chat.created_at,
                updated_at=chat.updated_at,
                messages=messages
            )
            
        except Exception as e:
            print(f"Error getting chat with messages: {e}")
            return None
    
    async def update_chat_title(self, chat_id: str, title: str) -> bool:
        """Update chat title"""
        try:
            result = self.client.table("chats").update({
                "title": title,
                "updated_at": datetime.utcnow().isoformat()
            }).eq("id", chat_id).execute()
            
            return bool(result.data)
            
        except Exception as e:
            print(f"Error updating chat title: {e}")
            return False
    
    async def delete_chat(self, chat_id: str) -> bool:
        """Delete a chat and all its messages"""
        if not self.client:
            raise Exception("Database not available")
            
        try:
            # First delete all messages for this chat
            messages_result = self.client.table("messages").delete().eq("chat_id", chat_id).execute()
            print(f"Deleted {len(messages_result.data) if messages_result.data else 0} messages for chat {chat_id}")
            
            # Then delete the chat itself
            chat_result = self.client.table("chats").delete().eq("id", chat_id).execute()
            
            return bool(chat_result.data)
            
        except Exception as e:
            error_msg = str(e)
            if "RLS policy" in error_msg or "42501" in error_msg:
                print(f"RLS policy error deleting chat: {e}")
                raise Exception("Database RLS policy blocking chat deletion. Please check your Supabase RLS settings.")
            else:
                print(f"Error deleting chat: {e}")
                raise Exception(f"Failed to delete chat: {error_msg}")

# Global instance
database_service = DatabaseService()
