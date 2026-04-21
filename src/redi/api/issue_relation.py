import json

import requests

from redi.client import client
from redi.config import redmine_url


def fetch_relation(relation_id: str) -> dict:
    response = client.get(f"/relations/{relation_id}.json")
    if response.status_code == 404:
        print(f"関係性が見つかりません: #{relation_id}")
        exit(1)
    response.raise_for_status()
    return response.json()["relation"]


def read_relation(relation_id: str, full: bool = False) -> None:
    relation = fetch_relation(relation_id)
    if full:
        print(json.dumps(relation, ensure_ascii=False))
        return
    issue_url = f"{redmine_url}/issues/{relation['issue_id']}"
    issue_to_url = f"{redmine_url}/issues/{relation['issue_to_id']}"
    print(
        f"{relation['id']} #{relation['issue_id']} --[{relation['relation_type']}]--> #{relation['issue_to_id']}"
    )
    print(f"  {issue_url}")
    print(f"  {issue_to_url}")
    if relation.get("delay") is not None:
        print(f"  delay: {relation['delay']}")


def create_relation(
    issue_id: str, issue_to_id: str, relation_type: str = "relates"
) -> None:
    response = client.post(
        f"/issues/{issue_id}/relations.json",
        json={
            "relation": {
                "issue_to_id": issue_to_id,
                "relation_type": relation_type,
            }
        },
    )
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        print(e)
        print(e.response.text)
        print("関係性の作成に失敗しました")
        exit(1)
    print(f"関係性を作成しました: #{issue_id} --[{relation_type}]--> #{issue_to_id}")


def delete_relation(issue_id: str, issue_to_id: str) -> None:
    response = client.get(f"/issues/{issue_id}/relations.json")
    response.raise_for_status()
    relations = response.json()["relations"]
    target_id = int(issue_to_id)
    target_relation = next(
        (
            r
            for r in relations
            if r["issue_id"] == target_id or r["issue_to_id"] == target_id
        ),
        None,
    )
    if not target_relation:
        print(f"#{issue_id} と #{issue_to_id} の間に関係性が見つかりません")
        exit(1)
    response = client.delete(f"/relations/{target_relation['id']}.json")
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        print(e)
        print(e.response.text)
        print("関係性の削除に失敗しました")
        return
    print(
        f"関係性を削除しました: #{target_relation['issue_id']} --[{target_relation['relation_type']}]--> #{target_relation['issue_to_id']}"
    )
