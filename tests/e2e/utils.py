"""e2e テストで共用する `redi` CLI 実行ラッパと識別子ヘルパ。"""

import os
import subprocess
import uuid


def run_redi(*args: str) -> subprocess.CompletedProcess[str]:
    """`redi <args...>` を subprocess で実行する (例: `run_redi("project", "list")`)。

    `REDI_E2E_PROFILE` が設定されていれば `--profile` を付けて実行し、
    テスト対象の Redmine バージョンを切り替えられるようにする。
    未設定の場合は default_profile が使われる。

    異常終了を見逃さないよう `check=True` で実行する。
    異常終了を検証する場合は `subprocess.CalledProcessError` を捕捉する。
    """
    profile = os.environ.get("REDI_E2E_PROFILE")
    profile_options = ["--profile", profile] if profile else []
    return subprocess.run(
        ["redi", *profile_options, *args],
        capture_output=True,
        text=True,
        check=True,
    )


def unique_identifier(prefix: str) -> str:
    """`<prefix>-<uuid8>` 形式で衝突しにくい識別子を返す。"""
    return f"{prefix}-{uuid.uuid4().hex[:8]}"
