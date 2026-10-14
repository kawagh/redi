"""`-` で始まる位置引数が短オプションに食われるのを検出する ArgumentParser。

argparse は短オプションと値の連結形 (`-dVALUE`) を認めるため、
`-d で始まるタイトル` のような文字列を位置引数のつもりで渡すと
「短オプション `-d` + 値」として解釈され、位置引数だけが黙って消える。
消えた結果は「件名が未指定」としてしか観測できず、
非対話環境では件名と無関係なオプションの入力を求めるエラーに化けるため、
argparse に渡す前に取り違えとして弾き、書き方を示す。
"""

import argparse
from collections.abc import Iterable
from typing import Any

from redi.i18n import messages


class RediArgumentParser(argparse.ArgumentParser):
    """短オプションの連結形に空白入りの値が付いた引数を弾くパーサ

    `subparsers.add_parser()` は呼び出し元のクラスでサブパーサを作るので、
    ルートをこのクラスにすれば全サブコマンドに伝播する。
    """

    def parse_known_args(
        self,
        args: Iterable[str] | None = None,
        namespace: Any = None,
    ) -> tuple[argparse.Namespace, list[str]]:
        arg_strings = None if args is None else list(args)
        for arg_string in arg_strings or []:
            # `--` 以降は全て位置引数なので取り違えは起きない
            if arg_string == "--":
                break
            option_string = self._misread_short_option(arg_string)
            if option_string is not None:
                self.error(
                    messages.arg_error_hyphen_prefixed_value.format(
                        arg=arg_string, option=option_string, prog=self.prog
                    )
                )
        return super().parse_known_args(arg_strings, namespace)

    def _misread_short_option(self, arg_string: str) -> str | None:
        """食われる短オプション名を返す。取り違えでなければ None を返す。"""
        if len(arg_string) <= 2 or arg_string[0] not in self.prefix_chars:
            return None
        # 長オプションは `=` でしか値を繋げないので取り違えは起きない
        if arg_string[1] in self.prefix_chars:
            return None
        option_string, value = arg_string[:2], arg_string[2:]
        # `-d=VALUE` は値であることが明示されているので取り違えではない
        if value.startswith("="):
            return None
        # 空白を含まない `-dVALUE` は連結形として意図されうるので触らない
        if " " not in value:
            return None
        action = self._option_string_actions.get(option_string)
        if action is None or action.nargs == 0:
            return None
        return option_string
