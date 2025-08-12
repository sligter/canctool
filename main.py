from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from models import ChatCompletionRequest, ChatCompletionResponse
from llm_service import LLMService
from response_formatter import ResponseFormatter
from config import Config

# 设置日志
Config.setup_logging()
import logging
logger = logging.getLogger(__name__)

app = FastAPI(
    title="LLM Tool Call Wrapper Service",
    description="让不支持OpenAI工具调用的LLM能够模拟标准OpenAI工具调用响应",
    version="1.0.0"
)

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
async def chat_completions(request: ChatCompletionRequest):
    """
    兼容OpenAI API的聊天补全接口
    """
    try:
        logger.info(f"收到请求: {request.model}, 消息数量: {len(request.messages)}")
        
        # 判断请求类型并处理
        if llm_service.is_tool_result_request(request):
            logger.info("处理工具结果请求")
            llm_response = await llm_service.handle_tool_result_request(request)
            response = response_formatter.format_tool_result_response(
                request, llm_response
            )
        elif llm_service.should_use_tools(request):
            logger.info("处理工具调用请求")
            llm_response = await llm_service.handle_tool_call_request(request)
            response = response_formatter.format_tool_call_response(
                request, llm_response
            )
        else:
            logger.info("处理普通请求")
            llm_response = await llm_service.handle_regular_request(request)
            response = response_formatter.format_regular_response(
                request, llm_response
            )
        
        logger.info(f"返回响应: {response.id}")
        return response
        
    except Exception as e:
        logger.error(f"处理请求时发生错误: {e}")
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
    """全局异常处理器"""
    logger.error(f"未处理的异常: {exc}")
    return JSONResponse(
        status_code=500,
        content={"error": {"message": str(exc), "type": "internal_error"}}
    )


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
        log_level="info"
    )