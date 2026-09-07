#!/bin/bash
set -e

# デモ用の Redmine を作り直し、英語版 (redidemo-en) と日本語版 (redidemo-ja) の
# 2 プロジェクトにダミーデータを投入する。
# vhs での収録は --profile demo_en / demo_ja を切り替えて行う。

# 言語ごとに Redmine インスタンスを分ける。ステータス/トラッカー/優先度は
# Redmine 全体の設定でプロジェクト単位に名前を変えられないため。
setup_instance() {
    local svc="$1" lang="$2" port="$3" project_name="$4" project_desc="$5"

    docker compose down "$svc"
    docker compose up -d "$svc"
    sleep 5
    docker compose exec -T \
        -e DEMO_LANG="$lang" \
        -e DEMO_PROJECT_NAME="$project_name" \
        -e DEMO_PROJECT_DESC="$project_desc" \
        "$svc" rails runner - <<'RUBY'
    # 初期生成される管理者のパスワードを変更
    admin = User.find_by(login: 'admin')
    admin.password = 'adminadmin'
    admin.password_confirmation = 'adminadmin'
    admin.must_change_passwd = false
    admin.save!

    # ステータス/トラッカー/優先度の名前はここで決まる
    Redmine::DefaultData::Loader.load(ENV['DEMO_LANG'])

    Setting.rest_api_enabled = '1'

    project = Project.find_or_initialize_by(identifier: 'redidemo')
    project.name = ENV['DEMO_PROJECT_NAME']
    project.description = ENV['DEMO_PROJECT_DESC']
    project.is_public = true
    project.enabled_module_names = %w[issue_tracking time_tracking news wiki]
    project.save!

    puts "ADMIN_KEY=#{admin.api_key}"
RUBY
}

EN_KEY=$(setup_instance redmine-for-demo-en en 3002 'redi demo' 'Sample project for the redi demo' |
    grep '^ADMIN_KEY=' | tail -1 | cut -d= -f2)
JA_KEY=$(setup_instance redmine-for-demo-ja ja 3003 'redi デモ' 'redi のデモ用サンプルプロジェクト' |
    grep '^ADMIN_KEY=' | tail -1 | cut -d= -f2)

setup_profile() {
    local name="$1" url="$2" key="$3" lang="$4"
    # profile作成がべき等でないので失敗するのを当座で防ぐ。
    uv run redi config create "$name" --url "$url" --api_key "$key" || true
    uv run redi config update "$name" \
        --url "$url" \
        --api_key "$key" \
        --project_id "redidemo" \
        --wiki_project_id "redidemo" \
        --language "$lang"
}

setup_profile demo_en "http://localhost:3002" "$EN_KEY" en
setup_profile demo_ja "http://localhost:3003" "$JA_KEY" ja
uv run redi config update --default_profile demo_en

# 作成したイシューの ID を拾う。メッセージは言語で変わるので最初の数値を取る。
create_issue() {
    local profile="$1"
    shift
    uv run redi issue create --profile "$profile" "$@" | grep -oE '[0-9]+' | head -1
}

# 作業時間の活動 ID は環境依存なのでインスタンスごとに一覧の先頭を使う
activity_id_of() {
    uv run redi time_entry_activity list --profile "$1" --format json |
        python3 -c 'import json,sys; print(json.load(sys.stdin)[0]["id"])'
}

# ---------------------------------------------------------------- 英語データ

