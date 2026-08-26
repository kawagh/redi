"""対話入力に入る前後の共通処理をまとめたヘルパー。

非TTYガード:
    エージェントやCIが引数不足のまま実行すると prompt_toolkit が EOFError を送出し、
    スタックトレースだけが残って何の入力が足りないのか分からないため、
    対話に入る前にTTYを確認し、求めていた入力を示して終了する。

キャンセル (Ctrl-C / Ctrl-D) の扱い:
    対話をキャンセルしたら `canceled_as_exit` が異常終了として
    標準エラーに通知して exit 1 する。
"""

import sys
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from prompt_toolkit import prompt as _prompt

from redi.i18n import messages
from redi.output import eprint


def ensure_interactive(message: str) -> None:
    """標準入力がTTYでなければ、求めていた入力を示して exit 1 する。"""
    if sys.stdin.isatty():
        return
    eprint(
        messages.non_interactive_input_required.format(
            message=message.strip().rstrip(":").strip()
        )
    )
    sys.exit(1)


def prompt(message: str, **kwargs: Any) -> str:
    """prompt_toolkit.prompt に非TTYガードを挟んだもの。

    CLI からの一行入力はこちらを使う。
    """
    ensure_interactive(message)
    return str(_prompt(message, **kwargs))


@contextmanager
def canceled_as_exit(notice: str | None = None) -> Iterator[None]:
    """キャンセルを掴んで標準エラーに通知し、exit 1 する。

    処理を続けようがない箇所で使う。
    notice は `redi init` のように設定とは別の言語で表示する箇所のためのもので、
    省略すると設定の言語で通知する。
    """
    try:
        yield
    except (KeyboardInterrupt, EOFError):
        eprint(notice or messages.canceled)
        sys.exit(1)
