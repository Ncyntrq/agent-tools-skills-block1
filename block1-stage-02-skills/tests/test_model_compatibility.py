"""Provider extension round-trip tests; no real model or credentials used."""

from copy import deepcopy
import json

from langchain_core.messages import HumanMessage, ToolMessage
from langchain_openai import ChatOpenAI

from agent import CompatibleChatOpenAI


def model():
    return CompatibleChatOpenAI(model="synthetic-model", api_key="synthetic", base_url="https://example.invalid/v1")


def response(signature=None, call_id="call-1", parallel=False):
    call = {"id": call_id, "type": "function", "function": {"name": "read_file", "arguments": '{"path":"data/note.md"}'}}
    if signature is not None:
        call["extra_content"] = {"google": {"thought_signature": signature}}
    calls = [call]
    if parallel:
        calls.append({"id": "call-2", "type": "function", "function": {"name": "list_files", "arguments": '{"path":"data"}'}})
    return {"choices": [{"message": {"role": "assistant", "content": None, "tool_calls": calls}, "finish_reason": "tool_calls"}]}

def normalized(call):
    result = deepcopy(call)
    result["function"]["arguments"] = json.loads(result["function"]["arguments"])
    return result


def test_signed_parallel_tool_call_metadata_round_trips():
    chat = model()
    raw = response("synthetic-signature", parallel=True)
    ai = chat._create_chat_result(raw).generations[0].message
    payload = chat._get_request_payload([
        HumanMessage(content="Read the note"), ai,
        ToolMessage(content='{"ok":true}', tool_call_id="call-1"),
        ToolMessage(content='{"ok":true}', tool_call_id="call-2"),
    ])
    calls = payload["messages"][1]["tool_calls"]
    assert normalized(calls[0]) == normalized(raw["choices"][0]["message"]["tool_calls"][0])
    assert normalized(calls[1]) == normalized(raw["choices"][0]["message"]["tool_calls"][1])
    assert "extra_content" not in calls[1]


def test_metadata_remains_attached_to_its_message_when_ids_repeat():
    chat = model()
    first = chat._create_chat_result(response("signature-one")).generations[0].message
    second = chat._create_chat_result(response("signature-two")).generations[0].message
    payload = chat._get_request_payload([first, second])
    assert payload["messages"][0]["tool_calls"][0]["extra_content"]["google"]["thought_signature"] == "signature-one"
    assert payload["messages"][1]["tool_calls"][0]["extra_content"]["google"]["thought_signature"] == "signature-two"


def test_metadata_is_copied_without_mutating_history_or_response():
    chat = model()
    raw = response("synthetic-signature")
    original = deepcopy(raw)
    ai = chat._create_chat_result(raw).generations[0].message
    payload = chat._get_request_payload([ai])
    payload["messages"][0]["tool_calls"][0]["extra_content"]["google"]["thought_signature"] = "changed"
    assert raw == original
    assert ai.additional_kwargs["provider_tool_call_extras"]["call-1"]["google"]["thought_signature"] == "synthetic-signature"


def test_ordinary_tool_calls_do_not_gain_provider_metadata():
    chat = model()
    raw = response()
    ai = chat._create_chat_result(raw).generations[0].message
    assert "provider_tool_call_extras" not in ai.additional_kwargs
    payload = chat._get_request_payload([ai])
    baseline = ChatOpenAI(model="synthetic-model", api_key="synthetic", base_url="https://example.invalid/v1")
    assert payload == baseline._get_request_payload([ai])
