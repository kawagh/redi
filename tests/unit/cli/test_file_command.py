"""`file` サブコマンドの標準出力を守るテスト。"""

from redi.cli import file_command
from redi.cli.shared_options import OutputFormat


class TestFileListTsv:
    """`file list --format tsv` は既存列の後ろに種別・作者・作成日時・DL 数・ダイジェストを並べる"""

    def test_prints_content_type_author_and_digest(self, monkeypatch, capsys):
        """author は author_id / author_name に展開し、version が無いファイルは空セルにする"""
        monkeypatch.setattr(
            file_command.file_service,
            "list_files",
            lambda project_id: [
                {
                    "id": 4,
                    "filename": "manual.pdf",
                    "filesize": 1024,
                    "content_type": "application/pdf",
                    "description": "",
                    "content_url": "http://localhost:3001/attachments/download/4/manual.pdf",
                    "author": {"id": 5, "name": "kawagh"},
                    "created_on": "2026-09-01T00:00:00Z",
                    "downloads": 2,
                    "digest": "abc123",
                }
            ],
        )

        file_command._list_files("demo", fmt=OutputFormat.TSV)

        assert capsys.readouterr().out == (
            "id\tfilename\tfilesize\tversion_id\tversion_name\tcontent_type"
            "\tauthor_id\tauthor_name\tcreated_on\tdownloads\tdigest\n"
            "4\tmanual.pdf\t1024\t\t\tapplication/pdf\t5\tkawagh"
            "\t2026-09-01T00:00:00Z\t2\tabc123\n"
        )
