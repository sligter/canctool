import httpx
import json
import logging
from typing import Dict, Any, Optional
from .models import ChatCompletionRequest, ChatMessage
from .prompt_engineering import PromptEngineeringService
from .config import Config, ProviderConfig

logger = logging.getLogger(__name__)


class LLMService:

    def __init__(self):
        Config.setup_logging()
        Config.validate_config()

        self.timeout = Config.REQUEST_TIMEOUT
        self.max_retries = Config.MAX_RETRIES
        self.prompt_engineering = PromptEngineeringService()

        # 创建HTTP客户端池，每个提供商一个客户端
        self.clients: Dict[str, httpx.Client] = {}
        self._initialize_clients()

        logger.info(f"LLM service initialized - supporting {len(self.clients)} providers")

    def _initialize_clients(self):
        """初始化所有提供商的HTTP客户端"""
        providers = Config.get_all_providers()
        for provider_name, provider in providers.items():
            self.clients[provider_name] = httpx.Client(
                base_url=provider.base_url,
                timeout=self.timeout
            )
            logger.info(f"Initialized provider client: {provider_name} -> {provider.base_url}")
    
    async def call_llm(self, prompt: str, model: str = "default") -> str:
        """
        调用LLM服务，返回原始文本响应
        支持多提供商和多模型
        """
        # Get provider configuration for the model
        provider = Config.get_provider_for_model(model)
        if not provider:
            raise ValueError(f"No provider configuration found for model {model}")

        # Get corresponding HTTP client
        client = self.clients.get(provider.name)
        if not client:
            raise ValueError(f"No HTTP client found for provider {provider.name}")

        # 构建请求头
        headers = Config.get_provider_headers(provider)

        # 确保prompt是字符串
        prompt = self._ensure_string_prompt(prompt)

        logger.info(f"Calling model: {model}, provider: {provider.name}")
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"Prompt length: {len(prompt)}")

        # Support multiple API formats
        for attempt in range(self.max_retries):
            try:
                if attempt > 0:
                    logger.info(f"Retrying LLM API call (attempt {attempt + 1}/{self.max_retries})")

                # Try OpenAI compatible format
                response = await self._call_openai_compatible(prompt, model, headers, client)
                if response:
                    return response

                if attempt < self.max_retries - 1:
                    logger.warning(f"API call failed, will retry (attempt {attempt + 1}/{self.max_retries})")
                    import asyncio
                    await asyncio.sleep(1)  # Wait 1 second before retry

            except Exception as e:
                logger.error(f"LLM API call exception (attempt {attempt + 1}/{self.max_retries}): {e}")
                if attempt == self.max_retries - 1:
                    raise Exception(f"LLM API call failed after {self.max_retries} retries: {e}")

        raise Exception("LLM API call failed")

    def _ensure_string_prompt(self, prompt: str) -> str:
        """Ensure prompt is string type"""
        if isinstance(prompt, str):
            return prompt

        logger.warning(f"Prompt is not string type, converting: {type(prompt)}")

        if isinstance(prompt, list):
            text_parts = []
            for item in prompt:
                if isinstance(item, dict) and "text" in item:
                    text_parts.append(item["text"])
                elif isinstance(item, str):
                    text_parts.append(item)
                else:
                    text_parts.append(str(item))
            return "\n".join(text_parts)

        return str(prompt)
    
    async def _call_openai_compatible(self, prompt: str, model: str, headers: dict, client: httpx.Client) -> Optional[str]:
        """Try OpenAI compatible format"""
        try:
            payload = {
                "model": model,
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 1000,
                "temperature": 0.7
            }

            logger.debug(f"Calling OpenAI compatible API, prompt length: {len(prompt)}")
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"Request payload: {json.dumps(payload, ensure_ascii=False, indent=2)}")

            response = client.post("/chat/completions", json=payload, headers=headers)
            response.raise_for_status()
            result = response.json()

            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"Response content: {json.dumps(result, ensure_ascii=False, indent=2)}")

            # Parse OpenAI format response
            if "choices" in result and len(result["choices"]) > 0:
                response_content = result["choices"][0].get("message", {}).get("content", "")
                logger.info("OpenAI compatible format call successful")
                return response_content
            else:
                logger.error(f"OpenAI format response error: missing choices field or empty choices")
                return None

        except httpx.HTTPError as e:
            logger.error(f"OpenAI compatible format HTTP error: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response status code: {e.response.status_code}")
                logger.error(f"Response content: {e.response.text}")
                logger.error(f"Request URL: {e.request.url}")
        except Exception as e:
            logger.error(f"OpenAI compatible format call failed: {e}")
            if logger.isEnabledFor(logging.DEBUG):
                import traceback
                logger.debug(f"Error traceback: {traceback.format_exc()}")

        return None
    
    def should_use_tools(self, request: ChatCompletionRequest) -> bool:
        """
        Determine if tools should be used
        """
        return bool(request.tools and len(request.tools) > 0)

    def is_tool_result_request(self, request: ChatCompletionRequest) -> bool:
        """
        Determine if this is a tool result processing request
        """
        for message in reversed(request.messages):
            if message.role == "tool":
                return True
            elif message.role == "assistant" and message.tool_calls:
                # Found tool call but no corresponding tool result
                return False
        return False
    
    def extract_tool_info(self, request: ChatCompletionRequest) -> Optional[Dict[str, Any]]:
        """
        Extract tool call information from request
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
        Extract tool result from request
        """
        for message in reversed(request.messages):
            if message.role == "tool":
                return message.content
        return None
    
    async def handle_unified_request(self, request: ChatCompletionRequest) -> str:
        """
        Unified request processing method, automatically identifies request type and calls appropriate processing logic
        """
        # Check if this is a tool result processing request
        if self.is_tool_result_request(request):
            tool_result = self.extract_tool_result(request)
            if tool_result is None:
                return "Tool result not found"

            # Use unified prompt building method
            prompt = self.prompt_engineering.build_unified_tool_prompt(
                request.messages, request.tools, tool_result
            )
            logger.info("Processing tool result request")

        # Check if tools should be used
        elif self.should_use_tools(request):
            # Use unified prompt building method
            prompt = self.prompt_engineering.build_unified_tool_prompt(
                request.messages, request.tools
            )
            logger.info("Processing tool call request")
        
        # Regular request
        else:
            # Build conversation history prompt, preserving complete information, prioritizing recent messages
            conversation = []

            # Build from most recent conversations, maintaining priority but preserving complete information
            for msg in reversed(request.messages):
                content = self.prompt_engineering._ensure_string_content(msg.content)
                line = f"User: {content}" if msg.role == "user" else f"Assistant: {content}"
                conversation.insert(0, line)  # Insert at beginning to maintain order

            prompt = "\n".join(conversation) + "\nAssistant: "
            logger.info(f"Processing regular request, final prompt length: {len(prompt)}")
        
        return await self.call_llm(prompt, request.model)
    
    # 保持向后兼容的方法
    async def handle_tool_call_request(self, request: ChatCompletionRequest) -> str:
        return await self.handle_unified_request(request)
    
    async def handle_tool_result_request(self, request: ChatCompletionRequest) -> str:
        return await self.handle_unified_request(request)
    
    async def handle_regular_request(self, request: ChatCompletionRequest) -> str:
        return await self.handle_unified_request(request)