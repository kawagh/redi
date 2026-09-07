#!/usr/bin/env python3
"""~/.config/redi/config.toml への直接アクセスを PreToolUse で拒否する hook。

config.toml は API キーを含むため、読まれると会話ログに鍵が残る。
`redi config` / `redi config --full` を使えば鍵を出さずに設定値を確認できるので、
その経路へ切り替えさせる。

Claude Code / Codex の双方から同じスクリプトを呼ぶ。stdin に届く `tool_name` は
エージェントごとに違う (Codex は `apply_patch` など) ため、`tool_input` の
文字列だけを見て判定する。
"""

import json
import re
import sys

# ~/.config/redi 配下を指す文字列。パス区切りは Windows も考慮する。
CONFIG_DIR_PATTERN = re.compile(r"\.config[/\\]redi", re.IGNORECASE)

DENY_REASON = (
    "Reading ~/.config/redi/config.toml is blocked: it contains Redmine API keys, "
    "and they would end up in the conversation log. "
    "Run `redi config` (or `redi config --full` for every profile) instead — "
    "it prints the profile settings without the keys."
)


def iter_strings(value: object) -> list[str]:
    """tool_input に含まれる文字列を再帰的に集める。"""
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [s for v in value.values() for s in iter_strings(v)]
    if isinstance(value, list):
        return [s for v in value for s in iter_strings(v)]
    return []


def is_denied(tool_input: object) -> bool:
    return any(CONFIG_DIR_PATTERN.search(s) for s in iter_strings(tool_input))


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, UnicodeDecodeError):
        # hook 自体の失敗でセッションを止めない
        return 0

    if not isinstance(payload, dict) or not is_denied(payload.get("tool_input")):
        return 0

    json.dump(
        {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": DENY_REASON,
            }
        },
        sys.stdout,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
