"""
测试API端点功能
"""

import pytest
from fastapi.testclient import TestClient
import os
import json
import tempfile

# 设置测试环境
os.environ["LOG_LEVEL"] = "ERROR"  # 减少测试时的日志输出

from main import app
from canctool.config import Config


@pytest.fixture
def client():
    """创建测试客户端"""
    return TestClient(app)


@pytest.fixture
def setup_test_config():
    """设置测试配置"""
    # 清理现有配置
    Config._providers.clear()
    Config._default_provider = None
    Config._model_provider_mapping.clear()
    
    # 设置测试配置
    providers_data = {
        "default_provider": "test_provider",
        "providers": {
            "test_provider": {
                "base_url": "http://localhost:8000",
                "api_key": None,
                "models": ["test_model", "gpt-3.5-turbo"],
                "headers": {}
            }
        }
    }
    
    Config._load_providers_from_dict(providers_data)
    
    yield
    
    # 清理
    Config._providers.clear()
    Config._default_provider = None
    Config._model_provider_mapping.clear()


class TestHealthEndpoint:
    """测试健康检查端点"""
    
    def test_health_check(self, client, setup_test_config):
        """测试健康检查端点"""
        response = client.get("/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "LLM Tool Call Wrapper"
        assert "config" in data


class TestRootEndpoint:
    """测试根端点"""
    
    def test_root_endpoint(self, client):
        """测试根端点"""
        response = client.get("/")
        assert response.status_code == 200
        
        data = response.json()
        assert data["service"] == "LLM Tool Call Wrapper Service"
        assert data["version"] == "1.0.0"


class TestModelsEndpoint:
    """测试模型列表端点"""
    
    def test_models_endpoint_without_auth(self, client, setup_test_config):
        """测试无认证的模型列表端点"""
        # 确保没有设置SERVICE_API_KEY
        if hasattr(Config, 'SERVICE_API_KEY'):
            original_key = Config.SERVICE_API_KEY
            Config.SERVICE_API_KEY = None
        
        try:
            response = client.get("/v1/models")
            assert response.status_code == 200
            
            data = response.json()
            assert data["object"] == "list"
            assert "data" in data
            assert len(data["data"]) > 0
            
            # 检查模型格式
            model = data["data"][0]
            assert "id" in model
            assert "object" in model
            assert model["object"] == "model"
            assert "owned_by" in model
            
        finally:
            if 'original_key' in locals():
                Config.SERVICE_API_KEY = original_key
    
    def test_models_endpoint_with_auth(self, client, setup_test_config):
        """测试需要认证的模型列表端点"""
        # 设置API密钥
        Config.SERVICE_API_KEY = "test_api_key"
        
        try:
            # 无认证请求应该失败
            response = client.get("/v1/models")
            assert response.status_code == 401
            
            # 错误的API密钥应该失败
            headers = {"Authorization": "Bearer wrong_key"}
            response = client.get("/v1/models", headers=headers)
            assert response.status_code == 401
            
            # 正确的API密钥应该成功
            headers = {"Authorization": "Bearer test_api_key"}
            response = client.get("/v1/models", headers=headers)
            assert response.status_code == 200
            
            data = response.json()
            assert data["object"] == "list"
            assert "data" in data
            
        finally:
            Config.SERVICE_API_KEY = None


class TestChatCompletionsEndpoint:
    """测试聊天完成端点"""
    
    def test_chat_completions_validation(self, client, setup_test_config):
        """测试聊天完成端点的请求验证"""
        # 确保没有设置SERVICE_API_KEY
        Config.SERVICE_API_KEY = None
        
        # 测试无效请求体
        response = client.post("/v1/chat/completions", json={})
        assert response.status_code == 422  # 验证错误
        
        # 测试缺少必需字段
        response = client.post("/v1/chat/completions", json={
            "model": "test_model"
            # 缺少messages字段
        })
        assert response.status_code == 422
        
        # 测试空消息列表
        response = client.post("/v1/chat/completions", json={
            "model": "test_model",
            "messages": []
        })
        assert response.status_code == 422
    
    def test_chat_completions_with_auth(self, client, setup_test_config):
        """测试需要认证的聊天完成端点"""
        Config.SERVICE_API_KEY = "test_api_key"
        
        try:
            request_data = {
                "model": "test_model",
                "messages": [
                    {"role": "user", "content": "Hello"}
                ]
            }
            
            # 无认证请求应该失败
            response = client.post("/v1/chat/completions", json=request_data)
            assert response.status_code == 401
            
            # 正确的API密钥应该尝试处理请求（可能因为没有真实的LLM服务而失败）
            headers = {"Authorization": "Bearer test_api_key"}
            response = client.post("/v1/chat/completions", json=request_data, headers=headers)
            # 这里可能返回500因为没有真实的LLM服务，但至少通过了认证
            assert response.status_code in [200, 500]
            
        finally:
            Config.SERVICE_API_KEY = None


class TestCORSMiddleware:
    """测试CORS中间件"""
    
    def test_cors_headers(self, client):
        """测试CORS头部"""
        response = client.options("/")
        assert response.status_code == 200
        
        # 检查CORS头部
        assert "access-control-allow-origin" in response.headers
        assert "access-control-allow-methods" in response.headers
