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


class TestWikiCreateExisting:
    """`wiki create <title>` は同名ページがあれば上書きせず exit 1 で止まる"""

    def test_exits_before_opening_editor(self, monkeypatch, capsys):
        """本文を書かせる前に止め、PUT もエディタ起動も行わない"""
        import argparse

        import pytest

        monkeypatch.setattr(config, "wiki_project_id", "demo")
        monkeypatch.setattr(
            wiki_command.wiki_service,
            "read_page",
            lambda project_id, page_title, version=None, full=False: {
                "title": page_title,
                "version": 2,
            },
        )

        def fail_editor(*args, **kwargs):
            raise AssertionError("open_editor should not be called")

        def fail_create(*args, **kwargs):
            raise AssertionError("create_page should not be called")

        monkeypatch.setattr(wiki_command, "open_editor", fail_editor)
        monkeypatch.setattr(wiki_command.wiki_service, "create_page", fail_create)
        args = argparse.Namespace(
            project_id=None,
            wiki_command="create",
            page_title="Existing",
            parent_title=None,
            description=None,
            comments="",
        )

        with pytest.raises(SystemExit) as e:
            wiki_command.handle_wiki(args)

        assert e.value.code == 1
        captured = capsys.readouterr()
        assert "Existing" in captured.err
        assert captured.out == ""
