import argparse
import json
from typing import cast

import pytest
import requests

from redi import config
from redi.api.exceptions import (
    ProjectNotFoundException,
    QueryNotFoundException,
    RedmineValidationException,
)
from redi.api.issue import Issue, WatcherNotFoundException
from redi.api.issue_relation import RELATION_TYPES
from redi.cli import editor as editor_module
from redi.cli.issue_command import add_issue_parser
from redi.cli.issue_command import create as create_module
from redi.cli.issue_command import dispatch as dispatch_module
from redi.cli.issue_command import update as update_module
from redi.cli.issue_command import view as view_module
from redi.cli.issue_command.create import IssueCreateArgs, handle_issue_create
from redi.cli.issue_command.update import IssueUpdateArgs, handle_issue_update
from redi.cli.shared_options import OutputFormat
from redi.i18n import messages

CREATED_ISSUE = {"id": 123, "subject": "件名"}


def _page(issues: list, total_count: int | None = None, offset: int = 0) -> dict:
    """GET /issues.json のレスポンスを組み立てる"""
    return {
        "issues": issues,
        "total_count": len(issues) if total_count is None else total_count,
        "offset": offset,
        "limit": 25,
    }


def _raise_http_error(status_code: int):
    """指定したステータスコードの HTTPError を投げるスタブを返す"""
    response = requests.Response()
    response.status_code = status_code

    def _raise(**kwargs):
        raise requests.exceptions.HTTPError(f"{status_code} Error", response=response)

    return _raise


def parse_issue_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    add_issue_parser(parser.add_subparsers(dest="command"), [])
    return parser.parse_args(argv)


@pytest.fixture
def created_issue(monkeypatch):
    """作成をスタブし、Redmine の URL を固定する"""
    monkeypatch.setattr(
        create_module.issue_service, "create_issue", lambda **kwargs: CREATED_ISSUE
    )
    monkeypatch.setattr(config, "redmine_url", "http://localhost:3001")


class TestIssueCreateOutput:
    """`issue create` の標準出力"""

    def test_prints_id_and_url(self, created_issue, capsys):
        """既定では作成した issue の id と URL を出す"""
        handle_issue_create(
            parse_issue_args(["issue", "create", "件名", "-p", "demo", "-d", "本文"])
        )

        out = capsys.readouterr().out
        assert "123" in out
        assert "http://localhost:3001/issues/123" in out

    def test_full_prints_json(self, created_issue, capsys):
        """--full では作成した issue の JSON だけを出す"""
        handle_issue_create(
            parse_issue_args(
                ["issue", "create", "件名", "-p", "demo", "-d", "本文", "--full"]
            )
        )

        assert json.loads(capsys.readouterr().out) == CREATED_ISSUE


class TestIssueUpdateArgsFromNamespace:
    def test_accepts_parser_output(self):
        """`issue update` のパース結果をそのまま受け取れる

        フィールド名が dest からずれていれば AttributeError で落ちる。
        `--to` と `--add-watcher` は明示的な dest 指定があり、特にずれやすい。
        """
        args = parse_issue_args(
            ["issue", "update", "42", "--to", "43", "--add-watcher", "7"]
        )

        update_args = IssueUpdateArgs.from_namespace(args)

        assert update_args.issue_id == "42"
        assert update_args.relate_to == "43"
        assert update_args.add_watcher_ids == [7]

    def test_accepts_project_id(self):
        """`--project_id` でイシューの移動先プロジェクトを受け取れる"""
        args = parse_issue_args(["issue", "update", "42", "--project_id", "demo"])

        update_args = IssueUpdateArgs.from_namespace(args)

        assert update_args.project_id == "demo"

    def test_short_option_is_not_assigned_to_project_id(self):
        """`-p` は `issue list` のフィルタなので、誤爆を避けて update では受け付けない"""
        with pytest.raises(SystemExit):
            parse_issue_args(["issue", "update", "42", "-p", "demo"])


