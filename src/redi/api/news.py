import json

from redi.client import client


def list_news(project_id: str | None = None, full: bool = False) -> None:
    if project_id:
        path = f"/projects/{project_id}/news.json"
    else:
        path = "/news.json"
    response = client.get(path)
    if response.status_code == 404:
        print(f"プロジェクトが見つかりません: {project_id}")
        exit(1)
    response.raise_for_status()
    news_list = response.json()["news"]
    if full:
        print(json.dumps(news_list, ensure_ascii=False))
        return
    for news in news_list:
        title = news.get("title", "")
        author = (news.get("author") or {}).get("name", "")
        project = (news.get("project") or {}).get("name", "")
        created = news.get("created_on", "")
        parts = [str(news["id"]), title]
        if project:
            parts.append(f"[{project}]")
        if author:
            parts.append(f"by {author}")
        if created:
            parts.append(created)
        print(" ".join(parts))
