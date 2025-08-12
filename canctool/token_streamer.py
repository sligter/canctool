"""
Token-based streaming utility using tiktoken
"""

import asyncio
import logging
from typing import AsyncGenerator, Optional

try:
    import tiktoken
except ImportError:
    tiktoken = None

logger = logging.getLogger(__name__)


class TokenStreamer:
    """Token-based streaming utility"""
    
    def __init__(self, model_name: str = "gpt-3.5-turbo"):
        self.model_name = model_name
        self.encoding = None
        self._initialize_encoding()
    
    def _initialize_encoding(self):
        """Initialize tiktoken encoding"""
        if tiktoken is None:
            logger.warning("tiktoken not available, falling back to character-based streaming")
            return
        
        try:
            # Try to get encoding for the specific model
            self.encoding = tiktoken.encoding_for_model(self.model_name)
            logger.debug(f"Initialized tiktoken encoding for model: {self.model_name}")
        except KeyError:
            # Fallback to cl100k_base encoding (used by GPT-3.5 and GPT-4)
            try:
                self.encoding = tiktoken.get_encoding("cl100k_base")
                logger.debug(f"Using cl100k_base encoding for model: {self.model_name}")
            except Exception as e:
                logger.warning(f"Failed to initialize tiktoken encoding: {e}")
                self.encoding = None
    
    def tokenize(self, text: str) -> list:
        """Tokenize text into tokens"""
        if self.encoding is None:
            # Fallback: split by characters for basic streaming
            return list(text)
        
        try:
            tokens = self.encoding.encode(text)
            return tokens
        except Exception as e:
            logger.warning(f"Tokenization failed: {e}, falling back to character split")
            return list(text)
    
    def decode_token(self, token) -> str:
        """Decode a single token back to text"""
        if self.encoding is None:
            # Fallback: return character as-is
            return str(token)

        try:
            if isinstance(token, int):
                # 使用errors='ignore'来处理无效的token
                decoded = self.encoding.decode([token])
                # 过滤掉控制字符和无效字符
                if decoded and decoded.isprintable() or decoded.isspace():
                    return decoded
                else:
                    # 如果解码结果包含不可打印字符，跳过
                    return ""
            else:
                return str(token)
        except Exception as e:
            logger.debug(f"Token decoding failed for token {token}: {e}")
            return ""
    
    def decode_tokens(self, tokens: list) -> str:
        """Decode a list of tokens back to text"""
        if self.encoding is None:
            # Fallback: join characters
            return ''.join(str(token) for token in tokens)

        try:
            # Filter out non-integer tokens for safety
            int_tokens = [token for token in tokens if isinstance(token, int)]
            if not int_tokens:
                return ""

            # 使用errors='ignore'来处理无效的token序列
            decoded = self.encoding.decode(int_tokens)
            # 确保返回的是有效的UTF-8字符串
            return decoded.encode('utf-8', errors='ignore').decode('utf-8')
        except Exception as e:
            logger.warning(f"Tokens decoding failed: {e}")
            # 尝试逐个解码并拼接
            result = ""
            for token in tokens:
                try:
                    if isinstance(token, int):
                        decoded = self.encoding.decode([token])
                        if decoded and (decoded.isprintable() or decoded.isspace()):
                            result += decoded
                except:
                    continue
            return result
    
    async def stream_tokens(self, text: str, delay: float = 0.01) -> AsyncGenerator[str, None]:
        """Stream text using word-based chunking (more reliable than token-based)"""
        if not text:
            return

        # 使用更成熟的基于单词的流式输出方法
        # 这种方法更稳定，避免了token解码的复杂性

        # 按单词和标点符号分割
        import re
        # 使用正则表达式分割，保留空格和标点
        chunks = re.findall(r'\S+|\s+', text)

        logger.debug(f"Streaming {len(chunks)} word chunks with {delay}s delay")

        for chunk in chunks:
            if chunk.strip():  # 非空白chunk
                yield chunk
                await asyncio.sleep(delay)
            elif chunk.isspace():  # 空白字符
                yield chunk
                await asyncio.sleep(delay * 0.5)  # 空白字符延迟减半
    
    async def stream_tokens_chunked(self, text: str, chunk_size: int = 3,
                                   delay: float = 0.01) -> AsyncGenerator[str, None]:
        """Stream text in character-based chunks (more reliable)"""
        if not text:
            return

        # 使用字符级分块，更稳定可靠
        logger.debug(f"Streaming text in character chunks of size {chunk_size}")

        for i in range(0, len(text), chunk_size):
            chunk = text[i:i + chunk_size]
            if chunk:
                yield chunk
                await asyncio.sleep(delay)
    
    def get_token_count(self, text: str) -> int:
        """Get the number of tokens in text"""
        if self.encoding is None:
            return len(text)  # Fallback to character count
        
        try:
            tokens = self.encoding.encode(text)
            return len(tokens)
        except Exception as e:
            logger.warning(f"Token counting failed: {e}")
            return len(text)
    
    @staticmethod
    def is_tiktoken_available() -> bool:
        """Check if tiktoken is available"""
        return tiktoken is not None
    
    def get_encoding_info(self) -> dict:
        """Get information about the current encoding"""
        return {
            "model_name": self.model_name,
            "encoding_available": self.encoding is not None,
            "tiktoken_available": self.is_tiktoken_available(),
            "encoding_name": getattr(self.encoding, 'name', None) if self.encoding else None
        }
