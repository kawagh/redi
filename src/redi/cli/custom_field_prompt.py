"""カスタムフィールドの値を対話で入力する。

`field_format` ごとに入力方法が変わる部分を issue の create/update から切り出したもの。
issue 固有の要素は持たないので、他リソースの CF 対応を足すときもここを使える。
"""

from redi.api.custom_field import CustomField
from redi.api.membership import fetch_project_users
from redi.cli.editor import open_editor, shorten_to_oneline
from redi.cli.interactive import prompt
from redi.cli.picker import inline_checkbox, inline_choice
from redi.cli.validator import (
    DateValidator,
    FloatValidator,
    IntValidator,
    RequiredValidator,
    build_custom_field_validator,
    check_custom_field_constraints,
)
from redi.i18n import messages
from redi.service import version_service

# attachment 型のような未対応フィールドで「スキップしてブラウザでの編集に倒す」ことを示すセンチネル
SKIP_UNSUPPORTED_FIELD = object()


def _choose_from_options(
    name: str,
    label: str,
    options: list[tuple[str, str]],
    multiple: bool,
    default_value: str | list[str],
) -> str | list[str] | object:
    """選択肢からの入力を取得する共通処理。空オプションは SKIP_UNSUPPORTED_FIELD を返す。"""
    if not options:
        return SKIP_UNSUPPORTED_FIELD
    label_map = dict(options)
    if multiple:
        # 複数選択の現在値(リスト)はそのまま、単一値は1要素のリストにして初期チェックする
        if isinstance(default_value, list):
            initial_checked = default_value
        else:
            initial_checked = [default_value] if default_value else None
        # 空選択は受け付けず、最低 1 つチェックされるまで再表示する
        while True:
            checked = inline_checkbox(
                label,
                options,
                initial_checked=initial_checked,
            )
            if checked:
                break
        display = ", ".join(label_map[k] for k in checked)
        print(messages.prompt_field_value.format(name=name, value=display))
        return checked
    default_key = default_value[0] if isinstance(default_value, list) else default_value
    key = inline_choice(label, options, default=default_key or None)
    print(messages.prompt_field_value.format(name=name, value=label_map[key]))
    return key


def prompt_custom_field_value(
    custom_field: CustomField,
    project_id: str,
) -> str | list[str] | object:
    name = custom_field["name"]
    field_format = custom_field["field_format"]
    multiple = custom_field["multiple"]
    label = messages.prompt_required_field.format(name=name)
    default_value = custom_field.get("default_value") or ""

    match field_format:
        # キーバリューリスト
        case "enumeration":
            possible_values = custom_field.get("possible_values") or []
            options: list[tuple[str, str]] = [
                (str(pv.get("value", "")), str(pv.get("label", "")))
                for pv in possible_values
                if pv.get("value", "") != ""
            ]
            return _choose_from_options(name, label, options, multiple, default_value)

        # リスト
        case "list":
            possible = custom_field.get("possible_values") or []
            options = [
                (str(pv.get("value", "")), str(pv.get("value", "")))
                for pv in possible
                if pv.get("value", "") != ""
            ]
            return _choose_from_options(name, label, options, multiple, default_value)

        # ユーザー
        case "user":
            users = fetch_project_users(project_id)
            options = [(str(u["id"]), u.get("name", "")) for u in users]
            return _choose_from_options(name, label, options, multiple, default_value)

        # バージョン
        case "version":
            versions = version_service.list_versions(project_id)
            options = [(str(v["id"]), v["name"]) for v in versions]
            return _choose_from_options(name, label, options, multiple, default_value)

        # 真偽値
        case "bool":
            bool_options: list[tuple[str, str]] = [
                ("1", messages.label_bool_true),
                ("0", messages.label_bool_false),
            ]
            bool_label_map = dict(bool_options)
            key = inline_choice(label, bool_options, default=default_value or None)
            print(
                messages.prompt_field_value.format(name=name, value=bool_label_map[key])
            )
            return key

        # 長いテキスト
        case "text":
            # 空のまま閉じられたらエディタを開き直す
            while True:
                value = open_editor(initial_text=default_value)
                if value:
                    err = check_custom_field_constraints(custom_field, value)
                    if err:
                        print(err)
                        continue
                    print(
                        messages.prompt_field_value.format(
                            name=name, value=shorten_to_oneline(value)
                        )
                    )
                    return value

        # 日付
        case "date":
            return prompt(
                messages.prompt_custom_field_label.format(name=label),
                validator=build_custom_field_validator(
                    custom_field, base=DateValidator()
                ),
                default=default_value,
            ).strip()

        # 進捗 (0-100% の 10% 刻み)
        case "progressbar":
            progress_options: list[tuple[str, str]] = [
                (str(r), f"{r}%") for r in range(0, 101, 10)
            ]
            value = inline_choice(
                label, progress_options, default=default_value or None
            )
            print(messages.prompt_field_value.format(name=name, value=f"{value}%"))
            return value

        # 整数
        case "int":
            return prompt(
                messages.prompt_custom_field_label.format(name=label),
                validator=build_custom_field_validator(
                    custom_field, base=IntValidator()
                ),
                default=default_value,
            ).strip()

        # 小数
        case "float":
            return prompt(
                messages.prompt_custom_field_label.format(name=label),
                validator=build_custom_field_validator(
                    custom_field, base=FloatValidator()
                ),
                default=default_value,
            ).strip()

        # ファイル添付は redi 側で対応していないため、呼び出し側に「ブラウザで編集」を強制させる
        case "attachment":
            print(messages.attachment_field_unsupported_notice.format(name=name))
            return SKIP_UNSUPPORTED_FIELD

        # 自由入力(string,link)。未知のフォーマット
        case _:
            return prompt(
                messages.prompt_custom_field_label.format(name=label),
                validator=build_custom_field_validator(
                    custom_field, base=RequiredValidator()
                ),
                default=default_value,
            ).strip()
