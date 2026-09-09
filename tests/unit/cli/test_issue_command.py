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
from redi.cli.issue_command import custom_fields as custom_fields_module
from redi.cli.issue_command import dispatch as dispatch_module
from redi.cli.issue_command import update as update_module
from redi.cli.issue_command import view as view_module
from redi.cli.issue_command.create import IssueCreateArgs, handle_issue_create
from redi.cli.issue_command.update import IssueUpdateArgs, handle_issue_update
from redi.cli.shared_options import OutputFormat
from redi.i18n import messages

CREATED_ISSUE = {"id": 123, "subject": "件名"}


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

        monkeypatch.setattr(view_module.issue_service, "list_issues", _raise)

        with pytest.raises(SystemExit) as exc_info:
            view_module.list_issues(project_id="missing")

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

        monkeypatch.setattr(view_module.issue_service, "list_issues", _raise)

        with pytest.raises(SystemExit) as exc_info:
            view_module.list_issues(project_id="demo", query_id="5")

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
            "list_issues",
            lambda **kwargs: called.update(kwargs) or [],
        )
        args = parse_issue_args(["issue", "list", "-q", "5", "-p", "demo"])

        dispatch_module.handle_issue(args)

        assert called["query_id"] == "5"
        assert called["project_id"] == "demo"


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

    def test_shows_meta_table(self):
        """件名の次にメタ情報を `[ラベル] 値` の表で出す (先頭はステータス)"""
        lines = view_module.format_issue_detail(VIEWED_ISSUE)

        assert lines[0] == "#42 件名"
        # ラベル列の幅は言語設定で変わるため、ラベルと値を前後から挟んで見る
        assert lines[2].startswith(f"[{messages.meta_status}")
        assert lines[2].endswith("] 終了")

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


def _issue_custom_field(cf_id: int, name: str, trackers: list[dict]) -> dict:
    """/custom_fields.json が返すイシュー用カスタムフィールドの最小形"""
    return {
        "id": cf_id,
        "name": name,
        "customized_type": "issue",
        "is_required": False,
        "trackers": trackers,
    }


# プロジェクトで有効なカスタムフィールド。3 はプロジェクトで無効、2 はバグトラッカー限定
PROJECT_CUSTOM_FIELDS = [{"id": 1, "name": "顧客"}, {"id": 2, "name": "バグ限定"}]
ALL_CUSTOM_FIELDS = [
    _issue_custom_field(1, "顧客", trackers=[]),
    _issue_custom_field(2, "バグ限定", trackers=[{"id": 1, "name": "バグ"}]),
    _issue_custom_field(3, "他プロジェクト", trackers=[]),
]


