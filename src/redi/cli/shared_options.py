import argparse
from typing import Any

from redi.i18n import messages


class SharedOptionParser(argparse.ArgumentParser):
    """リソースの親パーサと `list` サブパーサで共有するオプションをまとめるパーサ

    双方に parents として渡すことで `issue --limit 3 list` と
    `issue list --limit 3` の両方を受け付ける。

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


def add_full_argument(
    parser: argparse.ArgumentParser, *, postfix: bool = False
) -> None:
    """`--full` をパーサに直接足す

    postfix=True は親パーサも `--full` を持つサブパーサ側で使う。
    未指定なら namespace に載せないので `<resource> --full <action>` と
    `<resource> <action> --full` のどちらでも `--full` が効く。
    False をデフォルトにすると、前者が silent に無視される。
    """
    parser.add_argument(
        "--full",
        action="store_true",
        default=argparse.SUPPRESS if postfix else False,
        help=messages.arg_help_full_json,
    )


def full_option_parser(*, postfix: bool = False) -> argparse.ArgumentParser:
    """`--full` だけを共有するパーサ"""
    parser = SharedOptionParser(postfix=postfix)
    add_full_argument(parser, postfix=postfix)
    return parser


def project_option_parser(*, postfix: bool = False) -> argparse.ArgumentParser:
    """`--project_id` と `--full` を共有するパーサ"""
    parser = SharedOptionParser(postfix=postfix)
    parser.add_argument("--project_id", "-p", help=messages.arg_help_project_id)
    add_full_argument(parser, postfix=postfix)
    return parser


def pagination_option_parser(*, postfix: bool = False) -> argparse.ArgumentParser:
    """`--limit` と `--offset` を共有するパーサ

    versions / wiki / groups / issue_categories は Redmine の API が
    ページングに対応していないため、これらの一覧には足していない。
    """
    parser = SharedOptionParser(postfix=postfix)
    parser.add_argument("--limit", type=int, help=messages.arg_help_limit)
    parser.add_argument("--offset", type=int, help=messages.arg_help_offset)
    return parser
