"""Refund metadata stays in the catalog; procedures stay in skill resources."""

import paths
from agent import system_prompt
from reset_workspace import reset_workspace
from skill_catalog import parse_frontmatter, scan_skills


def test_refund_metadata_and_initial_prompt_only(lab_dirs):
    catalog = scan_skills(paths.WORKSPACE_DIR)
    skill = next(s for s in catalog.skills if s.name == "refund-policy")
    assert skill.location == "skills/refund-policy/SKILL.md"
    text = (paths.WORKSPACE_DIR / skill.location).read_text(encoding="utf-8")
    meta = parse_frontmatter(text)
    assert meta["name"] == "refund-policy"
    assert all(term in meta["description"] for term in ["ngày mua", "ngày yêu cầu", "kích hoạt"])
    prompt = system_prompt()
    assert "<name>refund-policy</name>" in prompt
    assert skill.description in prompt
    assert f"<location>{skill.location}</location>" in prompt
    body = text.split("---", 2)[2].strip()
    reference = paths.WORKSPACE_DIR / "skills/refund-policy/references/answer-template.md"
    assert body not in prompt
    assert body.splitlines()[0] not in prompt
    assert reference.read_text(encoding="utf-8").splitlines()[0] not in prompt
    for term in ["answer-template.md", "data/policies", "policy-before-oct.md", "policy-from-oct.md", "2026-10-01", "14 ngày", "7 ngày"]:
        assert term not in prompt
    for policy in (paths.WORKSPACE_DIR / "data/policies").iterdir():
        assert policy.name not in text
        assert policy.read_text(encoding="utf-8") not in prompt


def test_refund_fixture_workspace_and_reset_match(lab_dirs):
    relative_paths = [
        "skills/refund-policy/SKILL.md",
        "skills/refund-policy/references/answer-template.md",
    ]
    for relative in relative_paths:
        assert (paths.WORKSPACE_DIR / relative).read_bytes() == (paths.FIXTURES_DIR / relative).read_bytes()
    (paths.WORKSPACE_DIR / relative_paths[0]).write_text("changed")
    reset_workspace()
    assert [s.name for s in scan_skills(paths.WORKSPACE_DIR).skills] == ["refund-policy", "weekly-report"]
    for relative in relative_paths:
        assert (paths.WORKSPACE_DIR / relative).read_bytes() == (paths.FIXTURES_DIR / relative).read_bytes()
