# CancTool - LLM Tool Call Wrapper Service

一个通过提示词工程让不支持OpenAI工具调用的LLM能够模拟标准OpenAI工具调用响应的服务，支持多提供商和多模型配置。

## 🚀 功能特性

- ✅ **OpenAI API兼容**: 完全兼容OpenAI API的聊天补全接口
- ✅ **智能流式输出**: 自适应的可靠流式响应，支持多语言无乱码
- ✅ **工具调用支持**: 支持工具调用（tool calling）和工具结果处理
- ✅ **多提供商支持**: 支持多个LLM提供商（OpenAI、Anthropic、本地LLM等）
- ✅ **多模型配置**: 灵活的模型配置和动态模型列表
- ✅ **API密钥认证**: 内置API密钥认证机制
- ✅ **配置化模型列表**: `/v1/models`端点返回可配置的模型列表
- ✅ **智能提示词工程**: 基于提示词工程的工具调用模拟
- ✅ **自动请求识别**: 自动识别请求类型并相应处理
- ✅ **完整错误处理**: 完整的错误处理和优化的日志记录
- ✅ **重试机制**: 内置重试机制和超时控制
- ✅ **Python包**: 可通过pip安装的完整Python包

## 📦 安装

### 系统要求

- Python >= 3.8.1
- 推荐使用 Python 3.9+ 以获得最佳兼容性

### 通过pip安装

```bash
pip install canctool
```

### 从源码安装

```bash
git clone https://github.com/canctool/canctool.git
cd canctool
pip install -e .
```

### 开发环境安装

```bash
# 安装开发依赖
pip install -e ".[dev]"

# 或者手动安装开发工具
pip install pytest pytest-asyncio black isort
```

### 验证安装

```bash
# 运行基本测试
python test_basic.py

# 或者启动服务测试
canctool --help
```

## 🚀 快速开始

### 1. 基本使用

```bash
# 启动服务（使用默认配置）
canctool

# 或者使用自定义参数
canctool --host 0.0.0.0 --port 8001 --log-level info
```

### 2. 流式输出示例

```python
import requests
import json

# 非流式请求
response = requests.post("http://localhost:8001/v1/chat/completions",
    headers={"Content-Type": "application/json"},
    json={
        "model": "gpt-3.5-turbo",
        "messages": [{"role": "user", "content": "Hello, how are you?"}],
        "stream": False
    }
)
print(response.json())

# 流式请求
response = requests.post("http://localhost:8001/v1/chat/completions",
    headers={"Content-Type": "application/json"},
    json={
        "model": "gpt-3.5-turbo",
        "messages": [{"role": "user", "content": "Tell me a story"}],
        "stream": True
    },
    stream=True
)

for line in response.iter_lines():
    if line:
        line = line.decode('utf-8')
        if line.startswith('data: '):
            data = line[6:]  # Remove 'data: ' prefix
            if data == '[DONE]':
                break
            try:
                chunk = json.loads(data)
                content = chunk['choices'][0]['delta'].get('content', '')
                if content:
                    print(content, end='', flush=True)
            except json.JSONDecodeError:
                continue
print()  # New line at the end
```

### 3. 配置多提供商

创建 `providers_config.json` 文件：

```json
{
  "default_provider": "openai",
  "providers": {
    "openai": {
      "base_url": "https://api.openai.com/v1",
      "api_key": "${OPENAI_API_KEY}",
      "models": ["gpt-4", "gpt-3.5-turbo"],
      "headers": {}
    },
    "local_llm": {
      "base_url": "http://localhost:8000",
      "api_key": null,
      "models": ["llama2-7b", "mistral-7b"],
      "headers": {}
    }
  }
}
```

### 4. 设置环境变量

```bash
# 设置LLM提供商API密钥
export OPENAI_API_KEY="your-openai-api-key"
export ANTHROPIC_API_KEY="your-anthropic-api-key"

# 设置代理服务API密钥（可选，用于保护服务）
export SERVICE_API_KEY="your-service-api-key"

# 设置配置文件路径
export LLM_PROVIDERS_CONFIG_FILE="providers_config.json"

# 设置日志级别
export LOG_LEVEL="INFO"
```

### 5. 代理服务认证

如果设置了 `SERVICE_API_KEY`，客户端需要在请求头中包含认证信息：

