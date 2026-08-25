"""エラー出力のヘルパー。

標準出力に出すとリダイレクトした結果に混ざるため、エラー経路はここを経由させる。
"""

import sys
from typing import Any


def eprint(*args: Any, **kwargs: Any) -> None:
    """print と同じ使い方で標準エラー出力に書く。"""
    kwargs["file"] = sys.stderr
    print(*args, **kwargs)
