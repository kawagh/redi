from types import SimpleNamespace

import pytest
import requests

from redi import config
from redi.api.exceptions import (
    IssueListNotFoundException,
    ProjectNotFoundException,
    QueryNotFoundException,
)
from redi.api.issue import WatcherNotFoundException
from redi.service import issue_service


@pytest.fixture
def stub_issue_api(monkeypatch):
    """コメント追加の PUT を `added` に記録し、追加後のジャーナルを `journals` で差し替える。

    コメントが Redmine に正しく届くかは E2E (`tests/e2e/test_issue_cli.py`) で見る。
    """

    state = SimpleNamespace(journals=[], added=[])

    def fake_add_note(issue_id, notes):
        state.added.append((issue_id, notes))

    def fake_fetch_issue(issue_id, include=""):
        return {"id": int(issue_id), "journals": state.journals}

    monkeypatch.setattr(issue_service.issue_api, "add_note", fake_add_note)
    monkeypatch.setattr(issue_service.issue_api, "fetch_issue", fake_fetch_issue)
    monkeypatch.setattr(config, "redmine_url", "http://localhost:3001")
    return state


@pytest.fixture
def stub_update_issue_api(monkeypatch):
    """更新の PUT を `calls` に記録し、slug -> id の解決を差し替える。

    プロジェクトの解決は `reditest` -> `5` の 1 件だけを知っている状態にする。
    """

    calls: list[dict] = []

    def fake_resolve_project_id(project_id):
        return "5" if project_id == "reditest" else project_id

    def fake_update_issue(**kwargs):
        calls.append(kwargs)

    monkeypatch.setattr(issue_service, "resolve_project_id", fake_resolve_project_id)
    monkeypatch.setattr(issue_service.issue_api, "update_issue", fake_update_issue)
    return SimpleNamespace(calls=calls)


class TestUpdateIssue:
    """update_issue が API に渡す project_id"""

    def test_project_slug_is_resolved_to_id(self, stub_update_issue_api):
        """存在しない移動先を Redmine が黙って無視するので、数値の id に解決してから渡す"""
        issue_service.update_issue("42", project_id="reditest")

        assert stub_update_issue_api.calls[0]["project_id"] == "5"

    def test_project_is_not_resolved_when_omitted(self, stub_update_issue_api):
        """project_id を指定しなければ解決せず None のまま渡す (プロジェクトを変えない)"""
        issue_service.update_issue("42", subject="件名")

        assert stub_update_issue_api.calls[0]["project_id"] is None


class TestAddNote:
    """add_note が返すコメントの URL"""

    def test_returns_url_with_note_number(self, stub_issue_api):
        """追加後のジャーナル数を note 番号にした URL を返す"""
        stub_issue_api.journals = [{"id": 1}, {"id": 2}]

        url = issue_service.add_note("42", "コメント")

        assert url == "http://localhost:3001/issues/42#note-2"
        assert stub_issue_api.added == [("42", "コメント")]

    def test_returns_issue_url_without_journals(self, stub_issue_api):
        """ジャーナルが取れなければ note 番号のない URL を返す"""
        url = issue_service.add_note("42", "コメント")

        assert url == "http://localhost:3001/issues/42"


class TestListIssuesNotFound:
    """`--query_id` と `--project_id` を同時に指定した 404 の切り分け

    Redmine はどちらが原因でも 404 を返すため、クエリ一覧を引いて原因の側を指す。
    default_project_id が設定されていると常に両方指定になるため、切り分けないと
    クエリ由来の 404 がすべてプロジェクトのせいに見えてしまう。
    """

    @pytest.fixture
    def stub_not_found(self, monkeypatch):
        """イシュー取得を必ず IssueListNotFoundException にする"""

        def fake_fetch_issues(**kwargs):
            raise IssueListNotFoundException("demo", "5")

        monkeypatch.setattr(issue_service.issue_api, "fetch_issues", fake_fetch_issues)

    def test_raises_query_not_found_when_query_is_missing(
        self, stub_not_found, monkeypatch
    ):
        """クエリ一覧に無ければクエリ未検出のまま送出する"""
        monkeypatch.setattr(
            issue_service.query_api, "fetch_queries", lambda **kwargs: [{"id": 8}]
        )

        with pytest.raises(QueryNotFoundException) as exc_info:
            issue_service.list_issues(project_id="demo", query_id="5")

        assert exc_info.value.query_id == "5"

    def test_raises_project_not_found_when_query_exists(
        self, stub_not_found, monkeypatch
    ):
        """クエリが実在するならプロジェクト側が原因なので送出し直す"""
        monkeypatch.setattr(
            issue_service.query_api, "fetch_queries", lambda **kwargs: [{"id": 5}]
        )

        with pytest.raises(ProjectNotFoundException) as exc_info:
            issue_service.list_issues(project_id="demo", query_id="5")

        assert exc_info.value.project_id == "demo"

    def test_raises_query_not_found_when_queries_are_unavailable(
        self, stub_not_found, monkeypatch
    ):
        """クエリ一覧を取得できない場合は指定した側 (クエリ) を指す"""

        def fake_fetch_queries(**kwargs):
            raise requests.exceptions.HTTPError()

        monkeypatch.setattr(
            issue_service.query_api, "fetch_queries", fake_fetch_queries
        )

        with pytest.raises(QueryNotFoundException):
            issue_service.list_issues(project_id="demo", query_id="5")


class TestAddWatcher:
    """add_watcher が追加の反映を確かめる

    Redmine はウォッチャーにできないユーザーIDを渡しても追加せずに 200 を返すため、
    API の戻りだけを信じると追加できていないのに成功扱いになる。
    """

    @pytest.fixture
    def stub_watcher_api(self, monkeypatch):
        """POST を `added` に記録し、追加後に返るウォッチャー一覧を `watchers` で差し替える"""

        state = SimpleNamespace(watchers=[], added=[])

        def fake_add_watcher(issue_id, user_id):
            state.added.append((issue_id, user_id))

        def fake_fetch_issue(issue_id, include=""):
            issue = {"id": int(issue_id)}
            if state.watchers is not None:
                issue["watchers"] = state.watchers
            return issue

        monkeypatch.setattr(issue_service.issue_api, "add_watcher", fake_add_watcher)
        monkeypatch.setattr(issue_service.issue_api, "fetch_issue", fake_fetch_issue)
        return state

    def test_succeeds_when_watcher_is_added(self, stub_watcher_api):
        """追加後の一覧に指定したユーザーがいれば成功とみなす"""
        stub_watcher_api.watchers = [{"id": 7, "name": "redi"}]

        issue_service.add_watcher("42", 7)

        assert stub_watcher_api.added == [("42", 7)]

    def test_raises_when_watcher_is_not_added(self, stub_watcher_api):
        """追加後の一覧に指定したユーザーがいなければ追加できていないので送出する"""
        stub_watcher_api.watchers = [{"id": 1, "name": "other"}]

        with pytest.raises(WatcherNotFoundException) as exc_info:
            issue_service.add_watcher("42", 999)

        assert exc_info.value.issue_id == "42"
        assert exc_info.value.user_id == 999

    def test_does_not_raise_when_watchers_are_unavailable(self, stub_watcher_api):
        """ウォッチャーを参照する権限が無いと一覧が返らないので、確認せず成功とみなす"""
        stub_watcher_api.watchers = None

        issue_service.add_watcher("42", 7)

        assert stub_watcher_api.added == [("42", 7)]
