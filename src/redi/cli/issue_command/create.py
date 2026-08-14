import argparse
import sys
import urllib.parse
import webbrowser
from dataclasses import dataclass, fields
from datetime import date
from typing import Self

from redi import config
from redi.api.custom_field import (
    CustomField,
    fetch_custom_fields,
    fetch_project_issue_custom_field_ids,
    filter_optional_issue_custom_fields,
    filter_required_issue_custom_fields,
)
from redi.api.issue import create_issue, parse_custom_fields
from redi.api.issue_template import IssueTemplate, fetch_enabled_issue_templates
from redi.api.project import fetch_project
from redi.cli.custom_field_prompt import (
    SKIP_UNSUPPORTED_FIELD,
    prompt_custom_field_value,
)
from redi.cli.editor import open_editor, save_body_on_failure, shorten_to_oneline
from redi.cli.interactive import prompt
from redi.cli.issue_command.field_prompt import (
    parse_iso_date,
    prompt_assignee,
    prompt_due_date,
    prompt_estimated_hours,
    prompt_fixed_version,
    prompt_start_date,
)
from redi.cli.keybinding import (
    digit_only_key_bindings,
)
from redi.cli.picker import inline_checkbox, inline_choice
from redi.cli.validator import (
    IntValidator,
)
from redi.i18n import messages


@dataclass
class IssueCreateArgs:
    """`issue create` の入力値。

    フィールド名は `add_issue_parser` が定義する `dest` と一致させること。
    argparse 経由なら `from_namespace` で、TUI からは必要な項目だけ指定して生成する。
    """

    subject: str | None = None
    project_id: str | None = None
    tracker_id: str | None = None
    priority_id: str | None = None
    assigned_to_id: str | None = None
    fixed_version_id: str | None = None
    parent_issue_id: str | None = None
    start_date: str | None = None
    due_date: str | None = None
    estimated_hours: float | None = None
    description: str | None = None
    custom_fields: str | None = None

    @classmethod
    def from_namespace(cls, args: argparse.Namespace) -> Self:
        # dest 名がずれていたら AttributeError で気付けるよう getattr は防御しない
        return cls(**{f.name: getattr(args, f.name) for f in fields(cls)})


def _build_create_issue_url(args: IssueCreateArgs) -> str:
    # 呼び出し側で project_id は解決済み
    assert args.project_id is not None
    project_id = args.project_id
    params: list[tuple[str, str]] = []
    if args.subject:
        params.append(("issue[subject]", args.subject))
    if args.description:
        params.append(("issue[description]", args.description))
    if args.tracker_id:
        params.append(("issue[tracker_id]", args.tracker_id))
    if args.priority_id:
        params.append(("issue[priority_id]", args.priority_id))
    if args.assigned_to_id:
        params.append(("issue[assigned_to_id]", args.assigned_to_id))
    if args.fixed_version_id:
        params.append(("issue[fixed_version_id]", args.fixed_version_id))
    if args.parent_issue_id:
        params.append(("issue[parent_issue_id]", args.parent_issue_id))
    if args.start_date:
        params.append(("issue[start_date]", args.start_date))
    if args.due_date:
        params.append(("issue[due_date]", args.due_date))
    if args.estimated_hours is not None:
        params.append(("issue[estimated_hours]", str(args.estimated_hours)))
    if args.custom_fields:
        for cf in parse_custom_fields(args.custom_fields):
            value = cf["value"]
            if isinstance(value, list):
                for v in value:
                    params.append((f"issue[custom_field_values][{cf['id']}][]", str(v)))
            else:
                params.append((f"issue[custom_field_values][{cf['id']}]", str(value)))
    base = f"{config.redmine_url}/projects/{project_id}/issues/new"
    if not params:
        return base
    return f"{base}?{urllib.parse.urlencode(params)}"


