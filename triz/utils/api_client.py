"""OpenAI API 客户端封装"""
from openai import OpenAI
from triz.config import OPENAI_API_KEY, OPENAI_BASE_URL, MODEL_NAME


class OpenAIClient:
    """封装 OpenAI API 调用，提供统一的 chat 接口。"""

    def __init__(self, api_key: str = None, model: str = None, base_url: str = None):
        self.api_key = api_key or OPENAI_API_KEY
        self.model = model or MODEL_NAME
        self.base_url = base_url or OPENAI_BASE_URL
        if not self.api_key:
            raise ValueError("OpenAI API key is required. Set OPENAI_API_KEY in .env")
        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)

    def chat(self, prompt: str, system_prompt: str = "", temperature: float = 0.7, json_mode: bool = False) -> str:
        """发送单轮对话请求，返回文本内容。"""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        response = self.client.chat.completions.create(**kwargs)
        return response.choices[0].message.content or ""

    def chat_structured(self, prompt: str, system_prompt: str = "", temperature: float = 0.7) -> str:
        """强制 JSON 输出模式。"""
        return self.chat(prompt, system_prompt, temperature, json_mode=True)

    def chat_with_tools(self, messages: list, tools: list,
                        temperature: float = 0.3):
        """支持 function calling 的对话，返回原始 response 对象。

        调用方需要检查 response.choices[0].message.tool_calls 来决定是否继续对话。
        """
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=tools,
            tool_choice="auto",
            temperature=temperature,
        )
        return response
