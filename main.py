from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import json

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

# 添加请求日志中间件
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """记录所有HTTP请求的中间件"""
    
    # 记录请求基本信息
    logger.info(f"收到 {request.method} 请求: {request.url}")
    
    # 记录请求头
    headers = dict(request.headers)
    logger.debug(f"请求头: {json.dumps(headers, ensure_ascii=False, indent=2)}")
    
    # 尝试读取请求体
    try:
        body = await request.body()
        if body:
            # 解码并记录请求体
            try:
                body_text = body.decode('utf-8')
                logger.debug(f"原始请求体: {body_text}")
                
                # 尝试解析为JSON
                try:
                    body_json = json.loads(body_text)
                    logger.debug(f"解析后的请求体: {json.dumps(body_json, ensure_ascii=False, indent=2)}")
                except json.JSONDecodeError:
                    logger.debug("请求体不是有效的JSON格式")
                    
            except UnicodeDecodeError:
                logger.debug("无法解码请求体内容")
                
            # 重要：需要重置请求体，因为body()只能读取一次
            request._body = body
            
    except Exception as e:
        logger.debug(f"无法读取请求体: {e}")
    
    # 继续处理请求
    response = await call_next(request)
    
    # 记录响应信息
    logger.info(f"返回响应: {response.status_code}")
    
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
async def chat_completions(request: ChatCompletionRequest):
    """
    兼容OpenAI API的聊天补全接口
    """
    print(f"请求:{request}")
    try:
        logger.info(f"收到请求: {request.model}, 消息数量: {len(request.messages)}")
        
        # 打印请求体内容用于调试
        import json
        try:
            request_dict = request.model_dump()
            logger.debug(f"请求体内容: {json.dumps(request_dict, ensure_ascii=False, indent=2)}")
        except Exception as e:
            logger.debug(f"无法序列化请求体: {e}")
        
        # 检查消息内容类型
        for i, msg in enumerate(request.messages):
            logger.debug(f"消息 {i}: role={msg.role}, content类型={type(msg.content)}")
            if hasattr(msg.content, '__len__'):
                logger.debug(f"消息 {i} content长度: {len(msg.content)}")
            if isinstance(msg.content, (list, dict)):
                logger.debug(f"消息 {i} content详情: {msg.content}")
        
        # 使用统一的请求处理方法
        logger.info("处理聊天完成请求")
        llm_response = await llm_service.handle_unified_request(request)
        response = response_formatter.format_unified_response(
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

from fastapi.exceptions import RequestValidationError
from fastapi.responses import PlainTextResponse

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """请求验证异常处理器"""
    logger.error(f"请求验证失败: {exc}")
    logger.error(f"错误详情: {json.dumps(exc.errors(), ensure_ascii=False, indent=2)}")
    
    # 尝试获取请求体
    try:
        body = await request.body()
        if body:
            body_text = body.decode('utf-8')
            logger.error(f"失败的请求体: {body_text}")
    except Exception as e:
        logger.error(f"无法读取失败的请求体: {e}")
    
    return JSONResponse(
        status_code=422,
        content={"error": {"message": "请求验证失败", "details": exc.errors()}}
    )


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
        log_level="debug"
    )