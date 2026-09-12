"""一覧から 1 つ選ぶダイアログの状態。

wiki タブ (版一覧) と TuiState (プロジェクト / プロファイル切替) の両方が使うので、
__init__ に置くと wiki.py との間で循環 import になる。単独のモジュールに置き、
__init__ からは共通部品として再 export する。
"""

from dataclasses import dataclass, field


@dataclass
class ChoiceDialogState:
    """一覧から1つ選ぶダイアログ (p のプロジェクト切替 / P のプロファイル切替) の状態。

    描画とキーバインドは `tui.choice_dialog` が共通で持つ。
    """

    show: bool = False
    # 選択肢: (値, 表示ラベル) の組
    choices: list[tuple[str, str]] = field(default_factory=list)
    cursor: int = 0
    # 現在有効な選択肢の値。`*` 表示とカーソル初期位置に使う。プロジェクトは
    # config に identifier も設定できるため、開くときに id へ解決してから入れる。
    active_value: str | None = None
