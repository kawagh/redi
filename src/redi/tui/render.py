from wcwidth import wcswidth


def pad_display(text: str, width: int) -> str:
    padding = max(0, width - wcswidth(text))
    return text + " " * padding


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
