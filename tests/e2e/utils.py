"""e2e テストで共用する `redi` CLI 実行ラッパと識別子ヘルパ。"""

import os
import subprocess
import uuid
from pathlib import Path

import pytest

# テスト対象の Redmine バージョン (taskfile / CI から渡す)
REDMINE_VERSION = os.environ.get("REDI_E2E_REDMINE_VERSION")

# script/init-redmine.sh が設定とキャッシュを置く場所。同じ規約をここでも組み立てる。
# init と pytest は taskfile / CI / 手動と別々に起動されるため、渡し漏れると
# ユーザーのグローバル設定を見に行ってしまう。
E2E_DIR = Path(__file__).resolve().parents[2] / ".e2e" / (REDMINE_VERSION or "")


def _redi_env() -> dict[str, str]:
    """`redi` に渡す環境変数を返す。

    E2E 専用の設定・キャッシュを向かせ、ユーザーのグローバル設定 (~/.config/redi)
    を読み書きさせない。明示的に指定されていればそちらを優先する。
    """
    env = dict(os.environ)
    if not REDMINE_VERSION:
        return env
    env.setdefault("REDI_CONFIG_PATH", str(E2E_DIR / "config.toml"))
    env.setdefault("REDI_CACHE_DIR", str(E2E_DIR / "cache"))
    return env


def run_redi(*args: str) -> subprocess.CompletedProcess[str]:
    """`redi <args...>` を subprocess で実行する (例: `run_redi("project", "list")`)。

    `REDI_E2E_REDMINE_VERSION` が設定されていれば、そのバージョン向けに
    script/init-redmine.sh が作った設定を読ませ、その profile を `--profile` で
    指定する。未設定の場合はユーザーの設定と default_profile が使われる。

    異常終了を見逃さないよう `check=True` で実行する。
    異常終了を検証する場合は `subprocess.CalledProcessError` を捕捉する。
    """
    profile_options = (
        ["--profile", f"sandbox_admin_{REDMINE_VERSION}"] if REDMINE_VERSION else []
    )
    return subprocess.run(
        ["redi", *profile_options, *args],
        capture_output=True,
        text=True,
        check=True,
        env=_redi_env(),
    )


def unique_identifier(prefix: str) -> str:
    """`<prefix>-<uuid8>` 形式で衝突しにくい識別子を返す。"""
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def _version_tuple(version: str) -> tuple[int, ...]:
    return tuple(int(part) for part in version.split("."))


requires_redmine_7_0 = pytest.mark.skipif(
    REDMINE_VERSION is None or _version_tuple(REDMINE_VERSION) < (7, 0),
    reason="Redmine 7.0 以降で拡張されたレスポンスの検証",
)