class TestIssueCreateArgsFromNamespace:
    def test_accepts_parser_output(self):
        """`issue create` のパース結果をそのまま受け取れる

        フィールド名が dest からずれていれば AttributeError で落ちる。
        """
        args = parse_issue_args(["issue", "create", "題名", "-p", "demo"])

        create_args = IssueCreateArgs.from_namespace(args)

        assert create_args.subject == "題名"
        assert create_args.project_id == "demo"

    def test_accepts_full_flag(self):
        """`issue create --full` を受け取れる"""
        args = parse_issue_args(["issue", "create", "題名", "-p", "demo", "--full"])

        create_args = IssueCreateArgs.from_namespace(args)

        assert create_args.full is True


class TestBodyIsSavedOnFailure:
    """送信に失敗したとき、エディタで書いた本文を一時ファイルへ退避する

    422 (バリデーションエラー) だけでなく 404 / 500 などの HTTP エラーでも
    退避されること。失敗経路によって本文が失われるのを防ぐ。
    """

    @pytest.fixture
    def saved_paths(self, monkeypatch):
        """退避先を固定し、退避された本文を集める"""
        saved: list[str] = []

        def fake_save(text: str) -> str:
            saved.append(text)
            return "/tmp/redi-test.md"

        monkeypatch.setattr(editor_module, "save_text_to_tempfile", fake_save)
        return saved

    @pytest.mark.parametrize("status_code", [404, 500])
    def test_create_saves_body_on_http_error(
        self, monkeypatch, capsys, saved_paths, status_code
    ):
        """`issue create` が HTTP エラーで失敗しても本文が退避される"""
        monkeypatch.setattr(
            create_module.issue_service,
            "create_issue",
            _raise_http_error(status_code),
        )

        with pytest.raises(SystemExit) as exc_info:
            handle_issue_create(
                parse_issue_args(
                    ["issue", "create", "件名", "-p", "demo", "-d", "消えると困る本文"]
                )
            )

        assert exc_info.value.code == 1
        assert saved_paths == ["消えると困る本文"]
        assert "/tmp/redi-test.md" in capsys.readouterr().out

    def test_create_saves_body_on_validation_error(self, monkeypatch, saved_paths):
        """`issue create` が 422 で失敗しても本文が退避される"""

        def _raise(**kwargs):
            raise RedmineValidationException("issue", "create", ["Subject is invalid"])

        monkeypatch.setattr(create_module.issue_service, "create_issue", _raise)

        with pytest.raises(RedmineValidationException):
            handle_issue_create(
                parse_issue_args(
                    ["issue", "create", "件名", "-p", "demo", "-d", "消えると困る本文"]
                )
            )

        assert saved_paths == ["消えると困る本文"]

    @pytest.mark.parametrize("status_code", [404, 500])
    def test_update_saves_body_on_http_error(
        self, monkeypatch, capsys, saved_paths, status_code
    ):
        """`issue update` が HTTP エラーで失敗しても本文が退避される"""
        monkeypatch.setattr(
            update_module.issue_service,
            "update_issue",
            _raise_http_error(status_code),
        )

        with pytest.raises(SystemExit) as exc_info:
            handle_issue_update(
                parse_issue_args(["issue", "update", "1", "-d", "消えると困る本文"])
            )

        assert exc_info.value.code == 1
        assert saved_paths == ["消えると困る本文"]
        assert "/tmp/redi-test.md" in capsys.readouterr().out

    def test_update_saves_body_on_validation_error(self, monkeypatch, saved_paths):
        """`issue update` が 422 で失敗しても本文が退避される"""

        def _raise(**kwargs):
            raise RedmineValidationException(
                "issue", "update", ["Parent task is invalid"]
            )

        monkeypatch.setattr(update_module.issue_service, "update_issue", _raise)

        with pytest.raises(RedmineValidationException):
            handle_issue_update(
                parse_issue_args(["issue", "update", "1", "-d", "消えると困る本文"])
            )

        assert saved_paths == ["消えると困る本文"]


class TestIssueListNotFound:
    """`issue list` で存在しないプロジェクトを指定したとき"""

    def test_prints_guidance_and_exits(self, monkeypatch, capsys):
        """スタックトレースではなく案内を出して exit 1 する"""

        def _raise(**kwargs):
            raise ProjectNotFoundException("missing")

        monkeypatch.setattr(view_module.issue_service, "list_issues_page", _raise)

        with pytest.raises(SystemExit) as exc_info:
            view_module.print_issues(project_id="missing")

        assert exc_info.value.code == 1
        assert (
            messages.project_not_found.format(id="missing") in capsys.readouterr().err
        )


