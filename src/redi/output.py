import itertools
import re
import sys
import threading
from collections.abc import Iterable, Iterator, Mapping, Sequence
from contextlib import contextmanager
from typing import Any


def eprint(*args: Any, **kwargs: Any) -> None:
    """print と同じ使い方で標準エラー出力に書く。"""
    kwargs["file"] = sys.stderr
    print(*args, **kwargs)


_SPINNER_FRAMES = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
_SPINNER_INTERVAL_SECONDS = 0.1
# カーソル位置から行末までを消す
_ERASE_LINE = "\r\033[K"


@contextmanager
def loading(message: str) -> Iterator[None]:
    """ブロック内の処理を待つ間、標準エラー出力にスピナーを表示する。

    - 標準エラー出力が TTY でなければ何も出さない (パイプやエージェント・CI の出力を汚さない)
    - 処理が終わったらスピナーの行を消し、後続の出力の見た目を変えない
    """
    if not sys.stderr.isatty():
        yield
        return
    stop = threading.Event()

    def spin() -> None:
        # 通信はメインスレッドを止めるので、描画は別スレッドで回す
        for frame in itertools.cycle(_SPINNER_FRAMES):
            sys.stderr.write(f"\r{frame} {message}")
            sys.stderr.flush()
            if stop.wait(_SPINNER_INTERVAL_SECONDS):
                break
        sys.stderr.write(_ERASE_LINE)
        sys.stderr.flush()

    thread = threading.Thread(target=spin, daemon=True)
    thread.start()
    try:
        yield
    finally:
        stop.set()
        thread.join()


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


def tsv_ref(item: Mapping[str, Any], key: str) -> tuple[object, object]:
    """ネストした参照 `key: {id, name}` を `key_id` / `key_name` の 2 セルに展開する。

    参照が無い (担当者未割り当てなど) ときは両方とも None (空セル) にする。
    """
    ref = item.get(key) or {}
    return ref.get("id"), ref.get("name")
