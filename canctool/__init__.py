"""
CancTool - LLM Tool Call Wrapper Service

一个通过提示词工程让不支持OpenAI工具调用的LLM能够模拟标准OpenAI工具调用响应的服务。

主要功能:
- 兼容OpenAI API的聊天补全接口
- 支持工具调用（tool calling）
- 支持工具结果处理（tool call result）
- 多提供商和多模型支持
- API密钥认证
- 可配置的模型列表
"""

__version__ = "1.0.0"
__author__ = "CancTool Team"
__email__ = "support@canctool.com"
__description__ = "LLM Tool Call Wrapper Service with multi-provider support"

# 导入主要类和函数
from .config import Config, ProviderConfig
from .models import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatMessage,
    Tool,
    FunctionDefinition,
    FunctionParameters,
    FunctionParameter
)
from .llm_service import LLMService
from .prompt_engineering import PromptEngineeringService
from .response_formatter import ResponseFormatter
from .token_streamer import TokenStreamer
from .simple_streamer import SimpleStreamer

# 导出的公共API
__all__ = [
    # 版本信息
    "__version__",
    "__author__",
    "__email__",
    "__description__",
    
    # 配置类
    "Config",
    "ProviderConfig",
    
    # 数据模型
    "ChatCompletionRequest",
    "ChatCompletionResponse", 
    "ChatMessage",
    "Tool",
    "FunctionDefinition",
    "FunctionParameters",
    "FunctionParameter",
    
    # 服务类
    "LLMService",
    "PromptEngineeringService",
    "ResponseFormatter",
    "TokenStreamer",
    "SimpleStreamer",
]

def get_version():
    """获取版本信息"""
    return __version__

def get_info():
    """获取包信息"""
    return {
        "name": "canctool",
        "version": __version__,
        "author": __author__,
        "email": __email__,
        "description": __description__
    }
