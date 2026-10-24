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
    assert manifest["version"] == "0.1.11"
    assert manifest["author"]["name"]
    assert manifest["logo"] == "assets/logo.svg"
    assert manifest["mcpServers"] == "./mcp.json"
    assert manifest["skills"] == "./skills/"
    assert (ROOT / manifest["logo"]).is_file()
    assert "mcp" in manifest["keywords"]


def test_claude_plugin_manifest() -> None:
    manifest = _json(".claude-plugin/plugin.json")
    assert manifest["name"] == "clawdchat"
    assert manifest["version"] == "0.1.11"
    assert manifest["description"].strip()
    assert manifest["author"]["name"] == "Agentrix AI"
    assert manifest["author"]["email"] == "ray@clawdchat.ai"
    assert manifest["homepage"] == "https://clawdchat.ai"
    assert manifest["repository"] == "https://github.com/agentrix-ai/clawdchat-cursor-plugin"
    assert manifest["license"] == "MIT"


def test_mcp_points_at_hosted_https() -> None:
    mcp = _json("mcp.json")
    server = mcp["mcpServers"]["clawdchat"]
    assert server["type"] == "http"
    assert server["url"] == "https://mcp.clawdchat.ai/mcp"
    blob = json.dumps(mcp)
    assert "clawdchat_" not in blob
    assert "${" not in blob


def test_dot_mcp_matches_cursor_mcp() -> None:
    assert _json(".mcp.json") == _json("mcp.json")
    server = _json(".mcp.json")["mcpServers"]["clawdchat"]
    assert server["type"] == "http"
    assert server["url"] == "https://mcp.clawdchat.ai/mcp"


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
    for tool in (
        "read_posts",
        "read_comments",
        "read_circles",
        "read_social",
        "read_my_status",
        "read_direct_messages",
        "discover_tools",
        "list_my_agents",
        "create_post",
        "upload_file",
        "interact",
        "manage_circles",
        "social",
        "direct_message",
        "switch_agent",
    ):
        assert tool in body, tool


def test_readme_and_docs_exist() -> None:
    for rel in ("README.md", "CLAUDE.md", "LICENSE", "CHANGELOG.md"):
        assert (ROOT / rel).is_file(), rel
    readme = _read("README.md")
    assert "https://mcp.clawdchat.ai/mcp" in readme
    assert "marketplace/publish" in readme
    assert "read_comments" in readme
    assert "discover_tools" in readme
    assert "list_my_agents" in readme
    assert "my_status" in readme
    assert "use_tools" in readme


@pytest.mark.parametrize(
    "rel",
    [
        ".cursor-plugin/plugin.json",
        ".claude-plugin/plugin.json",
        "mcp.json",
        ".mcp.json",
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


def test_logo_under_claude_text_limit() -> None:
    size = (ROOT / "assets/logo.svg").stat().st_size
    assert size < 256 * 1024, f"logo.svg is {size} bytes"
