"""LangChain agent của stage 02: read_file, write_file, list_files + skill catalog trong system prompt."""

from copy import deepcopy

from langchain.agents import create_agent
from langchain.agents.middleware import ModelCallLimitMiddleware, ToolCallLimitMiddleware
from langchain_core.messages import AIMessage
from langchain_openai import ChatOpenAI

import paths
from config import MODEL_CALL_LIMIT, TOOL_CALL_LIMIT, Settings
from observer import ObserverMiddleware
from prompts import build_system_prompt
from skill_catalog import Catalog, render_catalog, scan_skills
from tools import list_files, read_file, write_file

TOOLS = [read_file, write_file, list_files]

class CompatibleChatOpenAI(ChatOpenAI):
    """Round-trip provider tool-call extra_content through Chat Completions.

    Gemini-compatible endpoints require their returned thought signatures on
    subsequent requests. Preserve the actual metadata per message and call ID;
    never synthesize signatures or bypass provider validation.
    """

    def _create_chat_result(self, response, generation_info=None):
        result = super()._create_chat_result(response, generation_info)
        raw = response if isinstance(response, dict) else response.model_dump(warnings=False)
        for choice, generation in zip(raw["choices"], result.generations):
            extras = {
                call["id"]: deepcopy(call["extra_content"])
                for call in choice["message"].get("tool_calls", []) or []
                if call.get("id") and isinstance(call.get("extra_content"), dict)
            }
            if extras and isinstance(generation.message, AIMessage):
                generation.message.additional_kwargs["provider_tool_call_extras"] = extras
        return result

    def _get_request_payload(self, input_, *, stop=None, **kwargs):
        payload = super()._get_request_payload(input_, stop=stop, **kwargs)
        messages = self._convert_input(input_).to_messages()
        for message, wire in zip(messages, payload.get("messages", [])):
            if isinstance(message, AIMessage):
                extras = message.additional_kwargs.get("provider_tool_call_extras", {})
                for call in wire.get("tool_calls", []):
                    if call["id"] in extras:
                        call["extra_content"] = deepcopy(extras[call["id"]])
        return payload


def build_model(settings: Settings) -> ChatOpenAI:
    kwargs = {"model": settings.model_name, "api_key": settings.api_key}
    if settings.base_url:
        kwargs["base_url"] = settings.base_url
    return CompatibleChatOpenAI(**kwargs)


def load_catalog() -> Catalog:
    return scan_skills(paths.WORKSPACE_DIR)


def system_prompt() -> str:
    return build_system_prompt(render_catalog(load_catalog()))


def capabilities() -> dict:
    catalog = load_catalog()
    return {"tools": [t.name for t in TOOLS], "skills": catalog.metadata(), "skill_diagnostics": catalog.diagnostics}


def build_agent(model):
    return create_agent(
        model=model,
        tools=TOOLS,
        system_prompt=system_prompt(),
        middleware=[
            ModelCallLimitMiddleware(run_limit=MODEL_CALL_LIMIT, exit_behavior="end"),
            ToolCallLimitMiddleware(run_limit=TOOL_CALL_LIMIT),
            ObserverMiddleware(),  # cuối danh sách = sát model/tool invocation nhất
        ],
    )
