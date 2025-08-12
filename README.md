# LLM Tool Call Wrapper Service

这个服务通过提示词工程让不支持OpenAI工具调用的LLM能够模拟标准OpenAI工具调用响应。

## 功能特性

- ✅ 兼容OpenAI API的聊天补全接口
- ✅ 支持工具调用（tool calling）
- ✅ 支持工具结果处理（tool call result）
- ✅ 基于提示词工程的工具调用模拟
- ✅ 自动识别请求类型并相应处理
- ✅ 完整的错误处理和日志记录
- ✅ 支持多种LLM API格式
- ✅ 环境变量配置管理
- ✅ 重试机制和超时控制

## 架构设计

### 核心组件

1. **models.py** - 数据模型定义
   - OpenAI API兼容的请求/响应模型
   - 工具定义和参数模型
   - 消息和选项模型

2. **config.py** - 配置管理
   - 环境变量加载和验证
   - LLM API配置管理
   - 日志配置

3. **prompt_engineering.py** - 提示词工程服务
   - 工具调用提示词模板
   - 工具结果处理提示词
   - LLM响应解析和格式化

4. **llm_service.py** - LLM服务接口
   - 与本地LLM的通信接口
   - 支持多种LLM API格式
   - 请求类型判断和路由
   - 工具调用和结果处理逻辑

5. **response_formatter.py** - 响应格式化服务
   - 标准OpenAI格式响应生成
   - 工具调用响应格式化
   - 普通响应格式化

6. **main.py** - FastAPI应用
   - API路由和端点
   - 中间件配置
   - 异常处理

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

## API接口

### POST /v1/chat/completions
兼容OpenAI API的聊天补全接口。

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

## 故障排除

### 常见问题

1. **LLM API连接失败**
   - 检查 `LLM_API_BASE_URL` 配置
   - 确认LLM服务正在运行
   - 检查网络连接

2. **API密钥错误**
   - 检查 `LLM_API_KEY` 配置
   - 确认API密钥有效

3. **请求超时**
   - 增加 `REQUEST_TIMEOUT` 值
   - 检查LLM服务响应时间

4. **工具调用解析失败**
   - 检查LLM响应格式
   - 调整提示词模板

### 调试模式

设置 `LOG_LEVEL=DEBUG` 可以查看详细的调试信息。