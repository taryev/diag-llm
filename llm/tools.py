import json
from collections.abc import Callable
from dataclasses import dataclass

from openai.types.chat import ChatCompletionToolParam
from pydantic import BaseModel, ValidationError

from icd import get_icd_from_autocode

from .schemas import ICDAutocodeArgs


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    args_model: type[BaseModel]  # Args models must be derived from BaseModel
    fn: Callable[..., object]  # fn(...) -> object

    def to_openai(self) -> ChatCompletionToolParam:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.args_model.model_json_schema(),
            },
        }


# Registered tools
# To add a new tool to the project, add a new Tool object in the list
# The TOOLS dict gets built by comprehension
TOOLS: dict[str, Tool] = {
    t.name: t
    for t in [
        Tool(
            name="get_icd_from_autocode",
            description=get_icd_from_autocode.__doc__ or "",
            args_model=ICDAutocodeArgs,
            fn=get_icd_from_autocode,
        ),
    ]
}

# Typed tools list for OpenAI API
tools: list[ChatCompletionToolParam] = [t.to_openai() for t in TOOLS.values()]


def execute_tool(tool_call) -> dict:
    tool = TOOLS.get(tool_call.function.name)
    if tool is None:
        return {"error": f"unknown function: {tool_call.function.name}"}

    try:
        raw_args = json.loads(tool_call.function.arguments)
    except json.JSONDecodeError:
        return {"error": "invalid JSON arguments"}

    try:
        args = tool.args_model.model_validate(raw_args)
        res = tool.fn(**args.model_dump())
        return res if isinstance(res, dict) else {"result": res}
    except ValidationError as e:
        return {"error": f"invalid arguments: {e.errors(include_url=False)}"}
    except Exception as e:
        return {"error": f"tool execution failed: {type(e).__name__}: {e}"}
