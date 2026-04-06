import os

redmine_url = os.environ.get("REDMINE_URL")
redmine_api_key = os.environ.get("REDMINE_API_KEY")

if not redmine_url:
    print("set REDMINE_URL")
    exit(1)
if not redmine_url:
    print("set REDMINE_API_KEY")
    exit(1)


def main() -> None:
    print("Hello from redi!")
