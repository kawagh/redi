import json
from collections import defaultdict

import requests

from redi.config import redmine_api_key, redmine_url


# redmineで空白文字を含んでwikiのpageを作成するとURLの都合か`_`に置き換えられている
# 既存のwikiのタイトルの先頭文字が大文字になっている
def normalize_title(t: str) -> str:
    normalized = t.strip().replace(" ", "_")
    if normalized and "a" <= normalized[0] <= "z":
        normalized = normalized[0].upper() + normalized[1:]
    return normalized


def fetch_wikis(project_id: str) -> list[dict]:
    response = requests.get(
        f"{redmine_url}/projects/{project_id}/wiki/index.json",
        headers={"X-Redmine-API-Key": redmine_api_key},
    )
    response.raise_for_status()
    return response.json()["wiki_pages"]


def build_children_map(pages: list[dict]) -> dict[str | None, list[str]]:
    children_map: dict[str | None, list[str]] = defaultdict(list)
    for page in pages:
        parent = page.get("parent", {}).get("title") if "parent" in page else None
        children_map[parent].append(page["title"])
    for titles in children_map.values():
        titles.sort()
    return children_map


def list_wikis(project_id: str, full: bool = False) -> None:
    pages = fetch_wikis(project_id)
    if full:
        print(json.dumps(pages, ensure_ascii=False))
        return
    children_map = build_children_map(pages)

    def print_tree(parent: str | None, prefix: str = "") -> None:
        children = children_map.get(parent, [])
        for i, title in enumerate(children):
            is_last = i == len(children) - 1
            connector = "└── " if is_last else "├── "
            url = f"{redmine_url}/projects/{project_id}/wiki/{title}"
            print(f"{prefix}{connector}[{title}]({url})")
            next_prefix = prefix + ("    " if is_last else "│   ")
            print_tree(title, next_prefix)

    print_tree(None)


def fetch_wiki(project_id: str, page_title: str) -> dict:
    response = requests.get(
        f"{redmine_url}/projects/{project_id}/wiki/{page_title}.json",
        headers={"X-Redmine-API-Key": redmine_api_key},
    )
    if response.status_code == 404:
        print(f"Wikiページが見つかりません: {page_title}")
        exit(1)
    response.raise_for_status()
    return response.json()["wiki_page"]


def read_wiki(project_id: str, page_title: str, full: bool = False) -> None:
    wiki = fetch_wiki(project_id, page_title)
    if full:
        print(json.dumps(wiki, ensure_ascii=False, indent=2))
    else:
        print(wiki.get("text", ""))


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
    parent_title: str | None = None,
) -> None:
    if parent_title:
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

    body: dict = {"text": text}
    if parent_title:
        body["parent_title"] = parent_title
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