seed_en() {
    local p=demo_en
    local -a ids=()
    local ACTIVITY_ID
    ACTIVITY_ID=$(activity_id_of "$p")

    # 件名|トラッカー(1:Bug 2:Feature 3:Support)|優先度(1:Low 2:Normal 3:High 4:Urgent)|説明
    local -a rows=(
        "Login times out on slow networks|1|4|Reported from a mobile network. The request gives up before the server responds."
        "Add CSV export to the issue list|2|2|Needed for the monthly report. The same columns as the list view are enough."
        "Search results are not sorted by updated date|1|2|The order looks random. It should follow the sort given on the command line."
        "Support multiple profiles in one config file|2|2|One file should hold several servers so that switching does not need an edit."
        "Document the non-interactive mode|3|1|Explain what happens when a required argument is missing and there is no TTY."
        "Crash when the API key is empty|1|4|A traceback is printed instead of a message telling the user what to fix."
        "Add a keyboard shortcut for filtering|2|2|Opening the filter takes too many keys when going through a long list."
        "Update dependencies for the next release|3|2|Bump the pinned versions and run the whole test suite once."
        "Wiki links break with non-ASCII titles|1|3|Titles are not escaped, so a link to a Japanese page ends up pointing nowhere."
        "Improve the error message for an invalid tracker|2|1|Show the valid values instead of only saying that the value is wrong."
        "Add pagination to the time entry list|2|2|Only the first page is shown and there is no sign that more entries exist."
        "Review how the API rate limit is handled|3|2|Decide whether to retry, and how to tell the user that we are waiting."
        "Cache the project list between runs|2|1|The list rarely changes but is fetched on every command."
        "Attachments are not saved to the given path|1|3|The file always lands in the current directory, ignoring the option."
        "Ask for confirmation before deleting an issue|2|2|A single key press deletes the issue together with its comments."
        "Write an end-to-end test for the wiki commands|3|2|Wiki is the only resource without coverage in the e2e suite."
        "Time entries show the wrong date in some timezones|1|3|The date shifts by a day for users east of UTC."
        "Allow filtering issues by assignee|2|2|Useful when several people share one project."
    )
    for row in "${rows[@]}"; do
        IFS='|' read -r subject tracker priority description <<<"$row"
        ids+=("$(create_issue "$p" "$subject" --tracker_id "$tracker" --priority_id "$priority" --description "$description")")
    done

    # ステータスを散らす (2:In Progress 3:Resolved 4:Feedback 5:Closed)
    uv run redi issue update --profile "$p" "${ids[0]}" --status_id 2 --done_ratio 60
    uv run redi issue update --profile "$p" "${ids[3]}" --status_id 3 --done_ratio 100
    uv run redi issue update --profile "$p" "${ids[5]}" --status_id 2 --done_ratio 30
    uv run redi issue update --profile "$p" "${ids[7]}" --status_id 5 --done_ratio 100
    uv run redi issue update --profile "$p" "${ids[11]}" --status_id 4
    uv run redi issue update --profile "$p" "${ids[13]}" --status_id 2 --done_ratio 20
    uv run redi issue update --profile "$p" "${ids[15]}" --status_id 3 --done_ratio 100
    uv run redi issue update --profile "$p" "${ids[16]}" --status_id 4

    # コメントのあるイシューを作る
    uv run redi issue comment --profile "$p" "${ids[0]}" "Reproduced with a 3G connection. The timeout is hardcoded to 5 seconds."
    uv run redi issue comment --profile "$p" "${ids[0]}" "Raised it to 30 seconds and made it configurable."
    uv run redi issue comment --profile "$p" "${ids[5]}" "Adding a guard clause before the request is built."

    # 工数
    uv run redi time_entry create --profile "$p" 2.5 --issue_id "${ids[0]}" --activity_id "$ACTIVITY_ID" --comments "Investigated the timeout"
    uv run redi time_entry create --profile "$p" 1.0 --issue_id "${ids[0]}" --activity_id "$ACTIVITY_ID" --comments "Wrote a regression test"
    uv run redi time_entry create --profile "$p" 3.0 --issue_id "${ids[3]}" --activity_id "$ACTIVITY_ID" --comments "Implemented profile switching"
    uv run redi time_entry create --profile "$p" 0.5 --issue_id "${ids[5]}" --activity_id "$ACTIVITY_ID" --comments "Reviewed the patch"

    # Wiki
    uv run redi wiki create --profile "$p" "Wiki" --description "# Welcome

This is the wiki of the demo project.

- [Release notes](Release_notes)
- [Coding guidelines](Coding_guidelines)
"
    uv run redi wiki create --profile "$p" "Release notes" --description "# Release notes

## 0.2.0

- Added CSV export
- Fixed the login timeout on slow networks

## 0.1.0

- First release
"
    uv run redi wiki create --profile "$p" "Coding guidelines" --description "# Coding guidelines

- Keep the CLI usable without a TTY
- Report failures on stderr
- Write the specification you want to keep as a test
"
}

# -------------------------------------------------------------- 日本語データ

