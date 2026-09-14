"""`news` サブコマンドの標準出力と対話を守るテスト。"""

import argparse

import pytest

from redi.cli import confirm, news_command
from redi.cli.interactive import InputCanceledException
from redi.cli.shared_options import OutputFormat


class TestNewsListTsv:
    """`news list --format tsv` は既存列の後ろに author_id と summary を並べる"""

    def test_prints_author_id_and_summary(self, monkeypatch, capsys):
        """author は author_name しか無かったので author_id を揃える。description は載せない"""
        monkeypatch.setattr(
            news_command.news_service,
            "list_news",
            lambda project_id, **kwargs: [
                {
                    "id": 2,
                    "project": {"id": 3, "name": "redi"},
                    "author": {"id": 5, "name": "kawagh"},
                    "title": "リリース",
                    "summary": "0.0.78 を公開",
                    "description": "本文\n複数行",
                    "created_on": "2026-09-01T00:00:00Z",
                }
            ],
        )

        news_command._list_news(fmt=OutputFormat.TSV)

        assert capsys.readouterr().out == (
            "id\ttitle\tproject_id\tproject_name\tauthor_name\tcreated_on"
            "\tauthor_id\tsummary\n"
            "2\tリリース\t3\tredi\tkawagh\t2026-09-01T00:00:00Z\t5\t0.0.78 を公開\n"
        )


class TestNewsDelete:
    """`news delete` はニュース ID を打ち直させてから消す

    一覧から選べるぶん誤選択の余地があり、削除するとコメントと添付ごと戻せないので、
    yes/No ではなく対象の id を打ち直させる (github#596)。
    """

    @staticmethod
    def _args(news_id: str | None, yes: bool = False) -> argparse.Namespace:
        return argparse.Namespace(
            news_command="delete", news_id=news_id, yes=yes, project_id=None
        )

    @pytest.fixture
    def stub_service(self, monkeypatch):
        deleted: list[str] = []
        monkeypatch.setattr(
            news_command.news_service,
            "read_news",
            lambda news_id: {"id": 12, "title": "リリース"},
        )
        monkeypatch.setattr(news_command.news_service, "delete_news", deleted.append)
        return deleted

    def test_deletes_when_id_retyped(self, monkeypatch, capsys, stub_service):
        """id を正しく打ち直したら削除する。プロンプトには対象の id とタイトルを示す"""
        monkeypatch.setattr(confirm, "prompt", lambda _msg: "12")

        news_command.handle_news(self._args("12"))

        assert stub_service == ["12"]
        assert "12 リリース" in capsys.readouterr().out

    def test_cancels_when_id_mismatch(self, monkeypatch, stub_service):
        """id が一致しなければ InputCanceledException を送出し、削除しない"""
        monkeypatch.setattr(confirm, "prompt", lambda _msg: "13")

        with pytest.raises(InputCanceledException):
            news_command.handle_news(self._args("12"))

        assert stub_service == []

    def test_yes_skips_confirmation(self, monkeypatch, stub_service):
        """--yes なら確認を飛ばして削除する"""

        def fail(_msg):
            raise AssertionError("confirmation prompt should not be shown")

        monkeypatch.setattr(confirm, "prompt", fail)

        news_command.handle_news(self._args("12", yes=True))

        assert stub_service == ["12"]

    def test_selected_from_list_still_requires_retype(self, monkeypatch, stub_service):
        """一覧から選んだ場合も id を打ち直させる。選ぶ便利さは保ちつつ消す直前に対象を意識させる"""
        monkeypatch.setattr(
            news_command, "_interactive_select_news_id", lambda *_a, **_k: "12"
        )
        monkeypatch.setattr(confirm, "prompt", lambda _msg: "")

        with pytest.raises(InputCanceledException):
            news_command.handle_news(self._args(None))

        assert stub_service == []
