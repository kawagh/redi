"""対話入力に入る前後の共通処理をまとめたヘルパー。

エージェントやCIが引数不足のまま実行すると prompt_toolkit が EOFError を送出し、
スタックトレースだけが残って何の入力が足りないのか分からないため、
対話に入る前にTTYを確認し、求めていた入力を示して終了する。

対話入力のキャンセルは InputCanceledException に揃える。CLI ではエントリポイント
(`redi.cli.main.main`) が標準エラーに通知して exit 1 に落とし、TUI から呼んだ経路では
TUI ループが受けて元の画面に戻す (github#564)。
"""

import sys
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from prompt_toolkit import prompt as _prompt

from redi.i18n import messages
from redi.output import eprint


class InputCanceledException(Exception):
    """対話入力がユーザーの意思でキャンセルされた。

    Ctrl-C / Ctrl-D のほか、項目を何も選ばずに確定したときや題名を空で確定した
    ときのように「やっぱりやめる」に相当する経路で送出する。
    message は利用者への通知文で、CLI では標準エラーへ、TUI では flash に出す。
    """

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


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
def raise_on_cancel(notice: str | None = None) -> Iterator[None]:
    """Ctrl-C / Ctrl-D を掴んで InputCanceledException に変換する。

    CLI から使うとエントリポイントで標準エラーに通知して exit 1 になる。
    notice は `redi init` のように設定とは別の言語で表示する箇所のためのもので、
    省略すると設定の言語で通知する。
    """
    try:
        yield
    except (KeyboardInterrupt, EOFError):
        raise InputCanceledException(notice or messages.canceled) from None
