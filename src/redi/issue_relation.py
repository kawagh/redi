import requests

from redi.config import redmine_api_key, redmine_url


def create_relation(
    issue_id: str, issue_to_id: str, relation_type: str = "relates"
) -> None:
    response = requests.post(
        f"{redmine_url}/issues/{issue_id}/relations.json",
        headers={
            "X-Redmine-API-Key": redmine_api_key,
            "Content-Type": "application/json",
        },
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
    response = requests.get(
        f"{redmine_url}/issues/{issue_id}/relations.json",
        headers={"X-Redmine-API-Key": redmine_api_key},
    )
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
    response = requests.delete(
        f"{redmine_url}/relations/{target_relation['id']}.json",
        headers={"X-Redmine-API-Key": redmine_api_key},
    )
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
