import argparse
import copy

import pytest

from redi.cli import main as main_module
from redi.cli.main import build_redi_parser


class TestProfileFlagPlacement:
    """--profile はサブコマンドの前後どちらに置いても受け付けられる"""

    @pytest.fixture
    def parser(self, monkeypatch) -> argparse.ArgumentParser:
        monkeypatch.setattr(main_module, "list_profile_names", list)
        return build_redi_parser()

    def test_before_subcommand(self, parser):
        """ルート直後の `--profile foo issue list` を受け付ける"""
        args = parser.parse_args(["--profile", "foo", "issue", "list"])

        assert args.profile == "foo"
        assert args.command == "issue"
        assert args.issue_command == "list"

    def test_after_top_level_subcommand(self, parser):
        """1階層目のサブコマンドの後ろの `issue --profile foo list` を受け付ける"""
        args = parser.parse_args(["issue", "--profile", "foo", "list"])

        assert args.command == "issue"
        assert args.issue_command == "list"
        assert args.profile == "foo"

    def test_after_nested_subcommand(self, parser):
        """ネストされたサブコマンドの後ろの `issue list --profile foo` を受け付ける"""
        args = parser.parse_args(["issue", "list", "--profile", "foo"])

        assert args.command == "issue"
        assert args.issue_command == "list"
        assert args.profile == "foo"

    def test_after_nested_subcommand_with_equals(self, parser):
        """`--profile=foo` 形式もサブコマンド後ろで受け付ける"""
        args = parser.parse_args(["issue", "create", "--profile=foo"])

        assert args.command == "issue"
        assert args.issue_command == "create"
        assert args.profile == "foo"

    def test_after_resource_only_subcommand(self, parser):
        """ネストの無い `me --profile foo` のような呼び出しも受け付ける"""
        args = parser.parse_args(["me", "--profile", "foo"])

        assert args.command == "me"
        assert args.profile == "foo"

    def test_with_tui_flag(self, parser):
        """サブコマンド無しで `--tui --profile foo` の組み合わせも受け付ける"""
        args = parser.parse_args(["--tui", "--profile", "foo"])

        assert args.tui is True
        assert args.profile == "foo"
        assert args.command is None


LIST_ONLY_RESOURCES = [
    ("tracker", "t"),
    ("issue_status", "is"),
    ("issue_priority", "ip"),
    ("time_entry_activity", "tea"),
    ("document_category", "dc"),
    ("query", "q"),
    ("custom_field", "cf"),
]


# 応答をキャッシュするリソース。--refresh はこれらにだけ付く
CACHED_RESOURCES = [
    (resource, alias) for resource, alias in LIST_ONLY_RESOURCES if resource != "query"
]


class TestRefreshFlagPlacement:
    """--refresh はキャッシュを持つリソースで前後どちらに置いても受け付けられる"""

    @pytest.fixture
    def parser(self, monkeypatch) -> argparse.ArgumentParser:
        monkeypatch.setattr(main_module, "list_profile_names", list)
        return build_redi_parser()

    @pytest.mark.parametrize("resource,alias", CACHED_RESOURCES)
    def test_defaults_to_false(self, parser, resource, alias):
        """指定が無ければ False (キャッシュを読む)"""
        args = parser.parse_args([resource, "list"])

        assert args.refresh is False

    @pytest.mark.parametrize("resource,alias", CACHED_RESOURCES)
    def test_refresh_flag_on_either_side(self, parser, resource, alias):
        """--refresh は list の前後どちらに置いても、list を省いても有効になる"""
        for argv in (
            [resource, "list", "--refresh"],
            # 前置した値が、後置の未指定によって False に戻されないことも兼ねる
            [resource, "--refresh", "list"],
            [alias, "--refresh"],
        ):
            args = parser.parse_args(argv)

            assert args.refresh is True, argv

    def test_not_added_to_uncached_resource(self, parser):
        """キャッシュしない query には --refresh を生やさない"""
        with pytest.raises(SystemExit):
            parser.parse_args(["query", "list", "--refresh"])


class TestListOnlyResourceListSubcommand:
    """一覧専用リソースは list (alias: l) を付けても引数無しと同じに解釈される"""

    @pytest.fixture
    def parser(self, monkeypatch) -> argparse.ArgumentParser:
        monkeypatch.setattr(main_module, "list_profile_names", list)
        return build_redi_parser()

    @pytest.mark.parametrize("resource,alias", LIST_ONLY_RESOURCES)
    def test_accepts_list_subcommand(self, parser, resource, alias):
        """`redi <resource> list` と `redi <alias> l` の双方を受け付ける"""
        for argv in ([resource, "list"], [alias, "l"]):
            args = parser.parse_args(argv)

            assert args.command == argv[0]
            assert args.full is False

    @pytest.mark.parametrize("resource,alias", LIST_ONLY_RESOURCES)
    def test_full_flag_on_either_side(self, parser, resource, alias):
        """--full は list の前後どちらに置いても有効になる"""
        for argv in (
            [resource, "list", "--full"],
            [resource, "--full", "list"],
            [resource, "--full"],
        ):
            args = parser.parse_args(argv)

            assert args.full is True, argv


