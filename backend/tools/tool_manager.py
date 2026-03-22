"""Tool Manager for LLM function calling."""

from __future__ import annotations

import asyncio
import inspect
import json
import logging
from collections.abc import Awaitable, Callable
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


# Type alias for tool functions
ToolFunc = Callable[..., Awaitable[str]]


class ToolManager:
    """Manages tool registration and execution for LLM function calling."""

    def __init__(self):
        self._tools: dict[str, ToolFunc] = {}
        self._schemas: dict[str, dict[str, Any]] = {}

    def register(self, name: str, func: ToolFunc, description: str = "") -> None:
        """Register a tool function.

        Args:
            name: Tool name (used in LLM function call)
            func: Async function to execute
            description: Tool description for LLM
        """
        self._tools[name] = func
        self._schemas[name] = self._generate_schema(name, func, description)
        logger.debug("Registered tool: %s", name)

    def _generate_schema(
        self, name: str, func: ToolFunc, description: str
    ) -> dict[str, Any]:
        """Generate OpenAI function schema from function signature."""
        sig = inspect.signature(func)
        parameters: dict[str, Any] = {"type": "object", "properties": {}, "required": []}

        for param_name, param in sig.parameters.items():
            if param_name in ("db", "session"):
                continue  # Skip injected parameters

            param_info: dict[str, Any] = {"type": "string"}
            param_desc = ""

            # Extract description from docstring if available
            if func.__doc__:
                for line in func.__doc__.split("\n"):
                    line = line.strip()
                    if line.lower().startswith(f"{param_name}:"):
                        param_desc = line.split(":", 1)[1].strip()
                        param_info["description"] = param_desc
                        break

            # Infer type from annotation
            if param.annotation != inspect.Parameter.empty:
                if param.annotation in (int, "int"):
                    param_info["type"] = "integer"
                elif param.annotation in (float, "float"):
                    param_info["type"] = "number"
                elif param.annotation in (bool, "bool"):
                    param_info["type"] = "boolean"
                elif param.annotation in (list, "list") or str(param.annotation).startswith("list"):
                    param_info["type"] = "array"
                elif param.annotation in (dict, "dict") or str(param.annotation).startswith("dict"):
                    param_info["type"] = "object"

            parameters["properties"][param_name] = param_info

            # Mark as required if no default value
            if param.default == inspect.Parameter.empty:
                parameters["required"].append(param_name)

        return {
            "type": "function",
            "function": {
                "name": name,
                "description": description or func.__doc__ or f"Execute {name}",
                "parameters": parameters,
            },
        }

    def get_openai_tools(self) -> list[dict[str, Any]]:
        """Get all registered tools in OpenAI format."""
        return list(self._schemas.values())

    async def execute(
        self, name: str, args: dict[str, Any], db: AsyncSession | None = None
    ) -> str:
        """Execute a registered tool.

        Args:
            name: Tool name
            args: Tool arguments
            db: Database session (injected if tool needs it)

        Returns:
            Tool execution result as string
        """
        if name not in self._tools:
            return f"Error: Tool '{name}' not found"

        func = self._tools[name]
        sig = inspect.signature(func)

        # Inject db session if needed
        if "db" in sig.parameters and db is not None:
            args = {**args, "db": db}

        try:
            result = await func(**args)
            return result
        except Exception as e:
            logger.error("Tool %s execution failed: %s", name, e)
            return f"Error executing {name}: {e}"


def tool(name: str, description: str = "") -> Callable[[ToolFunc], ToolFunc]:
    """Decorator to register a tool function.

    Usage:
        @tool("search_repos", "Search user's repositories")
        async def search_repos(query: str, db: AsyncSession) -> str:
            ...
    """
    def decorator(func: ToolFunc) -> ToolFunc:
        # Will be registered when tool manager is created
        func._tool_name = name
        func._tool_description = description
        return func
    return decorator


# Global tool manager instance
_global_tool_manager: ToolManager | None = None


def get_tool_manager() -> ToolManager:
    """Get or create the global tool manager."""
    global _global_tool_manager
    if _global_tool_manager is None:
        _global_tool_manager = ToolManager()
        _register_builtin_tools(_global_tool_manager)
    return _global_tool_manager


def _register_builtin_tools(manager: ToolManager) -> None:
    """Register built-in tools."""
    from tools.builtin import repository_tools

    # Register repository tools
    for name, func in repository_tools.get_tools().items():
        desc = getattr(func, "_tool_description", "")
        manager.register(name, func, desc)