class TestIssueListQueryNotFound:
    """`issue list` で存在しないカスタムクエリを指定したとき"""

    def test_prints_query_guidance_and_exits(self, monkeypatch, capsys):
        """プロジェクトではなくクエリを原因として案内し exit 1 する"""

        def _raise(**kwargs):
            raise QueryNotFoundException("5")

        monkeypatch.setattr(view_module.issue_service, "list_issues_page", _raise)

        with pytest.raises(SystemExit) as exc_info:
            view_module.print_issues(project_id="demo", query_id="5")

        assert exc_info.value.code == 1
        err = capsys.readouterr().err
        assert messages.query_not_found.format(id="5") in err
        assert messages.query_not_found_hint in err
        assert messages.project_not_found.format(id="demo") not in err


class TestIssueListQueryIdFilters:
    """`issue list` の `--query_id` と他フィルタの併用

    Redmine はカスタムクエリの条件を優先して他の条件を捨てるため、
    絞り込んだつもりで別の結果を見ないよう、渡させずに落とす。
    """

    @pytest.mark.parametrize(
        ("option", "value", "shown"),
        [
            ("-v", "3", "--version"),
            ("-a", "me", "--assigned_to"),
            ("-s", "closed", "--status_id"),
            ("-t", "1", "--tracker_id"),
            ("--priority_id", "2", "--priority_id"),
        ],
    )
    def test_ignored_filter_exits(self, option, value, shown, capsys):
        """無視されるフィルタ名を示して exit 1 する"""
        args = parse_issue_args(["issue", "list", "-q", "5", option, value])

        with pytest.raises(SystemExit) as exc_info:
            dispatch_module.handle_issue(args)

        assert exc_info.value.code == 1
        assert shown in capsys.readouterr().err

    def test_lists_all_ignored_filters(self, capsys):
        """複数指定した場合はすべての名前を示す"""
        args = parse_issue_args(["issue", "list", "-q", "5", "-s", "closed", "-t", "1"])

        with pytest.raises(SystemExit):
            dispatch_module.handle_issue(args)

        err = capsys.readouterr().err
        assert "--status_id" in err
        assert "--tracker_id" in err

    def test_project_id_is_allowed(self, monkeypatch):
        """`--project_id` は Redmine 側でも併用が効くので通す"""
        called = {}
        monkeypatch.setattr(
            view_module.issue_service,
            "list_issues_page",
            lambda **kwargs: called.update(kwargs) or _page([]),
        )
        args = parse_issue_args(["issue", "list", "-q", "5", "-p", "demo"])

        dispatch_module.handle_issue(args)

        assert called["query_id"] == "5"
        assert called["project_id"] == "demo"


class TestIssueListTruncation:
    """`issue list` は Redmine が既定 25 件で打ち切った結果をそのまま出している

    総件数も続きの有無も出ないと、全件見えているものと取り違えて
    重複起票などの判断を誤るため、表示範囲と総件数を伝える。
    """

    @pytest.fixture
    def redmine_url(self, monkeypatch):
        monkeypatch.setattr(config, "redmine_url", "http://localhost:3001")

    def _stub(self, monkeypatch, page):
        monkeypatch.setattr(
            view_module.issue_service, "list_issues_page", lambda **kwargs: page
        )

    def test_notice_is_printed_to_stderr(self, monkeypatch, capsys, redmine_url):
        """打ち切られたら表示範囲と総件数を出す。一覧を汚さないよう標準エラーに出す"""
        issues = [{"id": i, "subject": f"件名{i}"} for i in range(1, 26)]
        self._stub(monkeypatch, _page(issues, total_count=74))

        view_module.print_issues()

        captured = capsys.readouterr()
        assert captured.out.count("\n") == 25
        assert (
            messages.issue_list_truncated.format(start=1, end=25, total=74)
            in captured.err
        )

    def test_no_notice_when_all_issues_are_shown(
        self, monkeypatch, capsys, redmine_url
    ):
        """全件出せている場合は何も出さない"""
        issues = [{"id": 1, "subject": "件名"}]
        self._stub(monkeypatch, _page(issues))

        view_module.print_issues()

        assert capsys.readouterr().err == ""

    def test_offset_is_reflected_in_the_range(self, monkeypatch, capsys, redmine_url):
        """--offset を渡した場合は、その位置からの表示範囲を出す"""
        issues = [{"id": i, "subject": f"件名{i}"} for i in range(26, 31)]
        self._stub(monkeypatch, _page(issues, total_count=74, offset=25))

        view_module.print_issues(offset=25, limit=5)

        assert (
            messages.issue_list_truncated.format(start=26, end=30, total=74)
            in capsys.readouterr().err
        )

    def test_full_includes_total_count(self, monkeypatch, capsys, redmine_url):
        """--full では Redmine が返した total_count も含めて出す"""
        issues = [{"id": 1, "subject": "件名"}]
        self._stub(monkeypatch, _page(issues, total_count=74))

        view_module.print_issues(fmt=OutputFormat.JSON)

        printed = json.loads(capsys.readouterr().out)
        assert printed["total_count"] == 74
        assert printed["issues"] == issues


