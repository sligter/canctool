# CancTool - LLM Tool Call Wrapper Service

**Language / 语言**: [English](README.md) | [中文](README_ZH.md)

一个通过提示词工程让不支持OpenAI工具调用的LLM能够模拟标准OpenAI工具调用响应的服务，支持多提供商和多模型配置。

## 🚀 功能特性

- ✅ **OpenAI API兼容**: 完全兼容OpenAI API的聊天补全接口
- ✅ **工具调用支持**: 支持工具调用（tool calling）和工具结果处理
- ✅ **多提供商支持**: 支持多个LLM提供商（OpenAI、Anthropic、本地LLM等）
- ✅ **JSON配置**: 灵活的JSON配置文件，支持多模型和多提供商
- ✅ **完整错误处理**: 完整的错误处理和优化的日志记录

## 📦 安装

### 系统要求
- Python >= 3.8.1

## 🚀 快速开始

### 1. 配置服务

创建 `providers_config.json` 文件：

```json
{
  "default_provider": "openai",
  "service_config": {
    "log_level": "INFO",
    "request_timeout": 30,
    "max_retries": 3,
    "max_prompt_length": 200000,
    "service_api_key": "your-service-api-key"
  },
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

### 2. 启动服务

#### 方式一：从源码启动

```bash

git clone https://github.com/sligter/canctool.git
cd canctool
uv sync

uv run main.py
```

#### 方式二：Docker启动

```bash
# 使用预构建镜像
docker run -d --name canctool-service \
  -p 8001:8001 \
  -v "${PWD}/providers_config.json:/app/providers_config.json:ro" \
  -e LOG_LEVEL=INFO \
  --restart unless-stopped \
  bradleylzh/canctool:latest
```

或者从源码构建：

```bash
# 构建镜像
docker build -t canctool .

# 启动服务
docker run -d --name canctool-service \
  -p 8001:8001 \
  -v "${PWD}/providers_config.json:/app/providers_config.json:ro" \
  -e LOG_LEVEL=INFO \
  --restart unless-stopped \
  canctool
```

### 3. 使用示例

#### 非流式请求

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
```

#### 流式请求

```python
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

## 🏗️ 核心组件

| 组件 | 描述 |
|------|------|
| **canctool/models.py** | OpenAI API兼容的数据模型 |
| **canctool/config.py** | JSON配置文件管理和多提供商支持 |
| **canctool/prompt_engineering.py** | 智能提示词工程和工具调用模板 |
| **canctool/llm_service.py** | 多提供商LLM通信接口 |
| **canctool/response_formatter.py** | 标准OpenAI格式响应生成 |
| **canctool/token_streamer.py** | 智能流式输出和token计算 |
| **main.py** | FastAPI应用入口 |

## 🔌 API接口

### POST /v1/chat/completions
兼容OpenAI API的聊天补全接口，支持工具调用和流式输出。

**支持的参数**:
- `model`: 模型名称
- `messages`: 消息列表
- `temperature`: 温度参数 (0.0-2.0)
- `max_tokens`: 最大token数
- `tools`: 工具定义列表
- `tool_choice`: 工具选择策略
- `stream`: 是否启用流式输出 (true/false)

### GET /v1/models
获取可用模型列表，返回配置文件中默认提供商的模型列表。

### GET /health
健康检查接口，返回服务状态。

## 📋 使用示例

### 工具调用示例

```json
{
  "model": "gpt-3.5-turbo",
  "messages": [{"role": "user", "content": "现在北京时间是几点？"}],
  "tools": [
    {
      "type": "function",
      "function": {
        "name": "get_current_time",
        "description": "获取指定时区的当前时间",
        "parameters": {
          "type": "object",
          "properties": {
            "timezone": {"type": "string", "description": "时区名称"}
          }
        }
      }
    }
  ]
}
```

### 流式输出示例

```bash
curl -X POST http://localhost:8001/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-3.5-turbo",
    "messages": [{"role": "user", "content": "讲个故事"}],
    "stream": true
  }'
```

## ⚙️ 配置说明

### JSON配置文件

创建 `providers_config.json` 文件来配置多提供商：

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
    "anthropic": {
      "base_url": "https://api.anthropic.com/v1",
      "api_key": "${ANTHROPIC_API_KEY}",
      "models": ["claude-3-sonnet-20240229"],
      "headers": {"anthropic-version": "2023-06-01"}
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

## 🔧 特性说明

### 工具调用支持
- 自动识别工具调用请求
- 智能提示词工程，提高工具调用成功率
- 支持工具结果处理和最终回答生成
- 完全兼容OpenAI工具调用格式

### 多提供商架构
- 灵活的JSON配置文件
- 支持多个LLM提供商同时配置
- 智能模型路由和提供商选择
- 环境变量支持，便于部署

## 🔧 故障排除

### 常见问题

#### 1. LLM API连接失败
- 检查 `providers_config.json` 中的 `base_url`
- 确认LLM服务正在运行
- 检查网络连接

#### 2. API密钥错误
- 检查环境变量中的API密钥
- 确认API密钥有效且有足够权限

#### 3. 模型不可用
- 检查 `/v1/models` 端点返回的模型列表
- 确认请求的模型在配置文件中存在

### 测试连接

```bash
# 测试API端点
curl http://localhost:8001/health
curl http://localhost:8001/v1/models
```

---

## 📄 许可证

本项目采用 MIT 许可证，详见 [LICENSE](LICENSE) 文件。

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📞 支持

如有问题，请通过以下方式联系：
- 提交 [GitHub Issue](https://github.com/sligter/canctool/issues)