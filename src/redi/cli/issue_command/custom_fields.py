import sys
from collections import defaultdict

from redi.api.custom_field import (
    CustomField,
    fetch_custom_fields,
    fetch_project_issue_custom_fields,
    filter_optional_issue_custom_fields,
    filter_required_issue_custom_fields,
)
from redi.api.exceptions import (
    ProjectNotFoundException,
    ProjectPermissionDeniedException,
)
from redi.api.types import IdName
from redi.i18n import messages
from redi.output import eprint


def parse_custom_fields(custom_fields_str: str) -> list[dict]:
    """`id=value` をカンマ区切りでパースする。同一 id が複数回出現した場合は
    値をリスト化する（複数選択カスタムフィールド対応）。"""
    by_id: defaultdict[int, list[str]] = defaultdict(list)
    for pair in custom_fields_str.split(","):
        key, _, value = pair.partition("=")
        if not key:
            continue
        cf_id = int(key.strip())
        by_id[cf_id].append(value.strip())
    return [
        {"id": cf_id, "value": values if len(values) > 1 else values[0]}
        for cf_id, values in by_id.items()
    ]


def ensure_known_custom_field_ids(
    custom_fields: list[dict], project_id: str, tracker_id: str | None
) -> None:
    """対象プロジェクト/トラッカーで使えないカスタムフィールド id があれば、
    指定できる値を示して exit 1 する。

    Redmine は存在しない id や対象で使えない id を 200 で黙って無視するため、
    送る前に弾かないと「作成しました」と出たまま値が入らない。

    プロジェクトで有効なフィールドの一覧は非管理者でも取れるのでまずそれで弾き、
    トラッカーによる絞り込みは管理者限定の一覧が取れた場合だけ行う。
    管理者の一覧はキャッシュ済みのものを使うが、Redmine 側で追加された直後は
    キャッシュに無く正しい id を誤って弾いてしまうため、
    一致しなかったときだけ取り直して再判定する。
    """
    try:
        project_custom_fields = fetch_project_issue_custom_fields(project_id)
    except ProjectNotFoundException:
        eprint(messages.project_not_found.format(id=project_id))
        sys.exit(1)
    except ProjectPermissionDeniedException:
        eprint(messages.project_permission_denied.format(id=project_id))
        sys.exit(1)
    all_custom_fields = fetch_custom_fields()
    candidates = _applicable_custom_fields(
        project_custom_fields, all_custom_fields, tracker_id
    )
    unknown_ids = _unknown_ids(custom_fields, candidates)
    if unknown_ids and all_custom_fields is not None:
        candidates = _applicable_custom_fields(
            project_custom_fields, fetch_custom_fields(refresh=True), tracker_id
        )
        unknown_ids = _unknown_ids(custom_fields, candidates)
    if not unknown_ids:
        return
    eprint(
        messages.custom_field_not_found.format(
            id=", ".join(str(cf_id) for cf_id in unknown_ids)
        )
    )
    eprint(
        messages.available_ids.format(
            items=", ".join(
                f"{candidate['id']}:{candidate['name']}" for candidate in candidates
            )
        )
    )
    sys.exit(1)


def _applicable_custom_fields(
    project_custom_fields: list[IdName],
    all_custom_fields: list[CustomField] | None,
    tracker_id: str | None,
) -> list[IdName]:
    """プロジェクトで有効なフィールドのうち、トラッカーでも使えるものに絞る。

    全カスタムフィールドの一覧が取れない (非管理者) ならプロジェクトの一覧をそのまま返す。
    """
    if all_custom_fields is None:
        return project_custom_fields
    project_custom_field_ids = {cf["id"] for cf in project_custom_fields}
    applicable = filter_required_issue_custom_fields(
        all_custom_fields, project_custom_field_ids, tracker_id
    ) + filter_optional_issue_custom_fields(
        all_custom_fields, project_custom_field_ids, tracker_id
    )
    return [{"id": cf["id"], "name": cf["name"]} for cf in applicable]


def _unknown_ids(custom_fields: list[dict], candidates: list[IdName]) -> list[int]:
    known_ids = {candidate["id"] for candidate in candidates}
    return [cf["id"] for cf in custom_fields if cf["id"] not in known_ids]