def _interactive_fill_required_custom_fields(
    project_id: str, tracker_id: str | None, existing: str | None
) -> tuple[str | None, bool]:
    """戻り値の bool は「未対応の必須フィールドが含まれていた = ブラウザ編集が必須」を示す。"""
    custom_fields = fetch_custom_fields()
    if custom_fields is None:
        # 非管理者はあらかじめ渡されているパラメータを使うしかない
        return existing, False
    project_cf_ids = fetch_project_issue_custom_field_ids(project_id)
    required = filter_required_issue_custom_fields(
        custom_fields, project_cf_ids, tracker_id
    )
    if not required:
        return existing, False

    existing_ids: set[int] = set()
    if existing:
        for pair in existing.split(","):
            key = pair.split("=")[0]
            existing_ids.add(int(key))

    added: list[str] = []
    browser_only = False
    for cf in required:
        if cf["id"] in existing_ids:
            continue
        try:
            value = prompt_custom_field_value(cf, project_id)
        except (KeyboardInterrupt, EOFError):
            print(messages.canceled)
            sys.exit(1)
        if value is SKIP_UNSUPPORTED_FIELD:
            browser_only = True
            continue
        if isinstance(value, list):
            for v in value:
                added.append(f"{cf['id']}={v}")
        else:
            added.append(f"{cf['id']}={value}")
    if not added:
        return existing, browser_only
    if existing:
        return existing + "," + ",".join(added), browser_only
    return ",".join(added), browser_only


def _interactive_fill_optional_create_fields(args: IssueCreateArgs) -> None:
    """アクションメニューから「任意項目を入力する」を選んだときの入力フロー。

    標準項目（担当者・対象バージョン・親チケット・開始日・期日・予定工数）に加えて
    任意のカスタムフィールドも選択肢に並べ、入力結果を args へ書き戻す。
    """
    # 呼び出し側で project_id は解決済み
    assert args.project_id is not None
    project_id = args.project_id
    field_options: list[tuple[str, str]] = [
        ("assigned_to", messages.field_assignee),
        ("fixed_version", messages.field_fixed_version),
        ("parent_issue", messages.field_parent_issue),
        ("start_date", messages.field_start_date),
        ("due_date", messages.field_due_date),
        ("estimated_hours", messages.field_estimated_hours),
    ]
    optional_cfs: list[CustomField] = []
    all_cfs = fetch_custom_fields()
    if all_cfs is not None:
        existing_ids: set[int] = set()
        if args.custom_fields:
            for pair in args.custom_fields.split(","):
                existing_ids.add(int(pair.split("=")[0]))
        project_cf_ids = fetch_project_issue_custom_field_ids(project_id)
        optional_cfs = [
            cf
            for cf in filter_optional_issue_custom_fields(
                all_cfs, project_cf_ids, args.tracker_id
            )
            if cf["id"] not in existing_ids
        ]
        for cf in optional_cfs:
            field_options.append((f"cf_{cf['id']}", cf["name"]))
    try:
        selected = inline_checkbox(
            messages.prompt_select_create_optional_items,
            field_options,
        )
    except (KeyboardInterrupt, EOFError):
        print(messages.canceled)
        sys.exit(1)
    if not selected:
        return
    added_cfs: list[str] = []
    try:
        if "assigned_to" in selected:
            args.assigned_to_id = prompt_assignee(project_id)
        if "fixed_version" in selected:
            args.fixed_version_id = prompt_fixed_version(project_id)
        if "parent_issue" in selected:
            value = prompt(
                messages.prompt_parent_issue_id,
                validator=IntValidator(allow_empty=True),
                key_bindings=digit_only_key_bindings(),
            ).strip()
            args.parent_issue_id = value or None
        if "start_date" in selected:
            args.start_date = prompt_start_date(date.today().isoformat()) or None
        if "due_date" in selected:
            args.due_date = prompt_due_date(parse_iso_date(args.start_date)) or None
        if "estimated_hours" in selected:
            estimated_hours = prompt_estimated_hours()
            if estimated_hours is not None:
                args.estimated_hours = estimated_hours
        for cf in optional_cfs:
            if f"cf_{cf['id']}" not in selected:
                continue
            cf_value = prompt_custom_field_value(cf, project_id)
            if cf_value is SKIP_UNSUPPORTED_FIELD:
                continue
            if isinstance(cf_value, list):
                for v in cf_value:
                    added_cfs.append(f"{cf['id']}={v}")
            else:
                added_cfs.append(f"{cf['id']}={cf_value}")
    except (KeyboardInterrupt, EOFError):
        print(messages.canceled)
        sys.exit(1)
    if not added_cfs:
        return
    if args.custom_fields:
        args.custom_fields = args.custom_fields + "," + ",".join(added_cfs)
    else:
        args.custom_fields = ",".join(added_cfs)