VIEWED_ISSUE = cast(
    Issue,
    {
        "id": 42,
        "subject": "件名",
        "description": "本文",
        "status": {"name": "終了"},
        "priority": {"name": "通常"},
        "tracker": {"name": "バグ"},
        "author": {"name": "報告者"},
        "start_date": "2026-04-01",
        "due_date": None,
        "done_ratio": 70,
        "estimated_hours": 1.5,
        "spent_hours": 0.5,
        "created_on": "2026-04-01T00:00:00Z",
        "updated_on": "2026-04-02T00:00:00Z",
        "journals": [
            {
                "id": 238,
                "user": {"name": "コメントした人"},
                "created_on": "2026-04-29T02:26:43Z",
                "notes": "テストコメント",
            }
        ],
        "relations": [
            {
                "id": 13,
                "issue_id": 42,
                "issue_to_id": 162,
                "relation_type": "blocks",
                "delay": None,
            }
        ],
        "attachments": [
            {
                "id": 40,
                "filename": "sample.txt",
                "content_url": "http://localhost:3001/attachments/download/40/sample.txt",
            }
        ],
    },
)


class TestFormatIssueDetail:
    """`issue view` の整形出力"""

    @pytest.fixture(autouse=True)
    def redmine_url(self, monkeypatch):
        """URL の組み立てに使う Redmine の URL を固定する"""
        monkeypatch.setattr(config, "redmine_url", "http://localhost:3001")

    def test_shows_issue_url(self):
        """件名の次の行にイシュー自身の URL を出す (`issue list` / `issue create` と揃える)"""
        lines = view_module.format_issue_detail(VIEWED_ISSUE)

        assert lines[0] == "#42 件名"
        assert lines[1] == "http://localhost:3001/issues/42"

    def test_shows_meta_table(self):
        """URL の次にメタ情報を `[ラベル] 値` の表で出す (先頭はステータス)"""
        lines = view_module.format_issue_detail(VIEWED_ISSUE)

        # ラベル列の幅は言語設定で変わるため、ラベルと値を前後から挟んで見る
        assert lines[3].startswith(f"[{messages.meta_status}")
        assert lines[3].endswith("] 終了")

    def test_separates_description(self):
        """メタ情報と説明の間は `----` で区切る"""
        lines = view_module.format_issue_detail(VIEWED_ISSUE)

        assert lines[lines.index("本文") - 1] == "----"

    def test_shows_journal_id(self):
        """コメントの行頭に journal_id を出す (`issue_journal update/delete` に渡せる)"""
        lines = view_module.format_issue_detail(VIEWED_ISSUE)

        assert "  238 [2026-04-29T02:26:43Z] コメントした人" in lines

    def test_shows_relation_id(self):
        """関係性の行頭に relation_id を出す (`relation view` に渡せる)"""
        lines = view_module.format_issue_detail(VIEWED_ISSUE)

        relation_line = lines[lines.index(messages.label_relations_header) + 1]
        assert relation_line.startswith("  13 [")
        assert "162" in relation_line

    def test_shows_attachment_id(self):
        """添付ファイルの行頭に attachment_id を出す (`attachment view` などに渡せる)"""
        lines = view_module.format_issue_detail(VIEWED_ISSUE)

        assert lines[lines.index(messages.label_attachments_header) + 1].startswith(
            "  40 sample.txt "
        )


