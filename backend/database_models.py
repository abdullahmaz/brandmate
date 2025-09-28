from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from enum import Enum

class MessageRole(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"

class MessageType(str, Enum):
    TEXT = "text"
    IMAGE = "image"
    VIDEO = "video"
    WEBSITE = "website"

class ChatCreate(BaseModel):
    title: Optional[str] = None
    user_id: Optional[str] = None

class ChatResponse(BaseModel):
    id: str
    title: Optional[str]
    user_id: Optional[str]
    created_at: datetime
    updated_at: datetime

class MessageCreate(BaseModel):
    chat_id: str
    role: MessageRole
    content: str
    message_type: MessageType = MessageType.TEXT
    s3_url: Optional[str] = None
    metadata: Optional[dict] = None

class MessageResponse(BaseModel):
    id: str
    chat_id: str
    role: MessageRole
    content: str
    message_type: MessageType
    s3_url: Optional[str]
    metadata: Optional[dict]
    created_at: datetime

class ChatWithMessages(ChatResponse):
    messages: List[MessageResponse] = []

# Alias for Chat (same as ChatResponse)
Chat = ChatResponse
