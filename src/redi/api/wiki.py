import json
import webbrowser
from collections import defaultdict

import requests

from redi.client import client
from redi.config import redmine_url
from redi.i18n import messages


# redmineで空白文字を含んでwikiのpageを作成するとURLの都合か`_`に置き換えられている
# 既存のwikiのタイトルの先頭文字が大文字になっている
def normalize_title(t: str) -> str:
    normalized = t.strip().replace(" ", "_")
    if normalized and "a" <= normalized[0] <= "z":
        normalized = normalized[0].upper() + normalized[1:]
    return normalized


def fetch_wikis(project_id: str) -> list[dict]:
    response = client.get(f"/projects/{project_id}/wiki/index.json")
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


def flatten_wiki_tree(pages: list[dict]) -> list[tuple[dict, str]]:
    """
    Wiki ページをツリー順に並べ、(ページ辞書, ツリー前置子) のペア列として返す。
    前置子は `│   ├── ` のようなツリー装飾で、末尾にタイトル等を連結すれば
    1 行分のツリー表示になる。
    """
    children_map = build_children_map(pages)
    by_title = {p["title"]: p for p in pages}
    result: list[tuple[dict, str]] = []

    def walk(parent: str | None, prefix: str) -> None:
        children = children_map.get(parent, [])
        for i, title in enumerate(children):
            if title not in by_title:
                continue
            is_last = i == len(children) - 1
            connector = "└── " if is_last else "├── "
            result.append((by_title[title], f"{prefix}{connector}"))
            next_prefix = prefix + ("    " if is_last else "│   ")
            walk(title, next_prefix)

    walk(None, "")
    return result


def list_wikis(project_id: str, full: bool = False) -> None:
    pages = fetch_wikis(project_id)
    if full:
        print(json.dumps(pages, ensure_ascii=False))
        return
    for page, tree_prefix in flatten_wiki_tree(pages):
        title = page["title"]
        url = f"{redmine_url}/projects/{project_id}/wiki/{title}"
        print(f"{tree_prefix}[{title}]({url})")


def fetch_wiki(
    project_id: str, page_title: str, version: int | None = None
) -> dict | None:
    path = f"/projects/{project_id}/wiki/{page_title}.json"
    if version is not None:
        path = f"/projects/{project_id}/wiki/{page_title}/{version}.json"
    response = client.get(path)
    if response.status_code == 404:
        return None
    response.raise_for_status()
    return response.json()["wiki_page"]


def read_wiki(
    project_id: str,
    page_title: str,
    full: bool = False,
    web: bool = False,
    version: int | None = None,
) -> None:
    if web:
        url = f"{redmine_url}/projects/{project_id}/wiki/{page_title}"
        if version is not None:
            url = f"{url}/{version}"
        print(url)
        webbrowser.open(url)
        return
    wiki = fetch_wiki(project_id, page_title, version=version)
    if wiki is None:
        if version is not None:
            print(
                messages.wiki_page_with_version_not_found.format(
                    title=page_title, version=version
                )
            )
        else:
            print(messages.wiki_page_not_found.format(title=page_title))
        exit(1)
    if full:
        print(json.dumps(wiki, ensure_ascii=False, indent=2))
    else:
        print(wiki.get("text", ""))


def update_wiki(project_id: str, page_title: str, text: str) -> None:
    response = client.put(
        f"/projects/{project_id}/wiki/{page_title}.json",
        json={"wiki_page": {"text": text}},
    )
    response.raise_for_status()
    url = f"{redmine_url}/projects/{project_id}/wiki/{page_title}"
    print(messages.wiki_page_updated.format(url=url))


def delete_wiki(project_id: str, page_title: str) -> None:
    response = client.delete(f"/projects/{project_id}/wiki/{page_title}.json")
    if response.status_code == 404:
        print(messages.wiki_page_not_found.format(title=page_title))
        exit(1)
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        print(e)
        print(e.response.text)
        print(messages.wiki_page_delete_failed)
        exit(1)
    print(messages.wiki_page_deleted.format(title=page_title))


def create_wiki(
    project_id: str,
    page_title: str,
    text: str,
    parent_title: str | None = None,
) -> None:
    if parent_title:
        parent_exists = (
            client.get(f"/projects/{project_id}/wiki/{parent_title}.json").status_code
            == 200
        )
        if not parent_exists:
            print(messages.parent_page_not_found.format(title=parent_title))
            return

    exists = (
        client.get(f"/projects/{project_id}/wiki/{page_title}.json").status_code == 200
    )

    body: dict = {"text": text}
    if parent_title:
        body["parent_title"] = parent_title
    response = client.put(
        f"/projects/{project_id}/wiki/{page_title}.json",
        json={"wiki_page": body},
    )
    response.raise_for_status()
    url = f"{redmine_url}/projects/{project_id}/wiki/{page_title}"
    if exists:
        print(messages.wiki_page_updated.format(url=url))
    else:
        print(messages.wiki_page_created.format(url=url))
