import json
import re
from typing import Dict, Any, List, Optional
from datetime import datetime
from models import Tool, ChatMessage


class PromptEngineeringService:
    
    def __init__(self):
        self.tool_call_prompt = self._create_tool_call_prompt_template()
    
    def _create_tool_call_prompt_template(self) -> str:
        return """
你是一个智能助手，必须优先调用工具来回答用户的问题。只有当工具调用无法满足用户需求时，才直接回答。

可用工具：
{tools}

工具调用格式说明：
当需要调用工具时，你必须在回复中包含以下格式的工具调用信息：
```
TOOL_CALL: {{"tool_name": "工具名称", "arguments": {{"参数名": "参数值"}}}}
```

如果不需要调用任何工具，请直接回答用户的问题。

参数说明：
- tool_name: 必须是可用工具列表中的一个
- arguments: 必须是符合工具定义的JSON对象，包含所有必需参数

当前对话：
{conversation_history}

用户最新消息：
{user_message}

请分析用户的需求，如果需要调用工具，请按上述格式返回工具调用信息。如果不需要调用工具，请直接回答。
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
                        tools_str += f", 可选值: {param_info.enum}"
                    tools_str += f"\n    描述: {param_info.description}\n"
            else:
                tools_str += "  无参数\n"
            tools_str += "\n"
        
        return tools_str
    
    def _format_conversation_history(self, messages: List[ChatMessage]) -> str:
        conversation = []
        
        # 从最近的对话开始构建，保持优先级但保留完整信息
        for msg in reversed(messages):
            content = self._ensure_string_content(msg.content)
            
            if msg.role == "user":
                line = f"用户: {content}"
            elif msg.role == "assistant":
                if msg.tool_calls:
                    # 保留完整的工具调用信息
                    tool_calls_info = []
                    for tool_call in msg.tool_calls:
                        tool_name = tool_call['function']['name']
                        tool_args = tool_call['function']['arguments']
                        tool_calls_info.append(f"调用工具 {tool_name} 参数 {tool_args}")
                    line = f"助手: {'; '.join(tool_calls_info)}"
                elif msg.content:
                    line = f"助手: {content}"
                else:
                    continue  # 跳过空消息
            elif msg.role == "tool":
                # 保留完整的工具结果信息
                line = f"工具结果: {content}"
            else:
                continue  # 跳过其他角色
            
            conversation.insert(0, line)  # 插入到开头以保持顺序
        
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
    
    def build_unified_tool_prompt(self, messages: List[ChatMessage], tools: Optional[List[Tool]] = None, tool_result: Optional[str] = None) -> str:
        """
        统一的工具调用提示词构建方法，支持初始调用和工具结果处理
        """
        # 获取最新的用户消息
        user_message = self._ensure_string_content(messages[-1].content)
        
        # 构建对话历史（排除最后一条用户消息）
        conversation_history = self._format_conversation_history(messages[:-1])
        
        # 构建工具信息
        tools_info = ""
        if tools:
            tools_info = f"""
可用工具：
{self._tools_to_string(tools)}

工具调用格式说明：
当需要调用工具时，你必须在回复中包含以下格式的工具调用信息：
```
TOOL_CALL: {{"tool_name": "工具名称", "arguments": {{"参数名": "参数值"}}}}
```

参数说明：
- tool_name: 必须是可用工具列表中的一个
- arguments: 必须是符合工具定义的JSON对象，包含所有必需参数
"""
        
        # 构建工具结果信息（如果有）
        tool_result_info = ""
        if tool_result:
            tool_result_info = f"""
上一个工具调用结果：
{self._ensure_string_content(tool_result)}

请根据以上结果决定是否需要调用更多工具或直接回答用户问题。
"""
        
        # 统一的提示词模板
        unified_prompt = f"""你是一个智能助手，必须优先调用工具来回答用户的问题。只有当工具调用无法满足用户需求时，才直接回答。

{tools_info}
{tool_result_info}
当前对话：
{conversation_history}

用户最新消息：
{user_message}

请分析用户的需求，如果需要调用工具，请按上述格式返回工具调用信息。如果不需要调用工具，请直接回答。"""
        
        # 记录提示词长度用于调试
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"构建的统一提示词长度: {len(unified_prompt)}")
        
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