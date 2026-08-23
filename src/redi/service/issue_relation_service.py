"""イシューの関係性操作のサービス層。

CLI と TUI で共通の手順をここに置く。HTTP とステータスコードの解釈は
`api.issue_relation` が持つ。
"""

from __future__ import annotations

from redi.api import issue as issue_api
from redi.api import issue_relation as issue_relation_api
from redi.api.issue import IssueNotFoundException
from redi.api.issue_relation import IssueRelation


class RelatedIssueNotFoundException(Exception):
    """関係先に指定されたイシューが存在しないときに送出する例外。"""

    def __init__(self, issue_to_id: str) -> None:
        super().__init__(issue_to_id)
        self.issue_to_id = issue_to_id


class RelationBetweenNotFoundException(Exception):
    """2 つのイシューの間に関係性が見つからないときに送出する例外。"""

    def __init__(self, issue_id: str, issue_to_id: str) -> None:
        super().__init__(f"{issue_id}/{issue_to_id}")
        self.issue_id = issue_id
        self.issue_to_id = issue_to_id


def read_relation(relation_id: str) -> IssueRelation:
    """関係性を取得する。

    Raises:
        RelationNotFoundException: 対象の関係性が存在しない (HTTP 404)
        requests.exceptions.HTTPError: それ以外の HTTP エラー
    """
    return issue_relation_api.fetch_relation(relation_id)


def list_relations(issue_id: str) -> list[IssueRelation]:
    """イシューに紐づく関係性の一覧を取得する。"""
    return issue_relation_api.fetch_issue_relations(issue_id)


def create_relation(
    issue_id: str, issue_to_id: str, relation_type: str = "relates"
) -> IssueRelation:
    """関係性を作成し、作成された関係性を返す。

    関係先が存在しないときの Redmine の 422 は "Related issue cannot be blank" で、
    値を渡していないように読めてしまうため、送信前に存在を確かめる。

    Raises:
        RelatedIssueNotFoundException: 関係先のイシューが存在しない
        requests.exceptions.HTTPError: HTTP エラー
    """
    try:
        issue_api.fetch_issue(issue_to_id)
    except IssueNotFoundException as e:
        raise RelatedIssueNotFoundException(issue_to_id) from e
    return issue_relation_api.create_relation(
        issue_id=issue_id,
        issue_to_id=issue_to_id,
        relation_type=relation_type,
    )


def find_relation_between(issue_id: str, issue_to_id: str) -> IssueRelation | None:
    """イシュー間の関係性を探す。見つからない場合は None を返す。

    関係性は向きを持つが「#A と #B の間の関係性」は向きに依らず 1 つとして扱いたいので、
    `issue_id` の関係性一覧から `issue_to_id` を どちらの端に持つものも対象にする。
    """
    relations = issue_relation_api.fetch_issue_relations(issue_id)
    target_id = int(issue_to_id)
    return next(
        (
            r
            for r in relations
            if r["issue_id"] == target_id or r["issue_to_id"] == target_id
        ),
        None,
    )


def delete_relation(issue_id: str, issue_to_id: str) -> IssueRelation:
    """イシュー間の関係性を探して削除し、削除した関係性を返す。

    Raises:
        RelationBetweenNotFoundException: 2 つのイシューの間に関係性が無い
        RelationNotFoundException: 対象の関係性が存在しない (HTTP 404)
        requests.exceptions.HTTPError: それ以外の HTTP エラー
    """
    target_relation = find_relation_between(issue_id, issue_to_id)
    if target_relation is None:
        raise RelationBetweenNotFoundException(issue_id, issue_to_id)
    issue_relation_api.delete_relation(str(target_relation["id"]))
    return target_relation
