"""`list` 系コマンドの --limit / --offset が実際に一覧を絞ることを確かめる。

絞り込みが効くかは Redmine のエンドポイント側の実装次第なので、
指定を渡している project / news / membership を実 Redmine に対して確かめる。
"""

import json

import pytest

from tests.e2e.utils import run_redi, unique_identifier

PROJECT_ID = "reditest"


def _assert_paginates(*argv: str) -> None:
    """絞り込み無しの一覧を基準に、--limit / --offset の切り出しを突き合わせる。"""
    full = run_redi(*argv).stdout.splitlines()
    assert len(full) >= 3, f"検証には3件以上必要: {argv}"

    assert run_redi(*argv, "--limit", "1").stdout.splitlines() == full[:1]
    assert (
        run_redi(*argv, "--limit", "2", "--offset", "1").stdout.splitlines()
        == full[1:3]
    )


@pytest.mark.e2e
class TestProjectListPagination:
    """`redi project list` の --limit / --offset"""

    def test_slices_list(self):
        """作成済みの reditest と合わせて3件以上にしてから絞り込む"""
        for _ in range(2):
            name = unique_identifier("e2e-page-project")
            run_redi("project", "create", name, name)

        _assert_paginates("project", "list")


@pytest.mark.e2e
class TestNewsListPagination:
    """`redi news list` の --limit / --offset"""

    def test_slices_list(self):
        for _ in range(3):
            run_redi(
                "news", "create", unique_identifier("e2e-page-news"), "-d", "e2e body"
            )

        _assert_paginates("news", "list")


@pytest.mark.e2e
class TestMembershipListPagination:
    """`redi membership list` の --limit / --offset"""

    def test_slices_list(self):
        """グループをメンバーに加えて3件以上にしてから絞り込む"""
        role_id = run_redi("role", "list").stdout.splitlines()[0].split()[0]
        for _ in range(3):
            name = unique_identifier("e2e-page-member")
            run_redi("group", "create", name)
            group = next(
                g
                for g in json.loads(run_redi("group", "list", "--full").stdout)
                if g["name"] == name
            )
            run_redi(
                "membership",
                "create",
                "-p",
                PROJECT_ID,
                "-g",
                str(group["id"]),
                "-r",
                role_id,
            )

        _assert_paginates("membership", "list", "-p", PROJECT_ID)