class TestIssueCreateUnknownCustomFieldIdRejected:
    """`issue create --custom_fields` に使えないカスタムフィールド id を渡したとき

    Redmine は存在しない id や対象で使えない id を 200 で黙って無視するため、
    送る前に弾かないと「作成しました」と出たまま値が入らない。
    """

    @pytest.fixture
    def custom_field_lists(self, monkeypatch):
        """プロジェクト/全体の一覧と、呼ばれたら記録する作成をスタブする"""
        monkeypatch.setattr(config, "redmine_url", "http://localhost:3001")
        monkeypatch.setattr(
            custom_fields_module,
            "fetch_project_issue_custom_fields",
            lambda project_id: PROJECT_CUSTOM_FIELDS,
        )
        monkeypatch.setattr(
            custom_fields_module,
            "fetch_custom_fields",
            lambda refresh=False: ALL_CUSTOM_FIELDS,
        )
        called = {}

        def create_issue(**kwargs):
            called.update(kwargs)
            return CREATED_ISSUE

        monkeypatch.setattr(create_module.issue_service, "create_issue", create_issue)
        return called

    @staticmethod
    def _create(custom_fields: str, tracker_id: str = "2") -> None:
        handle_issue_create(
            parse_issue_args(
                [
                    "issue",
                    "create",
                    "件名",
                    "--project_id",
                    "proj",
                    "--tracker_id",
                    tracker_id,
                    "-d",
                    "本文",
                    "--custom_fields",
                    custom_fields,
                ]
            )
        )

    def test_unknown_custom_field_id_exits(self, custom_field_lists, capsys):
        """存在しない id は作成を送らず exit 1 する"""
        with pytest.raises(SystemExit) as exc_info:
            self._create("9999=x")

        assert exc_info.value.code == 1
        assert (
            messages.custom_field_not_found.format(id="9999") in capsys.readouterr().err
        )
        assert custom_field_lists == {}

    def test_shows_available_ids(self, custom_field_lists, capsys):
        """弾くときは指定できる id と名前を示す"""
        with pytest.raises(SystemExit):
            self._create("9999=x")

        assert "1:顧客" in capsys.readouterr().err

    def test_id_not_enabled_for_project_exits(self, custom_field_lists, capsys):
        """存在してもプロジェクトで有効でない id は弾く"""
        with pytest.raises(SystemExit):
            self._create("3=x")

        assert messages.custom_field_not_found.format(id="3") in (
            capsys.readouterr().err
        )
        assert custom_field_lists == {}

    def test_id_not_enabled_for_tracker_exits(self, custom_field_lists, capsys):
        """プロジェクトで有効でもトラッカーで使えない id は弾く"""
        with pytest.raises(SystemExit):
            self._create("2=x", tracker_id="2")

        assert messages.custom_field_not_found.format(id="2") in (
            capsys.readouterr().err
        )
        assert custom_field_lists == {}

    def test_lists_every_unknown_id(self, custom_field_lists, capsys):
        """使えない id が複数あればまとめて示す"""
        with pytest.raises(SystemExit):
            self._create("1=a,3=b,9999=c")

        assert messages.custom_field_not_found.format(id="3, 9999") in (
            capsys.readouterr().err
        )

    def test_known_ids_are_sent(self, custom_field_lists):
        """使える id はそのまま作成に渡す"""
        self._create("1=A,2=B", tracker_id="1")

        assert custom_field_lists["custom_fields"] == [
            {"id": 1, "value": "A"},
            {"id": 2, "value": "B"},
        ]

    def test_non_admin_rejects_by_project_list(
        self, custom_field_lists, monkeypatch, capsys
    ):
        """全体の一覧が取れない (非管理者) ときもプロジェクトの一覧で弾く

        トラッカーでは絞れないので、プロジェクトで有効な id はそのまま通す。
        """
        monkeypatch.setattr(
            custom_fields_module, "fetch_custom_fields", lambda refresh=False: None
        )

        with pytest.raises(SystemExit):
            self._create("3=x")
        assert messages.custom_field_not_found.format(id="3") in (
            capsys.readouterr().err
        )

        self._create("2=B", tracker_id="2")
        assert custom_field_lists["custom_fields"] == [{"id": 2, "value": "B"}]

    def test_id_missing_from_cache_is_rechecked_after_refresh(
        self, custom_field_lists, monkeypatch
    ):
        """キャッシュに無い id は全体の一覧を取り直して再判定する

        Redmine 側で追加された直後の正しい id を弾いてしまわないようにする。
        """
        monkeypatch.setattr(
            custom_fields_module,
            "fetch_project_issue_custom_fields",
            lambda project_id: PROJECT_CUSTOM_FIELDS + [{"id": 9, "name": "追加"}],
        )
        refresh_args = []

        def fetch_custom_fields(refresh=False):
            refresh_args.append(refresh)
            if refresh:
                return ALL_CUSTOM_FIELDS + [_issue_custom_field(9, "追加", [])]
            return ALL_CUSTOM_FIELDS

        monkeypatch.setattr(
            custom_fields_module, "fetch_custom_fields", fetch_custom_fields
        )

        self._create("9=x")

        assert refresh_args == [False, True]
        assert custom_field_lists["custom_fields"] == [{"id": 9, "value": "x"}]

    def test_known_id_does_not_refresh(self, custom_field_lists, monkeypatch):
        """キャッシュにある id では取り直さない(正常系のリクエストを増やさない)"""
        refresh_args = []

        def fetch_custom_fields(refresh=False):
            refresh_args.append(refresh)
            return ALL_CUSTOM_FIELDS

        monkeypatch.setattr(
            custom_fields_module, "fetch_custom_fields", fetch_custom_fields
        )

        self._create("1=x")

        assert refresh_args == [False]

    def test_missing_project_exits(self, custom_field_lists, monkeypatch, capsys):
        """プロジェクトが無ければ検証を続けず、プロジェクトが無い旨で exit 1 する"""

        def raise_not_found(project_id):
            raise ProjectNotFoundException(project_id)

        monkeypatch.setattr(
            custom_fields_module, "fetch_project_issue_custom_fields", raise_not_found
        )

        with pytest.raises(SystemExit) as exc_info:
            self._create("1=x")

        assert exc_info.value.code == 1
        assert messages.project_not_found.format(id="proj") in (capsys.readouterr().err)


