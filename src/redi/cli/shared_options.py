import argparse
import sys
from typing import Any

from redi.i18n import messages
from redi.output import eprint


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


FORMAT_PLAIN = "plain"
FORMAT_TSV = "tsv"
FORMAT_JSON = "json"
# view 系が受け付ける形式。tsv は 1 レコード 1 行が前提なので一覧にしか出せない
OUTPUT_FORMATS = (FORMAT_PLAIN, FORMAT_JSON)
# list 系が受け付ける形式
LIST_OUTPUT_FORMATS = (FORMAT_PLAIN, FORMAT_TSV, FORMAT_JSON)


def add_format_options(
    parser: argparse.ArgumentParser, *, postfix: bool = False, tsv: bool = False
) -> None:
    """出力形式を選ぶ `--format` と、その別名の `--full` を足す

    `--format` は親パーサとサブパーサの双方に足されるため、デフォルト値を持たせない。
    持たせると後から解釈するサブパーサ側の値が親の解釈結果を上書きしてしまう。
    未指定時の既定値は `resolve_format` が補う。

    postfix=True では `--full` も同様に namespace に載せない。

    tsv=True は list 系のパーサ用で、`--format tsv` と、ヘッダー行を省く
    `--no-header` を受け付ける。短縮形 `-f` は `--firstname` / `--filename` と
    衝突するので付けない。
    """
    parser.add_argument(
        "--format",
        choices=LIST_OUTPUT_FORMATS if tsv else OUTPUT_FORMATS,
        default=argparse.SUPPRESS,
        help=messages.arg_help_format_list if tsv else messages.arg_help_format,
    )
    parser.add_argument(
        "--full",
        action="store_true",
        default=argparse.SUPPRESS if postfix else False,
        help=messages.arg_help_full_json,
    )
    if tsv:
        parser.add_argument(
            "--no-header",
            dest="no_header",
            action="store_true",
            default=argparse.SUPPRESS if postfix else False,
            help=messages.arg_help_no_header,
        )


def resolve_format(args: argparse.Namespace) -> str:
    """`--format` と `--full` から出力形式を決める

    両方指定された場合は、形式を直接示している `--format` を優先する。
    """
    fmt = getattr(args, "format", None)
    if fmt is not None:
        return fmt
    return FORMAT_JSON if getattr(args, "full", False) else FORMAT_PLAIN


def resolve_list_format(args: argparse.Namespace) -> str:
    """list 系コマンドの出力形式を決める

    `--format tsv` を受け付けるパーサから呼ぶ。
    """
    return resolve_format(args)


def wants_header(args: argparse.Namespace) -> bool:
    """tsv 出力にヘッダー行を付けるか (`--no-header` で外す)"""
    return not getattr(args, "no_header", False)


def wants_json(args: argparse.Namespace) -> bool:
    """JSON 出力が求められているか (list 以外のサブコマンド用)

    tsv は list 系にしか無いので、ここに来るのは親パーサ側の `--format tsv` が
    view などに流れてきたとき。#461 のように黙って別の形式で出すのではなく、
    受け付けない旨を示して exit 1 する。
    """
    fmt = resolve_format(args)
    if fmt == FORMAT_TSV:
        eprint(messages.error_format_tsv_list_only)
        sys.exit(1)
    return fmt == FORMAT_JSON


def full_option_parser(*, postfix: bool = False) -> argparse.ArgumentParser:
    """出力形式のオプションだけを共有するパーサ

    リソースの親パーサと `list` サブパーサで共有するので tsv を受け付ける。
    """
    parser = SharedOptionParser(postfix=postfix)
    add_format_options(parser, tsv=True)
    return parser


def project_option_parser(*, postfix: bool = False) -> argparse.ArgumentParser:
    """`--project_id` と出力形式のオプションを共有するパーサ

    リソースの親パーサと `list` サブパーサで共有するので tsv を受け付ける。
    """
    parser = SharedOptionParser(postfix=postfix)
    parser.add_argument("--project_id", "-p", help=messages.arg_help_project_id)
    add_format_options(parser, tsv=True)
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