```bash
# 使用curl测试
curl -H "Authorization: Bearer your-service-api-key" \
     http://localhost:8001/v1/models

# 使用Python requests
import requests
headers = {"Authorization": "Bearer your-service-api-key"}
response = requests.get("http://localhost:8001/v1/models", headers=headers)
```

**注意**:
- 如果未设置 `SERVICE_API_KEY`，则不需要认证
- 设置后，所有API端点都需要认证（除了 `/health` 和 `/`）

## 🏗️ 架构设计

### 核心组件

1. **canctool/models.py** - 数据模型定义
   - OpenAI API兼容的请求/响应模型
   - 工具定义和参数模型
   - 消息和选项模型

2. **canctool/config.py** - 多提供商配置管理
   - 多提供商配置加载和验证
   - 模型到提供商的映射
   - 环境变量和配置文件支持

3. **canctool/prompt_engineering.py** - 提示词工程服务
   - 工具调用提示词模板
   - 工具结果处理提示词
   - LLM响应解析和格式化

4. **canctool/llm_service.py** - LLM服务接口
   - 多提供商LLM通信接口
   - 智能提供商选择和路由
   - 请求类型判断和处理逻辑

5. **canctool/response_formatter.py** - 响应格式化服务
   - 标准OpenAI格式响应生成
   - 工具调用响应格式化
   - 统一响应处理

6. **main.py** - FastAPI应用入口
   - API路由和端点
   - 认证中间件
   - 异常处理和日志

## 安装和配置

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

复制 `.env.example` 为 `.env` 并修改配置：

```bash
cp .env.example .env
```

编辑 `.env` 文件：

```env
# LLM API 配置
LLM_API_BASE_URL=http://localhost:8000
LLM_API_KEY=your_api_key_here
DEFAULT_MODEL_NAME=default
REQUEST_TIMEOUT=30
MAX_RETRIES=3
LOG_LEVEL=INFO
```

### 3. 配置说明

| 参数 | 说明 | 示例 |
|------|------|------|
| `LLM_API_BASE_URL` | LLM API的基础URL | `http://localhost:8000`, `https://api.openai.com/v1` |
| `LLM_API_KEY` | LLM API密钥（可选） | `sk-your-openai-api-key` |
| `DEFAULT_MODEL_NAME` | 默认模型名称 | `gpt-3.5-turbo`, `claude-3-sonnet` |
| `REQUEST_TIMEOUT` | 请求超时时间（秒） | `30` |
| `MAX_RETRIES` | 最大重试次数 | `3` |
| `LOG_LEVEL` | 日志级别 | `DEBUG`, `INFO`, `WARNING`, `ERROR` |

### 4. 支持的LLM API格式

服务支持多种LLM API格式：

#### OpenAI兼容格式
```
POST /chat/completions
{
  "model": "model-name",
  "messages": [{"role": "user", "content": "prompt"}],
  "max_tokens": 1000,
  "temperature": 0.7
}
```

#### 通用生成格式
```
POST /generate
{
  "model": "model-name",
  "prompt": "prompt",
  "max_tokens": 1000,
  "temperature": 0.7
}
```

### 5. 启动服务

```bash
python main.py
```

服务将在 `http://localhost:8000` 启动。

### 6. 运行测试

```bash
python test_client.py
```

## 工作流程

### 1. 工具调用流程
```
用户请求 → 判断需要工具调用 → 构建工具调用提示词 → 调用LLM → 解析LLM响应 → 格式化为标准工具调用响应
```

### 2. 工具结果处理流程
```
工具结果 → 识别为结果处理请求 → 构建结果处理提示词 → 调用LLM → 生成最终回答 → 返回标准响应
```

### 3. 普通对话流程
```
用户请求 → 识别为普通请求 → 构建对话提示词 → 调用LLM → 返回标准响应
```

## 🔌 API接口

### POST /v1/chat/completions
兼容OpenAI API的聊天补全接口，支持工具调用和流式输出。

**认证**: 可选（如果设置了`SERVICE_API_KEY`）
**Headers**: `Authorization: Bearer <your-api-key>`

**支持的参数**:
- `model`: 模型名称
- `messages`: 消息列表
- `temperature`: 温度参数 (0.0-2.0)
- `max_tokens`: 最大token数
- `tools`: 工具定义列表
- `tool_choice`: 工具选择策略
- `stream`: 是否启用流式输出 (true/false)

