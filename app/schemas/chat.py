from typing import List, Literal

from pydantic import BaseModel, constr


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: constr(min_length=1, max_length=4000)


class ChatRequest(BaseModel):
    messages: List[ChatMessage]


class ChatReply(BaseModel):
    reply: str