class TestSharedOptionPlacement:
    """親パーサ側のオプションは list サブコマンドの前後どちらに置いても受け付けられる"""

    @pytest.fixture
    def parser(self, monkeypatch) -> argparse.ArgumentParser:
        monkeypatch.setattr(main_module, "list_profile_names", list)
        return build_redi_parser()

    def test_issue_option_after_list(self, parser):
        """`issue list --limit 3` を受け付ける"""
        args = parser.parse_args(["issue", "list", "--limit", "3"])

        assert args.issue_command == "list"
        assert args.limit == 3

    def test_issue_option_before_list(self, parser):
        """`issue --limit 3 list` も従来どおり受け付ける"""
        args = parser.parse_args(["issue", "--limit", "3", "list"])

        assert args.issue_command == "list"
        assert args.limit == 3

    def test_issue_option_not_overwritten_by_list_default(self, parser):
        """前置した値を list サブパーサのデフォルト値が上書きしない"""
        args = parser.parse_args(["issue", "--project_id", "1", "list"])

        assert args.project_id == "1"

    def test_issue_option_defaults_kept(self, parser):
        """オプション未指定ならデフォルト値のまま"""
        args = parser.parse_args(["issue", "list"])

        assert args.limit is None
        assert args.project_id is None
        assert args.full is False

    def test_issue_option_after_list_alias(self, parser):
        """エイリアス `issue l` の後ろにも書ける"""
        args = parser.parse_args(["issue", "l", "-l", "3"])

        assert args.issue_command == "l"
        assert args.limit == 3

    def test_time_entry_option_after_list(self, parser):
        """issue 以外のリソースでも後置できる"""
        args = parser.parse_args(
            ["time_entry", "list", "--from", "2026-01-01", "--user_id", "1"]
        )

        assert args.time_entry_command == "list"
        assert args.from_date == "2026-01-01"
        assert args.user_id == "1"

    @pytest.mark.parametrize(
        ("argv", "dest", "expected"),
        [
            (["project", "list", "--full"], "full", True),
            (["user", "list", "--full"], "full", True),
            (["role", "list", "--full"], "full", True),
            (["group", "list", "--full"], "full", True),
            (["version", "list", "--project_id", "1"], "project_id", "1"),
            (["wiki", "list", "--project_id", "1"], "project_id", "1"),
            (["membership", "list", "--project_id", "1"], "project_id", "1"),
            (["news", "list", "--project_id", "1"], "project_id", "1"),
            (["issue_category", "list", "--project_id", "1"], "project_id", "1"),
            (["file", "list", "--project_id", "1"], "project_id", "1"),
        ],
    )
    def test_option_after_list_for_each_resource(self, parser, argv, dest, expected):
        """親側にオプションを持つリソースはすべて後置できる"""
        args = parser.parse_args(argv)

        assert getattr(args, dest) == expected


# `<resource> <action>` の両方に --full を書ける (親側にも --full がある) リソース
FULL_FLAG_VIEW_TARGETS = [
    ["project", "view", "1"],
    ["issue", "view", "1"],
    ["issue", "create", "subject"],
    ["version", "view", "1"],
    ["wiki", "view", "Home"],
    ["user", "view", "1"],
    ["membership", "view", "1"],
    ["news", "view", "1"],
    ["role", "view", "1"],
    ["group", "view", "1"],
    ["issue_category", "view", "1"],
    ["relation", "view", "1"],
    ["time_entry", "view", "1"],
]


class TestFullFlagPlacement:
    """--full はリソースとサブコマンドのどちら側に置いても効く"""

    @pytest.fixture
    def parser(self, monkeypatch) -> argparse.ArgumentParser:
        monkeypatch.setattr(main_module, "list_profile_names", list)
        return build_redi_parser()

    @pytest.mark.parametrize("argv", FULL_FLAG_VIEW_TARGETS)
    def test_before_subcommand(self, parser, argv):
        """`<resource> --full <action>` が silent に無視されない"""
        args = parser.parse_args([argv[0], "--full", *argv[1:]])

        assert args.full is True

    @pytest.mark.parametrize("argv", FULL_FLAG_VIEW_TARGETS)
    def test_after_subcommand(self, parser, argv):
        """`<resource> <action> --full` も従来どおり効く"""
        args = parser.parse_args([*argv, "--full"])

        assert args.full is True

    @pytest.mark.parametrize("argv", FULL_FLAG_VIEW_TARGETS)
    def test_defaults_to_false(self, parser, argv):
        """指定が無ければ False"""
        args = parser.parse_args(argv)

        assert args.full is False

    def test_no_subparser_shadows_parent_full(self, parser):
        """--full を持つ親パーサの下では、サブパーサの --full は未指定時に値を載せない

        argparse はサブパーサのデフォルト値でパース済みの値を上書きするため、
        default=False のままだと前置した --full が silent に落ちる。
        """
        shadowing = _find_shadowing_full_defaults(parser, ["redi"])

        assert shadowing == []


