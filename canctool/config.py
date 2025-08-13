import os
import json
from typing import Optional, Dict, List, Any
from dotenv import load_dotenv
import logging

# 加载环境变量
load_dotenv()

class ProviderConfig:
    """单个LLM提供商配置"""

    def __init__(self, name: str, base_url: str, api_key: Optional[str] = None,
                 models: Optional[List[str]] = None, headers: Optional[Dict[str, str]] = None):
        self.name = name
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.models = models or []
        self.headers = headers or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "base_url": self.base_url,
            "api_key": "***" if self.api_key else None,
            "models": self.models,
            "headers": {k: "***" if "key" in k.lower() or "token" in k.lower() else v
                       for k, v in self.headers.items()}
        }

class Config:
    """增强的配置管理类，支持多提供商和多模型"""

    # 服务配置（默认值，可被 JSON 配置覆盖）
    SERVICE_API_KEY: Optional[str] = None
    REQUEST_TIMEOUT: int = 30
    MAX_RETRIES: int = 3
    LOG_LEVEL: str = "INFO"
    MAX_PROMPT_LENGTH: int = 200000

    # 提供商配置
    _providers: Dict[str, ProviderConfig] = {}
    _default_provider: Optional[str] = None
    _model_provider_mapping: Dict[str, str] = {}  # model_name -> provider_name
    _config_loaded: bool = False
    
    @classmethod
    def setup_logging(cls):
        """设置日志配置"""
        # 确保配置已加载
        if not cls._config_loaded:
            cls.load_providers_config()

        level = getattr(logging, cls.LOG_LEVEL.upper())
        logging.basicConfig(
            level=level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )



    @classmethod
    def load_providers_config(cls):
        """加载提供商配置"""
        if cls._config_loaded:
            return

        # 首先尝试从环境变量加载JSON配置
        providers_json = os.getenv("LLM_PROVIDERS_CONFIG")
        if providers_json:
            try:
                providers_data = json.loads(providers_json)
                cls._load_providers_from_dict(providers_data)
                cls._config_loaded = True
                return
            except json.JSONDecodeError as e:
                logging.warning(f"Unable to parse LLM_PROVIDERS_CONFIG JSON: {e}")

        # Try loading from configuration file
        config_file = os.getenv("LLM_PROVIDERS_CONFIG_FILE", "providers_config.json")
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    providers_data = json.load(f)
                cls._load_providers_from_dict(providers_data)
                cls._config_loaded = True
                return
            except (json.JSONDecodeError, IOError) as e:
                logging.warning(f"Unable to load configuration file {config_file}: {e}")

        # Fall back to environment variable configuration (backward compatibility)
        cls._load_legacy_config()
        cls._config_loaded = True

    @classmethod
    def _load_providers_from_dict(cls, providers_data: Dict[str, Any]):
        """Load provider configuration from dictionary data"""
        cls._providers.clear()
        cls._model_provider_mapping.clear()

        # 加载服务配置
        service_config = providers_data.get("service_config", {})
        cls._load_service_config(service_config)

        default_provider = providers_data.get("default_provider")
        providers = providers_data.get("providers", {})

        for provider_name, provider_config in providers.items():
            provider = ProviderConfig(
                name=provider_name,
                base_url=provider_config["base_url"],
                api_key=provider_config.get("api_key"),
                models=provider_config.get("models", []),
                headers=provider_config.get("headers", {})
            )
            cls._providers[provider_name] = provider

            # Build model to provider mapping
            for model in provider.models:
                cls._model_provider_mapping[model] = provider_name

        # Set default provider
        if default_provider and default_provider in cls._providers:
            cls._default_provider = default_provider
        elif cls._providers:
            cls._default_provider = next(iter(cls._providers.keys()))

    @classmethod
    def _load_service_config(cls, service_config: Dict[str, Any]):
        """从 service_config 部分加载服务配置"""
        # 直接从 JSON 配置加载，不再使用环境变量
        cls.SERVICE_API_KEY = service_config.get("service_api_key")
        cls.REQUEST_TIMEOUT = int(service_config.get("request_timeout", cls.REQUEST_TIMEOUT))
        cls.MAX_RETRIES = int(service_config.get("max_retries", cls.MAX_RETRIES))
        cls.LOG_LEVEL = service_config.get("log_level", cls.LOG_LEVEL)
        cls.MAX_PROMPT_LENGTH = int(service_config.get("max_prompt_length", cls.MAX_PROMPT_LENGTH))

    @classmethod
    def _load_legacy_config(cls):
        """Load legacy configuration (backward compatibility)"""
        base_url = os.getenv("LLM_API_BASE_URL", "http://localhost:8000")
        api_key = os.getenv("LLM_API_KEY")
        default_model = os.getenv("DEFAULT_MODEL_NAME", "default")

        # Create default provider
        provider = ProviderConfig(
            name="default",
            base_url=base_url,
            api_key=api_key,
            models=[default_model]
        )

        cls._providers["default"] = provider
        cls._default_provider = "default"
        cls._model_provider_mapping[default_model] = "default"

        logging.info("Using legacy configuration mode, recommend upgrading to new multi-provider configuration")
    
    @classmethod
    def get_provider(cls, provider_name: Optional[str] = None) -> Optional[ProviderConfig]:
        """获取指定提供商配置"""
        if not cls._providers:
            cls.load_providers_config()

        if provider_name:
            return cls._providers.get(provider_name)

        # 返回默认提供商
        if cls._default_provider:
            return cls._providers.get(cls._default_provider)

        return None

    @classmethod
    def get_provider_for_model(cls, model_name: str) -> Optional[ProviderConfig]:
        """根据模型名称获取对应的提供商配置"""
        if not cls._providers:
            cls.load_providers_config()

        provider_name = cls._model_provider_mapping.get(model_name)
        if provider_name:
            return cls._providers.get(provider_name)

        # 如果没有找到映射，返回默认提供商
        return cls.get_provider()

    @classmethod
    def get_all_providers(cls) -> Dict[str, ProviderConfig]:
        """获取所有提供商配置"""
        if not cls._providers:
            cls.load_providers_config()
        return cls._providers.copy()

    @classmethod
    def get_all_models(cls) -> List[str]:
        """获取所有可用模型列表"""
        if not cls._providers:
            cls.load_providers_config()

        models = []
        for provider in cls._providers.values():
            models.extend(provider.models)
        return list(set(models))  # 去重

    @classmethod
    def get_provider_headers(cls, provider: ProviderConfig) -> Dict[str, str]:
        """获取指定提供商的请求头"""
        headers = {
            "Content-Type": "application/json"
        }

        # 添加API密钥
        if provider.api_key:
            headers["Authorization"] = f"Bearer {provider.api_key}"

        # 添加自定义头部
        headers.update(provider.headers)

        return headers
    
    @classmethod
    def validate_config(cls):
        """验证配置"""
        if not cls._providers:
            cls.load_providers_config()

        if not cls._providers:
            raise ValueError("至少需要配置一个LLM提供商")

        if cls.REQUEST_TIMEOUT <= 0:
            raise ValueError("REQUEST_TIMEOUT 必须大于0")

        if cls.MAX_RETRIES < 0:
            raise ValueError("MAX_RETRIES 不能小于0")

        # 验证每个提供商配置
        for provider_name, provider in cls._providers.items():
            if not provider.base_url:
                raise ValueError(f"提供商 {provider_name} 的 base_url 不能为空")

    @classmethod
    def get_config_info(cls) -> dict:
        """获取配置信息（用于调试）"""
        if not cls._providers:
            cls.load_providers_config()

        return {
            "service_api_key": "***" if cls.SERVICE_API_KEY else None,
            "request_timeout": cls.REQUEST_TIMEOUT,
            "max_retries": cls.MAX_RETRIES,
            "log_level": cls.LOG_LEVEL,
            "default_provider": cls._default_provider,
            "providers": {name: provider.to_dict() for name, provider in cls._providers.items()},
            "total_models": len(cls.get_all_models()),
            "available_models": cls.get_all_models()
        }