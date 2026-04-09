import json
from collections import defaultdict

import requests

from redi.config import redmine_api_key, redmine_url


def list_wikis(project_id: str) -> None:
    response = requests.get(
        f"{redmine_url}/projects/{project_id}/wiki/index.json",
        headers={"X-Redmine-API-Key": redmine_api_key},
    )
    pages = response.json()["wiki_pages"]

    children_map = defaultdict(list)
    for page in pages:
        parent = page.get("parent", {}).get("title") if "parent" in page else None
        children_map[parent].append(page["title"])

    def print_tree(parent: str | None, prefix: str = "") -> None:
        children = sorted(children_map.get(parent, []))
        for i, title in enumerate(children):
            is_last = i == len(children) - 1
            connector = "└── " if is_last else "├── "
            print(f"{prefix}{connector}{title}")
            next_prefix = prefix + ("    " if is_last else "│   ")
            print_tree(title, next_prefix)

    print_tree(None)


def fetch_wiki(project_id: str, page_title: str) -> dict:
    response = requests.get(
        f"{redmine_url}/projects/{project_id}/wiki/{page_title}.json",
        headers={"X-Redmine-API-Key": redmine_api_key},
    )
    response.raise_for_status()
    return response.json()["wiki_page"]


def read_wiki(project_id: str, page_title: str) -> None:
    wiki = fetch_wiki(project_id, page_title)
    print(wiki)


def update_wiki(project_id: str, page_title: str, text: str) -> None:
    response = requests.put(
        f"{redmine_url}/projects/{project_id}/wiki/{page_title}.json",
        headers={
            "X-Redmine-API-Key": redmine_api_key,
            "Content-Type": "application/json",
        },
        json={"wiki_page": {"text": text}},
    )
    response.raise_for_status()
    url = f"{redmine_url}/projects/{project_id}/wiki/{page_title}"
    print(f"Wikiページを更新しました: {url}")


def create_wiki(
    project_id: str,
    page_title: str,
    text: str,
    parent_title: str,
) -> None:
    # wikiの書き込みに3度のAPIリクエストが実行される
    # wiki作成(更新)時にステータスコード 422 を返すのでそれで代用する
    parent_exists = (
        requests.get(
            f"{redmine_url}/projects/{project_id}/wiki/{parent_title}.json",
            headers={"X-Redmine-API-Key": redmine_api_key},
        ).status_code
        == 200
    )
    if not parent_exists:
        print(f"親ページが見つかりません: {parent_title}")
        return

    exists = (
        requests.get(
            f"{redmine_url}/projects/{project_id}/wiki/{page_title}.json",
            headers={"X-Redmine-API-Key": redmine_api_key},
        ).status_code
        == 200
    )

    body: dict = {"text": text, "parent_title": parent_title}
    response = requests.put(
        f"{redmine_url}/projects/{project_id}/wiki/{page_title}.json",
        headers={
            "X-Redmine-API-Key": redmine_api_key,
            "Content-Type": "application/json",
        },
        json={"wiki_page": body},
    )
    response.raise_for_status()
    url = f"{redmine_url}/projects/{project_id}/wiki/{page_title}"
    if exists:
        print(f"Wikiページを更新しました: {url}")
    else:
        print(f"Wikiページを作成しました: {url}")