class TestViewIssueComments:
    """`issue view` のコメント表示"""

    def test_shows_comments_without_include(self, monkeypatch, capsys):
        """`--include journals` 無しでも journals を取得して本文まで出す"""
        called = {}
        monkeypatch.setattr(
            view_module.issue_service,
            "read_issue",
            lambda issue_id, include: called.update(include=include) or VIEWED_ISSUE,
        )

        view_module.view_issue("42")

        assert "journals" in called["include"].split(",")
        assert "テストコメント" in capsys.readouterr().out


class TestIssueViewInclude:
    """`issue view --include` は有効値だけを受け付ける

    Redmine は未知の include を黙って無視するため、送信前に弾かないと
    タイポしても rc=0 で正常終了してしまう。`search --type` と同じ扱いにする。
    """

    def test_rejects_unknown_value(self, capsys):
        """未知の値があれば送信前に exit 2 し、その値と指定可能な値を案内する"""
        with pytest.raises(SystemExit) as e:
            parse_issue_args(["issue", "view", "42", "--include", "journal"])

        assert e.value.code == 2
        err = capsys.readouterr().err
        assert "journal" in err
        assert "allowed_statuses" in err

    def test_rejects_unknown_value_mixed_with_valid(self, capsys):
        """有効値と混ざっていても未知の値があれば弾く"""
        with pytest.raises(SystemExit):
            parse_issue_args(["issue", "view", "42", "--include", "journals,bogus"])

        assert "bogus" in capsys.readouterr().err

    def test_accepts_valid_values(self):
        """有効値をカンマ区切りで受け付け、前後の空白は取り除く"""
        args = parse_issue_args(
            ["issue", "view", "42", "--include", "children, watchers"]
        )

        assert args.include == ["children", "watchers"]

    def test_passes_include_to_api_with_defaults(self, monkeypatch):
        """指定した include を既定の relations,attachments,journals に足して取得する"""
        called = {}
        monkeypatch.setattr(
            view_module.issue_service,
            "read_issue",
            lambda issue_id, include: called.update(include=include) or VIEWED_ISSUE,
        )

        view_module.view_issue("42", include=["watchers", "journals"])

        assert called["include"].split(",") == [
            "relations",
            "attachments",
            "journals",
            "watchers",
        ]


