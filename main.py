from fastapi import FastAPI, HTTPException, Request, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import uvicorn
import json
import time
from typing import Optional

from canctool.models import ChatCompletionRequest, ChatCompletionResponse
from canctool.llm_service import LLMService
from canctool.response_formatter import ResponseFormatter
from canctool.config import Config

# 设置日志
Config.setup_logging()
import logging
logger = logging.getLogger(__name__)

# 设置HTTP Bearer认证
security = HTTPBearer(auto_error=False)

app = FastAPI(
    title="LLM Tool Call Wrapper Service",
    description="让不支持OpenAI工具调用的LLM能够模拟标准OpenAI工具调用响应",
    version="1.0.0"
)

# 认证依赖函数
async def verify_api_key(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)):
    """验证API密钥"""
    # 确保配置已加载
    Config.load_providers_config()

    # 如果没有配置SERVICE_API_KEY，则不需要认证
    if not Config.SERVICE_API_KEY:
        logger.debug("No SERVICE_API_KEY configured, skipping authentication")
        return True

    if not credentials:
        logger.warning("Missing API key in request")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key. Please provide Authorization header with Bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if credentials.credentials != Config.SERVICE_API_KEY:
        logger.warning(f"Invalid API key provided: {credentials.credentials[:10]}...")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "Bearer"},
        )

    logger.debug("API key authentication successful")
    return True

# Add request logging middleware (optimized version)
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """HTTP request logging middleware (optimized version)"""

    # Only log important request information
    logger.info(f"{request.method} {request.url.path}")

    # Only log detailed information at DEBUG level
    if logger.isEnabledFor(logging.DEBUG):
        headers = dict(request.headers)
        # Hide sensitive information
        for key in headers:
            if "authorization" in key.lower() or "key" in key.lower():
                headers[key] = "***"
        logger.debug(f"Request headers: {json.dumps(headers, ensure_ascii=False, indent=2)}")

        # Try to read request body
        try:
            body = await request.body()
            if body:
                try:
                    body_text = body.decode('utf-8')
                    # Limit log length
                    if len(body_text) > 1000:
                        body_text = body_text[:1000] + "... (truncated)"
                    logger.debug(f"Request body: {body_text}")
                except UnicodeDecodeError:
                    logger.debug("Request body contains binary data")

                # Important: need to reset request body
                request._body = body

        except Exception as e:
            logger.debug(f"Failed to read request body: {e}")

    # Process request
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time

    # Log response information
    if response.status_code >= 400:
        logger.warning(f"{request.method} {request.url.path} -> {response.status_code} ({process_time:.3f}s)")
    else:
        logger.info(f"{request.method} {request.url.path} -> {response.status_code} ({process_time:.3f}s)")

    return response

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 初始化服务
llm_service = LLMService()
response_formatter = ResponseFormatter()


@app.post("/v1/chat/completions", response_model=ChatCompletionResponse)
async def chat_completions(request: ChatCompletionRequest, authenticated: bool = Depends(verify_api_key)):
    """
    兼容OpenAI API的聊天补全接口
    """
    try:
        logger.info(f"Chat completion request: {request.model}, messages: {len(request.messages)}")

        # Only log detailed information at DEBUG level
        if logger.isEnabledFor(logging.DEBUG):
            try:
                request_dict = request.model_dump()
                logger.debug(f"Request details: {json.dumps(request_dict, ensure_ascii=False, indent=2)}")
            except Exception as e:
                logger.debug(f"Unable to serialize request: {e}")

            # Check message content types
            for i, msg in enumerate(request.messages):
                logger.debug(f"Message {i}: role={msg.role}, content type={type(msg.content)}")
                if isinstance(msg.content, (list, dict)):
                    logger.debug(f"Message {i} content details: {msg.content}")

        # Use unified request processing method
        llm_response = await llm_service.handle_unified_request(request)
        response = response_formatter.format_unified_response(
            request, llm_response
        )

        logger.info(f"Chat completion request successful: {response.id}")
        return response

    except Exception as e:
        logger.error(f"Chat completion request failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/v1/models")
async def list_models(authenticated: bool = Depends(verify_api_key)):
    """获取可用模型列表 - 只显示默认提供商的模型"""
    try:
        # 确保配置已加载
        Config.load_providers_config()

        # 获取默认提供商
        default_provider = Config.get_provider()
        if not default_provider:
            logger.error("No default provider configured")
            raise HTTPException(status_code=500, detail="No default provider configured")

        # 只返回默认提供商的模型
        models = default_provider.models
        logger.info(f"Returning {len(models)} models from default provider: {default_provider.name}")

        # 构建OpenAI兼容的模型列表响应
        model_list = []
        for model in models:
            model_list.append({
                "id": model,
                "object": "model",
                "created": 1677610602,  # 固定时间戳
                "owned_by": default_provider.name,
                "permission": [],
                "root": model,
                "parent": None
            })

        return {
            "object": "list",
            "data": model_list
        }
    except HTTPException:
        # 重新抛出HTTP异常
        raise
    except Exception as e:
        logger.error(f"Failed to get model list: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    """健康检查接口"""
    return {
        "status": "healthy",
        "service": "LLM Tool Call Wrapper",
        "config": Config.get_config_info()
    }


@app.get("/")
async def root():
    """根路径"""
    return {
        "service": "LLM Tool Call Wrapper Service",
        "version": "1.0.0",
        "description": "让不支持OpenAI工具调用的LLM能够模拟标准OpenAI工具调用响应"
    }


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"error": {"message": str(exc), "type": "internal_error"}}
    )

from fastapi.exceptions import RequestValidationError
from fastapi.responses import PlainTextResponse

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Request validation exception handler"""
    logger.error(f"Request validation failed: {exc}")
    logger.error(f"Error details: {json.dumps(exc.errors(), ensure_ascii=False, indent=2)}")

    # Try to get request body
    try:
        body = await request.body()
        if body:
            body_text = body.decode('utf-8')
            logger.error(f"Failed request body: {body_text}")
    except Exception as e:
        logger.error(f"Unable to read failed request body: {e}")

    return JSONResponse(
        status_code=422,
        content={"error": {"message": "Request validation failed", "details": exc.errors()}}
    )


def main():
    """主入口点函数"""
    import argparse
    import os

    parser = argparse.ArgumentParser(description="CancTool - LLM Tool Call Wrapper Service")
    parser.add_argument("--host", default="0.0.0.0", help="Server host address (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8001, help="Server port (default: 8001)")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload (development mode)")
    parser.add_argument("--log-level", default="info", choices=["debug", "info", "warning", "error"],
                       help="Log level (default: info)")
    parser.add_argument("--config", help="Configuration file path")

    args = parser.parse_args()

    # 设置配置文件路径
    if args.config:
        os.environ["LLM_PROVIDERS_CONFIG_FILE"] = args.config

    # 设置日志级别
    os.environ["LOG_LEVEL"] = args.log_level.upper()

    print(f"Starting CancTool service...")
    print(f"Service address: http://{args.host}:{args.port}")
    print(f"Log level: {args.log_level}")
    if args.config:
        print(f"Configuration file: {args.config}")

    uvicorn.run(
        "main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level=args.log_level
    )


if __name__ == "__main__":
    main()