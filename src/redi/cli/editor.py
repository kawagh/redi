import os
import subprocess
import tempfile

from redi.cli.interactive import ensure_interactive
from redi.config import editor
from redi.i18n import messages


def open_editor(initial_text: str = "") -> str:
    ensure_interactive(messages.prompt_editor_input)
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


def shorten_to_oneline(text: str, max_len: int = 80) -> str:
    """改行をスペースに畳んで 1 行化し、長すぎたら省略する。"""
    one_line = " ".join(text.splitlines())
    if len(one_line) > max_len:
        return one_line[: max_len - 1] + "…"
    return one_line


def save_body_on_failure(text: str | None) -> None:
    """送信失敗時に、エディタで記載した本文を一時ファイルへ退避する。"""
    if not text:
        return
    path = save_text_to_tempfile(text)
    print(messages.body_saved_to_tempfile.format(path=path))
