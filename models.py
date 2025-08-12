from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import uuid
import json


class ChatMessage(BaseModel):
    role: str
    content: str
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_call_id: Optional[str] = None


class FunctionParameter(BaseModel):
    description: Optional[str] = None
    type: str = "string"
    enum: Optional[List[str]] = None
    default: Optional[Any] = None


class FunctionParameters(BaseModel):
    type: str = "object"
    properties: Dict[str, FunctionParameter] = {}
    required: List[str] = []


class FunctionDefinition(BaseModel):
    name: str
    description: str
    parameters: FunctionParameters


class Tool(BaseModel):
    type: str = "function"
    function: FunctionDefinition


class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[ChatMessage]
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 1000
    tools: Optional[List[Tool]] = None
    tool_choice: Optional[str] = "auto"


class ToolCall(BaseModel):
    id: str
    type: str = "function"
    function: Dict[str, str]


class Choice(BaseModel):
    index: int = 0
    message: ChatMessage
    finish_reason: str


class Usage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[Choice]
    usage: Usage