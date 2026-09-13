from types import SimpleNamespace

import pytest

from redi.api.issue import IssueNotFoundException
from redi.service import issue_relation_service
from redi.service.issue_relation_service import (
    RelatedIssueNotFoundException,
    RelationBetweenNotFoundException,
)


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


@pytest.fixture
def stub_create_relation_api(monkeypatch):
    """関係先イシューの存在を `existing_issue_ids` で決め、POST を `created` に記録する。"""

    state = SimpleNamespace(existing_issue_ids={"2"}, created=[])

    def fake_fetch_issue(issue_id, include=""):
        if issue_id not in state.existing_issue_ids:
            raise IssueNotFoundException(issue_id)
        return {"id": int(issue_id)}

    def fake_create_relation(issue_id, issue_to_id, relation_type="relates"):
        state.created.append((issue_id, issue_to_id, relation_type))
        return _relation(20, issue_id=int(issue_id), issue_to_id=int(issue_to_id))

    monkeypatch.setattr(
        issue_relation_service.issue_api, "fetch_issue", fake_fetch_issue
    )
    monkeypatch.setattr(
        issue_relation_service.issue_relation_api,
        "create_relation",
        fake_create_relation,
    )
    return state


class TestCreateRelation:
    """create_relation の関係先イシューの存在確認"""

    def test_creates_relation_when_related_issue_exists(self, stub_create_relation_api):
        """関係先が存在すれば関係性を作成し、作成された関係性を返す"""
        created = issue_relation_service.create_relation("1", "2", "blocks")

        assert created["id"] == 20
        assert stub_create_relation_api.created == [("1", "2", "blocks")]

    def test_raises_when_related_issue_not_found(self, stub_create_relation_api):
        """関係先が存在しなければ例外を送出し、作成は行わない"""
        # Redmine の 422 は "Related issue cannot be blank" で値を渡していないように
        # 読めてしまうため、送信前に落として実態に合ったメッセージを出す
        with pytest.raises(RelatedIssueNotFoundException) as e:
            issue_relation_service.create_relation("1", "999999")

        assert e.value.issue_to_id == "999999"
        assert stub_create_relation_api.created == []
