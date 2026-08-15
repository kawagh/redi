import argparse
from typing import Any

from redi.i18n import messages


class FilterParser(argparse.ArgumentParser):
    """サブコマンドの前後どちらにも書けるフィルタオプションをまとめるパーサ

    リソースの親パーサ (`redi issue`) と `list` サブパーサの双方に parents として
    渡すことで `issue --limit 3 list` と `issue list --limit 3` の両方を受け付ける。

    postfix=True (`list` サブパーサ側) では未指定のオプションを namespace に載せない。
    サブパーサのデフォルト値が、親パーサが先に解釈した値を上書きするのを防ぐため。
    """

    def __init__(self, *, postfix: bool = False) -> None:
        self._postfix = postfix
        # 親子でヘルプを衝突させない
        super().__init__(add_help=False)

    def add_argument(self, *args: Any, **kwargs: Any) -> argparse.Action:
        if self._postfix:
            kwargs["default"] = argparse.SUPPRESS
        return super().add_argument(*args, **kwargs)


def full_filter_parser(*, postfix: bool = False) -> argparse.ArgumentParser:
    """`--full` だけを持つフィルタパーサ"""
    parser = FilterParser(postfix=postfix)
    parser.add_argument("--full", action="store_true", help=messages.arg_help_full_json)
    return parser


def project_filter_parser(*, postfix: bool = False) -> argparse.ArgumentParser:
    """`--project_id` と `--full` を持つフィルタパーサ"""
    parser = FilterParser(postfix=postfix)
    parser.add_argument("--project_id", "-p", help=messages.arg_help_project_id)
    parser.add_argument("--full", action="store_true", help=messages.arg_help_full_json)
    return parser
