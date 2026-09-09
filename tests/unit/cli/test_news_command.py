"""`news` サブコマンドの標準出力を守るテスト。"""

from redi.cli import news_command
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
