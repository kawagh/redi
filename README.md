# redi

redmine CLI tool

## install

Install via [uv](https://github.com/astral-sh/uv)

```shell
uv tool install https://github.com/kawagh/redi.git
```

## install(for development)

In repository root

```sh
ov tool install -e .
```

## setup

### config

以下のいずれかを設定する。

#### environment variable

```sh
export REDMINE_URL=xxx
export REDMINE_API_KEY=yyy
```

#### ~/.config/redi/config.toml

```toml
redmine_url = "xxx"
redmine_api_key = "yyy"
default_project_id = "1"
```

- `redi config --project_id 1` でdefault_project_idを1に変更できる

### setup completion

```
uv tool install argparsecomplete
echo 'eval "$(register-python-argcomplete redi)"' >> ~/.zshrc
```

## usage(example)

- list projects
    ```sh
    redi project # or `redi p`
    ```

- list issues
    ```sh
    redi issue # or `redi i`
    ```

- view issue
    ```sh
    redi issue view <issue_id>
    ```
- comment to issue
    ```sh
    redi issue comment <issue_id> # then editor open
    # or `redi issue comment <issue_id> hello~`
    ```

- create(update) wiki
    ```sh
    redi wiki create <page_title --parent_title <parent_title>
    ```
- list wiki
    ```sh
    redi wiki -p <project_id> # you can get version from `redi p`
    ```

- ...