def _find_shadowing_full_defaults(
    parser: argparse.ArgumentParser, path: list[str], parent_has_full: bool = False
) -> list[str]:
    """親が --full を持つのに default を SUPPRESS にしていないサブパーサを集める"""
    has_full = parent_has_full
    shadowing = []
    for action in parser._actions:
        if action.dest != "full" or not action.option_strings:
            continue
        if parent_has_full and action.default is not argparse.SUPPRESS:
            shadowing.append(" ".join(path))
        has_full = True
    for action in parser._actions:
        if not isinstance(action, argparse._SubParsersAction):
            continue
        for name, subparser in action.choices.items():
            shadowing += _find_shadowing_full_defaults(
                subparser, [*path, name], has_full
            )
    return shadowing


class TestTuiProfileSwitchLoop:
    """TUI が switch_profile で抜けたらプロファイルを適用して state 無しで再起動する"""

    @pytest.fixture
    def run_tui_calls(self, monkeypatch) -> list:
        """run_issue_tui に渡された TuiState を順に記録する"""
        from redi.tui.state import IssueFilter, TuiResult, TuiState

        monkeypatch.setattr("sys.argv", ["redi", "--tui"])
        monkeypatch.setattr(main_module, "list_profile_names", list)
        monkeypatch.setattr(main_module, "check_config", lambda: None)
        # 実物のシングルトンの接続先を書き換えないようにしておく
        monkeypatch.setattr(main_module.client, "reconfigure", lambda url, key: None)

        calls: list[TuiState] = []
        results = [
            TuiResult(action="switch_profile", tab="issues", profile_name="sub"),
            None,
        ]

        def fake_run_issue_tui(state, debug_log_path=None):
            # 呼び出し後にも state を触るので、受け取った時点の姿を控える
            calls.append(copy.deepcopy(state))
            # 切替前のセッションで state が育っている状況を作る
            state.project_id = "42"
            state.project_label = "Old"
            state.issue_tab.filter = IssueFilter(status_id="*", status_label="all")
            state.search_query = "keyword"
            state.preview_scroll = 5
            return results.pop(0)

        monkeypatch.setattr(main_module, "run_issue_tui", fake_run_issue_tui)
        return calls

    def test_applies_profile_and_reconfigures_client(self, run_tui_calls, monkeypatch):
        """config を貼り替えるだけでは足りず、束縛済みの client も再設定する

        忘れると設定値だけ新プロファイルになり、リクエストは旧インスタンスへ飛び続ける。
        """
        applied: list[str] = []
        reconfigured: list[tuple[str, str]] = []

        def fake_apply_profile(name):
            applied.append(name)
            monkeypatch.setattr(
                main_module.config, "redmine_url", "https://sub.example"
            )
            monkeypatch.setattr(main_module.config, "redmine_api_key", "secret-sub")

        monkeypatch.setattr(main_module.config, "apply_profile", fake_apply_profile)
        monkeypatch.setattr(
            main_module.client,
            "reconfigure",
            lambda url, key: reconfigured.append((url, key)),
        )

        main_module.main()

        assert applied == ["sub"]
        assert reconfigured == [("https://sub.example", "secret-sub")]

    def test_restarts_with_cleared_state(self, run_tui_calls, monkeypatch):
        """再起動時の state は前のプロファイルの内容を引き継がない

        carry_over を通すと別インスタンスの id を持ったまま再取得することになる。
        """
        from redi.tui.state import IssueFilter

        monkeypatch.setattr(main_module.config, "apply_profile", lambda name: None)

        main_module.main()

        assert len(run_tui_calls) == 2
        restarted = run_tui_calls[1]
        assert restarted.project_id is None
        assert restarted.project_label == ""
        assert restarted.issue_tab.filter == IssueFilter()
        assert restarted.search_query == ""
        assert restarted.preview_scroll == 0

    def test_carries_flash_message(self, run_tui_calls, monkeypatch):
        """再起動後の画面に切替完了のフラッシュメッセージが出る"""
        from redi.i18n import messages

        monkeypatch.setattr(main_module.config, "apply_profile", lambda name: None)

        main_module.main()

        assert run_tui_calls[1].flash_message == (
            messages.tui_flash_profile_switched.format(name="sub")
        )
