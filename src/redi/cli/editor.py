import os
import subprocess
import tempfile

from redi.config import editor


def open_editor(initial_text: str = "") -> str:
    with tempfile.NamedTemporaryFile(suffix=".md", mode="w+", delete=False) as f:
        if initial_text:
            f.write(initial_text)
        tmp_path = f.name
    try:
        if editor == "code":
            # wait to close file
            editor_command = ["code", "--wait"]
        else:
            editor_command = [editor]

        subprocess.run([*editor_command, tmp_path], check=True)
        with open(tmp_path) as f:
            return f.read().strip()
    finally:
        os.unlink(tmp_path)


def save_text_to_tempfile(text: str) -> str:
    """text を一時ファイルに保存してそのパスを返す(呼び出し側で削除しない)。

    issue create/update などが失敗したときに、エディタで記載した本文が
    失われないよう退避させる用途で使う。
    """
    with tempfile.NamedTemporaryFile(
        prefix="redi-", suffix=".md", mode="w", delete=False
    ) as f:
        f.write(text)
        return f.name