def _interactive_select_issue_template(
    project_id: str, tracker_id: str | None
) -> IssueTemplate | None:
    """create フローでテンプレートを選択させる。

    redmine_issue_templates プラグインが無い、または有効なテンプレートが
    無い場合は None を返し、選択ステップ自体をスキップする。
    """
    templates = fetch_enabled_issue_templates(project_id, tracker_id)
    if not templates:
        return None
    options: list[tuple[str, str]] = [("", messages.prompt_select_template_none)] + [
        (str(t["id"]), t["title"]) for t in templates
    ]
    template_map = {str(t["id"]): t for t in templates}
    try:
        selected = inline_choice(messages.prompt_select_template, options)
    except (KeyboardInterrupt, EOFError):
        print(messages.canceled)
        sys.exit(1)
    if not selected:
        return None
    template = template_map[selected]
    print(messages.template_label.format(value=template["title"]))
    return template


def handle_issue_create(args: argparse.Namespace) -> None:
    """argparse アダプタ。Namespace を読むのはここまでに閉じる。"""
    _run_issue_create(IssueCreateArgs.from_namespace(args))


def create_issue_interactively(project_id: str | None = None) -> None:
    """題名・説明を対話で入力する入口。TUI から使う。"""
    _run_issue_create(IssueCreateArgs(project_id=project_id))


def _run_issue_create(args: IssueCreateArgs) -> None:
    project_id = args.project_id or config.default_project_id
    if not project_id:
        print(messages.project_id_required)
        sys.exit(1)
    args.project_id = project_id
    # 対話フローに入るかは args を書き換える前に決める
    interactive = args.subject is None or args.description is None
    browser_only = False
    template_description = ""
    if args.subject is None:
        if args.tracker_id is None:
            project = fetch_project(project_id, include="trackers")
            trackers = project.get("trackers") or []
            tracker_options: list[tuple[str, str]] = [
                (str(t["id"]), t["name"]) for t in trackers
            ]
            labels = dict(tracker_options)
            try:
                args.tracker_id = inline_choice(
                    messages.prompt_select_tracker, tracker_options
                )
            except (KeyboardInterrupt, EOFError):
                print(messages.canceled)
                sys.exit(1)
            print(messages.tracker_label.format(value=labels[args.tracker_id]))
        # テンプレートを選択し、題名・説明の初期値として反映させる
        template = _interactive_select_issue_template(project_id, args.tracker_id)
        subject_default = ""
        if template is not None:
            subject_default = template["issue_title"]
            template_description = template["description"]
        try:
            args.subject = prompt(
                messages.prompt_subject, default=subject_default
            ).strip()
        except (KeyboardInterrupt, EOFError):
            print(messages.canceled)
            sys.exit(1)
        if not args.subject:
            print(messages.canceled_empty_subject)
            sys.exit(1)
        # 必要なカスタムフィールドを対話的に入力
        args.custom_fields, browser_only = _interactive_fill_required_custom_fields(
            project_id=project_id,
            tracker_id=args.tracker_id,
            existing=args.custom_fields,
        )
    if args.description is None:
        args.description = open_editor(initial_text=template_description)
        if args.description:
            print(
                messages.prompt_field_value.format(
                    name=messages.field_description,
                    value=shorten_to_oneline(args.description),
                )
            )
    if interactive:
        # 添付ファイル必須など redi で送信できないケースは「ブラウザで編集」のみ提示する
        while True:
            action_options: list[tuple[str, str]] = (
                [
                    ("browser", messages.action_continue_in_browser),
                    ("optional", messages.action_fill_optional),
                ]
                if browser_only
                else [
                    ("submit", messages.action_submit),
                    ("browser", messages.action_continue_in_browser),
                    ("optional", messages.action_fill_optional),
                ]
            )
            try:
                action = inline_choice(messages.prompt_what_next, action_options)
            except (KeyboardInterrupt, EOFError):
                print(messages.canceled)
                sys.exit(1)
            if action == "optional":
                _interactive_fill_optional_create_fields(args)
                continue
            if action == "browser":
                webbrowser.open(_build_create_issue_url(args))
                return
            break
    try:
        create_issue(
            project_id=project_id,
            subject=args.subject,
            description=args.description,
            tracker_id=args.tracker_id,
            priority_id=args.priority_id,
            assigned_to_id=args.assigned_to_id,
            fixed_version_id=args.fixed_version_id,
            parent_issue_id=args.parent_issue_id,
            start_date=args.start_date,
            due_date=args.due_date,
            estimated_hours=args.estimated_hours,
            custom_fields=args.custom_fields,
        )
    except Exception:
        save_body_on_failure(args.description)
        raise