**Token流式输出示例**:
```bash
curl -X POST http://localhost:8001/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-api-key" \
  -d '{
    "model": "gpt-3.5-turbo",
    "messages": [{"role": "user", "content": "Tell me a story"}],
    "stream": true
  }'
```

**智能流式输出特性**:
- 自适应流式模式：根据内容长度自动选择最佳方式
- 多语言支持：完美支持中文、emoji、特殊字符，无乱码
- 多种流式模式：单词级、句子级、字符级流式输出
- 可靠稳定：避免复杂的token编码问题，确保输出正确性

**流式响应格式**:
```
data: {"id":"chatcmpl-xxx","object":"chat.completion.chunk","created":1677610602,"model":"gpt-3.5-turbo","choices":[{"index":0,"delta":{"role":"assistant","content":"Hello"},"finish_reason":null}]}

data: {"id":"chatcmpl-xxx","object":"chat.completion.chunk","created":1677610602,"model":"gpt-3.5-turbo","choices":[{"index":0,"delta":{"content":" there!"},"finish_reason":null}]}

data: {"id":"chatcmpl-xxx","object":"chat.completion.chunk","created":1677610602,"model":"gpt-3.5-turbo","choices":[{"index":0,"delta":{},"finish_reason":"stop"}]}

data: [DONE]
```

### GET /v1/models
获取可用模型列表，返回OpenAI兼容的模型列表格式。

**认证**: 可选（如果设置了`SERVICE_API_KEY`）

**行为**: 只返回默认提供商（`default_provider`）的模型列表

**响应示例**:
```json
{
  "object": "list",
  "data": [
    {
      "id": "gpt-4",
      "object": "model",
      "created": 1677610602,
      "owned_by": "openai",
      "permission": [],
      "root": "gpt-4",
      "parent": null
    },
    {
      "id": "gpt-3.5-turbo",
      "object": "model",
      "created": 1677610602,
      "owned_by": "openai",
      "permission": [],
      "root": "gpt-3.5-turbo",
      "parent": null
    }
  ]
}
```

**注意**:
- 只显示配置文件中 `default_provider` 指定的提供商的模型
- 如果需要使用其他提供商的模型，请在聊天请求中直接指定模型名称

#### 请求示例 - 工具调用
```json
{
  "model": "your-model",
  "messages": [
    {
      "role": "user",
      "content": "现在北京时间是几点？"
    }
  ],
  "temperature": 0.7,
  "max_tokens": 1000,
  "tools": [
    {
      "type": "function",
      "function": {
        "name": "get_current_time",
        "description": "获取指定时区的当前时间",
        "parameters": {
          "type": "object",
          "properties": {
            "timezone": {
              "default": "UTC",
              "description": "时区名称，例如：UTC, Asia/Shanghai, America/New_York",
              "type": "string"
            }
          },
          "required": []
        }
      }
    }
  ],
  "tool_choice": "auto"
}
```

#### 请求示例 - 工具结果处理
```json
{
  "model": "your-model",
  "messages": [
    {
      "role": "user",
      "content": "现在北京时间是几点？"
    },
    {
      "role": "assistant",
      "content": "",
      "tool_calls": [
        {
          "id": "call_123",
          "type": "function",
          "function": {
            "name": "get_current_time",
            "arguments": "{\"timezone\": \"Asia/Shanghai\"}"
          }
        }
      ]
    },
    {
      "role": "tool",
      "content": "{\"timezone\": \"Asia/Shanghai\", \"current_time\": \"2025-08-12 13:30:01 CST\", \"timestamp\": 1754976601.004147, \"status\": \"success\"}",
      "tool_call_id": "call_123"
    }
  ],
  "temperature": 0.7,
  "max_tokens": 1000
}
```

### GET /health
健康检查接口，返回服务状态和配置信息。

### GET /
根路径，返回服务信息。

## ⚙️ 配置说明

### 多提供商配置

支持三种配置方式（按优先级排序）：

1. **环境变量JSON配置**:
```bash
export LLM_PROVIDERS_CONFIG='{"default_provider": "openai", "providers": {...}}'
```

2. **配置文件**:
```bash
export LLM_PROVIDERS_CONFIG_FILE="providers_config.json"
```

