"""`issue list` のフィルタ値を送信前に検証する。

Redmine は未知の ID を渡しても 0 件を返すだけなので、「該当なし」と「指定ミス」が
区別できない。マスタを引ける項目はマスタと、引けない項目は書式と突き合わせ、
送信前に落として指定ミスに気付けるようにする。
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

import requests

from redi.api.enumeration import fetch_issue_priorities
from redi.api.issue_status import fetch_issue_statuses
from redi.api.tracker import fetch_trackers
from redi.i18n import messages

# Redmine のフィルタ値は `!` で否定、`|` で複数指定を表せる。
# 検証はこれらを取り除いた個々の値に対して行う。
_NEGATION_PREFIX = "!"
_VALUE_SEPARATOR = "|"


@dataclass(frozen=True)
class _FilterSpec:
    """検証するフィルタ 1 件の定義。

    fetch を持つものはマスタの ID と突き合わせ、持たないものは数値 ID かだけを見る。
    プロジェクト依存の担当者・対象バージョンは、プロジェクト未指定でも検証できる
    書式チェックに留めている。
    """

    dest: str
    label: str
    # ID 以外に指定できる値（`*` や `open` など）
    keywords: tuple[str, ...]
    fetch: Callable[[], Sequence[Mapping[str, Any]]] | None = None


# fetch は呼び出し時に解決したいので lambda で包む
_FILTER_SPECS: tuple[_FilterSpec, ...] = (
    _FilterSpec(
        "status_id",
        messages.meta_status,
        ("open", "closed", "*"),
        lambda: fetch_issue_statuses(),
    ),
    _FilterSpec("tracker_id", messages.meta_tracker, ("*",), lambda: fetch_trackers()),
    _FilterSpec(
        "priority_id",
        messages.meta_priority,
        ("*",),
        lambda: fetch_issue_priorities(),
    ),
    _FilterSpec("assigned_to", messages.meta_assignee, ("me", "*")),
    _FilterSpec("version", messages.meta_version, ("*",)),
)


def _split_values(value: str) -> list[str]:
    """`!1|2` のようなフィルタ値を個々の値に分解する。"""
    body = value.removeprefix(_NEGATION_PREFIX)
    return [v.strip() for v in body.split(_VALUE_SEPARATOR)]


def _known_ids(spec: _FilterSpec) -> list[str] | None:
    """マスタの ID 一覧を返す。マスタを引けない・引かない場合は None。"""
    if spec.fetch is None:
        return None
    try:
        return [str(item["id"]) for item in spec.fetch()]
    except requests.exceptions.RequestException:
        # マスタを取れないことを理由に一覧そのものを止めない
        return None


def _available(spec: _FilterSpec, known_ids: list[str] | None) -> str:
    ids = known_ids if known_ids is not None else [messages.filter_available_numeric_id]
    return ",".join([*ids, *spec.keywords])


def _invalid_value(
    spec: _FilterSpec, value: str, known_ids: list[str] | None
) -> str | None:
    """指定できない値があれば最初の 1 件を返す。"""
    for v in _split_values(value):
        if v in spec.keywords:
            continue
        if known_ids is not None:
            if v not in known_ids:
                return v
        elif not v.isdigit():
            return v
    return None


def validate_list_filters(args: argparse.Namespace) -> None:
    """一覧フィルタに指定できない値があれば、値と指定できる値を示して exit 1。"""
    for spec in _FILTER_SPECS:
        value = getattr(args, spec.dest, None)
        if not value:
            continue
        known_ids = _known_ids(spec)
        invalid = _invalid_value(spec, value, known_ids)
        if invalid is None:
            continue
        print(
            messages.error_unknown_filter_value.format(
                label=spec.label,
                value=invalid,
                available=_available(spec, known_ids),
            )
        )
        sys.exit(1)
