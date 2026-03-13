"""OpenAI client and thin request wrappers."""

from typing import Any

from openai import AsyncOpenAI

from config import get_settings

settings = get_settings()

client = AsyncOpenAI(
    api_key=settings.openai_api_key,
    base_url=settings.openai_base_url,
)


async def create_chat_completion(
    *,
    messages: list[dict[str, str]],
    temperature: float,
    max_tokens: int,
    enforce_json: bool = False,
) -> str:
    kwargs: dict[str, Any] = {
        "model": settings.openai_model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if enforce_json:
        kwargs["response_format"] = {"type": "json_object"}

    response = await client.chat.completions.create(**kwargs)
    return (response.choices[0].message.content or "").strip()


async def create_embedding(text_content: str) -> list[float]:
    response = await client.embeddings.create(
        model=settings.openai_embedding_model,
        input=text_content[:8000],
    )
    return response.data[0].embedding
