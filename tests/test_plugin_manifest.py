"""Validate Cursor plugin packaging. No live MCP calls."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SECRET_RE = re.compile(
    r"(clawdchat_[A-Za-z0-9]{8,}|sk_live_|password\s*=\s*\S+)",
    re.IGNORECASE,
)


def _read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def _json(rel: str) -> dict:
    return json.loads(_read(rel))


def test_plugin_manifest_required_fields() -> None:
    manifest = _json(".cursor-plugin/plugin.json")
    assert manifest["name"] == "clawdchat"
    assert re.fullmatch(r"[a-z0-9][a-z0-9.-]*[a-z0-9]", manifest["name"])
    assert manifest["description"].strip()
    assert len(manifest["description"]) <= 240
    assert manifest["version"]
    assert manifest["author"]["name"]
    assert manifest["logo"] == "assets/logo.svg"
    assert manifest["mcpServers"] == "./mcp.json"
    assert manifest["skills"] == "./skills/"
    assert (ROOT / manifest["logo"]).is_file()
    assert "mcp" in manifest["keywords"]


def test_mcp_points_at_hosted_https() -> None:
    mcp = _json("mcp.json")
    server = mcp["mcpServers"]["clawdchat"]
    assert server["type"] == "http"
    assert server["url"] == "https://mcp.clawdchat.ai/mcp"
    blob = json.dumps(mcp)
    assert "clawdchat_" not in blob
    assert "${" not in blob


def test_skill_frontmatter_and_triggers() -> None:
    text = _read("skills/clawdchat/SKILL.md")
    assert text.startswith("---\n")
    _, fm, body = text.split("---", 2)
    assert "name: clawdchat" in fm
    assert "description:" in fm
    desc = re.search(r"description:\s*>-\s*(.+?)(?:\n---|\Z)", text, re.S)
    assert desc, "skill description missing"
    description = " ".join(desc.group(1).split())
    assert 20 <= len(description) <= 1024
    for needle in ("虾聊", "ClawdChat", "MCP"):
        assert needle in description
    assert "curl" not in body.lower() or "Do not call `curl`" in body
    assert "web_url" in body
    assert "use_tools" in body
    assert "my_status" in body


def test_readme_and_docs_exist() -> None:
    for rel in ("README.md", "CLAUDE.md", "LICENSE", "CHANGELOG.md"):
        assert (ROOT / rel).is_file(), rel
    readme = _read("README.md")
    assert "https://mcp.clawdchat.ai/mcp" in readme
    assert "marketplace/publish" in readme


@pytest.mark.parametrize(
    "rel",
    [
        ".cursor-plugin/plugin.json",
        "mcp.json",
        "README.md",
        "CLAUDE.md",
        "skills/clawdchat/SKILL.md",
    ],
)
def test_no_secrets_in_packaged_files(rel: str) -> None:
    assert SECRET_RE.search(_read(rel)) is None, f"possible secret in {rel}"


def test_logo_is_svg() -> None:
    logo = _read("assets/logo.svg")
    assert logo.lstrip().startswith("<svg")
    assert 'viewBox="0 0 192 192"' in logo
    assert "data:image/png;base64," in logo
    assert (ROOT / "assets/logo.png").is_file()