seed_ja() {
    local p=demo_ja
    local -a ids=()
    local ACTIVITY_ID
    ACTIVITY_ID=$(activity_id_of "$p")

    # 件名|トラッカー(1:バグ 2:機能 3:サポート)|優先度(1:低め 2:通常 3:高め 4:急いで)|説明
    local -a rows=(
        "低速な回線でログインがタイムアウトする|1|4|モバイル回線から報告あり。サーバの応答を待たずに諦めてしまう。"
        "チケット一覧に CSV エクスポートを追加する|2|2|月次レポートで必要。一覧と同じ項目が出れば十分。"
        "検索結果が更新日順に並ばない|1|2|順序がばらばらに見える。コマンドラインで指定した並び順に従うべき。"
        "1 つの設定ファイルで複数プロファイルを扱えるようにする|2|2|複数のサーバを 1 ファイルに持てれば、切り替えるたびに編集せずに済む。"
        "非対話モードの使い方をドキュメントに書く|3|1|必須の引数が無く TTY も無いときに何が起きるかを説明する。"
        "API キーが空のときにクラッシュする|1|4|何を直せばよいか示すメッセージではなく、トレースバックが出てしまう。"
        "絞り込みのキーボードショートカットを追加する|2|2|長い一覧を見ているとき、絞り込みを開くまでのキー操作が多い。"
        "次のリリースに向けて依存関係を更新する|3|2|固定しているバージョンを上げ、テストを一通り流す。"
        "日本語のタイトルだと Wiki のリンクが壊れる|1|3|タイトルがエスケープされておらず、日本語ページへのリンクがどこにも繋がらない。"
        "不正なトラッカーを指定したときのエラーメッセージを改善する|2|1|値が不正だと言うだけでなく、有効な値を示す。"
        "作業時間の一覧にページングを追加する|2|2|1 ページ目しか出ず、続きがあることも分からない。"
        "API のレート制限の扱いを見直す|3|2|再試行するかどうかと、待っていることをどう伝えるかを決める。"
        "プロジェクト一覧を実行間でキャッシュする|2|1|めったに変わらないのに、コマンドごとに取得している。"
        "添付ファイルが指定したパスに保存されない|1|3|オプションを無視して、常にカレントディレクトリに置かれる。"
        "チケットを削除する前に確認する|2|2|キー 1 つでコメントごと消えてしまう。"
        "Wiki コマンドの E2E テストを書く|3|2|E2E で覆われていないリソースは Wiki だけ。"
        "タイムゾーンによって作業時間の日付がずれる|1|3|UTC より東の利用者で日付が 1 日ずれる。"
        "担当者でチケットを絞り込めるようにする|2|2|複数人で 1 つのプロジェクトを使うときに要る。"
    )
    for row in "${rows[@]}"; do
        IFS='|' read -r subject tracker priority description <<<"$row"
        ids+=("$(create_issue "$p" "$subject" --tracker_id "$tracker" --priority_id "$priority" --description "$description")")
    done

    uv run redi issue update --profile "$p" "${ids[0]}" --status_id 2 --done_ratio 60
    uv run redi issue update --profile "$p" "${ids[3]}" --status_id 3 --done_ratio 100
    uv run redi issue update --profile "$p" "${ids[5]}" --status_id 2 --done_ratio 30
    uv run redi issue update --profile "$p" "${ids[7]}" --status_id 5 --done_ratio 100
    uv run redi issue update --profile "$p" "${ids[11]}" --status_id 4
    uv run redi issue update --profile "$p" "${ids[13]}" --status_id 2 --done_ratio 20
    uv run redi issue update --profile "$p" "${ids[15]}" --status_id 3 --done_ratio 100
    uv run redi issue update --profile "$p" "${ids[16]}" --status_id 4

    uv run redi issue comment --profile "$p" "${ids[0]}" "3G 回線で再現した。タイムアウトが 5 秒で決め打ちになっている。"
    uv run redi issue comment --profile "$p" "${ids[0]}" "30 秒に延ばし、設定で変えられるようにした。"
    uv run redi issue comment --profile "$p" "${ids[5]}" "リクエストを組み立てる前にガード節を入れる。"

    uv run redi time_entry create --profile "$p" 2.5 --issue_id "${ids[0]}" --activity_id "$ACTIVITY_ID" --comments "タイムアウトの調査"
    uv run redi time_entry create --profile "$p" 1.0 --issue_id "${ids[0]}" --activity_id "$ACTIVITY_ID" --comments "回帰テストの作成"
    uv run redi time_entry create --profile "$p" 3.0 --issue_id "${ids[3]}" --activity_id "$ACTIVITY_ID" --comments "プロファイル切り替えの実装"
    uv run redi time_entry create --profile "$p" 0.5 --issue_id "${ids[5]}" --activity_id "$ACTIVITY_ID" --comments "パッチのレビュー"

    uv run redi wiki create --profile "$p" "Wiki" --description "# ようこそ

デモ用プロジェクトの Wiki です。

- [リリースノート](リリースノート)
- [コーディング規約](コーディング規約)
"
    uv run redi wiki create --profile "$p" "リリースノート" --description "# リリースノート

## 0.2.0

- CSV エクスポートを追加
- 低速な回線でのログインタイムアウトを修正

## 0.1.0

- 最初のリリース
"
    uv run redi wiki create --profile "$p" "コーディング規約" --description "# コーディング規約

- TTY が無くても CLI が使える状態を保つ
- 失敗は標準エラー出力に出す
- 守りたい仕様はテストとして書く
"
}

seed_en
seed_ja

echo
echo "デモ用データを投入しました。"
echo "  英語:   uv run redi --tui --profile demo_en   (http://localhost:3002)"
echo "  日本語: uv run redi --tui --profile demo_ja   (http://localhost:3003)"
