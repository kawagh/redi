import argparse
import sys
from enum import StrEnum
from typing import Any, assert_never

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


class OutputFormat(StrEnum):
    """`--format` で選ぶ出力形式

    形式ごとの分岐は `match` で全列挙し `case _: assert_never(fmt)` を置く。
    形式を足したときに分岐漏れを型チェックで検出するため。
    """

    PLAIN = "plain"
    TSV = "tsv"
    JSON = "json"


# view 系が受け付ける形式。tsv は 1 レコード 1 行が前提なので一覧にしか出せない
OUTPUT_FORMATS = (OutputFormat.PLAIN, OutputFormat.JSON)
# list 系が受け付ける形式
LIST_OUTPUT_FORMATS = tuple(OutputFormat)


def add_format_options(
    parser: argparse.ArgumentParser, *, postfix: bool = False, tsv: bool = False
) -> None:
    """出力形式を選ぶ `--format` と、その別名の `--full` を足す

    `--format` は親パーサとサブパーサの双方に足されるため、デフォルト値を持たせない。
    持たせると後から解釈するサブパーサ側の値が親の解釈結果を上書きしてしまう。
    未指定時の既定値は `resolve_format` が補う。

    postfix=True では `--full` も同様に namespace に載せない。

    tsv=True は list 系のパーサ用で、`--format tsv` を受け付ける。
    短縮形 `-f` は `--firstname` / `--filename` と衝突するので付けない。

    `type=OutputFormat` は付けない。付けると未対応の値のエラーが
    `invalid OutputFormat value` になり、選べる形式の案内が消えるため。
    値は `choices` で絞り、Enum への変換は `resolve_format` で行う。
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


def resolve_format(args: argparse.Namespace) -> OutputFormat:
    """`--format` と `--full` から出力形式を決める

    両方指定された場合は、形式を直接示している `--format` を優先する。
    """
    fmt = getattr(args, "format", None)
    if fmt is not None:
        return OutputFormat(fmt)
    return OutputFormat.JSON if getattr(args, "full", False) else OutputFormat.PLAIN


def resolve_list_format(args: argparse.Namespace) -> OutputFormat:
    """list 系コマンドの出力形式を決める

    `--format tsv` を受け付けるパーサから呼ぶ。
    """
    return resolve_format(args)


def wants_json(args: argparse.Namespace) -> bool:
    """JSON 出力が求められているか (list 以外のサブコマンド用)

    tsv は list 系にしか無いので、ここに来るのは親パーサ側の `--format tsv` が
    view などに流れてきたとき。#461 のように黙って別の形式で出すのではなく、
    受け付けない旨を示して exit 1 する。
    """
    fmt = resolve_format(args)
    match fmt:
        case OutputFormat.TSV:
            eprint(messages.error_format_tsv_list_only)
            sys.exit(1)
        case OutputFormat.JSON:
            return True
        case OutputFormat.PLAIN:
            return False
        case _:
            assert_never(fmt)


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
