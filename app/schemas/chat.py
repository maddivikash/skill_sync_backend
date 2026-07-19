from typing import List, Literal, Optional

from pydantic import BaseModel, constr


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: constr(min_length=1, max_length=4000)


class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    goal_id: Optional[int] = None  # the goal the user is currently working on


class ChatSuggestion(BaseModel):
    name: str
    category: str


class ChatReply(BaseModel):
    reply: str
    changed: bool = False  # true if the agent modified the user's data (UI should refresh)
    suggestions: List[ChatSuggestion] = []  # selectable chips to render in chat
    goal_id: Optional[int] = None  # goal being built, so the UI can add chips to it