3. **传统环境变量**（向后兼容）:
```bash
export LLM_API_BASE_URL="http://localhost:8000"
export LLM_API_KEY="your-api-key"
export DEFAULT_MODEL_NAME="default"
```

### 配置文件格式

```json
{
  "default_provider": "openai",
  "providers": {
    "openai": {
      "base_url": "https://api.openai.com/v1",
      "api_key": "${OPENAI_API_KEY}",
      "models": ["gpt-4", "gpt-4-turbo", "gpt-3.5-turbo"],
      "headers": {
        "User-Agent": "CancTool/1.0"
      }
    },
    "anthropic": {
      "base_url": "https://api.anthropic.com/v1",
      "api_key": "${ANTHROPIC_API_KEY}",
      "models": ["claude-3-opus-20240229", "claude-3-sonnet-20240229"],
      "headers": {
        "anthropic-version": "2023-06-01"
      }
    },
    "local_llm": {
      "base_url": "http://localhost:8000",
      "api_key": null,
      "models": ["llama2-7b", "llama2-13b", "mistral-7b"],
      "headers": {}
    }
  }
}
```

### 环境变量

| 变量名 | 描述 | 默认值 |
|--------|------|--------|
| `SERVICE_API_KEY` | 服务API密钥（可选） | None |
| `LLM_PROVIDERS_CONFIG` | JSON格式的提供商配置 | None |
| `LLM_PROVIDERS_CONFIG_FILE` | 配置文件路径 | providers_config.json |
| `REQUEST_TIMEOUT` | 请求超时时间（秒） | 30 |
| `MAX_RETRIES` | 最大重试次数 | 3 |
| `LOG_LEVEL` | 日志级别 | INFO |

## 扩展功能

### 添加新的工具类型
1. 在 `models.py` 中添加工具定义
2. 在 `prompt_engineering.py` 中更新工具描述模板
3. 在LLM服务中实现实际的工具调用逻辑

### 支持更多LLM特性
可以扩展提示词模板以支持更多的LLM特性，如流式响应、多模态输入等。

### 自定义API格式
在 `llm_service.py` 中添加新的API格式支持方法。

## 错误处理

服务包含完整的错误处理机制：
- 网络请求异常处理
- JSON解析异常处理
- LLM服务调用异常处理
- 全局异常捕获和响应
- 重试机制

## 日志记录

使用Python标准日志库，支持不同日志级别：
- `DEBUG`: 详细调试信息
- `INFO`: 一般信息
- `WARNING`: 警告信息
- `ERROR`: 错误信息
- `CRITICAL`: 严重错误信息

## 🔧 故障排除

### 安装问题

1. **Python版本兼容性**
   ```bash
   # 检查Python版本
   python --version

   # 确保版本 >= 3.8.1
   # 如果版本过低，请升级Python
   ```

2. **依赖冲突**
   ```bash
   # 使用虚拟环境
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # 或
   venv\Scripts\activate     # Windows

   # 重新安装
   pip install canctool
   ```

3. **开发依赖问题**
   ```bash
   # 如果开发依赖安装失败，可以单独安装核心包
   pip install canctool

   # 然后手动安装需要的开发工具
   pip install pytest black isort
   ```

### 运行时问题

1. **LLM API连接失败**
   - 检查提供商配置中的 `base_url`
   - 确认LLM服务正在运行
   - 检查网络连接和防火墙设置

2. **API密钥错误**
   - 检查环境变量中的API密钥配置
   - 确认API密钥有效且有足够权限
   - 检查配置文件中的密钥格式

3. **请求超时**
   - 增加 `REQUEST_TIMEOUT` 值
   - 检查LLM服务响应时间
   - 考虑使用更快的模型

4. **工具调用解析失败**
   - 检查LLM响应格式
   - 确认模型支持英文提示词
   - 调整温度参数降低随机性

5. **模型不可用**
   - 检查 `/v1/models` 端点返回的模型列表
   - 确认请求的模型在配置中存在
   - 检查提供商和模型的映射关系

### 调试模式

```bash
# 启用详细日志
export LOG_LEVEL=DEBUG
canctool

# 或者在启动时指定
canctool --log-level debug
```

### 测试连接

```bash
# 测试基本功能
python test_basic.py

# 测试API端点
curl http://localhost:8001/health
curl http://localhost:8001/v1/models
```