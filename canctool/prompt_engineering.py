import json
import re
from typing import Dict, Any, List, Optional
from datetime import datetime
from .models import Tool, ChatMessage


class PromptEngineeringService:
    
    def __init__(self):
        self.tool_call_prompt = self._create_tool_call_prompt_template()
    
    def _create_tool_call_prompt_template(self) -> str:
        return """
You are an intelligent assistant that must prioritize using tools to answer user questions. Only provide direct answers when tool calls cannot satisfy the user's needs.

Available tools:
{tools}

Tool calling format:
When you need to call a tool, you must include the following format in your response:
```
TOOL_CALL: {{"tool_name": "tool_name", "arguments": {{"parameter_name": "parameter_value"}}}}
```

If no tools are needed, please answer the user's question directly.

Parameter requirements:
- tool_name: Must be one of the available tools from the list above
- arguments: Must be a JSON object that conforms to the tool definition, including all required parameters

Current conversation:
{conversation_history}

User's latest message:
{user_message}

Please analyze the user's needs. If you need to call a tool, return the tool call information in the format above. If no tools are needed, answer directly.
"""
    
    def _tools_to_string(self, tools: List[Tool]) -> str:
        tools_str = ""
        for tool in tools:
            func = tool.function
            tools_str += f"\nTool name: {func.name}\n"
            tools_str += f"Description: {func.description}\n"
            tools_str += f"Parameters:\n"

            if func.parameters.properties:
                for param_name, param_info in func.parameters.properties.items():
                    required = param_name in func.parameters.required
                    tools_str += f"  - {param_name} ({param_info.type})"
                    if required:
                        tools_str += " (required)"
                    else:
                        tools_str += f" (optional, default: {param_info.default})"
                    if param_info.enum:
                        tools_str += f", allowed values: {param_info.enum}"
                    tools_str += f"\n    Description: {param_info.description}\n"
            else:
                tools_str += "  No parameters\n"
            tools_str += "\n"

        return tools_str
    
    def _format_conversation_history(self, messages: List[ChatMessage]) -> str:
        conversation = []

        # Build conversation from most recent messages, maintaining priority but preserving complete information
        for msg in reversed(messages):
            content = self._ensure_string_content(msg.content)

            if msg.role == "user":
                line = f"User: {content}"
            elif msg.role == "assistant":
                if msg.tool_calls:
                    # Preserve complete tool call information
                    tool_calls_info = []
                    for tool_call in msg.tool_calls:
                        tool_name = tool_call['function']['name']
                        tool_args = tool_call['function']['arguments']
                        tool_calls_info.append(f"Called tool {tool_name} with arguments {tool_args}")
                    line = f"Assistant: {'; '.join(tool_calls_info)}"
                elif msg.content:
                    line = f"Assistant: {content}"
                else:
                    continue  # Skip empty messages
            elif msg.role == "tool":
                # Preserve complete tool result information
                line = f"Tool result: {content}"
            else:
                continue  # Skip other roles

            conversation.insert(0, line)  # Insert at beginning to maintain order

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
        Unified tool call prompt building method, supporting initial calls and tool result processing
        """
        # Get the latest user message
        user_message = self._ensure_string_content(messages[-1].content)

        # Build conversation history (excluding the last user message)
        conversation_history = self._format_conversation_history(messages[:-1])

        # Build tool information
        tools_info = ""
        if tools:
            tools_info = f"""
Available tools:
{self._tools_to_string(tools)}

Tool calling format:
When you need to call a tool, you must include the following format in your response:
```
TOOL_CALL: {{"tool_name": "tool_name", "arguments": {{"parameter_name": "parameter_value"}}}}
```

Parameter requirements:
- tool_name: Must be one of the available tools from the list above
- arguments: Must be a JSON object that conforms to the tool definition, including all required parameters
"""

        # Build tool result information (if any)
        tool_result_info = ""
        if tool_result:
            tool_result_info = f"""
Previous tool call result:
{self._ensure_string_content(tool_result)}

Based on the above result, please decide whether you need to call more tools or answer the user's question directly.
"""

        # Unified prompt template
        unified_prompt = f"""You are an intelligent assistant that must prioritize using tools to answer user questions. Only provide direct answers when tool calls cannot satisfy the user's needs.

{tools_info}
{tool_result_info}
Current conversation:
{conversation_history}

User's latest message:
{user_message}

Please analyze the user's needs. If you need to call a tool, return the tool call information in the format above. If no tools are needed, answer directly."""

        # Log prompt length for debugging
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Built unified prompt length: {len(unified_prompt)}")

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