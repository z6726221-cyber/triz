"""OpenAI API 客户端封装"""

import time
import logging
from openai import OpenAI
from openai import RateLimitError
from triz_pipeline.config import (
    OPENAI_API_KEY,
    OPENAI_BASE_URL,
    MODEL_NAME,
    API_MAX_RETRIES,
    API_BASE_DELAY,
)

logger = logging.getLogger(__name__)


class OpenAIClient:
    """封装 OpenAI API 调用，提供统一的 chat 接口。"""

    MAX_RETRIES = API_MAX_RETRIES
    BASE_DELAY = API_BASE_DELAY

    def __init__(self, api_key: str = None, model: str = None, base_url: str = None):
        self.api_key = api_key or OPENAI_API_KEY
        self.model = model or MODEL_NAME
        self.base_url = base_url or OPENAI_BASE_URL
        if not self.api_key:
            raise ValueError("OpenAI API key is required. Set OPENAI_API_KEY in .env")
        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)

    @staticmethod
    def _is_rate_limit_error(e: Exception) -> bool:
        """判断异常是否为速率限制错误（兼容多种 API 代理）。"""
        # 1. OpenAI 原生 RateLimitError
        if isinstance(e, RateLimitError):
            return True
        # 2. APIStatusError with status_code 429
        if hasattr(e, "status_code") and e.status_code == 429:
            return True
        # 3. 错误消息中包含 429 / rate limit / throttling 关键词
        msg = str(e).lower()
        return any(
            kw in msg
            for kw in (
                "429",
                "rate limit",
                "ratelimit",
                "throttling",
                "quota exceeded",
                "concurrency",
            )
        )

    @staticmethod
    def _extract_retry_after(e: Exception) -> float | None:
        """从异常中提取 Retry-After 秒数。"""
        # 1. 从响应头中读取（OpenAI 原生格式）
        if hasattr(e, "response") and hasattr(e.response, "headers"):
            ra = e.response.headers.get("retry-after") or e.response.headers.get(
                "Retry-After"
            )
            if ra:
                try:
                    return float(ra)
                except ValueError:
                    pass
        # 2. 从错误消息中匹配（兼容 LiteLLM 等代理）
        import re

        msg = str(e)
        m = re.search(r"retry[_\s]?after[:=]\s*(\d+(?:\.\d+)?)", msg, re.IGNORECASE)
        if m:
            return float(m.group(1))
        return None

    def _call_with_retry(self, create_fn):
        """带退避重试的 API 调用。优先使用 API 返回的 Retry-After。"""
        for attempt in range(self.MAX_RETRIES):
            try:
                return create_fn()
            except Exception as e:
                if not self._is_rate_limit_error(e):
                    logger.error(
                        f"API 调用失败 (非速率限制错误): model={self.model}, "
                        f"base_url={self.base_url}, error={type(e).__name__}: {e}"
                    )
                    raise
                if attempt == self.MAX_RETRIES - 1:
                    logger.error(
                        f"API 速率限制重试耗尽: model={self.model}, "
                        f"base_url={self.base_url}, attempts={self.MAX_RETRIES}, "
                        f"last_error={type(e).__name__}: {e}"
                    )
                    raise
                # 优先使用 API 返回的 Retry-After，否则用指数退避
                ra = self._extract_retry_after(e)
                if ra is not None and ra > 0:
                    delay = ra
                else:
                    delay = self.BASE_DELAY * (2**attempt)
                # 限制最大等待时间，避免无限阻塞
                delay = min(delay, 60)
                logger.warning(
                    f"API 速率限制，等待 {delay:.1f}s 后重试 "
                    f"(attempt {attempt + 1}/{self.MAX_RETRIES}): "
                    f"model={self.model}, error={type(e).__name__}"
                )
                time.sleep(delay)
        raise RuntimeError("Unexpected exit from retry loop")

    def chat(
        self,
        prompt: str,
        system_prompt: str = "",
        temperature: float = 0.7,
        json_mode: bool = False,
    ) -> str:
        """发送单轮对话请求，返回文本内容。"""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "timeout": 90,
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        response = self._call_with_retry(
            lambda: self.client.chat.completions.create(**kwargs)
        )
        return response.choices[0].message.content or ""

    def chat_structured(
        self, prompt: str, system_prompt: str = "", temperature: float = 0.7
    ) -> str:
        """强制 JSON 输出模式。"""
        return self.chat(prompt, system_prompt, temperature, json_mode=True)

    def chat_with_tools(
        self, messages: list, tools: list, temperature: float = 0.3, model: str = None
    ):
        """支持 function calling 的对话，返回原始 response 对象。

        调用方需要检查 response.choices[0].message.tool_calls 来决定是否继续对话。

        Args:
            model: 可临时覆盖默认模型（用于不同 Skill 使用不同模型）
        """
        return self._call_with_retry(
            lambda: self.client.chat.completions.create(
                model=model or self.model,
                messages=messages,
                tools=tools,
                tool_choice="auto",
                temperature=temperature,
                timeout=90,
            )
        )
