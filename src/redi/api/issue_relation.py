from typing import TypedDict, cast

from redi.client import client


class IssueRelation(TypedDict):
    """redmine IssueRelation"""

    id: int
    issue_id: int
    issue_to_id: int
    relation_type: str  # ex. relates
    # precedes / follows 以外では null
    delay: int | None


class RelationNotFoundException(Exception):
    def __init__(self, relation_id: str) -> None:
        super().__init__(relation_id)
        self.relation_id = relation_id


def fetch_relation(relation_id: str) -> IssueRelation:
    """関係性を取得する

    Raises:
        RelationNotFoundException: 対象の関係性が存在しない場合（HTTP 404）
        requests.exceptions.HTTPError: 404 以外の HTTP エラーが返った場合
    """
    response = client.get(f"/relations/{relation_id}.json")
    if response.status_code == 404:
        raise RelationNotFoundException(relation_id)
    response.raise_for_status()
    return cast("IssueRelation", response.json()["relation"])


def fetch_issue_relations(issue_id: str) -> list[IssueRelation]:
    """イシューに紐づく関係性の一覧を取得する

    Raises:
        requests.exceptions.HTTPError: HTTP エラーが返った場合
    """
    response = client.get(f"/issues/{issue_id}/relations.json")
    response.raise_for_status()
    return cast("list[IssueRelation]", response.json()["relations"])


def create_relation(
    issue_id: str, issue_to_id: str, relation_type: str = "relates"
) -> IssueRelation:
    """関係性を作成し、作成された関係性を返す

    Raises:
        requests.exceptions.HTTPError: HTTP エラーが返った場合
    """
    response = client.post(
        f"/issues/{issue_id}/relations.json",
        json={
            "relation": {
                "issue_to_id": issue_to_id,
                "relation_type": relation_type,
            }
        },
    )
    response.raise_for_status()
    return cast("IssueRelation", response.json()["relation"])


def delete_relation(relation_id: str) -> None:
    """関係性を削除する

    Raises:
        RelationNotFoundException: 対象の関係性が存在しない場合（HTTP 404）
        requests.exceptions.HTTPError: 404 以外の HTTP エラーが返った場合
    """
    response = client.delete(f"/relations/{relation_id}.json")
    if response.status_code == 404:
        raise RelationNotFoundException(relation_id)
    response.raise_for_status()