class TestIssueUpdateUnknownIdRejected:
    """`issue update` に存在しない tracker_id / status_id を渡したとき

    Redmine は不正な tracker_id / status_id を 200 で黙って無視するため、
    送る前に弾かないと「更新しました」と出たまま値が変わらない。
    """

    @pytest.fixture
    def choices(self, monkeypatch):
        """トラッカー/ステータスの一覧と、呼ばれたら記録する更新をスタブする"""
        monkeypatch.setattr(
            update_module,
            "fetch_trackers",
            lambda refresh=False: [{"id": 1, "name": "バグ"}],
        )
        monkeypatch.setattr(
            update_module,
            "fetch_issue_statuses",
            lambda refresh=False: [{"id": 2, "name": "新規"}],
        )
        called = {}
        monkeypatch.setattr(
            update_module.issue_service,
            "update_issue",
            lambda **kwargs: called.update(kwargs),
        )
        return called

    def test_unknown_tracker_id_exits(self, choices, capsys):
        """存在しない tracker_id は更新を送らず exit 1 する"""
        with pytest.raises(SystemExit) as exc_info:
            handle_issue_update(
                parse_issue_args(["issue", "update", "42", "--tracker_id", "99999"])
            )

        assert exc_info.value.code == 1
        assert messages.tracker_not_found.format(id="99999") in capsys.readouterr().err
        assert choices == {}

    def test_unknown_status_id_exits(self, choices, capsys):
        """存在しない status_id は更新を送らず exit 1 する"""
        with pytest.raises(SystemExit) as exc_info:
            handle_issue_update(
                parse_issue_args(["issue", "update", "42", "--status_id", "99999"])
            )

        assert exc_info.value.code == 1
        assert messages.status_not_found.format(id="99999") in capsys.readouterr().err
        assert choices == {}

    def test_shows_available_ids(self, choices, capsys):
        """弾くときは指定できる id と名前を示す"""
        with pytest.raises(SystemExit):
            handle_issue_update(
                parse_issue_args(["issue", "update", "42", "--tracker_id", "99999"])
            )

        assert "1:バグ" in capsys.readouterr().err

    def test_id_missing_from_cache_is_rechecked_after_refresh(
        self, choices, monkeypatch
    ):
        """キャッシュに無い id は一覧を取り直して再判定する

        トラッカー/ステータスの一覧はほぼ無期限にキャッシュされるので、
        Redmine 側で追加された直後の正しい id を弾いてしまわないようにする。
        """
        monkeypatch.setattr(config, "redmine_url", "http://localhost:3001")
        refresh_args = []

        def fetch_trackers(refresh=False):
            refresh_args.append(refresh)
            trackers = [{"id": 1, "name": "バグ"}]
            if refresh:
                trackers.append({"id": 9, "name": "追加されたトラッカー"})
            return trackers

        monkeypatch.setattr(update_module, "fetch_trackers", fetch_trackers)

        handle_issue_update(
            parse_issue_args(["issue", "update", "42", "--tracker_id", "9"])
        )

        assert refresh_args == [False, True]
        assert choices["tracker_id"] == "9"

    def test_known_id_does_not_refresh(self, choices, monkeypatch):
        """キャッシュにある id では取り直さない(正常系のリクエストを増やさない)"""
        monkeypatch.setattr(config, "redmine_url", "http://localhost:3001")
        refresh_args = []

        def fetch_trackers(refresh=False):
            refresh_args.append(refresh)
            return [{"id": 1, "name": "バグ"}]

        monkeypatch.setattr(update_module, "fetch_trackers", fetch_trackers)

        handle_issue_update(
            parse_issue_args(["issue", "update", "42", "--tracker_id", "1"])
        )

        assert refresh_args == [False]

    def test_known_ids_are_sent(self, choices, monkeypatch):
        """一覧にある id はそのまま更新に渡す"""
        monkeypatch.setattr(config, "redmine_url", "http://localhost:3001")

        handle_issue_update(
            parse_issue_args(
                ["issue", "update", "42", "--tracker_id", "1", "--status_id", "2"]
            )
        )

        assert choices["tracker_id"] == "1"
        assert choices["status_id"] == "2"


class TestIssueUpdateAddWatcher:
    """`--add-watcher` に追加できないユーザーIDを渡したとき

    Redmine はウォッチャーにできないユーザーIDを 200 で黙って無視するため、
    追加できたかを確かめないと「追加しました」と出たまま追加されない。
    """

    def test_not_added_watcher_exits(self, monkeypatch, capsys):
        """追加が反映されていなければ exit 1 し、成功メッセージを出さない"""

        def fake_add_watcher(issue_id, user_id):
            raise WatcherNotFoundException(issue_id, user_id)

        monkeypatch.setattr(
            update_module.issue_service, "add_watcher", fake_add_watcher
        )

        with pytest.raises(SystemExit) as exc_info:
            handle_issue_update(
                parse_issue_args(["issue", "update", "42", "--add-watcher", "999"])
            )

        captured = capsys.readouterr()
        assert exc_info.value.code == 1
        assert (
            messages.watcher_not_added.format(issue_id="42", user_id=999)
            in captured.err
        )
        assert messages.watcher_added.format(issue_id="42", user_id=999) not in (
            captured.out
        )


class TestIssueUpdateDeleteRelation:
    """`--delete-relation` が Redmine のエラーで失敗したとき"""

    def test_http_error_exits(self, monkeypatch, capsys):
        """削除に失敗したら理由を出して exit 1 し、成功メッセージを出さない"""
        monkeypatch.setattr(
            update_module.issue_relation_service,
            "delete_relation",
            _raise_http_error(403),
        )

        with pytest.raises(SystemExit) as exc_info:
            handle_issue_update(
                parse_issue_args(
                    ["issue", "update", "42", "--delete-relation", "--to", "43"]
                )
            )

        captured = capsys.readouterr()
        assert exc_info.value.code == 1
        assert messages.relation_delete_failed in captured.err
        assert captured.out == ""


