# TUI の機能紹介 (日本語)。1 本で通しの GIF と要所の静止画を撮る。
#   前提: bash ./script/init-redmine-demo.sh でデモ用データを投入しておく
#   実行: vhs ./doc/tape/tui-ja.tape

Output "site/public/img/tui-tour-ja.gif"

Set Shell "bash"
Set FontSize 16
Set Width 1200
Set Height 600
Set WindowBar Colorful
Set WindowBarSize 40
Set Theme "Catppuccin Mocha"

Env LANG en_US.UTF-8

# 画面には redi と表示しつつ、実体はリポジトリ上のコードを実行する
Hide
Type "alias redi='uv run redi --profile demo_ja'"
Enter
Type "clear"
Enter
Show

Type "redi --tui"
Sleep 500ms
Enter
Sleep 4s
Screenshot "site/public/img/tui-issues-ja.png"
Sleep 1s

# 一覧を移動して右ペインが切り替わるのを見せる
Type "j"
Sleep 400ms
Type "j"
Sleep 400ms
Type "j"
Sleep 1s

# 検索
Type "/"
Sleep 800ms
Type "タイムアウト"
Sleep 1s
Screenshot "site/public/img/tui-search-ja.png"
Sleep 1s
Enter
Sleep 1500ms
Escape
Sleep 500ms

# 絞り込み
Type "f"
Sleep 1500ms
Screenshot "site/public/img/tui-filter-ja.png"
Sleep 1s
Escape
Sleep 500ms

# ヘルプ
Type "?"
Sleep 1500ms
Screenshot "site/public/img/tui-help-ja.png"
Sleep 1s
Escape
Sleep 500ms

# 作業時間タブ
Tab
Sleep 2s
Screenshot "site/public/img/tui-time-entries-ja.png"
Sleep 1s

# Wiki タブ
Tab
Sleep 2500ms
Screenshot "site/public/img/tui-wiki-ja.png"
Sleep 1s

# Wiki は Enter で本文を読み込む
Enter
Sleep 2s
Screenshot "site/public/img/tui-wiki-body-ja.png"
Sleep 1s

Type "q"
Sleep 1s
