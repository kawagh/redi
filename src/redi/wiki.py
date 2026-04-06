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


def read_wiki(project_id: str, page_title: str) -> None:
    response = requests.get(
        f"{redmine_url}/projects/{project_id}/wiki/{page_title}.json",
        headers={"X-Redmine-API-Key": redmine_api_key},
    )
    wiki = response.json()["wiki_page"]
    print(wiki)