class TestIssueUpdateStatusChoices:
    """`issue update` の対話でステータスを選ぶとき

    ステータス一覧には活動中のプロジェクトで使っていないものも並ぶため、
    そのイシューから遷移できるステータスだけに絞る。
    """

    @pytest.fixture
    def selected_options(self, monkeypatch):
        """ステータスだけ選んだ対話にして、提示された選択肢を記録する"""
        monkeypatch.setattr(
            update_module, "fetch_custom_fields", lambda *args, **kwargs: None
        )
        monkeypatch.setattr(
            update_module,
            "inline_checkbox",
            lambda *args, **kwargs: ["status"],
        )
        recorded: list[tuple[str, str]] = []

        def inline_choice(message, options, default=None):
            recorded.extend(options)
            return options[0][0]

        monkeypatch.setattr(update_module, "inline_choice", inline_choice)
        return recorded

    def _stub_read_issue(self, monkeypatch, issue):
        """read_issue をスタブし、渡された include を記録して返す"""
        called = {}

        def read_issue(issue_id, include=""):
            called["include"] = include
            return issue

        monkeypatch.setattr(update_module.issue_service, "read_issue", read_issue)
        return called

    def test_limits_to_allowed_statuses(self, selected_options, monkeypatch):
        """遷移できるステータス (allowed_statuses) だけを選択肢に出す"""
        called = self._stub_read_issue(
            monkeypatch,
            {
                "project": {"id": 1},
                "tracker": {"id": 1},
                "status": {"id": 2, "name": "進行中"},
                "allowed_statuses": [
                    {"id": 2, "name": "進行中"},
                    {"id": 10, "name": "レビュー"},
                ],
            },
        )
        args = IssueUpdateArgs(issue_id="42")

        update_module._interactive_fill_issue_update_args(args)

        assert "allowed_statuses" in called["include"].split(",")
        assert selected_options == [("2", "進行中"), ("10", "レビュー")]


class TestIssueUpdateParentIssue:
    """`issue update` の対話で親チケットを変更する"""

    @pytest.fixture
    def interactive(self, monkeypatch):
        """親チケットだけ選んだ対話にして、提示された項目と入力の既定値を記録する"""
        monkeypatch.setattr(
            update_module, "fetch_custom_fields", lambda *args, **kwargs: None
        )
        recorded: dict = {}

        def inline_checkbox(message, options, initial_value=None):
            recorded["options"] = options
            return ["parent_issue"]

        monkeypatch.setattr(update_module, "inline_checkbox", inline_checkbox)
        return recorded

    def _stub_prompt(self, monkeypatch, recorded, value):
        def prompt_parent_issue_id(default=""):
            recorded["default"] = default
            return value

        monkeypatch.setattr(
            update_module, "prompt_parent_issue_id", prompt_parent_issue_id
        )

    def _stub_read_issue(self, monkeypatch, issue):
        monkeypatch.setattr(
            update_module.issue_service,
            "read_issue",
            lambda issue_id, include="": issue,
        )

    def test_parent_issue_is_selectable(self, interactive, monkeypatch):
        """更新項目に親チケットが並ぶ"""
        self._stub_read_issue(monkeypatch, {"project": {"id": 1}, "tracker": {"id": 1}})
        self._stub_prompt(monkeypatch, interactive, "100")
        args = IssueUpdateArgs(issue_id="42")

        update_module._interactive_fill_issue_update_args(args)

        assert ("parent_issue", messages.field_parent_issue) in interactive["options"]
        assert args.parent_issue_id == "100"

    def test_current_parent_is_default(self, interactive, monkeypatch):
        """現在の親チケット id を入力の既定値として出す"""
        self._stub_read_issue(
            monkeypatch,
            {"project": {"id": 1}, "tracker": {"id": 1}, "parent": {"id": 7}},
        )
        self._stub_prompt(monkeypatch, interactive, "7")
        args = IssueUpdateArgs(issue_id="42")

        update_module._interactive_fill_issue_update_args(args)

        assert interactive["default"] == "7"

    def test_empty_input_clears_parent(self, interactive, monkeypatch):
        """空入力は「親チケットを外す」として空文字のまま渡す"""
        self._stub_read_issue(
            monkeypatch,
            {"project": {"id": 1}, "tracker": {"id": 1}, "parent": {"id": 7}},
        )
        self._stub_prompt(monkeypatch, interactive, "")
        args = IssueUpdateArgs(issue_id="42")

        update_module._interactive_fill_issue_update_args(args)

        assert args.parent_issue_id == ""


