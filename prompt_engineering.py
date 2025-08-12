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
你是一个智能助手，可以调用工具来帮助用户完成任务。当用户的问题需要使用工具时，你需要以特定的格式返回工具调用信息。

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
        for msg in messages:
            if msg.role == "user":
                conversation.append(f"用户: {msg.content}")
            elif msg.role == "assistant":
                if msg.tool_calls:
                    for tool_call in msg.tool_calls:
                        conversation.append(f"助手: 调用工具 {tool_call['function']['name']} 参数 {tool_call['function']['arguments']}")
                elif msg.content:
                    conversation.append(f"助手: {msg.content}")
            elif msg.role == "tool":
                conversation.append(f"工具结果: {msg.content}")
        
        return "\n".join(conversation)
    
    def build_tool_call_prompt(self, messages: List[ChatMessage], tools: List[Tool]) -> str:
        user_message = messages[-1].content
        conversation_history = self._format_conversation_history(messages[:-1])
        tools_str = self._tools_to_string(tools)
        
        return self.tool_call_prompt.format(
            tools=tools_str,
            conversation_history=conversation_history,
            user_message=user_message
        )
    
    def build_tool_result_prompt(self, messages: List[ChatMessage], tool_result: str, tool_call_id: str, tools: Optional[List[Tool]] = None) -> str:
        """
        构建工具结果处理提示词，支持在处理工具结果后可能还需要调用其他工具的情况
        """
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

如果需要调用更多工具，请按上述格式返回工具调用信息。如果不需要调用工具，请直接回答用户的问题。
"""
        else:
            tools_info = """
如果需要更多信息或其他工具调用，请直接说明。
"""
        
        return f"""
工具调用已完成。

工具结果:
{tool_result}

对话历史:
{self._format_conversation_history(messages)}

请根据工具结果继续回答用户的问题。{tools_info}
"""
    
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