class TestIssueUpdateUnknownCustomFieldIdRejected:
    """`issue update --custom_fields` に使えないカスタムフィールド id を渡したとき

    判定は対象イシューのプロジェクト/トラッカーで行い、
    --project_id / --tracker_id を指定していればそちらで行う。
    """

    @pytest.fixture
    def custom_field_lists(self, monkeypatch):
        """対象イシュー・一覧と、呼ばれたら記録する更新をスタブする"""
        monkeypatch.setattr(config, "redmine_url", "http://localhost:3001")
        monkeypatch.setattr(
            update_module.issue_service,
            "read_issue",
            lambda issue_id, include="": {
                "id": 42,
                "project": {"id": 7, "name": "現プロジェクト"},
                "tracker": {"id": 2, "name": "機能"},
            },
        )
        asked_projects = []

        def fetch_project_issue_custom_fields(project_id):
            asked_projects.append(project_id)
            return PROJECT_CUSTOM_FIELDS

        monkeypatch.setattr(
            custom_fields_module,
            "fetch_project_issue_custom_fields",
            fetch_project_issue_custom_fields,
        )
        monkeypatch.setattr(
            custom_fields_module,
            "fetch_custom_fields",
            lambda refresh=False: ALL_CUSTOM_FIELDS,
        )
        monkeypatch.setattr(
            update_module,
            "fetch_trackers",
            lambda refresh=False: [
                {"id": 1, "name": "バグ"},
                {"id": 2, "name": "機能"},
            ],
        )
        called = {}
        monkeypatch.setattr(
            update_module.issue_service,
            "update_issue",
            lambda **kwargs: called.update(kwargs),
        )
        return called, asked_projects

    def test_unknown_custom_field_id_exits(self, custom_field_lists, capsys):
        """存在しない id は更新を送らず exit 1 する"""
        called, _ = custom_field_lists

        with pytest.raises(SystemExit) as exc_info:
            handle_issue_update(
                parse_issue_args(["issue", "update", "42", "--custom_fields", "9999=x"])
            )

        assert exc_info.value.code == 1
        assert (
            messages.custom_field_not_found.format(id="9999") in capsys.readouterr().err
        )
        assert called == {}

    def test_judged_by_current_project_and_tracker(self, custom_field_lists, capsys):
        """指定が無ければ対象イシューのプロジェクト/トラッカーで判定する"""
        called, asked_projects = custom_field_lists

        with pytest.raises(SystemExit):
            handle_issue_update(
                parse_issue_args(["issue", "update", "42", "--custom_fields", "2=x"])
            )

        assert asked_projects == ["7"]
        assert messages.custom_field_not_found.format(id="2") in (
            capsys.readouterr().err
        )
        assert called == {}

    def test_judged_by_given_project_and_tracker(self, custom_field_lists):
        """--project_id / --tracker_id を指定していればそちらで判定する"""
        called, asked_projects = custom_field_lists

        handle_issue_update(
            parse_issue_args(
                [
                    "issue",
                    "update",
                    "42",
                    "--project_id",
                    "dest",
                    "--tracker_id",
                    "1",
                    "--custom_fields",
                    "2=x",
                ]
            )
        )

        assert asked_projects == ["dest"]
        assert called["custom_fields"] == [{"id": 2, "value": "x"}]

    def test_known_ids_are_sent(self, custom_field_lists):
        """使える id はそのまま更新に渡す"""
        called, _ = custom_field_lists

        handle_issue_update(
            parse_issue_args(["issue", "update", "42", "--custom_fields", "1=A"])
        )

        assert called["custom_fields"] == [{"id": 1, "value": "A"}]


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
            view_module.issue_service, "list_issues", lambda **kwargs: [LISTED_ISSUE]
        )
        monkeypatch.setattr(config, "redmine_url", "http://localhost:3001")

    def test_expands_refs_and_leaves_unassigned_empty(self, listed, capsys):
        """参照は id / name に展開し、未割り当ての assigned_to は空セルにする

        description と custom_fields は tsv に載せない。
        """
        view_module.list_issues(fmt=OutputFormat.TSV)

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
