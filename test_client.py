import json
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_health_check():
    """测试健康检查"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_root_endpoint():
    """测试根路径"""
    response = client.get("/")
    assert response.status_code == 200
    assert "service" in response.json()

def test_regular_chat_completion():
    """测试普通聊天补全"""
    request_data = {
        "model": "test-model",
        "messages": [
            {"role": "user", "content": "你好，请介绍一下你自己"}
        ],
        "temperature": 0.7,
        "max_tokens": 1000
    }
    
    response = client.post("/v1/chat/completions", json=request_data)
    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert data["object"] == "chat.completion"
    assert len(data["choices"]) > 0
    assert data["choices"][0]["message"]["role"] == "assistant"

def test_tool_call_chat_completion():
    """测试工具调用聊天补全"""
    request_data = {
        "model": "test-model",
        "messages": [
            {"role": "user", "content": "现在北京时间是几点？"}
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
    
    response = client.post("/v1/chat/completions", json=request_data)
    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert data["object"] == "chat.completion"
    assert len(data["choices"]) > 0

def test_tool_result_chat_completion():
    """测试工具结果处理"""
    request_data = {
        "model": "test-model",
        "messages": [
            {"role": "user", "content": "现在北京时间是几点？"},
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": "test_tool_call_id",
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
                "content": '{"timezone": "Asia/Shanghai", "current_time": "2025-08-12 13:30:01 CST", "timestamp": 1754976601.004147, "status": "success"}',
                "tool_call_id": "test_tool_call_id"
            }
        ],
        "temperature": 0.7,
        "max_tokens": 1000
    }
    
    response = client.post("/v1/chat/completions", json=request_data)
    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert data["object"] == "chat.completion"
    assert len(data["choices"]) > 0

def test_tool_result_with_followup_tool_call():
    """测试工具结果后可能还需要调用其他工具的情况"""
    request_data = {
        "model": "test-model",
        "messages": [
            {"role": "user", "content": "获取北京时间，然后查询北京的天气"},
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": "test_tool_call_id_1",
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
                "content": '{"timezone": "Asia/Shanghai", "current_time": "2025-08-12 13:30:01 CST", "timestamp": 1754976601.004147, "status": "success"}',
                "tool_call_id": "test_tool_call_id_1"
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
            },
            {
                "type": "function",
                "function": {
                    "name": "get_weather",
                    "description": "获取指定位置的天气信息",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "location": {
                                "description": "城市名称，例如：北京、上海、New York",
                                "type": "string"
                            },
                            "unit": {
                                "description": "温度单位，默认为摄氏度",
                                "enum": ["celsius", "fahrenheit"],
                                "type": "string"
                            }
                        },
                        "required": ["location"]
                    }
                }
            }
        ],
        "tool_choice": "auto"
    }
    
    response = client.post("/v1/chat/completions", json=request_data)
    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert data["object"] == "chat.completion"
    assert len(data["choices"]) > 0
    
    # 检查响应是否可能包含工具调用
    message = data["choices"][0]["message"]
    assert "role" in message
    assert message["role"] == "assistant"

if __name__ == "__main__":
    print("运行测试...")
    
    try:
        test_health_check()
        print("✓ 健康检查测试通过")
    except Exception as e:
        print(f"✗ 健康检查测试失败: {e}")
    
    try:
        test_root_endpoint()
        print("✓ 根路径测试通过")
    except Exception as e:
        print(f"✗ 根路径测试失败: {e}")
    
    try:
        test_regular_chat_completion()
        print("✓ 普通聊天补全测试通过")
    except Exception as e:
        print(f"✗ 普通聊天补全测试失败: {e}")
    
    try:
        test_tool_call_chat_completion()
        print("✓ 工具调用聊天补全测试通过")
    except Exception as e:
        print(f"✗ 工具调用聊天补全测试失败: {e}")
    
    try:
        test_tool_result_chat_completion()
        print("✓ 工具结果处理测试通过")
    except Exception as e:
        print(f"✗ 工具结果处理测试失败: {e}")
    
    try:
        test_tool_result_with_followup_tool_call()
        print("✓ 工具结果后工具调用测试通过")
    except Exception as e:
        print(f"✗ 工具结果后工具调用测试失败: {e}")
    
    print("测试完成!")