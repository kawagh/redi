"""e2e テストで共用する `redi` CLI 実行ラッパと識別子ヘルパ。"""

import subprocess
import uuid


def run_redi(*args: str) -> subprocess.CompletedProcess[str]:
    """`redi <args...>` を subprocess で実行する (例: `run_redi("project", "list")`)。"""
    return subprocess.run(
        ["redi", *args],
        capture_output=True,
        text=True,
    )


def unique_identifier(prefix: str) -> str:
    """`<prefix>-<uuid8>` 形式で衝突しにくい識別子を返す。"""
    return f"{prefix}-{uuid.uuid4().hex[:8]}"
