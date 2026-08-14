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
