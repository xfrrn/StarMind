"""OpenAI client object and request wrappers."""

from collections.abc import AsyncGenerator
from typing import Any

from openai import AsyncOpenAI

from config import Settings


class LLMClient:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._client = AsyncOpenAI(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
        )

    async def create_chat_completion(
        self,
        *,
        messages: list[dict[str, str]],
        temperature: float,
        max_tokens: int,
        enforce_json: bool = False,
    ) -> str:
        kwargs: dict[str, Any] = {
            "model": self.settings.openai_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if enforce_json:
            kwargs["response_format"] = {"type": "json_object"}

        response = await self._client.chat.completions.create(**kwargs)
        return (response.choices[0].message.content or "").strip()

    async def create_chat_completion_stream(
        self,
        *,
        messages: list[dict[str, str]],
        temperature: float,
        max_tokens: int,
    ) -> AsyncGenerator[str, None]:
        """Stream chat completion tokens one by one."""
        stream = await self._client.chat.completions.create(
            model=self.settings.openai_model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        )
        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    async def create_embedding(self, text_content: str) -> list[float]:
        max_len = self.settings.openai_embedding_max_text_length
        response = await self._client.embeddings.create(
            model=self.settings.openai_embedding_model,
            input=text_content[:max_len],
        )
        return response.data[0].embedding
