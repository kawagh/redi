from types import SimpleNamespace

import pytest

from redi.service import issue_relation_service
from redi.service.issue_relation_service import RelationBetweenNotFoundException


@pytest.fixture
def stub_issue_relation_api(monkeypatch):
    """イシューに紐づく関係性を `relations` で差し替え、DELETE を `deleted` に記録する。

    削除リクエストが Redmine に正しく届くかは E2E (`tests/e2e/test_issue_cli.py`) で見る。
    """

    state = SimpleNamespace(relations=[], deleted=[])

    def fake_fetch_issue_relations(issue_id):
        return state.relations

    def fake_delete_relation(relation_id):
        state.deleted.append(relation_id)

    monkeypatch.setattr(
        issue_relation_service.issue_relation_api,
        "fetch_issue_relations",
        fake_fetch_issue_relations,
    )
    monkeypatch.setattr(
        issue_relation_service.issue_relation_api,
        "delete_relation",
        fake_delete_relation,
    )
    return state


def _relation(relation_id: int, issue_id: int, issue_to_id: int) -> dict:
    return {
        "id": relation_id,
        "issue_id": issue_id,
        "issue_to_id": issue_to_id,
        "relation_type": "relates",
        "delay": None,
    }


class TestDeleteRelation:
    """delete_relation が削除する関係性の特定"""

    def test_deletes_relation_to_target(self, stub_issue_relation_api):
        """相手イシューを issue_to_id に持つ関係性を削除し、削除した関係性を返す"""
        stub_issue_relation_api.relations = [
            _relation(10, issue_id=1, issue_to_id=3),
            _relation(11, issue_id=1, issue_to_id=2),
        ]

        deleted = issue_relation_service.delete_relation("1", "2")

        assert deleted["id"] == 11
        assert stub_issue_relation_api.deleted == ["11"]

    def test_deletes_relation_from_target(self, stub_issue_relation_api):
        """向きが逆(相手イシューが issue_id 側)でも同じ関係性として削除する"""
        stub_issue_relation_api.relations = [_relation(12, issue_id=2, issue_to_id=1)]

        deleted = issue_relation_service.delete_relation("1", "2")

        assert deleted["id"] == 12
        assert stub_issue_relation_api.deleted == ["12"]

    def test_raises_when_no_relation_between(self, stub_issue_relation_api):
        """イシュー間に関係性が無ければ例外を送出し、削除は行わない"""
        stub_issue_relation_api.relations = [_relation(13, issue_id=1, issue_to_id=3)]

        with pytest.raises(RelationBetweenNotFoundException):
            issue_relation_service.delete_relation("1", "2")

        assert stub_issue_relation_api.deleted == []
