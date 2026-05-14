from pydantic import BaseModel, Field
from typing import Optional, Literal, Union
from enum import Enum


class Role(str, Enum):
    system = "system"
    user = "user"
    assistant = "assistant"
    tool = "tool"


class ChatMessage(BaseModel):
    role: Role
    content: Optional[Union[str, list]] = None
    name: Optional[str] = None
    tool_calls: Optional[list] = None
    tool_call_id: Optional[str] = None
    reasoning_content: Optional[str] = None


class ChatCompletionRequest(BaseModel):
    model: str = "deepseek-v4-flash"
    messages: list[ChatMessage]
    temperature: Optional[float] = Field(default=1.0, ge=0, le=2)
    top_p: Optional[float] = Field(default=1.0, ge=0, le=1)
    n: Optional[int] = 1
    stream: Optional[bool] = False
    stop: Optional[Union[str, list[str]]] = None
    max_tokens: Optional[int] = None
    presence_penalty: Optional[float] = Field(default=0, ge=-2, le=2)
    frequency_penalty: Optional[float] = Field(default=0, ge=-2, le=2)
    tools: Optional[list] = None
    tool_choice: Optional[Union[str, dict]] = None
    response_format: Optional[dict] = None
    seed: Optional[int] = None
    logprobs: Optional[bool] = None
    top_logprobs: Optional[int] = None


class Usage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class ChoiceMessage(BaseModel):
    role: Role = Role.assistant
    content: Optional[str] = None
    reasoning_content: Optional[str] = None
    tool_calls: Optional[list] = None


class Choice(BaseModel):
    index: int = 0
    message: ChoiceMessage
    finish_reason: Optional[str] = "stop"


class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: list[Choice]
    usage: Usage = Usage()


class DeltaMessage(BaseModel):
    role: Optional[Role] = None
    content: Optional[str] = None
    reasoning_content: Optional[str] = None
    tool_calls: Optional[list] = None


class StreamChoice(BaseModel):
    index: int = 0
    delta: DeltaMessage
    finish_reason: Optional[str] = None


class ChatCompletionStreamResponse(BaseModel):
    id: str
    object: str = "chat.completion.chunk"
    created: int
    model: str
    choices: list[StreamChoice]
    usage: Optional[Usage] = None


class ModelObject(BaseModel):
    id: str
    object: str = "model"
    created: int = 0
    owned_by: str = "atomcode-codingplan"


class ModelListResponse(BaseModel):
    object: str = "list"
    data: list[ModelObject]
