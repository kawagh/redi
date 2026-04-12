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
    print(
        f"関係性を作成しました: #{issue_id} --[{relation_type}]--> #{issue_to_id}"
    )
