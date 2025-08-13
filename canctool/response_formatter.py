import json
import uuid
import time
from datetime import datetime
from typing import Dict, Any, Optional
from .models import (
    ChatCompletionRequest, ChatCompletionResponse, ChatCompletionStreamResponse,
    ToolCall, Choice, Usage, ChatMessage, StreamChoice
)
from .prompt_engineering import PromptEngineeringService


class ResponseFormatter:
    
    def __init__(self):
        self.prompt_engineering = PromptEngineeringService()
    
    def format_unified_response(self,
                           request: ChatCompletionRequest,
                           llm_response: str,
                           prompt_tokens: int = 0,
                           completion_tokens: int = 0,
                           check_tool_calls: bool = True) -> ChatCompletionResponse:
        """
        统一的响应格式化方法，自动检测工具调用并格式化响应
        """
        tool_call_data = None
        clean_content = llm_response
        
        if check_tool_calls:
            tool_call_data = self.prompt_engineering.parse_tool_call(llm_response)
            clean_content = self.prompt_engineering.extract_clean_response(llm_response)
        
        if tool_call_data:
            # 创建工具调用对象
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
            # 普通文本响应
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
            created=int(time.time()),
            model=request.model,
            choices=[choice],
            usage=usage
        )
    
    # 保持向后兼容的方法
    def format_tool_call_response(self, 
                                request: ChatCompletionRequest, 
                                llm_response: str,
                                prompt_tokens: int = 0,
                                completion_tokens: int = 0) -> ChatCompletionResponse:
        return self.format_unified_response(request, llm_response, prompt_tokens, completion_tokens, True)
    
    def format_regular_response(self,
                              request: ChatCompletionRequest,
                              llm_response: str,
                              prompt_tokens: int = 0,
                              completion_tokens: int = 0) -> ChatCompletionResponse:
        return self.format_unified_response(request, llm_response, prompt_tokens, completion_tokens, False)
    
    def format_tool_result_response(self,
                                  request: ChatCompletionRequest,
                                  llm_response: str,
                                  prompt_tokens: int = 0,
                                  completion_tokens: int = 0) -> ChatCompletionResponse:
        return self.format_unified_response(request, llm_response, prompt_tokens, completion_tokens, True)

    def format_stream_chunk(self, request: ChatCompletionRequest, content: str,
                           finish_reason: Optional[str] = None) -> ChatCompletionStreamResponse:
        """Format streaming response chunk"""
        response_id = f"chatcmpl-{uuid.uuid4().hex[:29]}"

        # Create delta message
        delta = ChatMessage(role="assistant", content=content)

        choice = StreamChoice(
            index=0,
            delta=delta,
            finish_reason=finish_reason
        )

        response = ChatCompletionStreamResponse(
            id=response_id,
            created=int(time.time()),
            model=request.model,
            choices=[choice]
        )

        return response

    def format_stream_end_chunk(self, request: ChatCompletionRequest,
                               prompt_tokens: int = 0,
                               completion_tokens: int = 0) -> ChatCompletionStreamResponse:
        """Format final streaming chunk with token usage information"""
        response_id = f"chatcmpl-{uuid.uuid4().hex[:29]}"

        # Empty delta for final chunk
        delta = ChatMessage(role="assistant", content="")

        choice = StreamChoice(
            index=0,
            delta=delta,
            finish_reason="stop"
        )

        # Include usage information in the final chunk
        usage = Usage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens
        )

        response = ChatCompletionStreamResponse(
            id=response_id,
            created=int(time.time()),
            model=request.model,
            choices=[choice],
            usage=usage
        )

        return response