"""`wiki` サブコマンドの標準出力を守るテスト。"""

from redi import config
from redi.cli import wiki_command
from redi.cli.shared_options import OutputFormat


class TestWikiListTsv:
    """`wiki list --format tsv` は既存列の後ろに created_on を並べる"""

    def test_prints_created_on(self, monkeypatch, capsys):
        """index が返す created_on を末尾に足す。親が無いページは parent_title が空になる"""
        monkeypatch.setattr(
            wiki_command.wiki_service,
            "list_pages",
            lambda project_id: [
                {
                    "title": "Wiki",
                    "version": 3,
                    "created_on": "2026-01-01T00:00:00Z",
                    "updated_on": "2026-02-01T00:00:00Z",
                },
                {
                    "title": "Child",
                    "version": 1,
                    "parent": {"title": "Wiki"},
                    "created_on": "2026-03-01T00:00:00Z",
                    "updated_on": "2026-03-01T00:00:00Z",
                },
            ],
        )
        monkeypatch.setattr(config, "redmine_url", "http://localhost:3001")

        wiki_command._list_pages("demo", fmt=OutputFormat.TSV)

        assert capsys.readouterr().out == (
            "title\tparent_title\tversion\tupdated_on\turl\tcreated_on\n"
            "Wiki\t\t3\t2026-02-01T00:00:00Z\thttp://localhost:3001/projects/demo/wiki/Wiki"
            "\t2026-01-01T00:00:00Z\n"
            "Child\tWiki\t1\t2026-03-01T00:00:00Z"
            "\thttp://localhost:3001/projects/demo/wiki/Child\t2026-03-01T00:00:00Z\n"
        )
