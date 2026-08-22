"""レンダリング結果を YAML に追記するデバッグ用ログ。

`--debug-log` 指定時だけ有効にする。描画のたびに直前のキーと画面の内容を
1 エントリとして書き出し、TUI の表示を後から追えるようにする。
"""

import json
from datetime import datetime
from pathlib import Path

from prompt_toolkit import Application


def dump_rendered_screen(app: Application) -> dict:
    """
    最後にレンダリングした画面 (`_last_screen`) の内容を
    `{"width": int, "height": int, "lines": [str, ...]}` 形式で返す。
    """
    screen = app.renderer._last_screen
    if screen is None:
        return {"width": 0, "height": 0, "lines": []}
    size = app.output.get_size()
    width, height = size.columns, size.rows
    lines = []
    for y in range(height):
        row = screen.data_buffer[y]
        line = "".join(row[x].char for x in range(width)).rstrip()
        lines.append(line)
    return {"width": width, "height": height, "lines": lines}


def _append_screen_yaml(path: Path, dumped: dict, key: str) -> None:
    timestamp = datetime.now().isoformat(timespec="microseconds")
    lines = dumped["lines"]
    indented = "\n".join(f"    {line}" for line in lines) if lines else "    "
    entry = (
        f"- timestamp: {timestamp}\n"
        # 任意の文字が入るのでクォートして YAML の特殊構文と解釈させない
        f"  key: {json.dumps(key, ensure_ascii=False)}\n"
        f"  width: {dumped['width']}\n"
        f"  height: {dumped['height']}\n"
        # 画面の 1 行目が空白で始まってもインデント幅を誤推定させないため
        # インデント指示子を明示する (親ノードの 2 スペース + 2 = 4 スペース)
        f"  screen: |2\n{indented}\n"
    )
    with open(path, "a", encoding="utf-8") as f:
        f.write(entry)


def attach_screen_log(app: Application, path: Path) -> None:
    """描画のたびに画面の内容を `path` へ追記するフックを登録する。"""

    def _on_after_render(sender: Application) -> None:
        seq = sender.key_processor._previous_key_sequence
        key = " ".join(getattr(kp.key, "value", str(kp.key)) for kp in seq)
        _append_screen_yaml(path, dump_rendered_screen(sender), key=key)

    app.after_render += _on_after_render
