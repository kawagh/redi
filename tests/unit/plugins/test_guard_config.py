"""redmine-redi プラグインの PreToolUse hook (guard_config.py) の仕様。"""

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

HOOK_PATH = (
    Path(__file__).resolve().parents[3]
    / "plugins"
    / "redmine-redi"
    / "hooks"
    / "guard_config.py"
)


def _load_hook():
    spec = importlib.util.spec_from_file_location("guard_config", HOOK_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


guard_config = _load_hook()


@pytest.mark.parametrize(
    "tool_input",
    [
        {"file_path": "/home/user/.config/redi/config.toml"},
        {"file_path": "~/.config/redi/config.toml"},
        {"command": "cat ~/.config/redi/config.toml"},
        {"command": "grep redmine_api_key $HOME/.config/redi/config.toml"},
        # ディレクトリごと覗く場合も止める
        {"command": "ls ~/.config/redi"},
        {"path": "/home/user/.config/redi", "pattern": "api_key"},
        # Windows のパス区切り
        {"file_path": r"C:\Users\user\.config\redi\config.toml"},
        # 文字列がネストしていても見つける
        {"edits": [{"old_string": "x", "file_path": "~/.config/redi/config.toml"}]},
    ],
)
def test_config_toml_へのアクセスを拒否する(tool_input: dict) -> None:
    """~/.config/redi 配下を指す文字列が tool_input にあれば deny する。"""
    assert guard_config.is_denied(tool_input) is True


@pytest.mark.parametrize(
    "tool_input",
    [
        # redi 経由の参照は妨げない
        {"command": "redi config --full"},
        {"command": "redi issue list --profile work"},
        # 別物の config.toml を巻き込まない
        {"file_path": "/home/user/project/config.toml"},
        {"file_path": "/home/user/.config/gh/config.yml"},
        # リポジトリ自身のソースは読める
        {"file_path": "src/redi/config.py"},
    ],
)
def test_無関係な入力は素通しする(tool_input: dict) -> None:
    """redi config の実行や他所の設定ファイルは deny しない。"""
    assert guard_config.is_denied(tool_input) is False


def test_deny_のときだけ_PreToolUse_の_deny_を_stdout_に出す() -> None:
    """deny 時は Claude Code / Codex が解釈する形式の JSON を返す。"""
    payload = {
        "tool_name": "Read",
        "tool_input": {"file_path": "/home/user/.config/redi/config.toml"},
    }
    result = subprocess.run(
        [sys.executable, str(HOOK_PATH)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    output = json.loads(result.stdout)["hookSpecificOutput"]
    assert output["hookEventName"] == "PreToolUse"
    assert output["permissionDecision"] == "deny"
    assert "redi config" in output["permissionDecisionReason"]


def test_許可するときは何も出力しない() -> None:
    """deny しない場合は stdout を汚さず正常終了する。"""
    payload = {"tool_name": "Bash", "tool_input": {"command": "redi config"}}
    result = subprocess.run(
        [sys.executable, str(HOOK_PATH)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert result.stdout == ""


def test_壊れた入力でもセッションを止めない() -> None:
    """JSON として読めない stdin は hook 側の失敗として握り潰す。"""
    result = subprocess.run(
        [sys.executable, str(HOOK_PATH)],
        input="not json",
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert result.stdout == ""
