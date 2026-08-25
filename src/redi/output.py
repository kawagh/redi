"""診断メッセージを標準エラー出力へ出すためのヘルパー。

エラーを stdout に出すと `redi issue list > issues.txt` のようにリダイレクトしたとき
出力データに混ざり、呼び出し側が結果とエラーを分けられない。出力先や書式を
後からまとめて変えられるよう、エラー経路の出力はこの関数を経由させる。
"""

import sys
from typing import Any


def eprint(*args: Any, **kwargs: Any) -> None:
    """print と同じ使い方で標準エラー出力に書く。

    exit 1 に伴うメッセージなど、正常な結果ではない出力に使う。
    """
    kwargs["file"] = sys.stderr
    print(*args, **kwargs)
