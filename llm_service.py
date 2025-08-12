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
        
        # 添加详细的调试信息
        logger.debug(f"原始prompt类型: {type(prompt)}")
        logger.debug(f"原始prompt长度: {len(str(prompt))}")
        
        # 确保prompt是字符串
        if not isinstance(prompt, str):
            logger.warning(f"prompt不是字符串类型，正在转换: {type(prompt)}")
            if isinstance(prompt, list) or isinstance(prompt, dict):
                # 如果是复杂对象，尝试提取文本内容
                logger.error(f"prompt是复杂对象: {prompt}")
                # 尝试提取文本内容
                if isinstance(prompt, list):
                    text_parts = []
                    for item in prompt:
                        if isinstance(item, dict) and "text" in item:
                            text_parts.append(item["text"])
                        elif isinstance(item, str):
                            text_parts.append(item)
                    prompt = "\n".join(text_parts)
                else:
                    prompt = str(prompt)
            else:
                prompt = str(prompt)
        
        # 再次检查prompt是否为字符串
        if not isinstance(prompt, str):
            logger.error(f"转换后prompt仍然不是字符串: {type(prompt)}")
            prompt = str(prompt)
        
        logger.debug(f"最终prompt类型: {type(prompt)}")
        logger.debug(f"最终prompt长度: {len(prompt)}")
        
        # 支持多种API格式
        for attempt in range(self.max_retries):
            try:
                logger.debug(f"调用LLM API (尝试 {attempt + 1}/{self.max_retries}) - Model: {model}")
                
                # 尝试OpenAI兼容格式
                response = await self._call_openai_compatible(prompt, model, headers)
                if response:
                    return response
                
                # 如果OpenAI兼容格式失败，直接报错，不再尝试通用格式
                logger.warning(f"OpenAI兼容格式调用失败 (尝试 {attempt + 1}/{self.max_retries})")
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
            import json
            # 确保prompt是字符串
            if isinstance(prompt, str):
                content = prompt
            else:
                content = str(prompt)
            
            payload = {
                "model": model,
                "messages": [
                    {"role": "user", "content": content}
                ],
                "max_tokens": 1000,
                "temperature": 0.7
            }
            
            logger.debug(f"调用OpenAI兼容API，prompt长度: {len(content)}")
            logger.debug(f"请求体内容: {json.dumps(payload, ensure_ascii=False, indent=2)}")
            
            response = self.client.post("/chat/completions", json=payload, headers=headers)
            response.raise_for_status()
            result = response.json()
            
            logger.debug(f"响应内容: {json.dumps(result, ensure_ascii=False, indent=2)}")
            
            # 解析OpenAI格式响应
            if "choices" in result and len(result["choices"]) > 0:
                response_content = result["choices"][0].get("message", {}).get("content", "")
                logger.debug("OpenAI兼容格式调用成功")
                return response_content
            else:
                logger.error(f"OpenAI格式响应异常: 不包含choices字段或choices为空")
                return None
            
        except httpx.HTTPError as e:
            logger.error(f"OpenAI兼容格式HTTP错误: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"响应状态码: {e.response.status_code}")
                logger.error(f"响应内容: {e.response.text}")
                logger.error(f"请求URL: {e.request.url}")
        except Exception as e:
            logger.error(f"OpenAI兼容格式调用失败: {e}")
            import traceback
            logger.error(f"错误堆栈: {traceback.format_exc()}")
        
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
    
    async def handle_unified_request(self, request: ChatCompletionRequest) -> str:
        """
        统一的请求处理方法，自动识别请求类型并调用相应的处理逻辑
        """
        # 检查是否是工具结果处理请求
        if self.is_tool_result_request(request):
            tool_result = self.extract_tool_result(request)
            if tool_result is None:
                return "未找到工具结果"
            
            # 使用统一的提示词构建方法
            prompt = self.prompt_engineering.build_unified_tool_prompt(
                request.messages, request.tools, tool_result
            )
            logger.info("处理工具结果请求")
        
        # 检查是否需要使用工具
        elif self.should_use_tools(request):
            # 使用统一的提示词构建方法
            prompt = self.prompt_engineering.build_unified_tool_prompt(
                request.messages, request.tools
            )
            logger.info("处理工具调用请求")
        
        # 普通请求
        else:
            # 构建对话历史提示，保留完整信息，优先保留最近的消息
            conversation = []
            
            # 从最近的对话开始构建，保持优先级但保留完整信息
            for msg in reversed(request.messages):
                content = self.prompt_engineering._ensure_string_content(msg.content)
                line = f"用户: {content}" if msg.role == "user" else f"助手: {content}"
                conversation.insert(0, line)  # 插入到开头以保持顺序
            
            prompt = "\n".join(conversation) + "\n助手: "
            logger.info(f"处理普通请求，最终提示词长度: {len(prompt)}")
        
        return await self.call_llm(prompt, request.model)
    
    # 保持向后兼容的方法
    async def handle_tool_call_request(self, request: ChatCompletionRequest) -> str:
        return await self.handle_unified_request(request)
    
    async def handle_tool_result_request(self, request: ChatCompletionRequest) -> str:
        return await self.handle_unified_request(request)
    
    async def handle_regular_request(self, request: ChatCompletionRequest) -> str:
        return await self.handle_unified_request(request)