"""イシューが存在しないときの CLI 共通の失敗処理。

`api.fetch_issue` などは 404 を `IssueNotFoundException` に変換する。CLI では
それを「見つからないと伝えて exit 1」に揃えるため、各コマンドはここを経由する。
"""

import sys
from collections.abc import Iterator
from contextlib import contextmanager

from redi.api.issue import Issue, IssueNotFoundException
from redi.i18n import messages
from redi.output import eprint
from redi.service import issue_service


@contextmanager
def exit_if_issue_not_found(issue_id: str) -> Iterator[None]:
    """ブロック内で `IssueNotFoundException` が出たら見つからないと伝えて exit 1 する。

    取得を伴わない書き込み (コメント追加・削除・ウォッチャー追加) で使う。
    """
    try:
        yield
    except IssueNotFoundException:
        eprint(messages.issue_not_found.format(id=issue_id))
        sys.exit(1)


def read_issue_or_exit(issue_id: str, include: str = "") -> Issue:
    """イシューを取得する。存在しなければ見つからないと伝えて exit 1。"""
    with exit_if_issue_not_found(issue_id):
        return issue_service.read_issue(issue_id, include=include)
