"""e2e テストで共用する `redi` CLI 実行ラッパと識別子ヘルパ。"""

import json
import os
import subprocess
import uuid

import pytest

# script/init-redmine.sh がコンテナ作成時に仕込むカスタムクエリの名前
# (Redmine の REST API にクエリの作成系エンドポイントが無く、シードでしか用意できない)
GLOBAL_QUERY_NAME = "e2e 全プロジェクト (機能 or サポート)"
PROJECT_QUERY_NAME = "e2e reditest 限定 (機能 or サポート)"
OTHER_PROJECT_QUERY_NAME = "e2e 別プロジェクト限定 (reditother)"
PRIVATE_QUERY_NAME = "e2e 非公開 (作成者のみ)"

# テスト対象の Redmine バージョン (taskfile / CI から渡す)
REDMINE_VERSION = os.environ.get("REDI_E2E_REDMINE_VERSION")


def run_redi(*args: str) -> subprocess.CompletedProcess[str]:
    """`redi <args...>` を subprocess で実行する (例: `run_redi("project", "list")`)。

    `REDI_E2E_REDMINE_VERSION` が設定されていれば、そのバージョン向けに
    script/init-redmine.sh が作った profile を `--profile` で指定する。
    未設定の場合は default_profile が使われる。

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
    )


def run_redi_as_developer(*args: str) -> subprocess.CompletedProcess[str]:
    """`redi` を sandbox_developer の profile で実行する (例: 非公開クエリの見え方)。

    profile 名がバージョンごとなので `REDI_E2E_REDMINE_VERSION` が要る。
    未設定で呼ばれた場合に admin として実行してしまわないよう、`requires_e2e_profiles`
    を付けたテストからのみ呼ぶ。
    """
    return subprocess.run(
        ["redi", "--profile", f"sandbox_developer_{REDMINE_VERSION}", *args],
        capture_output=True,
        text=True,
        check=True,
    )


def query_named(name: str) -> dict:
    """シードしたカスタムクエリを名前で引く。id はコンテナごとに変わるので固定しない。"""
    queries = json.loads(run_redi("query", "list", "--full").stdout)
    return next(query for query in queries if query["name"] == name)


def unique_identifier(prefix: str) -> str:
    """`<prefix>-<uuid8>` 形式で衝突しにくい識別子を返す。"""
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def _version_tuple(version: str) -> tuple[int, ...]:
    return tuple(int(part) for part in version.split("."))


requires_redmine_7_0 = pytest.mark.skipif(
    REDMINE_VERSION is None or _version_tuple(REDMINE_VERSION) < (7, 0),
    reason="Redmine 7.0 以降で拡張されたレスポンスの検証",
)


requires_e2e_profiles = pytest.mark.skipif(
    REDMINE_VERSION is None,
    reason="admin 以外の profile を使うので REDI_E2E_REDMINE_VERSION が要る",
)
