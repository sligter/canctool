import json
import uuid
from datetime import datetime
from typing import Dict, Any, Optional
from models import ChatCompletionRequest, ChatCompletionResponse, ToolCall, Choice, Usage, ChatMessage
from prompt_engineering import PromptEngineeringService


class ResponseFormatter:
    
    def __init__(self):
        self.prompt_engineering = PromptEngineeringService()
    
    def format_tool_call_response(self, 
                                request: ChatCompletionRequest, 
                                llm_response: str,
                                prompt_tokens: int = 0,
                                completion_tokens: int = 0) -> ChatCompletionResponse:
        
        tool_call_data = self.prompt_engineering.parse_tool_call(llm_response)
        clean_content = self.prompt_engineering.extract_clean_response(llm_response)
        
        if tool_call_data:
            tool_call = ToolCall(
                id=str(uuid.uuid4()),
                type="function",
                function={
                    "name": tool_call_data["tool_name"],
                    "arguments": json.dumps(tool_call_data["arguments"], ensure_ascii=False)
                }
            )
            message = ChatMessage(
                role="assistant",
                content="",
                tool_calls=[tool_call.dict()]
            )
            finish_reason = "tool_calls"
        else:
            message = ChatMessage(
                role="assistant",
                content=clean_content
            )
            finish_reason = "stop"
        
        choice = Choice(
            index=0,
            message=message,
            finish_reason=finish_reason
        )
        
        usage = Usage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens
        )
        
        return ChatCompletionResponse(
            id=f"chatcmpl-{str(uuid.uuid4()).replace('-', '')[:24]}",
            object="chat.completion",
            created=int(datetime.now().timestamp()),
            model=request.model,
            choices=[choice],
            usage=usage
        )
    
    def format_regular_response(self,
                              request: ChatCompletionRequest,
                              llm_response: str,
                              prompt_tokens: int = 0,
                              completion_tokens: int = 0) -> ChatCompletionResponse:
        
        message = ChatMessage(
            role="assistant",
            content=llm_response
        )
        
        choice = Choice(
            index=0,
            message=message,
            finish_reason="stop"
        )
        
        usage = Usage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens
        )
        
        return ChatCompletionResponse(
            id=f"chatcmpl-{str(uuid.uuid4()).replace('-', '')[:24]}",
            object="chat.completion",
            created=int(datetime.now().timestamp()),
            model=request.model,
            choices=[choice],
            usage=usage
        )
    
    def format_tool_result_response(self,
                                  request: ChatCompletionRequest,
                                  llm_response: str,
                                  prompt_tokens: int = 0,
                                  completion_tokens: int = 0) -> ChatCompletionResponse:
        
        # 检查工具结果响应中是否包含新的工具调用
        tool_call_data = self.prompt_engineering.parse_tool_call(llm_response)
        clean_content = self.prompt_engineering.extract_clean_response(llm_response)
        
        if tool_call_data:
            # 在处理工具结果后，LLM决定调用另一个工具
            tool_call = ToolCall(
                id=str(uuid.uuid4()),
                type="function",
                function={
                    "name": tool_call_data["tool_name"],
                    "arguments": json.dumps(tool_call_data["arguments"], ensure_ascii=False)
                }
            )
            message = ChatMessage(
                role="assistant",
                content="",
                tool_calls=[tool_call.dict()]
            )
            finish_reason = "tool_calls"
        else:
            # 直接回答用户，不再调用工具
            message = ChatMessage(
                role="assistant",
                content=clean_content
            )
            finish_reason = "stop"
        
        choice = Choice(
            index=0,
            message=message,
            finish_reason=finish_reason
        )
        
        usage = Usage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens
        )
        
        return ChatCompletionResponse(
            id=f"chatcmpl-{str(uuid.uuid4()).replace('-', '')[:24]}",
            object="chat.completion",
            created=int(datetime.now().timestamp()),
            model=request.model,
            choices=[choice],
            usage=usage
        )