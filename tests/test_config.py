"""
测试配置管理功能
"""

import pytest
import os
import json
import tempfile
from canctool.config import Config, ProviderConfig


class TestProviderConfig:
    """测试ProviderConfig类"""
    
    def test_provider_config_creation(self):
        """测试提供商配置创建"""
        provider = ProviderConfig(
            name="test_provider",
            base_url="http://localhost:8000",
            api_key="test_key",
            models=["model1", "model2"],
            headers={"Custom-Header": "value"}
        )
        
        assert provider.name == "test_provider"
        assert provider.base_url == "http://localhost:8000"
        assert provider.api_key == "test_key"
        assert provider.models == ["model1", "model2"]
        assert provider.headers == {"Custom-Header": "value"}
    
    def test_provider_config_to_dict(self):
        """测试提供商配置转换为字典"""
        provider = ProviderConfig(
            name="test_provider",
            base_url="http://localhost:8000",
            api_key="secret_key",
            models=["model1"],
            headers={"Authorization": "Bearer token"}
        )
        
        config_dict = provider.to_dict()
        
        assert config_dict["name"] == "test_provider"
        assert config_dict["base_url"] == "http://localhost:8000"
        assert config_dict["api_key"] == "***"  # 应该被隐藏
        assert config_dict["models"] == ["model1"]
        assert config_dict["headers"]["Authorization"] == "***"  # 应该被隐藏


class TestConfig:
    """测试Config类"""
    
    def setup_method(self):
        """每个测试方法前的设置"""
        # 清理配置状态
        Config._providers.clear()
        Config._default_provider = None
        Config._model_provider_mapping.clear()
    
    def test_load_providers_from_dict(self):
        """测试从字典加载提供商配置"""
        providers_data = {
            "default_provider": "openai",
            "providers": {
                "openai": {
                    "base_url": "https://api.openai.com/v1",
                    "api_key": "sk-test",
                    "models": ["gpt-4", "gpt-3.5-turbo"],
                    "headers": {}
                },
                "local": {
                    "base_url": "http://localhost:8000",
                    "api_key": None,
                    "models": ["llama2"],
                    "headers": {}
                }
            }
        }
        
        Config._load_providers_from_dict(providers_data)
        
        assert len(Config._providers) == 2
        assert Config._default_provider == "openai"
        assert "gpt-4" in Config._model_provider_mapping
        assert Config._model_provider_mapping["gpt-4"] == "openai"
        assert Config._model_provider_mapping["llama2"] == "local"
    
    def test_get_provider(self):
        """测试获取提供商配置"""
        providers_data = {
            "default_provider": "test",
            "providers": {
                "test": {
                    "base_url": "http://test.com",
                    "api_key": "test_key",
                    "models": ["test_model"],
                    "headers": {}
                }
            }
        }
        
        Config._load_providers_from_dict(providers_data)
        
        # 测试获取指定提供商
        provider = Config.get_provider("test")
        assert provider is not None
        assert provider.name == "test"
        
        # 测试获取默认提供商
        default_provider = Config.get_provider()
        assert default_provider is not None
        assert default_provider.name == "test"
        
        # 测试获取不存在的提供商
        non_existent = Config.get_provider("non_existent")
        assert non_existent is None
    
    def test_get_provider_for_model(self):
        """测试根据模型获取提供商"""
        providers_data = {
            "default_provider": "openai",
            "providers": {
                "openai": {
                    "base_url": "https://api.openai.com/v1",
                    "api_key": "sk-test",
                    "models": ["gpt-4"],
                    "headers": {}
                },
                "local": {
                    "base_url": "http://localhost:8000",
                    "api_key": None,
                    "models": ["llama2"],
                    "headers": {}
                }
            }
        }
        
        Config._load_providers_from_dict(providers_data)
        
        # 测试已知模型
        provider = Config.get_provider_for_model("gpt-4")
        assert provider is not None
        assert provider.name == "openai"
        
        provider = Config.get_provider_for_model("llama2")
        assert provider is not None
        assert provider.name == "local"
        
        # 测试未知模型（应该返回默认提供商）
        provider = Config.get_provider_for_model("unknown_model")
        assert provider is not None
        assert provider.name == "openai"  # 默认提供商
    
    def test_get_all_models(self):
        """测试获取所有模型列表"""
        providers_data = {
            "default_provider": "openai",
            "providers": {
                "openai": {
                    "base_url": "https://api.openai.com/v1",
                    "api_key": "sk-test",
                    "models": ["gpt-4", "gpt-3.5-turbo"],
                    "headers": {}
                },
                "local": {
                    "base_url": "http://localhost:8000",
                    "api_key": None,
                    "models": ["llama2", "gpt-4"],  # 重复模型测试去重
                    "headers": {}
                }
            }
        }
        
        Config._load_providers_from_dict(providers_data)
        
        models = Config.get_all_models()
        assert len(models) == 3  # 应该去重
        assert "gpt-4" in models
        assert "gpt-3.5-turbo" in models
        assert "llama2" in models
    
    def test_load_providers_config_from_file(self):
        """测试从文件加载配置"""
        providers_data = {
            "default_provider": "test",
            "providers": {
                "test": {
                    "base_url": "http://test.com",
                    "api_key": "test_key",
                    "models": ["test_model"],
                    "headers": {}
                }
            }
        }
        
        # 创建临时配置文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(providers_data, f)
            temp_file = f.name
        
        try:
            # 设置环境变量指向临时文件
            os.environ["LLM_PROVIDERS_CONFIG_FILE"] = temp_file
            
            Config.load_providers_config()
            
            assert len(Config._providers) == 1
            assert Config._default_provider == "test"
            
        finally:
            # 清理
            os.unlink(temp_file)
            if "LLM_PROVIDERS_CONFIG_FILE" in os.environ:
                del os.environ["LLM_PROVIDERS_CONFIG_FILE"]
    
    def test_legacy_config_fallback(self):
        """测试传统配置回退"""
        # 设置传统环境变量
        os.environ["LLM_API_BASE_URL"] = "http://legacy.com"
        os.environ["LLM_API_KEY"] = "legacy_key"
        os.environ["DEFAULT_MODEL_NAME"] = "legacy_model"
        
        try:
            Config._load_legacy_config()
            
            assert len(Config._providers) == 1
            assert "default" in Config._providers
            assert Config._default_provider == "default"
            
            provider = Config._providers["default"]
            assert provider.base_url == "http://legacy.com"
            assert provider.api_key == "legacy_key"
            assert "legacy_model" in provider.models
            
        finally:
            # 清理环境变量
            for key in ["LLM_API_BASE_URL", "LLM_API_KEY", "DEFAULT_MODEL_NAME"]:
                if key in os.environ:
                    del os.environ[key]
