# redi

redmine CLI tool

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
```
