import json
import re
from typing import Dict, Any, List, Optional
from datetime import datetime
from .models import Tool, ChatMessage
from .config import Config


class PromptEngineeringService:

    def __init__(self, max_prompt_length: int = None):
        """
        初始化提示词工程服务

        Args:
            max_prompt_length: 最大提示词长度，默认200K字符
        """
        self.max_prompt_length = max_prompt_length or Config.MAX_PROMPT_LENGTH
        self.tool_call_prompt = self._create_tool_call_prompt_template()
    
    def _create_tool_call_prompt_template(self) -> str:
        return """
你是一个智能助手，必须优先使用工具来回答用户问题。只有在工具调用无法满足用户需求时，才提供直接答案。

可用工具：
{tools}

工具调用格式：
当你需要调用工具时，必须在回复中包含以下格式：
```
TOOL_CALL: {{"tool_name": "工具名称", "arguments": {{"参数名": "参数值"}}}}
```

如果不需要工具，请直接回答用户问题。

参数要求：
- tool_name: 必须是上述可用工具列表中的一个
- arguments: 必须是符合工具定义的JSON对象，包含所有必需参数

当前对话：
{conversation_history}

用户最新消息：
{user_message}

请分析用户需求。如果需要调用工具，请按上述格式返回工具调用信息。如果不需要工具，请直接回答。
"""
    
    def _tools_to_string(self, tools: List[Tool]) -> str:
        tools_str = ""
        for tool in tools:
            func = tool.function
            tools_str += f"\n工具名称: {func.name}\n"
            tools_str += f"描述: {func.description}\n"
            tools_str += f"参数:\n"

            if func.parameters.properties:
                for param_name, param_info in func.parameters.properties.items():
                    required = param_name in func.parameters.required
                    tools_str += f"  - {param_name} ({param_info.type})"
                    if required:
                        tools_str += " (必需)"
                    else:
                        tools_str += f" (可选, 默认值: {param_info.default})"
                    if param_info.enum:
                        tools_str += f", 允许的值: {param_info.enum}"
                    tools_str += f"\n    描述: {param_info.description}\n"
            else:
                tools_str += "  无参数\n"
            tools_str += "\n"

        return tools_str
    
    def _format_conversation_history(self, messages: List[ChatMessage]) -> str:
        """格式化对话历史，控制在最大消息数量内"""
        conversation = []

        # 处理消息，构建对话历史
        for msg in messages:
            content = self._ensure_string_content(msg.content)

            if msg.role == "user":
                line = f"用户: {content}"
            elif msg.role == "assistant":
                if msg.tool_calls:
                    # 简化工具调用信息显示
                    tool_calls_info = []
                    for tool_call in msg.tool_calls:
                        tool_name = tool_call['function']['name']
                        tool_calls_info.append(f"调用工具 {tool_name}")
                    line = f"助手: {'; '.join(tool_calls_info)}"
                elif msg.content:
                    line = f"助手: {content}"
                else:
                    continue  # Skip empty messages
            elif msg.role == "tool":
                line = f"工具结果: {content}"
            else:
                continue  # Skip other roles

            conversation.append(line)

        return "\n".join(conversation)
    
    def _ensure_string_content(self, content) -> str:
        """确保内容是字符串类型"""
        if content is None:
            return ""
        
        if isinstance(content, str):
            return content
        
        # 如果是复杂对象，尝试提取文本内容
        if isinstance(content, list):
            text_parts = []
            for item in content:
                if isinstance(item, dict) and "text" in item:
                    text_parts.append(item["text"])
                elif isinstance(item, str):
                    text_parts.append(item)
                else:
                    text_parts.append(str(item))
            return "\n".join(text_parts)
        
        if isinstance(content, dict):
            if "text" in content:
                return content["text"]
            # 尝试将dict转换为字符串
            return str(content)
        
        # 其他类型直接转换为字符串
        return str(content)

    def _calculate_prompt_length(self, messages: List[ChatMessage], tools: Optional[List[Tool]] = None, tool_result: Optional[str] = None) -> int:
        """计算给定消息和工具信息的提示词长度"""
        # 计算基础模板长度
        base_template_length = 500  # 估算基础模板长度

        # 计算工具信息长度
        tools_length = 0
        if tools:
            tools_info = self._tools_to_string(tools)
            tools_length = len(tools_info)

        # 计算工具结果长度
        tool_result_length = 0
        if tool_result:
            tool_result_length = len(str(tool_result)) + 100  # 加上模板文字

        # 计算消息长度
        messages_length = 0
        for msg in messages:
            content = self._ensure_string_content(msg.content)
            messages_length += len(content) + 50  # 加上角色标签等

        return base_template_length + tools_length + tool_result_length + messages_length

    def _trim_messages_to_fit(self, messages: List[ChatMessage], tools: Optional[List[Tool]] = None, tool_result: Optional[str] = None) -> List[ChatMessage]:
        """自动删减历史消息以适应长度限制"""
        if not messages:
            return messages

        # 如果当前长度在限制内，直接返回
        current_length = self._calculate_prompt_length(messages, tools, tool_result)
        if current_length <= self.max_prompt_length:
            return messages

        # 从前往后删减消息，直到长度符合要求
        trimmed_messages = messages[:]

        while len(trimmed_messages) > 1:  # 至少保留最后一条消息
            # 删除最老的消息
            trimmed_messages = trimmed_messages[1:]

            # 重新计算长度
            new_length = self._calculate_prompt_length(trimmed_messages, tools, tool_result)
            if new_length <= self.max_prompt_length:
                break

        return trimmed_messages
    
    def build_unified_tool_prompt(self, messages: List[ChatMessage], tools: Optional[List[Tool]] = None, tool_result: Optional[str] = None) -> str:
        """
        统一工具调用提示词构建方法，设置提示词长度上限200K，超过则自动删减历史消息
        """
        # 自动删减消息以适应长度限制
        trimmed_messages = self._trim_messages_to_fit(messages, tools, tool_result)

        # 获取最新用户消息
        user_message = self._ensure_string_content(trimmed_messages[-1].content)

        # 构建对话历史（排除最后一条用户消息）
        conversation_history = self._format_conversation_history(trimmed_messages[:-1])

        # Build tool information
        tools_info = ""
        if tools:
            tools_info = f"""
可用工具：
{self._tools_to_string(tools)}

工具调用格式：
当你需要调用工具时，必须在回复中包含以下格式：
```
TOOL_CALL: {{"tool_name": "工具名称", "arguments": {{"参数名": "参数值"}}}}
```

参数要求：
- tool_name: 必须是上述可用工具列表中的一个
- arguments: 必须是符合工具定义的JSON对象，包含所有必需参数
"""

        # Build tool result information (if any) - 保持工具结果完整
        tool_result_info = ""
        if tool_result:
            result_content = self._ensure_string_content(tool_result)
            tool_result_info = f"""
上次工具调用结果：
{result_content}

基于上述结果，请决定是否需要调用更多工具或直接回答用户问题。
"""

        # 构建提示词模板 - 包含最新10条消息的对话历史
        if conversation_history:
            unified_prompt = f"""你是一个智能助手，必须优先使用工具来回答用户问题。只有在工具调用无法满足用户需求时，才提供直接答案。

{tools_info}
{tool_result_info}
当前对话：
{conversation_history}

用户最新消息：
{user_message}

请分析用户需求。如果需要调用工具，请按上述格式返回工具调用信息。如果不需要工具，请直接回答。"""
        else:
            # 如果没有对话历史，使用简化模板
            unified_prompt = f"""你是一个智能助手，必须优先使用工具来回答用户问题。只有在工具调用无法满足用户需求时，才提供直接答案。

{tools_info}
{tool_result_info}
用户消息：
{user_message}

请分析用户需求。如果需要调用工具，请按上述格式返回工具调用信息。如果不需要工具，请直接回答。"""

        # Log prompt length for debugging
        import logging
        logger = logging.getLogger(__name__)
        original_count = len(messages)
        trimmed_count = len(trimmed_messages)
        logger.info(f"构建提示词长度: {len(unified_prompt)} (原始消息: {original_count}, 保留消息: {trimmed_count}, 长度限制: {self.max_prompt_length})")

        return unified_prompt
    
    # 保持向后兼容的方法
    def build_tool_call_prompt(self, messages: List[ChatMessage], tools: List[Tool]) -> str:
        return self.build_unified_tool_prompt(messages, tools)
    
    def build_tool_result_prompt(self, messages: List[ChatMessage], tool_result: str, tool_call_id: str, tools: Optional[List[Tool]] = None) -> str:
        return self.build_unified_tool_prompt(messages, tools, tool_result)
    
    def parse_tool_call(self, llm_response: str) -> Optional[Dict[str, Any]]:
        pattern = r'TOOL_CALL:\s*(\{.*\})'
        match = re.search(pattern, llm_response, re.DOTALL)
        
        if match:
            try:
                tool_call_data = json.loads(match.group(1))
                return {
                    "tool_name": tool_call_data.get("tool_name"),
                    "arguments": tool_call_data.get("arguments", {})
                }
            except json.JSONDecodeError:
                pass
        
        return None
    
    def extract_clean_response(self, llm_response: str) -> str:
        pattern = r'TOOL_CALL:\s*\{.*\}'
        clean_response = re.sub(pattern, '', llm_response, flags=re.DOTALL)
        return clean_response.strip()