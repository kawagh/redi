import sys
from typing import Any


def eprint(*args: Any, **kwargs: Any) -> None:
    """print と同じ使い方で標準エラー出力に書く。"""
    kwargs["file"] = sys.stderr
    print(*args, **kwargs)
