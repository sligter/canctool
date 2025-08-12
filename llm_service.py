import httpx
import json
import logging
from typing import Dict, Any, Optional
from models import ChatCompletionRequest, ChatMessage
from prompt_engineering import PromptEngineeringService
from config import Config

logger = logging.getLogger(__name__)


class LLMService:
    
    def __init__(self):
        Config.setup_logging()
        Config.validate_config()
        
        self.base_url = Config.LLM_API_BASE_URL
        self.api_key = Config.LLM_API_KEY
        self.default_model = Config.DEFAULT_MODEL_NAME
        self.timeout = Config.REQUEST_TIMEOUT
        self.max_retries = Config.MAX_RETRIES
        
        self.prompt_engineering = PromptEngineeringService()
        self.client = httpx.Client(
            base_url=self.base_url.rstrip('/'),
            timeout=self.timeout
        )
        
        logger.info(f"LLM服务初始化完成 - Base URL: {self.base_url}, Default Model: {self.default_model}")
    
    async def call_llm(self, prompt: str, model: str = "default") -> str:
        """
        调用LLM服务，返回原始文本响应
        支持多种LLM API格式
        """
        # 使用默认模型如果未指定
        if model == "default":
            model = self.default_model
        
        # 构建请求头
        headers = Config.get_llm_headers()
        
        # 支持多种API格式
        for attempt in range(self.max_retries):
            try:
                logger.debug(f"调用LLM API (尝试 {attempt + 1}/{self.max_retries}) - Model: {model}")
                
                # 尝试OpenAI兼容格式
                response = await self._call_openai_compatible(prompt, model, headers)
                if response:
                    return response
                
                # 尝试通用生成格式
                response = await self._call_generic_format(prompt, model, headers)
                if response:
                    return response
                
                logger.warning(f"所有API格式都失败了 (尝试 {attempt + 1}/{self.max_retries})")
                if attempt < self.max_retries - 1:
                    import asyncio
                    await asyncio.sleep(1)  # 等待1秒后重试
                
            except Exception as e:
                logger.error(f"LLM API调用失败 (尝试 {attempt + 1}/{self.max_retries}): {e}")
                if attempt == self.max_retries - 1:
                    raise Exception(f"LLM API调用失败，已重试{self.max_retries}次: {e}")
        
        raise Exception("LLM API调用失败")
    
    async def _call_openai_compatible(self, prompt: str, model: str, headers: dict) -> Optional[str]:
        """尝试OpenAI兼容格式"""
        try:
            payload = {
                "model": model,
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 1000,
                "temperature": 0.7
            }
            
            response = self.client.post("/chat/completions", json=payload, headers=headers)
            response.raise_for_status()
            result = response.json()
            
            # 解析OpenAI格式响应
            if "choices" in result and len(result["choices"]) > 0:
                content = result["choices"][0].get("message", {}).get("content", "")
                logger.debug("OpenAI兼容格式调用成功")
                return content
            
        except Exception as e:
            logger.debug(f"OpenAI兼容格式调用失败: {e}")
        
        return None
    
    async def _call_generic_format(self, prompt: str, model: str, headers: dict) -> Optional[str]:
        """尝试通用生成格式"""
        try:
            payload = {
                "model": model,
                "prompt": prompt,
                "max_tokens": 1000,
                "temperature": 0.7
            }
            
            response = self.client.post("/generate", json=payload, headers=headers)
            response.raise_for_status()
            result = response.json()
            
            # 解析通用格式响应
            if "response" in result:
                logger.debug("通用格式调用成功")
                return result["response"]
            elif "text" in result:
                logger.debug("通用格式调用成功 (text字段)")
                return result["text"]
            elif "content" in result:
                logger.debug("通用格式调用成功 (content字段)")
                return result["content"]
            elif isinstance(result, str):
                logger.debug("通用格式调用成功 (直接返回字符串)")
                return result
            
        except Exception as e:
            logger.debug(f"通用格式调用失败: {e}")
        
        return None
    
    def should_use_tools(self, request: ChatCompletionRequest) -> bool:
        """
        判断是否需要使用工具
        """
        return bool(request.tools and len(request.tools) > 0)
    
    def is_tool_result_request(self, request: ChatCompletionRequest) -> bool:
        """
        判断是否是工具结果处理请求
        """
        for message in reversed(request.messages):
            if message.role == "tool":
                return True
            elif message.role == "assistant" and message.tool_calls:
                # 找到工具调用但没有对应的工具结果
                return False
        return False
    
    def extract_tool_info(self, request: ChatCompletionRequest) -> Optional[Dict[str, Any]]:
        """
        从请求中提取工具调用信息
        """
        for message in reversed(request.messages):
            if message.role == "assistant" and message.tool_calls:
                tool_call = message.tool_calls[0]
                return {
                    "tool_name": tool_call["function"]["name"],
                    "arguments": tool_call["function"]["arguments"],
                    "tool_call_id": tool_call["id"]
                }
        return None
    
    def extract_tool_result(self, request: ChatCompletionRequest) -> Optional[str]:
        """
        从请求中提取工具结果
        """
        for message in reversed(request.messages):
            if message.role == "tool":
                return message.content
        return None
    
    async def handle_tool_call_request(self, request: ChatCompletionRequest) -> str:
        """
        处理工具调用请求
        """
        prompt = self.prompt_engineering.build_tool_call_prompt(
            request.messages, request.tools
        )
        return await self.call_llm(prompt, request.model)
    
    async def handle_tool_result_request(self, request: ChatCompletionRequest) -> str:
        """
        处理工具结果请求，支持在工具结果后可能还需要调用其他工具
        """
        tool_result = self.extract_tool_result(request)
        tool_call_id = ""
        
        # 找到对应的工具调用ID
        for message in reversed(request.messages):
            if message.role == "assistant" and message.tool_calls:
                tool_call_id = message.tool_calls[0]["id"]
                break
        
        if tool_result is None:
            return "未找到工具结果"
        
        prompt = self.prompt_engineering.build_tool_result_prompt(
            request.messages, tool_result, tool_call_id, request.tools
        )
        return await self.call_llm(prompt, request.model)
    
    async def handle_regular_request(self, request: ChatCompletionRequest) -> str:
        """
        处理普通请求
        """
        # 构建对话历史提示
        conversation = []
        for msg in request.messages:
            if msg.role == "user":
                conversation.append(f"用户: {msg.content}")
            elif msg.role == "assistant":
                conversation.append(f"助手: {msg.content}")
        
        prompt = "\n".join(conversation) + "\n助手: "
        return await self.call_llm(prompt, request.model)