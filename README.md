# CancTool - LLM Tool Call Wrapper Service

**Language / 语言**: [English](README.md) | [中文](README_ZH.md)

A service that enables LLMs without native OpenAI tool calling support to simulate standard OpenAI tool calling responses through prompt engineering, supporting multiple providers and model configurations.

## 🚀 Features

- ✅ **OpenAI API Compatible**: Fully compatible with OpenAI API chat completion interface
- ✅ **Tool Calling Support**: Supports tool calling and tool result processing
- ✅ **Multi-Provider Support**: Supports multiple LLM providers (OpenAI, Anthropic, local LLMs, etc.)
- ✅ **JSON Configuration**: Flexible JSON configuration files supporting multiple models and providers
- ✅ **Complete Error Handling**: Comprehensive error handling and optimized logging

## 📦 Installation

### System Requirements
- Python >= 3.8.1

## 🚀 Quick Start

### 1. Configure Service

Create `providers_config.json` file:

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

### 2. Start Service

#### Option 1: Run from Source

```bash
git clone https://github.com/sligter/canctool.git
cd canctool
uv sync

uv run main.py
```

#### Option 2: Docker Deployment

```bash
# Use pre-built image
docker run -d --name canctool-service \
  -p 8001:8001 \
  -v "${PWD}/providers_config.json:/app/providers_config.json:ro" \
  -e LOG_LEVEL=INFO \
  --restart unless-stopped \
  bradleylzh/canctool:latest
```

Or build from source:

```bash
# Build image
docker build -t canctool .

# Start service
docker run -d --name canctool-service \
  -p 8001:8001 \
  -v "${PWD}/providers_config.json:/app/providers_config.json:ro" \
  -e LOG_LEVEL=INFO \
  --restart unless-stopped \
  canctool
```

### 3. Usage Examples

#### Non-streaming Request

```python
import requests
import json

# Non-streaming request
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

#### Streaming Request

```python
# Streaming request
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

## 🏗️ Core Components

| Component | Description |
|-----------|-------------|
| **canctool/models.py** | OpenAI API compatible data models |
| **canctool/config.py** | JSON configuration file management and multi-provider support |
| **canctool/prompt_engineering.py** | Intelligent prompt engineering and tool calling templates |
| **canctool/llm_service.py** | Multi-provider LLM communication interface |
| **canctool/response_formatter.py** | Standard OpenAI format response generation |
| **canctool/token_streamer.py** | Intelligent streaming output and token calculation |
| **main.py** | FastAPI application entry point |

## 🔌 API Endpoints

### POST /v1/chat/completions
OpenAI API compatible chat completion endpoint supporting tool calling and streaming output.

**Supported Parameters**:
- `model`: Model name
- `messages`: Message list
- `temperature`: Temperature parameter (0.0-2.0)
- `max_tokens`: Maximum token count
- `tools`: Tool definition list
- `tool_choice`: Tool selection strategy
- `stream`: Enable streaming output (true/false)

### GET /v1/models
Get available model list, returns models from the default provider in configuration file.

### GET /health
Health check endpoint, returns service status.

## 📋 Usage Examples

### Tool Calling Example

```json
{
  "model": "gpt-3.5-turbo",
  "messages": [{"role": "user", "content": "What time is it in Beijing now?"}],
  "tools": [
    {
      "type": "function",
      "function": {
        "name": "get_current_time",
        "description": "Get current time for specified timezone",
        "parameters": {
          "type": "object",
          "properties": {
            "timezone": {"type": "string", "description": "Timezone name"}
          }
        }
      }
    }
  ]
}
```

### Streaming Output Example

```bash
curl -X POST http://localhost:8001/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-3.5-turbo",
    "messages": [{"role": "user", "content": "Tell me a story"}],
    "stream": true
  }'
```

## ⚙️ Configuration Guide

### JSON Configuration File

Create `providers_config.json` file to configure multiple providers:

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

## 🔧 Feature Details

### Tool Calling Support
- Automatic tool calling request detection
- Intelligent prompt engineering for improved tool calling success rates
- Support for tool result processing and final answer generation
- Fully compatible with OpenAI tool calling format

### Multi-Provider Architecture
- Flexible JSON configuration files
- Support for multiple LLM providers simultaneously
- Intelligent model routing and provider selection
- Environment variable support for easy deployment

## 🔧 Troubleshooting

### Common Issues

#### 1. LLM API Connection Failed
- Check `base_url` in `providers_config.json`
- Confirm LLM service is running
- Check network connectivity

#### 2. API Key Error
- Check API key in environment variables
- Confirm API key is valid and has sufficient permissions

#### 3. Model Unavailable
- Check model list returned by `/v1/models` endpoint
- Confirm requested model exists in configuration file

### Test Connection

```bash
# Test API endpoints
curl http://localhost:8001/health
curl http://localhost:8001/v1/models
```

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🤝 Contributing

Issues and Pull Requests are welcome!

## 📞 Support

For questions, please contact us through:
- Submit [GitHub Issue](https://github.com/sligter/canctool/issues)