import os
from typing import Optional
from dotenv import load_dotenv
import logging

# 加载环境变量
load_dotenv()

class Config:
    """配置管理类"""
    
    # LLM API 配置
    LLM_API_BASE_URL: str = os.getenv("LLM_API_BASE_URL", "http://localhost:8000")
    LLM_API_KEY: Optional[str] = os.getenv("LLM_API_KEY")
    DEFAULT_MODEL_NAME: str = os.getenv("DEFAULT_MODEL_NAME", "default")
    
    # 请求配置
    REQUEST_TIMEOUT: int = int(os.getenv("REQUEST_TIMEOUT", "30"))
    MAX_RETRIES: int = int(os.getenv("MAX_RETRIES", "3"))
    
    # 日志配置
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    @classmethod
    def setup_logging(cls):
        """设置日志配置"""
        level = getattr(logging, cls.LOG_LEVEL.upper())
        logging.basicConfig(
            level=level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    @classmethod
    def get_llm_headers(cls) -> dict:
        """获取LLM API请求头"""
        headers = {
            "Content-Type": "application/json"
        }
        
        if cls.LLM_API_KEY:
            headers["Authorization"] = f"Bearer {cls.LLM_API_KEY}"
        
        return headers
    
    @classmethod
    def validate_config(cls) -> bool:
        """验证配置是否有效"""
        if not cls.LLM_API_BASE_URL:
            raise ValueError("LLM_API_BASE_URL 未配置")
        
        if cls.REQUEST_TIMEOUT <= 0:
            raise ValueError("REQUEST_TIMEOUT 必须大于0")
        
        if cls.MAX_RETRIES < 0:
            raise ValueError("MAX_RETRIES 不能为负数")
        
        return True
    
    @classmethod
    def get_config_info(cls) -> dict:
        """获取配置信息（用于调试）"""
        return {
            "LLM_API_BASE_URL": cls.LLM_API_BASE_URL,
            "LLM_API_KEY": "***" if cls.LLM_API_KEY else None,
            "DEFAULT_MODEL_NAME": cls.DEFAULT_MODEL_NAME,
            "REQUEST_TIMEOUT": cls.REQUEST_TIMEOUT,
            "MAX_RETRIES": cls.MAX_RETRIES,
            "LOG_LEVEL": cls.LOG_LEVEL
        }