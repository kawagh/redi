"""画面を構成するペイン (タブ行 / 一覧 / プレビュー)。

各モジュールは `build_*_window(state, conditions)` で Window と、その上で起きる
マウスイベントのハンドラを一緒に定義する。キー操作はモードに紐づくので
`keybindings/` にモード別でまとまっているが、マウスは「どこで起きたか」で
意味が決まるので、要素 (ペイン) の定義と同じ場所に置く。

ハンドラはイベントを状態操作に変換する薄い層に留め、キーと共有する状態操作
(`activate_tab` / `scroll_preview` など) は `keybindings/keybinding_actions.py`
に置く。
"""

from prompt_toolkit.layout.dimension import Dimension

# 一覧とプレビューの幅。両方に同じ値を渡すことで、一覧の内容によらず境界が
# 端末幅の半分の桁に来る (preferred=0 で内容の幅を無視し weight で等分する)。
HALF = Dimension(weight=1, preferred=0)
