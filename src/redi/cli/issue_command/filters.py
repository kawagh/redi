"""`issue list` のフィルタ値を送信前に検証する。

Redmine は未知の ID を渡しても 0 件を返すだけなので、「該当なし」と「指定ミス」が
区別できない。マスタを引ける項目はマスタと突き合わせ、送信前に落として
指定ミスに気付けるようにする。

担当者・対象バージョンはプロジェクト依存でマスタを安価に引けないため検証しない。
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


@dataclass(frozen=True)
class _FilterSpec:
    """検証するフィルタ 1 件の定義。値はマスタの ID か keywords のいずれかに限る。"""

    dest: str
    label: str
    # ID 以外に指定できる値（`*` や `open` など）
    keywords: tuple[str, ...]
    fetch: Callable[[], Sequence[Mapping[str, Any]]]


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
)


def _known_ids(spec: _FilterSpec) -> list[str] | None:
    """マスタの ID 一覧を返す。マスタを引けない場合は None。"""
    try:
        return [str(item["id"]) for item in spec.fetch()]
    except requests.exceptions.RequestException:
        # マスタを取れないことを理由に一覧そのものを止めない
        return None


def validate_list_filters(args: argparse.Namespace) -> None:
    """一覧フィルタに指定できない値があれば、値と指定できる値を示して exit 1。"""
    for spec in _FILTER_SPECS:
        value = getattr(args, spec.dest, None)
        if not value or value in spec.keywords:
            continue
        known_ids = _known_ids(spec)
        if known_ids is None or value in known_ids:
            continue
        print(
            messages.error_unknown_filter_value.format(
                label=spec.label,
                value=value,
                available=",".join([*known_ids, *spec.keywords]),
            )
        )
        sys.exit(1)
