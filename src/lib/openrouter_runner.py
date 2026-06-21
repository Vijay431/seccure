import inspect
import json
import os
from collections.abc import Callable
from typing import Any

from openai import AsyncOpenAI
from pydantic import BaseModel

from src.config.config import RunLimits


class OpenRouterResponse:
    def __init__(self, text_content: str):
        self._text = text_content

    async def text(self) -> str:
        return self._text


class OpenRouterAgent:
    def __init__(
        self,
        system_instructions: str,
        tools: list[Callable] | None = None,
        model: str = "deepseek/deepseek-chat",
        response_schema: Any | None = None,
        max_tool_calls: int | None = None,
    ):
        self.system_prompt = system_instructions
        self.tools = tools or []
        self.model = model
        self.response_schema = response_schema
        self.max_tool_calls: int = (
            max_tool_calls
            if max_tool_calls is not None
            else RunLimits.COORDINATOR_MAX_TOOL_CALLS
        )
        self.client = AsyncOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.environ.get("OPENROUTER_API_KEY", "dummy_key"),
        )
        if tools:
            system_instructions += (
                "\n\nCRITICAL: You MUST call the provided tools to gather data "
                "FIRST. Do not generate the final response until you have "
                "successfully executed the required tools."
            )
        self.messages = [{"role": "system", "content": system_instructions}]
        self.tool_map = {t.__name__: t for t in self.tools}
        self.prompt_token_count = 0
        self.candidates_token_count = 0
        self.total_token_count = 0

    @staticmethod
    def _is_injected_param(param: inspect.Parameter) -> bool:
        if param.default is not inspect.Parameter.empty and callable(param.default):
            return True
        return "callable" in str(param.annotation).lower()

    @staticmethod
    def _serialize_tool_result(result: Any) -> str:
        if isinstance(result, BaseModel):
            return result.model_dump_json()
        try:
            return json.dumps(result)
        except TypeError:
            return str(result)

    @staticmethod
    def _prepare_tool_args(
        func: Callable,
        supplied_args: dict[str, Any],
    ) -> dict[str, Any]:
        sig = inspect.signature(func)
        args: dict[str, Any] = {}
        for name, param in sig.parameters.items():
            if not OpenRouterAgent._is_injected_param(param) and name in supplied_args:
                args[name] = supplied_args[name]
        return args

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

    def _get_tool_schemas(self) -> list[dict]:
        schemas = []
        for tool in self.tools:
            sig = inspect.signature(tool)
            properties = {}
            required = []
            for name, param in sig.parameters.items():
                if name == "self" or self._is_injected_param(param):
                    continue

                param_type = "string"
                ann = str(param.annotation).lower()
                if "int" in ann:
                    param_type = "integer"
                elif "bool" in ann:
                    param_type = "boolean"
                elif "float" in ann:
                    param_type = "number"
                elif "list" in ann:
                    param_type = "array"
                elif "dict" in ann or "any" in ann:
                    param_type = "object"

                prop: dict[str, Any] = {"type": param_type}
                if param_type == "array":
                    prop["items"] = {"type": "string"}

                properties[name] = prop
                if param.default == inspect.Parameter.empty:
                    required.append(name)

            desc = (tool.__doc__ or "").strip().split("\n")[0]
            schemas.append(
                {
                    "type": "function",
                    "function": {
                        "name": tool.__name__,
                        "description": desc or f"Tool {tool.__name__}",
                        "parameters": {
                            "type": "object",
                            "properties": properties,
                            "required": required,
                            "additionalProperties": False,
                        },
                    },
                }
            )
        return schemas

    async def chat(self, prompt: str) -> OpenRouterResponse:
        self.messages.append({"role": "user", "content": prompt})
        _tool_call_count: int = 0

        while True:
            # ----------------------------------------------------------------
            # Guard: prevent infinite tool-call loops
            # ----------------------------------------------------------------
            if _tool_call_count > self.max_tool_calls:
                raise RuntimeError(
                    f"[Seccure] OpenRouterAgent exceeded {self.max_tool_calls} "
                    f"tool calls. Aborting to prevent an infinite loop. "
                    f"Increase SECCURE_COORDINATOR_MAX_TOOLS (or "
                    f"SECCURE_SUBAGENT_MAX_TOOLS) to allow more steps."
                )
            kwargs: dict[str, Any] = {
                "model": self.model,
                "messages": self.messages,
            }
            if self.tools:
                kwargs["tools"] = self._get_tool_schemas()
                kwargs["tool_choice"] = "auto"
            if self.response_schema:
                kwargs["response_format"] = {"type": "json_object"}

            response = await self.client.chat.completions.create(**kwargs)

            if hasattr(response, "usage") and response.usage:
                self.prompt_token_count += getattr(response.usage, "prompt_tokens", 0)
                self.candidates_token_count += getattr(
                    response.usage,
                    "completion_tokens",
                    0,
                )
                self.total_token_count += getattr(response.usage, "total_tokens", 0)

            message = response.choices[0].message

            # OpenAI python package represents tool_calls as objects
            msg_dict = {"role": message.role}
            if message.content:
                msg_dict["content"] = message.content
            if message.tool_calls:
                msg_dict["tool_calls"] = [
                    {
                        "id": t.id,
                        "type": "function",
                        "function": {
                            "name": t.function.name,
                            "arguments": t.function.arguments,
                        },
                    }
                    for t in message.tool_calls
                ]

            self.messages.append(msg_dict)

            if not message.tool_calls:
                content = message.content or ""
                try:
                    content_json = json.loads(content)
                    if (
                        isinstance(content_json, dict)
                        and "name" in content_json
                        and content_json["name"] in self.tool_map
                    ):
                        func_name = content_json["name"]
                        args = content_json.get("parameters", {})
                        if "args" in content_json and not args:
                            args = content_json["args"]
                        print(
                            f"[OpenRouter Fallback] Calling tool: {func_name}({args})"
                        )
                        _tool_call_count += 1

                        func = self.tool_map[func_name]
                        call_args = self._prepare_tool_args(func, args)

                        if inspect.iscoroutinefunction(func):
                            result = await func(**call_args)
                        else:
                            result = func(**call_args)

                        self.messages.append(
                            {
                                "role": "user",
                                "content": (
                                    f"Tool {func_name} returned:\n"
                                    f"{self._serialize_tool_result(result)}"
                                ),
                            }
                        )
                        continue
                except Exception:
                    pass
                return OpenRouterResponse(content)

            for tool_call in message.tool_calls:
                func_name = tool_call.function.name
                args = json.loads(tool_call.function.arguments)
                print(f"[OpenRouter] Calling tool: {func_name}({args})")
                _tool_call_count += 1

                tool_func = self.tool_map.get(func_name)
                if tool_func is None:
                    result = f"Error: Tool {func_name} not found."
                else:
                    try:
                        call_args = self._prepare_tool_args(tool_func, args)

                        if inspect.iscoroutinefunction(tool_func):
                            result = await tool_func(**call_args)
                        else:
                            result = tool_func(**call_args)
                    except Exception as e:
                        result = f"Error: {e}"

                self.messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": func_name,
                        "content": self._serialize_tool_result(result),
                    }
                )

    @property
    def conversation(self):
        class UsageDummy:
            def __init__(self, agent):
                self.prompt_token_count = agent.prompt_token_count
                self.candidates_token_count = agent.candidates_token_count
                self.thoughts_token_count = 0
                self.total_token_count = agent.total_token_count

        class ConvDummy:
            def __init__(self, agent):
                self.total_usage = UsageDummy(agent)

        return ConvDummy(self)
