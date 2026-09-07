#!/bin/bash
set -e

# doc/tape/init-*.tape.template から tape を組み立てて vhs で収録する。
# テンプレートにしているのは API キーをリポジトリに置かないため。
#
# redi init は既存プロファイルがあると exit 1 するので、収録の間だけ config.toml を
# 退避する。中断されても戻すよう trap で復元する。

REPO=$(git rev-parse --show-toplevel)
CONFIG="$HOME/.config/redi/config.toml"
WORK=$(mktemp -d)
BACKUP="$WORK/config.toml.bak"
had_config=

# 退避を終えるまでは config.toml に触れない。ここで失敗しても消さないため。
trap 'rm -rf "$WORK"' EXIT

restore_config() {
    if [ -n "$had_config" ]; then
        mkdir -p "$(dirname "$CONFIG")"
        cp -f "$BACKUP" "$CONFIG"
    else
        rm -f "$CONFIG"
    fi
    rm -rf "$WORK"
}

api_key_of() {
    uv run python -c "
import pathlib, tomllib
doc = tomllib.loads(pathlib.Path('$CONFIG').read_text())
print(doc['$1']['redmine_api_key'])
"
}

# 退避する前に読む
EN_KEY=$(api_key_of demo_en)
JA_KEY=$(api_key_of demo_ja)

if [ -f "$CONFIG" ]; then
    cp "$CONFIG" "$BACKUP"
    had_config=1
fi
trap restore_config EXIT

for lang in en ja; do
    key_var="${lang^^}_KEY"
    rm -f "$CONFIG"

    sed -e "s|__API_KEY__|${!key_var}|" \
        -e "s|__REPO__|$REPO|" \
        "$REPO/doc/tape/init-$lang.tape.template" >"$WORK/init-$lang.tape"

    # tape をそのまま出力するため、API キーが端末に出ないよう抑制する
    (cd "$REPO" && vhs "$WORK/init-$lang.tape" >/dev/null)
done
