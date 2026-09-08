import re
import sys
from collections.abc import Iterable, Sequence
from typing import Any


def eprint(*args: Any, **kwargs: Any) -> None:
    """print と同じ使い方で標準エラー出力に書く。"""
    kwargs["file"] = sys.stderr
    print(*args, **kwargs)


# TSV は 1 レコード 1 行・1 フィールド 1 セルが前提なので、
# 行と列の区切りになる文字はフィールドの中に残さない
_TSV_SEPARATORS = re.compile(r"[\t\r\n]+")


def tsv_cell(value: object) -> str:
    """値を TSV の 1 セルにする。

    - None は空文字
    - bool は `true` / `false` (Redmine の JSON と同じ綴り)
    - タブと改行は空白 1 つに潰す (連続していても 1 つ)
    """
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    return _TSV_SEPARATORS.sub(" ", str(value))


def format_tsv_row(cells: Sequence[object]) -> str:
    """1 レコードを TSV の 1 行 (改行なし) にする。"""
    return "\t".join(tsv_cell(cell) for cell in cells)


def print_tsv(header: Sequence[str], rows: Iterable[Sequence[object]]) -> None:
    """一覧を TSV として標準出力に出す。

    ヘッダー名はスクリプトから列名で参照される前提なので、言語設定に
    関わらず英語のまま出す (i18n の対象外)。
    列は末尾に足す分には既存のスクリプトを壊さないが、並べ替えや削除は壊す。
    """
    print(format_tsv_row(header))
    for row in rows:
        print(format_tsv_row(row))
