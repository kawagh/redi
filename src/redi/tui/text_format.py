from wcwidth import wcswidth


def pad_display(text: str, width: int) -> str:
    padding = max(0, width - wcswidth(text))
    return text + " " * padding


def highlight_segments(
    text: str,
    query: str,
    base_style: str = "",
    hit_style: str = "reverse",
) -> list[tuple[str, str]]:
    """
    `text` の中で `query` (case-insensitive) にマッチする部分を
    `hit_style` で、それ以外を `base_style` で返す `(style, chunk)` のリスト。
    `query` が空なら全体を `base_style` で返す。
    """
    if not query:
        return [(base_style, text)]
    lower_text = text.lower()
    lower_query = query.lower()
    segments: list[tuple[str, str]] = []
    i = 0
    query_len = len(query)
    while i < len(text):
        idx = lower_text.find(lower_query, i)
        if idx == -1:
            segments.append((base_style, text[i:]))
            break
        if idx > i:
            segments.append((base_style, text[i:idx]))
        end = idx + query_len
        segments.append((hit_style, text[idx:end]))
        i = end
    return segments


def render_meta_table(meta: list[tuple[str, str]]) -> list[str]:
    """
    `[ラベル] 値` 形式のメタ情報テーブルを整形する。ラベル列はメタの中で
    最大表示幅に揃える。値が空文字列のときは `-` を表示する。
    """
    if not meta:
        return []
    label_width = max(wcswidth(label) for label, _ in meta)
    return [
        f"[{pad_display(label, label_width)}] {value if value else '-'}"
        for label, value in meta
    ]