class TestIssueUpdateRelateChoices:
    """`issue update --relate` の関係性タイプ

    値の集合は Redmine 側で固定なので、API を叩く前にクライアントで弾き、
    有効な値を一覧で示す。
    """

    @pytest.mark.parametrize("relation_type", RELATION_TYPES)
    def test_accepts_every_relation_type(self, relation_type):
        """Redmine が受け付ける 9 種はすべて指定できる"""
        args = parse_issue_args(
            ["issue", "update", "42", "--relate", relation_type, "--to", "43"]
        )

        assert args.relate == relation_type

    def test_rejects_unknown_relation_type(self, capsys):
        """不正なタイプは API を叩かずに弾き、有効な値を示す

        `relates` のつもりで `related` と打ちやすいので、Redmine の 422 を
        待たずにその場で候補を出す。
        """
        with pytest.raises(SystemExit):
            parse_issue_args(
                ["issue", "update", "42", "--relate", "related", "--to", "43"]
            )

        err = capsys.readouterr().err
        for relation_type in RELATION_TYPES:
            assert relation_type in err

    def test_covers_relation_types_shown_in_view(self):
        """表示できる関係性はすべて指定できる

        `issue view` の読み替え表と集合がずれると、見えているのに作れない
        (あるいはその逆の) タイプが出る。
        """
        assert set(RELATION_TYPES) == set(view_module.INVERSE_RELATION)


LISTED_ISSUE = {
    "id": 12,
    "subject": "ログインできない",
    "description": "複数行\nの説明",
    "project": {"id": 3, "name": "redi"},
    "tracker": {"id": 1, "name": "バグ"},
    "status": {"id": 2, "name": "進行中", "is_closed": False},
    "priority": {"id": 4, "name": "高め"},
    "author": {"id": 5, "name": "kawagh"},
    "category": {"id": 6, "name": "認証"},
    "fixed_version": {"id": 7, "name": "v1.0"},
    "start_date": "2026-09-01",
    "due_date": None,
    "done_ratio": 30,
    "is_private": False,
    "estimated_hours": 2.5,
    "spent_hours": 1.0,
    "custom_fields": [{"id": 1, "name": "顧客", "value": "A"}],
    "created_on": "2026-09-01T00:00:00Z",
    "updated_on": "2026-09-02T00:00:00Z",
    "closed_on": None,
}


class TestIssueListTsv:
    """`issue list --format tsv` は既存の id / subject / url の後ろに API のフィールドを並べる"""

    @pytest.fixture
    def listed(self, monkeypatch):
        monkeypatch.setattr(
            view_module.issue_service,
            "list_issues_page",
            lambda **kwargs: _page([LISTED_ISSUE]),
        )
        monkeypatch.setattr(config, "redmine_url", "http://localhost:3001")

    def test_expands_refs_and_leaves_unassigned_empty(self, listed, capsys):
        """参照は id / name に展開し、未割り当ての assigned_to は空セルにする

        description と custom_fields は tsv に載せない。
        """
        view_module.print_issues(fmt=OutputFormat.TSV)

        header, row = capsys.readouterr().out.splitlines()
        assert header.split("\t") == [
            "id", "subject", "url", "project_id", "project_name", "tracker_name",
            "status_name", "priority_name", "author_name", "assigned_to_id",
            "assigned_to_name", "category_name", "fixed_version_name", "start_date",
            "due_date", "done_ratio", "estimated_hours", "spent_hours", "is_private",
            "created_on", "updated_on", "closed_on",
        ]  # fmt: skip
        assert row.split("\t") == [
            "12", "ログインできない", "http://localhost:3001/issues/12", "3", "redi",
            "バグ", "進行中", "高め", "kawagh", "", "", "認証", "v1.0", "2026-09-01",
            "", "30", "2.5", "1.0", "false", "2026-09-01T00:00:00Z",
            "2026-09-02T00:00:00Z", "",
        ]  # fmt: skip
