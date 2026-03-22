"""OpenAI client object and request wrappers."""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncGenerator
from typing import Any

from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession

from config import Settings

logger = logging.getLogger(__name__)


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
        tools: list[dict[str, Any]] | None = None,
    ) -> str:
        kwargs: dict[str, Any] = {
            "model": self.settings.openai_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if enforce_json:
            kwargs["response_format"] = {"type": "json_object"}
        if tools:
            kwargs["tools"] = tools

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

    async def create_chat_completion_with_tools(
        self,
        *,
        messages: list[dict[str, Any]],
        temperature: float,
        max_tokens: int,
        tools: list[dict[str, Any]],
        tool_executor: callable,
        db: AsyncSession,
        max_iterations: int = 5,
    ) -> AsyncGenerator[str | dict[str, Any], None]:
        """Create chat completion with tool support.

        Yields:
            - String tokens during final response streaming
            - Dict with tool call info when tools are executed

        Tool call loop:
        1. Send request with tools
        2. If tool_calls, execute them and continue
        3. If no tool_calls, stream the final response
        """
        current_messages = messages.copy()

        for iteration in range(max_iterations):
            response = await self._client.chat.completions.create(
                model=self.settings.openai_model,
                messages=current_messages,
                temperature=temperature,
                max_tokens=max_tokens,
                tools=tools,
                tool_choice="auto",
            )

            message = response.choices[0].message

            # Check if LLM wants to call tools
            if not message.tool_calls:
                # No tool calls - stream the final response
                if message.content:
                    yield {"type": "content", "content": message.content}
                return

            # Execute tool calls
            current_messages.append({
                "role": "assistant",
                "content": message.content or "",
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in message.tool_calls
                ],
            })

            for tool_call in message.tool_calls:
                func_name = tool_call.function.name
                try:
                    func_args = json.loads(tool_call.function.arguments)
                except json.JSONDecodeError:
                    func_args = {}

                # Notify about tool execution
                yield {
                    "type": "tool_call",
                    "name": func_name,
                    "args": func_args,
                }

                # Execute the tool
                tool_result = await tool_executor(func_name, func_args, db)

                # Add tool result to messages
                current_messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": tool_result,
                })

                # Notify about tool result
                yield {
                    "type": "tool_result",
                    "name": func_name,
                    "result": tool_result[:500] + "..." if len(tool_result) > 500 else tool_result,
                }

        # Max iterations reached - get final response without tools
        final_response = await self._client.chat.completions.create(
            model=self.settings.openai_model,
            messages=current_messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        if final_response.choices[0].message.content:
            yield {"type": "content", "content": final_response.choices[0].message.content}

    async def create_embedding(self, text_content: str) -> list[float]:
        max_len = self.settings.openai_embedding_max_text_length
        response = await self._client.embeddings.create(
            model=self.settings.openai_embedding_model,
            input=text_content[:max_len],
        )
        return response.data[0].embedding
