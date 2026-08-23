"""表示幅(全角込み)を扱う整形ヘルパー。

`cli` と `tui` のどちらからも使うため層に依存しない位置に置く。
"""

from wcwidth import wcswidth

ELLIPSIS = "…"


def display_width(text: str) -> int:
    """`text` の表示幅を返す。

    `wcswidth` は制御文字を含むと -1 を返すので、その場合は 1 文字ずつ数え直し、
    幅を測れない文字を 1 幅として扱う。
    """
    width = wcswidth(text)
    if width >= 0:
        return width
    return sum(max(wcswidth(char), 1) for char in text)


def pad_display(text: str, width: int) -> str:
    padding = max(0, width - display_width(text))
    return text + " " * padding


def truncate_display(text: str, width: int) -> str:
    """表示幅が `width` に収まるよう、はみ出す分を `…` に置き換える。"""
    if width <= 0:
        return ""
    if display_width(text) <= width:
        return text
    limit = width - display_width(ELLIPSIS)
    if limit <= 0:
        return ELLIPSIS
    kept = ""
    kept_width = 0
    for char in text:
        char_width = display_width(char)
        if kept_width + char_width > limit:
            break
        kept += char
        kept_width += char_width
    return kept + ELLIPSIS
