#!/usr/bin/env python3
"""PreToolUse hook to auto-approve safe public HTTPS web fetches and searches."""

from __future__ import annotations

import ipaddress
import json
import sys
from typing import Any
from urllib.parse import urlparse

WEB_FETCH_TOOLS = {
    "web_fetch",
    "webfetch",
    "fetch_webpage",
    "web_search",
    "websearch",
}

# Restrict auto-approval to specific domains if needed (empty set allows all public HTTPS hosts).
# Example: {"docs.github.com", "code.visualstudio.com", "learn.microsoft.com"}
ALLOWED_DOMAINS: set[str] = set()


def is_safe_https_url(raw_url: str) -> bool:
    """Return True only for public HTTPS URLs (reject localhost, .local, and non-global IPs)."""
    try:
        parsed = urlparse(raw_url.strip())
    except ValueError:
        return False

    if parsed.scheme.lower() != "https" or not parsed.hostname:
        return False

    host = parsed.hostname.lower()
    if host in ("localhost", "localhost.localdomain") or host.endswith(".local"):
        return False

    try:
        ip = ipaddress.ip_address(host)
        if not ip.is_global:
            return False
    except ValueError:
        pass

    if ALLOWED_DOMAINS:
        return any(host == d or host.endswith(f".{d}") for d in ALLOWED_DOMAINS)

    return True


def extract_urls(tool_args: dict[str, Any]) -> list[str]:
    """Extract URL strings from various harness tool argument schemas."""
    urls: list[str] = []
    for key in ("url", "uri"):
        val = tool_args.get(key)
        if isinstance(val, str) and val.strip():
            urls.append(val)

    raw_urls = tool_args.get("urls")
    if isinstance(raw_urls, list):
        urls.extend(u for u in raw_urls if isinstance(u, str) and u.strip())

    return urls


def format_allow_output(event: dict[str, Any], reason: str) -> dict[str, Any]:
    """Format stdout JSON according to the calling harness's PreToolUse contract."""
    # Copilot camelCase (`preToolUse`) or Copilot CLI PascalCase (`PreToolUse` has timestamp, no tool_use_id)
    if "toolName" in event or ("timestamp" in event and "tool_use_id" not in event):
        return {
            "permissionDecision": "allow",
            "permissionDecisionReason": reason,
        }

    # Cursor native `preToolUse`
    if event.get("hook_event_name") == "preToolUse":
        return {
            "decision": "allow",
            "reason": reason,
        }

    # Claude Code / VS Code Local / Codex / Gemini `PreToolUse`
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow",
            "permissionDecisionReason": reason,
        }
    }


def parse_tool_args(event: dict[str, Any]) -> dict[str, Any] | None:
    """Safely parse tool arguments from event payload."""
    raw_args = event.get("toolArgs") if "toolArgs" in event else event.get("tool_input")
    if raw_args is None:
        return {}
    if isinstance(raw_args, dict):
        return raw_args
    if isinstance(raw_args, str):
        try:
            parsed = json.loads(raw_args)
            return parsed if isinstance(parsed, dict) else None
        except json.JSONDecodeError:
            return None
    return None


def main() -> int:
    """Read hook event JSON from stdin and output allow decision for safe web fetches."""
    raw_stdin = sys.stdin.read()
    if not raw_stdin or not raw_stdin.strip():
        sys.stdout.write("{}")
        return 0

    try:
        event = json.loads(raw_stdin)
    except json.JSONDecodeError as exc:
        sys.stderr.write(f"auto_approve_web hook: invalid JSON on stdin: {exc}\n")
        return 1

    if not isinstance(event, dict):
        sys.stderr.write("auto_approve_web hook: expected JSON object on stdin\n")
        return 1

    raw_tool_name = event.get("toolName") or event.get("tool_name") or ""
    if not isinstance(raw_tool_name, str) or raw_tool_name.strip().lower() not in WEB_FETCH_TOOLS:
        sys.stdout.write("{}")
        return 0

    tool_args = parse_tool_args(event)
    if tool_args is None:
        sys.stdout.write("{}")
        return 0

    tool_lower = raw_tool_name.strip().lower()
    urls = extract_urls(tool_args)

    # Fetch tools must provide at least one URL and all URLs must be safe public HTTPS
    if tool_lower in ("web_fetch", "webfetch", "fetch_webpage"):
        if not urls or not all(is_safe_https_url(u) for u in urls):
            sys.stdout.write("{}")
            return 0
    elif urls and not all(is_safe_https_url(u) for u in urls):
        sys.stdout.write("{}")
        return 0

    output = format_allow_output(event, "Safe public HTTPS web access auto-approved.")
    sys.stdout.write(json.dumps(output, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
