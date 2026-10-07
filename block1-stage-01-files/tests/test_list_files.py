"""Directory discovery: real tools, security, schema binding and reset preservation."""

import json

import pytest
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.utils.function_calling import convert_to_openai_tool

import paths
from agent import TOOLS, build_agent
from reset_workspace import reset_workspace
from tests.conftest import ScriptedChatModel
from tests.test_agent import stream_events
from tools import list_files
from tools.files import _list


def test_direct_children_sorted_with_name_path_type(tmp_path):
    workspace = tmp_path / "workspace"
    folder = workspace / "data"
    (folder / "z-folder").mkdir(parents=True)
    (folder / "z-folder" / "nested.md").write_text("nested")
    (folder / "b.md").write_text("B")
    (folder / "a.md").write_text("A")
    expected = {
        "ok": True, "path": "data",
        "entries": [
            {"name": "a.md", "path": "data/a.md", "type": "file"},
            {"name": "b.md", "path": "data/b.md", "type": "file"},
            {"name": "z-folder", "path": "data/z-folder", "type": "directory"},
        ],
    }
    assert _list(workspace, "data") == expected
    assert _list(workspace, "data/") == expected


def test_empty_directory_is_success(tmp_path):
    assert _list(tmp_path, ".") == {"ok": True, "path": ".", "entries": []}


def test_missing_directory_and_file_are_errors(tmp_path):
    (tmp_path / "note.md").write_text("synthetic")
    assert _list(tmp_path, "missing")["error"]["code"] == "DIRECTORY_NOT_FOUND"
    assert _list(tmp_path, "note.md")["error"]["code"] == "NOT_A_DIRECTORY"


@pytest.mark.parametrize("path", ["../outside", "data/../../outside", "~/outside"])
def test_escape_and_home_paths_are_blocked(tmp_path, path):
    assert _list(tmp_path, path)["error"]["code"] == "PATH_OUTSIDE_WORKSPACE"


def test_absolute_path_blocked(tmp_path):
    assert _list(tmp_path, str(tmp_path))["error"]["code"] == "PATH_OUTSIDE_WORKSPACE"


@pytest.mark.parametrize("path", ["", "   "])
def test_empty_path_blocked(tmp_path, path):
    assert _list(tmp_path, path)["error"]["code"] == "INVALID_PATH"


def test_invalid_path_is_structured(tmp_path):
    assert _list(tmp_path, "data/\0bad")["error"]["code"] == "INVALID_PATH"


def test_symlink_directory_escape_and_child_escape(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "note.md").write_text("synthetic")
    (workspace / "link").symlink_to(outside, target_is_directory=True)
    assert _list(workspace, "link")["error"]["code"] == "PATH_OUTSIDE_WORKSPACE"
    # Listing the parent must not follow an escaping child to inspect its type.
    result = _list(workspace, ".")
    assert result["error"]["code"] == "PATH_OUTSIDE_WORKSPACE"
    assert "entries" not in result


def test_internal_symlink_preserves_discovered_name_and_path(tmp_path):
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "note.md").write_text("synthetic")
    (tmp_path / "alias").symlink_to(tmp_path / "data", target_is_directory=True)
    entries = _list(tmp_path, ".")["entries"]
    assert entries[0] == {"name": "alias", "path": "alias", "type": "directory"}
    assert _list(tmp_path, "alias")["entries"][0]["path"] == "data/note.md"


def test_access_error_is_structured(tmp_path, monkeypatch):
    def denied(self):
        raise PermissionError("synthetic")
    monkeypatch.setattr(type(tmp_path), "iterdir", denied)
    assert _list(tmp_path, ".")["error"]["code"] == "DIRECTORY_ACCESS_ERROR"


def test_tool_invocation_and_schema_reach_model(lab_dirs, monkeypatch):
    bound = []
    def record_binding(self, tools, **kwargs):
        bound.extend(convert_to_openai_tool(tool)["function"] for tool in tools)
        return self
    monkeypatch.setattr(ScriptedChatModel, "bind_tools", record_binding)
    model = ScriptedChatModel(responses=[
        AIMessage(content="", tool_calls=[
            {"name": "list_files", "args": {"path": "data/policies"}, "id": "list-1"}
        ]),
        AIMessage(content="Discovery complete."),
    ])
    events, _ = stream_events(build_agent(model), [HumanMessage(content="List available policy documents.")])
    schema = next(tool for tool in bound if tool["name"] == "list_files")
    assert schema["parameters"]["required"] == ["path"]
    assert schema["parameters"]["properties"]["path"]["type"] == "string"
    assert [tool.name for tool in TOOLS] == ["read_file", "write_file", "list_files"]
    request = next(event["data"] for event in events if event["event"] == "model_request")
    assert "list_files" in [tool["name"] for tool in request["tools"]]
    finished = next(event["data"] for event in events if event["event"] == "tool_finished")
    assert finished["result"] == json.loads(list_files.invoke({"path": "data/policies"}))
    assert finished["result"]["ok"] is True
    assert len(finished["result"]["entries"]) == 2


def test_reset_restores_policy_assets(lab_dirs):
    policy_dir = paths.WORKSPACE_DIR / "data/policies"
    before = {p.name: p.read_bytes() for p in policy_dir.iterdir()}
    first = next(policy_dir.iterdir())
    first.rename(policy_dir / "renamed.md")
    reset_workspace()
    assert {p.name: p.read_bytes() for p in policy_dir.iterdir()} == before
