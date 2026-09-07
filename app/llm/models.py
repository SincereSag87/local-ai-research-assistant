from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ChatRole = Literal["system", "user", "assistant"]


class ChatMessage(BaseModel):
    role: ChatRole
    content: str = Field(min_length=1)


class ChatResponse(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    model: str
    content: str

