"""
Simple and reliable streaming utility
"""

import asyncio
import re
import logging
from typing import AsyncGenerator

logger = logging.getLogger(__name__)


class SimpleStreamer:
    """Simple and reliable text streaming utility"""
    
    def __init__(self, delay: float = 0.03):
        self.delay = delay
    
    async def stream_by_words(self, text: str) -> AsyncGenerator[str, None]:
        """Stream text word by word - most reliable method"""
        if not text:
            return
        
        # 使用简单的空格分割
        words = text.split()
        logger.debug(f"Streaming {len(words)} words")
        
        for i, word in enumerate(words):
            # 添加空格，除了最后一个单词
            if i < len(words) - 1:
                yield word + " "
            else:
                yield word
            await asyncio.sleep(self.delay)
    
    async def stream_by_sentences(self, text: str) -> AsyncGenerator[str, None]:
        """Stream text sentence by sentence"""
        if not text:
            return
        
        # 按句子分割（简单版本）
        sentences = re.split(r'([.!?]+\s*)', text)
        sentences = [s for s in sentences if s.strip()]
        
        logger.debug(f"Streaming {len(sentences)} sentences")
        
        for sentence in sentences:
            if sentence.strip():
                yield sentence
                await asyncio.sleep(self.delay * 2)  # 句子间延迟更长
    
    async def stream_by_chars(self, text: str, chunk_size: int = 1) -> AsyncGenerator[str, None]:
        """Stream text character by character or in small chunks"""
        if not text:
            return
        
        logger.debug(f"Streaming {len(text)} characters in chunks of {chunk_size}")
        
        for i in range(0, len(text), chunk_size):
            chunk = text[i:i + chunk_size]
            yield chunk
            await asyncio.sleep(self.delay)
    
    async def stream_by_tokens_simple(self, text: str) -> AsyncGenerator[str, None]:
        """Stream text using simple token-like chunks"""
        if not text:
            return
        
        # 使用正则表达式分割成类似token的块
        # 这种方法避免了复杂的编码问题
        pattern = r'(\w+|[^\w\s]|\s+)'
        chunks = re.findall(pattern, text)
        chunks = [chunk for chunk in chunks if chunk]
        
        logger.debug(f"Streaming {len(chunks)} token-like chunks")
        
        for chunk in chunks:
            yield chunk
            await asyncio.sleep(self.delay)
    
    async def stream_adaptive(self, text: str, mode: str = "words") -> AsyncGenerator[str, None]:
        """Adaptive streaming based on text length and content"""
        if not text:
            return
        
        text_length = len(text)
        
        # 根据文本长度选择合适的流式方法
        if mode == "words" or text_length < 100:
            # 短文本使用单词流式
            async for chunk in self.stream_by_words(text):
                yield chunk
        elif mode == "sentences" or text_length > 500:
            # 长文本使用句子流式
            async for chunk in self.stream_by_sentences(text):
                yield chunk
        else:
            # 中等长度文本使用简单token流式
            async for chunk in self.stream_by_tokens_simple(text):
                yield chunk
    
    def estimate_streaming_time(self, text: str, mode: str = "words") -> float:
        """Estimate total streaming time"""
        if mode == "words":
            word_count = len(text.split())
            return word_count * self.delay
        elif mode == "sentences":
            sentence_count = len(re.split(r'[.!?]+', text))
            return sentence_count * self.delay * 2
        elif mode == "chars":
            return len(text) * self.delay
        else:
            # token-like chunks
            chunks = re.findall(r'(\w+|[^\w\s]|\s+)', text)
            return len(chunks) * self.delay
    
    def get_chunk_count(self, text: str, mode: str = "words") -> int:
        """Get the number of chunks for a given mode"""
        if mode == "words":
            return len(text.split())
        elif mode == "sentences":
            return len(re.split(r'[.!?]+', text))
        elif mode == "chars":
            return len(text)
        else:
            # token-like chunks
            chunks = re.findall(r'(\w+|[^\w\s]|\s+)', text)
            return len(chunks)


# 便捷函数
async def stream_text(text: str, mode: str = "words", delay: float = 0.03) -> AsyncGenerator[str, None]:
    """Convenient function for streaming text"""
    streamer = SimpleStreamer(delay=delay)
    async for chunk in streamer.stream_adaptive(text, mode=mode):
        yield chunk


# 测试函数
async def test_streaming():
    """Test different streaming modes"""
    test_text = "Hello world! This is a test message. How are you today? 你好世界！"
    
    print("Testing word streaming:")
    async for chunk in stream_text(test_text, mode="words", delay=0.1):
        print(f"'{chunk}'", end="", flush=True)
    print("\n")
    
    print("Testing sentence streaming:")
    async for chunk in stream_text(test_text, mode="sentences", delay=0.2):
        print(f"[{chunk}]", end="", flush=True)
    print("\n")


if __name__ == "__main__":
    asyncio.run(test_streaming())
