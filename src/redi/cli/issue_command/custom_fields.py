from collections import defaultdict


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
