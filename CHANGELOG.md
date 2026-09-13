# Changelog

## [0.0.83](https://github.com/kawagh/redi/compare/0.0.82...0.0.83) (2026-09-13)

- feat(tui): マウスホイールでプレビューのスクロールと一覧のカーソル移動ができるようにする ([#582](https://github.com/kawagh/redi/pull/582))
- feat(tui): タブ行のラベルをクリックしてタブを切り替えられるようにする ([#584](https://github.com/kawagh/redi/pull/584))
- feat(tui): wiki の右ペインをクリックしたら本文を読み込むようにする ([#586](https://github.com/kawagh/redi/pull/586))
- refactor(tui): マウスハンドラをペインの定義と同じモジュールに置く ([#589](https://github.com/kawagh/redi/pull/589))
- refactor: client.py と cache.py を api/ 配下へ移す ([#591](https://github.com/kawagh/redi/pull/591))
- fix(tui): 接続できないプロファイルへ切り替えても TUI を終了させない ([#594](https://github.com/kawagh/redi/pull/594))
- feat(tui): profile / project をマウスで切り替えられるようにする ([#592](https://github.com/kawagh/redi/pull/592))

## [0.0.82](https://github.com/kawagh/redi/compare/0.0.81...0.0.82) (2026-09-13)

- feat(config): list / view サブコマンドを追加し --full を廃止する ([#576](https://github.com/kawagh/redi/pull/576))
- fix(config): config list の出力を既知の項目だけ出すホワイトリスト方式にする ([#579](https://github.com/kawagh/redi/pull/579))
- feat(config): プロファイルを削除する config delete サブコマンドを追加する ([#577](https://github.com/kawagh/redi/pull/577))
- docs: CHANGELOG.md を作成する ([#581](https://github.com/kawagh/redi/pull/581))

## [0.0.81](https://github.com/kawagh/redi/compare/0.0.80...0.0.81) (2026-09-12)

- feat(tui): wiki タブで過去版を閲覧できるようにする ([#563](https://github.com/kawagh/redi/pull/563))
- feat(tui): wiki タブで 2 つの版の差分を右ペインに表示する ([#569](https://github.com/kawagh/redi/pull/569))
- refactor(tui): state.py をタブ毎に分割する ([#572](https://github.com/kawagh/redi/pull/572))
- refactor(tui): modal / モーダル / Float の用語を dialog / ダイアログ に揃える ([#573](https://github.com/kawagh/redi/pull/573))

## [0.0.80](https://github.com/kawagh/redi/compare/0.0.79...0.0.80) (2026-09-10)

- 存在しないプロファイル指定時のエラーに利用可能なプロファイル名を出す ([#553](https://github.com/kawagh/redi/pull/553))
- fix(cli): user 一覧と関係性削除が失敗しても exit 0 になるのを直す ([#556](https://github.com/kawagh/redi/pull/556))
- feat(cli): issue view の見出し行の直後にイシュー自身の URL を出す ([#554](https://github.com/kawagh/redi/pull/554))
- refactor(cli): イシュー不在時の exit 1 を issue_guard に集約する ([#557](https://github.com/kawagh/redi/pull/557))
- refactor(cli): issue_url の引数型と cli 側 list_issues の命名を整理する ([#561](https://github.com/kawagh/redi/pull/561))
- fix(cli): time_entry list と search の不正な -p で生の 404 を出さない ([#562](https://github.com/kawagh/redi/pull/562))
- docs(skill): redmine-redi に issue 間の relation を張る方法を書く ([#567](https://github.com/kawagh/redi/pull/567))
- fix(tui): 対話入力をキャンセルしても TUI に戻るようにする ([#565](https://github.com/kawagh/redi/pull/565))

## [0.0.79](https://github.com/kawagh/redi/compare/0.0.78...0.0.79) (2026-09-09)

- refactor(cli): 出力形式 (plain/tsv/json) を StrEnum にして分岐を match で書く ([#535](https://github.com/kawagh/redi/pull/535))
- build(deps-dev): bump ruff from 0.16.5 to 0.16.6 ([#538](https://github.com/kawagh/redi/pull/538))
- build(deps-dev): bump ty from 0.0.75 to 0.0.78 ([#537](https://github.com/kawagh/redi/pull/537))
- feat(cli): list 系の tsv 出力に各リソースの列定義を埋める ([#536](https://github.com/kawagh/redi/pull/536))
- chore(test): カバレッジ計測から i18n の定数モジュールを除外する ([#541](https://github.com/kawagh/redi/pull/541))
- feat(cli): --format に短縮形 -f を付ける ([#543](https://github.com/kawagh/redi/pull/543))
- fix(config): config --full でトップレベルの redmine_api_key もマスクする ([#544](https://github.com/kawagh/redi/pull/544))
- feat(config): config update の更新項目に現在の値を表示する ([#545](https://github.com/kawagh/redi/pull/545))
- fix(wiki): create で同名ページがあれば上書きせず exit 1 で止める ([#546](https://github.com/kawagh/redi/pull/546))
- feat(issue): view --include の不正値を送信前にエラーにする ([#547](https://github.com/kawagh/redi/pull/547))

## [0.0.78](https://github.com/kawagh/redi/compare/0.0.77...0.0.78) (2026-09-08)

- feat(plugin): redmine-redi を Claude Code / Codex のプラグインとして配布する ([#528](https://github.com/kawagh/redi/pull/528))
- feat(site): ブラウザ上で TUI を触れる体験ページを追加する ([#529](https://github.com/kawagh/redi/pull/529))
- fix(plugin): manifest から hooks の重複参照を外す ([#530](https://github.com/kawagh/redi/pull/530))
- feat(cli): list 系コマンドの --format に tsv を追加する ([#532](https://github.com/kawagh/redi/pull/532))

## [0.0.77](https://github.com/kawagh/redi/compare/0.0.76...0.0.77) (2026-09-07)

- feat(site): ドキュメントサイトの配色とトップページを整える ([#523](https://github.com/kawagh/redi/pull/523))
- feat(demo): TUI の収録環境を整え、ドキュメントサイトに画面を載せる ([#524](https://github.com/kawagh/redi/pull/524))
- feat(demo): redi init の収録を追加し、Getting Started に載せる ([#525](https://github.com/kawagh/redi/pull/525))
- feat(cli): issue view に journal/relation/attachment の id を出す ([#527](https://github.com/kawagh/redi/pull/527))

## [0.0.76](https://github.com/kawagh/redi/compare/0.0.75...0.0.76) (2026-09-05)

- ci: GitHub Pages にサイトをデプロイするCI追加 ([#519](https://github.com/kawagh/redi/pull/519))
- docs: サイトのページを追加し目次を再構成する ([#520](https://github.com/kawagh/redi/pull/520))
- feat(cli): 出力形式を --format で選べるようにし、--full をその別名にする ([#522](https://github.com/kawagh/redi/pull/522))

## [0.0.75](https://github.com/kawagh/redi/compare/0.0.74...0.0.75) (2026-09-02)

- [config] Redmine の記法 (Markdown / Textile) を text_formatting として設定に持たせる ([#513](https://github.com/kawagh/redi/pull/513))
- build(deps-dev): bump ty from 0.0.74 to 0.0.75 ([#510](https://github.com/kawagh/redi/pull/510))
- build(deps-dev): bump ruff from 0.16.4 to 0.16.5 ([#509](https://github.com/kawagh/redi/pull/509))
- build(deps): bump wcwidth from 0.8.2 to 0.8.3 ([#511](https://github.com/kawagh/redi/pull/511))
- ci: リリースノートをラベルでカテゴリ分けし dependabot を除外する ([#518](https://github.com/kawagh/redi/pull/518))
- docs(skill): redmine-redi にチケット添付手順と --full の JSON 形状を追記する ([#517](https://github.com/kawagh/redi/pull/517))

## [0.0.74](https://github.com/kawagh/redi/compare/0.0.73...0.0.74) (2026-08-31)

- feat(tui): ターミナルのリサイズ後に page_size を再計算する ([#409](https://github.com/kawagh/redi/pull/409))

## [0.0.73](https://github.com/kawagh/redi/compare/0.0.72...0.0.73) (2026-08-30)

- [cli] list 系コマンドに --limit / --offset をリソース横断で追加する ([#508](https://github.com/kawagh/redi/pull/508))
- fix(cli): issue update --relate を choices で弾き、有効な値を示す ([#494](https://github.com/kawagh/redi/pull/494))
- fix(cli): issue update --add-watcher が追加できないユーザーIDで成功扱いになるのを直す ([#496](https://github.com/kawagh/redi/pull/496))

## [0.0.72](https://github.com/kawagh/redi/compare/0.0.71...0.0.72) (2026-08-29)

- [TUI] イシュー検索 (F) を追加 ([#506](https://github.com/kawagh/redi/pull/506))

## [0.0.71](https://github.com/kawagh/redi/compare/0.0.70...0.0.71) (2026-08-27)

- refactor(cli): 対話入力のキャンセル処理をコンテキストマネージャに集約する ([#495](https://github.com/kawagh/redi/pull/495))
- feat(cli): エディタの一時ファイルに用途が分かる名前を付ける ([#493](https://github.com/kawagh/redi/pull/493))
- docs: add CONTRIBUTING.md ([#498](https://github.com/kawagh/redi/pull/498))
- docs: PR テンプレートを追加する ([#502](https://github.com/kawagh/redi/pull/502))
- feat: イシューのメタ表に親チケットの行を追加する ([#504](https://github.com/kawagh/redi/pull/504))
- ci: ドキュメントのみの変更でCIを実行しないようにする ([#500](https://github.com/kawagh/redi/pull/500))
- feat(cli): issue update の対話モードで親チケットを変更できるようにする ([#501](https://github.com/kawagh/redi/pull/501))

## [0.0.70](https://github.com/kawagh/redi/compare/0.0.69...0.0.70) (2026-08-26)

- build(deps-dev): bump ty from 0.0.72 to 0.0.74 ([#489](https://github.com/kawagh/redi/pull/489))
- build(deps-dev): bump ruff from 0.16.3 to 0.16.4 ([#488](https://github.com/kawagh/redi/pull/488))
- feat(tui): 検索クエリの残存を表示し normal mode の Esc で解除できるようにする ([#473](https://github.com/kawagh/redi/pull/473))
- feat(config): config create を対話的に実行できるようにする ([#345](https://github.com/kawagh/redi/pull/345))
- issue update のステータス選択を遷移可能なものに限定する ([#490](https://github.com/kawagh/redi/pull/490))

## [0.0.69](https://github.com/kawagh/redi/compare/0.0.68...0.0.69) (2026-08-25)

- fix(issue): HTTPエラーでもエディタで書いた本文を退避する ([#465](https://github.com/kawagh/redi/pull/465))
- [CLI] project create/update に homepage / enabled_module_names / inherit_members 等を渡せるようにする ([#475](https://github.com/kawagh/redi/pull/475))
- エラーメッセージを標準エラー出力に出す ([#486](https://github.com/kawagh/redi/pull/486))
- feat(project): update を対話で実行できるようにする ([#487](https://github.com/kawagh/redi/pull/487))

## [0.0.68](https://github.com/kawagh/redi/compare/0.0.67...0.0.68) (2026-08-24)

- [CLI] query list に公開/非公開と対象プロジェクトを出す ([#435](https://github.com/kawagh/redi/pull/435))
- fix(issue): 存在しない --query_id の 404 をクエリ未検出として案内する ([#468](https://github.com/kawagh/redi/pull/468))
- fix(cli): issue update の存在しない tracker_id / status_id を弾く ([#478](https://github.com/kawagh/redi/pull/478))
- feat(role): role view の権限を admin/roles と同じカテゴリ単位で表示する ([#470](https://github.com/kawagh/redi/pull/470))
- fix(time_entry): create で必須項目が欠けていれば対話で補う ([#469](https://github.com/kawagh/redi/pull/469))
- fix(cli): 接続できない Redmine を指したときに生のトレースバックを出さない ([#444](https://github.com/kawagh/redi/pull/444))
- revert(role): 権限の表示名を内部名に戻す ([#482](https://github.com/kawagh/redi/pull/482))
- fix(cli): list 系の HTTP エラーでトレースバックを出さない ([#445](https://github.com/kawagh/redi/pull/445))
- fix(cli): 422 の生 JSON を出さず、入力エラーの整形を全リソースで揃える ([#446](https://github.com/kawagh/redi/pull/446))
- fix(cli): time_entry update で存在しないIDに生の 404 を出さない ([#447](https://github.com/kawagh/redi/pull/447))

## [0.0.67](https://github.com/kawagh/redi/compare/0.0.66...0.0.67) (2026-08-24)

- feat(project create): 引数省略時に対話的に入力できるようにする ([#408](https://github.com/kawagh/redi/pull/408))
- feat(tui): フィルタモーダルにクエリ列を足してカスタムクエリで絞り込めるようにする ([#430](https://github.com/kawagh/redi/pull/430))
- fix(time_entry): 不正な日付フィルタを argparse で弾く ([#466](https://github.com/kawagh/redi/pull/466))
- refactor: 不要な from __future__ import annotations を削除する ([#480](https://github.com/kawagh/redi/pull/480))

## [0.0.66](https://github.com/kawagh/redi/compare/0.0.65...0.0.66) (2026-08-23)

- fix(cli): issue list で --query_id と併用不可なフィルタを弾く ([#420](https://github.com/kawagh/redi/pull/420))
- refactor(cli): enumerations_command の add_*_parser をテーブル駆動にまとめる ([#412](https://github.com/kawagh/redi/pull/412))
- feat(cli): issue view にメタ情報ヘッダとコメントを既定表示する ([#425](https://github.com/kawagh/redi/pull/425))
- fix(cli): redi me と user view current の出力形式と項目を揃える ([#426](https://github.com/kawagh/redi/pull/426))
- feat(cli): config の出力に現在のプロファイル名を表示する ([#434](https://github.com/kawagh/redi/pull/434))
- feat(time_entry): 一覧の行に活動名を表示する ([#437](https://github.com/kawagh/redi/pull/437))

## [0.0.65](https://github.com/kawagh/redi/compare/0.0.64...0.0.65) (2026-08-22)

- fix(tui): 左右ペインの分割幅を端末幅の50%に固定する ([#413](https://github.com/kawagh/redi/pull/413))
- fix(tui): 一覧と区切り線の間に空白を挟んで境界を揃える ([#414](https://github.com/kawagh/redi/pull/414))
- feat(tui): 切替モーダルに gg/G を足す ([#418](https://github.com/kawagh/redi/pull/418))

## [0.0.64](https://github.com/kawagh/redi/compare/0.0.63...0.0.64) (2026-08-22)

- fix(project): アーカイブ済みプロジェクトの view で 403 を処理する ([#405](https://github.com/kawagh/redi/pull/405))
- feat(issue create): カスタムフィールドの min_length/max_length/regexp を検証する ([#171](https://github.com/kawagh/redi/pull/171))
- feat(user): user list に絞り込みとページングのオプションを追加 ([#393](https://github.com/kawagh/redi/pull/393))

## [0.0.63](https://github.com/kawagh/redi/compare/0.0.62...0.0.63) (2026-08-19)

- feat(cli): キャッシュを取り直す --refresh オプションを追加する ([#403](https://github.com/kawagh/redi/pull/403))
- chore: redmineのインスタンスを7.0 に更新(7.0.0.stableであることを画面上から確認) ([#407](https://github.com/kawagh/redi/pull/407))

## [0.0.62](https://github.com/kawagh/redi/compare/0.0.61...0.0.62) (2026-08-19)

- chore(deps-dev): bump ruff from 0.16.2 to 0.16.3 ([#398](https://github.com/kawagh/redi/pull/398))
- chore(deps-dev): bump ty from 0.0.69 to 0.0.72 ([#397](https://github.com/kawagh/redi/pull/397))
- feat(tui): イシュー一覧を tracker で絞り込めるようにする ([#400](https://github.com/kawagh/redi/pull/400))

## [0.0.61](https://github.com/kawagh/redi/compare/0.0.60...0.0.61) (2026-08-18)

- fix(cli): 存在しないプロジェクトIDでイシュー一覧を取得したときの案内を追加する ([#274](https://github.com/kawagh/redi/pull/274))
- refactor(api): ProjectNotFoundException の二重定義を解消する ([#396](https://github.com/kawagh/redi/pull/396))

## [0.0.60](https://github.com/kawagh/redi/compare/0.0.59...0.0.60) (2026-08-17)

- refactor(news): news の view / create / update / delete を news_service 経由にする ([#375](https://github.com/kawagh/redi/pull/375))
- refactor(issue_journal): update / delete を issue_journal_service 経由にする ([#373](https://github.com/kawagh/redi/pull/373))
- refactor(me): me の view / update を me_service 経由にする ([#381](https://github.com/kawagh/redi/pull/381))
- docs(skills): dogfooding-redi スキルの起票書式を ISSUE_TEMPLATE に寄せる ([#390](https://github.com/kawagh/redi/pull/390))
- refactor(project): project の操作を project_service 経由にする ([#377](https://github.com/kawagh/redi/pull/377))
- refactor(group): view / create / update / delete とユーザー追加・削除を group_service 経由にする ([#376](https://github.com/kawagh/redi/pull/376))
- refactor(membership): membership の view / create / update / delete を membership_service 経由にする ([#378](https://github.com/kawagh/redi/pull/378))
- refactor(user): user の view / create / update / delete を user_service 経由にする ([#374](https://github.com/kawagh/redi/pull/374))
- refactor(version): view / create / update / delete を version_service 経由にする ([#379](https://github.com/kawagh/redi/pull/379))
- refactor(issue_category): view/create/update/delete を issue_category_service 経由にする ([#380](https://github.com/kawagh/redi/pull/380))
- [refactor] project file の list / create を file_service 経由にする ([#382](https://github.com/kawagh/redi/pull/382))
- refactor(api): 読み取り専用リソースの表示整形を cli へ移す ([#385](https://github.com/kawagh/redi/pull/385))
- refactor(relation): issue_relation を service 経由にする ([#383](https://github.com/kawagh/redi/pull/383))
- [refactor] attachment の view / upload / download / update / delete を attachment_service 経由にする ([#384](https://github.com/kawagh/redi/pull/384))
- feat(issue): issue update でプロジェクトを移動できるようにする ([#394](https://github.com/kawagh/redi/pull/394))

## [0.0.59](https://github.com/kawagh/redi/compare/0.0.58...0.0.59) (2026-08-17)

- refactor(issue): view / create / update / comment も issue_service 経由にする ([#358](https://github.com/kawagh/redi/pull/358))
- refactor(time_entry): view / create / update も time_entry_service 経由にする ([#357](https://github.com/kawagh/redi/pull/357))
- docs(skills): redmine-redi に使用例と手順を追記し、仕様の任意フィールドを補う ([#387](https://github.com/kawagh/redi/pull/387))

## [0.0.58](https://github.com/kawagh/redi/compare/0.0.57...0.0.58) (2026-08-16)

- [TUI] issue を D + ID 入力モーダルで削除できるようにする ([#172](https://github.com/kawagh/redi/pull/172))
- [TUI] Wikiの削除を出来るようにする ([#350](https://github.com/kawagh/redi/pull/350))
- refactor(wiki): view / create / update も wiki_service 経由にする ([#353](https://github.com/kawagh/redi/pull/353))
- refactor: issue / time_entry の削除を service 経由にする ([#354](https://github.com/kawagh/redi/pull/354))

## [0.0.57](https://github.com/kawagh/redi/compare/0.0.56...0.0.57) (2026-08-15)

- refactor(config): プロファイルを Profile クラスとして扱う ([#342](https://github.com/kawagh/redi/pull/342))
- feat(issue): issue create の出力に ID を含め --full を追加する ([#343](https://github.com/kawagh/redi/pull/343))
- [cli] list サブコマンドの後ろにもフィルタオプションを書けるようにする ([#346](https://github.com/kawagh/redi/pull/346))
- #338 一覧専用リソースに list サブコマンド (alias: l) を追加 ([#344](https://github.com/kawagh/redi/pull/344))
- AGENTS.md を作成し、テストの方針を追記する ([#348](https://github.com/kawagh/redi/pull/348))

## [0.0.56](https://github.com/kawagh/redi/compare/0.0.55...0.0.56) (2026-08-14)

- feat(tui): P キーでプロファイルを切り替えられるようにする ([#332](https://github.com/kawagh/redi/pull/332))
- feat(config): プロファイル更新時にデフォルト化を選べるようにする ([#336](https://github.com/kawagh/redi/pull/336))

## [0.0.55](https://github.com/kawagh/redi/compare/0.0.54...0.0.55) (2026-08-13)

- feat(e2e): redmine 7.0 に対しても E2E テストを実行できるようにする ([#329](https://github.com/kawagh/redi/pull/329))
- feat(api): redmine 7.0 で拡張されたレスポンスに対応する ([#331](https://github.com/kawagh/redi/pull/331))
- テンプレート解決にトラッカーを渡せるようにする ([#333](https://github.com/kawagh/redi/pull/333))
- chore(deps): bump argcomplete from 3.7.0 to 3.7.2 ([#324](https://github.com/kawagh/redi/pull/324))

## [0.0.54](https://github.com/kawagh/redi/compare/0.0.53...0.0.54) (2026-08-12)

- feat: エージェント向けスキル redmine-redi を追加 ([#326](https://github.com/kawagh/redi/pull/326))
- redi init で言語設定を選択させる ([#327](https://github.com/kawagh/redi/pull/327))

## [0.0.53](https://github.com/kawagh/redi/compare/0.0.52...0.0.53) (2026-08-12)

- fix(cli): 非TTY環境で対話に入る前に足りない入力を示して終了する ([#322](https://github.com/kawagh/redi/pull/322))
- chore(deps-dev): bump ruff from 0.16.1 to 0.16.2 ([#325](https://github.com/kawagh/redi/pull/325))
- chore(deps-dev): bump ty from 0.0.65 to 0.0.69 ([#323](https://github.com/kawagh/redi/pull/323))

## [0.0.52](https://github.com/kawagh/redi/compare/0.0.51...0.0.52) (2026-08-11)

- refactor(cli): issue update の引数を dataclass 化する ([#311](https://github.com/kawagh/redi/pull/311))
- refactor(cli): issue create の引数を dataclass 化する ([#312](https://github.com/kawagh/redi/pull/312))
- refactor(cli): issue_command.py をパッケージに分割する ([#314](https://github.com/kawagh/redi/pull/314))
- refactor(cli): issue の項目入力を共通化し update を create に揃える ([#317](https://github.com/kawagh/redi/pull/317))
- docs: 開発対象の redmine バージョンを明記する ([#315](https://github.com/kawagh/redi/pull/315))
- feat(cli): news コマンドに view/create/update/delete を追加する ([#319](https://github.com/kawagh/redi/pull/319))

## [0.0.51](https://github.com/kawagh/redi/compare/0.0.50...0.0.51) (2026-08-10)

- refactor(tui): app.py からキーバインド定義を切り出す ([#299](https://github.com/kawagh/redi/pull/299))
- refactor(tui): app.py の残りを描画・レイアウト・画面ログに分割する ([#300](https://github.com/kawagh/redi/pull/300))
- [update(config)] config update で選択したプロファイルの項目を対話的に更新できるようにする ([#301](https://github.com/kawagh/redi/pull/301))

## [0.0.50](https://github.com/kawagh/redi/compare/0.0.49...0.0.50) (2026-08-08)

- feat(search): search コマンドに Redmine Search API のフィルターを追加 ([#293](https://github.com/kawagh/redi/pull/293))
- ruff の ignore を解消するか維持するか判断して対応する ([#298](https://github.com/kawagh/redi/pull/298))

## [0.0.49](https://github.com/kawagh/redi/compare/0.0.48...0.0.49) (2026-08-07)

- feat(project): プロジェクト選択ダイアログを ID 降順で表示する ([#295](https://github.com/kawagh/redi/pull/295))
- fix(cli): 選択ダイアログで画面外の候補にスクロールできるようにする ([#297](https://github.com/kawagh/redi/pull/297))

## [0.0.48](https://github.com/kawagh/redi/compare/0.0.47...0.0.48) (2026-08-05)

- feat(cli): attachment download コマンドを追加 ([#286](https://github.com/kawagh/redi/pull/286))
- fix(api): プロジェクト一覧を全ページ取得する ([#285](https://github.com/kawagh/redi/pull/285))
- chore(deps-dev): bump ty from 0.0.64 to 0.0.65 ([#282](https://github.com/kawagh/redi/pull/282))
- chore(deps): bump prompt-toolkit from 3.0.52 to 3.0.53 ([#276](https://github.com/kawagh/redi/pull/276))
- chore(lint): ruff 0.16 で追加されたルールの一部を ignore ([#287](https://github.com/kawagh/redi/pull/287))
- chore(deps-dev): bump ruff from 0.15.22 to 0.16.1 ([#281](https://github.com/kawagh/redi/pull/281))

## [0.0.47](https://github.com/kawagh/redi/compare/0.0.46...0.0.47) (2026-08-04)

- chore(deps-dev): bump ty from 0.0.63 to 0.0.64 ([#277](https://github.com/kawagh/redi/pull/277))
- chore(deps-dev): update uv-build requirement from <0.12.0,>=0.9.2 to >=0.9.2,<0.13.0 ([#275](https://github.com/kawagh/redi/pull/275))
- fix(tui): ダイアログの見切れを解消する ([#280](https://github.com/kawagh/redi/pull/280))

## [0.0.46](https://github.com/kawagh/redi/compare/0.0.45...0.0.46) (2026-07-25)

- rulesyncの追加、スキルの同期 ([#254](https://github.com/kawagh/redi/pull/254))
- chore(deps-dev): bump ty from 0.0.51 to 0.0.53 ([#256](https://github.com/kawagh/redi/pull/256))
- chore(deps-dev): bump ruff from 0.15.18 to 0.15.19 ([#255](https://github.com/kawagh/redi/pull/255))
- chore(deps-dev): bump ty from 0.0.53 to 0.0.56 ([#262](https://github.com/kawagh/redi/pull/262))
- chore(deps-dev): bump ruff from 0.15.19 to 0.15.20 ([#259](https://github.com/kawagh/redi/pull/259))
- chore(deps-dev): bump ruff from 0.15.20 to 0.15.21 ([#264](https://github.com/kawagh/redi/pull/264))
- chore(deps-dev): bump ty from 0.0.56 to 0.0.59 ([#263](https://github.com/kawagh/redi/pull/263))
- chore(deps-dev): bump ruff from 0.15.21 to 0.15.22 ([#268](https://github.com/kawagh/redi/pull/268))
- chore(deps): bump tomlkit from 0.15.0 to 0.15.1 ([#266](https://github.com/kawagh/redi/pull/266))
- chore(deps): bump wcwidth from 0.8.1 to 0.8.2 ([#260](https://github.com/kawagh/redi/pull/260))
- chore(deps): bump argcomplete from 3.6.3 to 3.7.0 ([#258](https://github.com/kawagh/redi/pull/258))
- feat(tui): TUI 上でプロジェクトを切り替えられるようにする ([#269](https://github.com/kawagh/redi/pull/269))
- fix(cli): picker の cursor 初期化に is not None を明示する ([#270](https://github.com/kawagh/redi/pull/270))
- chore(deps-dev): bump ty from 0.0.59 to 0.0.63 ([#267](https://github.com/kawagh/redi/pull/267))
- feat(tui): ヘルプダイアログの右下にバージョンを表示する ([#272](https://github.com/kawagh/redi/pull/272))

## [0.0.45](https://github.com/kawagh/redi/compare/0.0.44...0.0.45) (2026-06-23)

- chore(deps-dev): bump pytest from 9.1.0 to 9.1.1 ([#251](https://github.com/kawagh/redi/pull/251))
- chore(deps-dev): bump ty from 0.0.49 to 0.0.51 ([#250](https://github.com/kawagh/redi/pull/250))
- chore(deps-dev): bump ruff from 0.15.17 to 0.15.18 ([#249](https://github.com/kawagh/redi/pull/249))
- [issue update(interactive)] カスタムフィールドに対応 ([#253](https://github.com/kawagh/redi/pull/253))

## [0.0.44](https://github.com/kawagh/redi/compare/0.0.43...0.0.44) (2026-06-16)

- chore(deps-dev): bump pytest from 9.0.3 to 9.1.0 ([#245](https://github.com/kawagh/redi/pull/245))
- chore(deps-dev): bump ty from 0.0.46 to 0.0.49 ([#244](https://github.com/kawagh/redi/pull/244))
- feat: issue create/update 失敗時に本文を一時ファイルへ退避する #246 ([#247](https://github.com/kawagh/redi/pull/247))
- chore(deps-dev): bump ruff from 0.15.16 to 0.15.17 ([#243](https://github.com/kawagh/redi/pull/243))
- chore(deps): bump wcwidth from 0.7.0 to 0.8.1 ([#235](https://github.com/kawagh/redi/pull/235))

## [0.0.43](https://github.com/kawagh/redi/compare/0.0.42...0.0.43) (2026-06-10)

- [update] uv lock --upgrade-package idna --upgrade-package urllib3 ([#241](https://github.com/kawagh/redi/pull/241))

## [0.0.42](https://github.com/kawagh/redi/compare/0.0.41...0.0.42) (2026-06-09)

- chore(deps-dev): bump ruff from 0.15.15 to 0.15.16 ([#233](https://github.com/kawagh/redi/pull/233))
- chore(deps-dev): bump ty from 0.0.43 to 0.0.46 ([#236](https://github.com/kawagh/redi/pull/236))
- feat: issue create 時にテンプレートを選択して使えるようにする ([#238](https://github.com/kawagh/redi/pull/238))
- feat: CLIでの項目選択/チェック時に gg/G で先頭・末尾へ移動できるようにする ([#240](https://github.com/kawagh/redi/pull/240))

## [0.0.41](https://github.com/kawagh/redi/compare/0.0.40...0.0.41) (2026-06-05)

- feat: redmine_issue_templateプラグインによって提供されるテンプレートを取得するissue_templateコマンドを追加 ([#232](https://github.com/kawagh/redi/pull/232))
- chore(deps-dev): bump ty from 0.0.39 to 0.0.43 ([#231](https://github.com/kawagh/redi/pull/231))
- chore(deps-dev): bump ruff from 0.15.14 to 0.15.15 ([#229](https://github.com/kawagh/redi/pull/229))

## [0.0.40](https://github.com/kawagh/redi/compare/0.0.39...0.0.40) (2026-05-27)

- typing Wiki ([#224](https://github.com/kawagh/redi/pull/224))
- update(types): time_entry リソースを型つけ ([#225](https://github.com/kawagh/redi/pull/225))
- feat(tui): フィルタの絞り込み条件をTUIループ間で引き継ぐ ([#227](https://github.com/kawagh/redi/pull/227))

## [0.0.39](https://github.com/kawagh/redi/compare/0.0.38...0.0.39) (2026-05-26)

- Issueを型つけ ([#216](https://github.com/kawagh/redi/pull/216))
- chore(deps-dev): bump ruff from 0.15.13 to 0.15.14 ([#214](https://github.com/kawagh/redi/pull/214))
- [cli] --profile で補完候補をきくようにした ([#220](https://github.com/kawagh/redi/pull/220))
- chore(deps-dev): bump ty from 0.0.38 to 0.0.39 ([#217](https://github.com/kawagh/redi/pull/217))
- typing Project ([#221](https://github.com/kawagh/redi/pull/221))

## [0.0.38](https://github.com/kawagh/redi/compare/0.0.37...0.0.38) (2026-05-20)

- chore(deps-dev): bump ty from 0.0.35 to 0.0.37 ([#209](https://github.com/kawagh/redi/pull/209))
- chore(deps-dev): bump ty from 0.0.37 to 0.0.38 ([#210](https://github.com/kawagh/redi/pull/210))
- TUIでissueのコメントの更新/削除 を追加 ([#211](https://github.com/kawagh/redi/pull/211))
- update(tui): TUIのEscキーを終了に割り当てないように更新 ([#213](https://github.com/kawagh/redi/pull/213))

## [0.0.37](https://github.com/kawagh/redi/compare/0.0.36...0.0.37) (2026-05-17)

- chore(deps): bump wcwidth from 0.6.0 to 0.7.0 ([#194](https://github.com/kawagh/redi/pull/194))
- chore(deps-dev): bump ruff from 0.15.12 to 0.15.13 ([#203](https://github.com/kawagh/redi/pull/203))
- chore(deps): bump tomlkit from 0.14.0 to 0.15.0 ([#199](https://github.com/kawagh/redi/pull/199))
- fix: requests 2.34 への bump で発生した型エラーを解消 ([#206](https://github.com/kawagh/redi/pull/206))
- キャッシュの保存先をredmineごとに分ける ([#208](https://github.com/kawagh/redi/pull/208))

## [0.0.36](https://github.com/kawagh/redi/compare/0.0.35...0.0.36) (2026-05-15)

- chore(deps-dev): update uv-build requirement from <0.10.0,>=0.9.2 to >=0.9.2,<0.12.0 ([#195](https://github.com/kawagh/redi/pull/195))
- chore(deps-dev): bump ruff from 0.15.9 to 0.15.12 ([#198](https://github.com/kawagh/redi/pull/198))
- chore(deps-dev): bump ty from 0.0.31 to 0.0.35 ([#197](https://github.com/kawagh/redi/pull/197))
- fix(tui): TUI からの issue create で AttributeError を解消 ([#202](https://github.com/kawagh/redi/pull/202))

## [0.0.35](https://github.com/kawagh/redi/compare/0.0.34...0.0.35) (2026-05-13)

- feat(tui): フィルタモーダルに ctrl+n / ctrl+p を追加 ([#191](https://github.com/kawagh/redi/pull/191))
- feat(tui): フィルタモーダルで自分と実ユーザーの重複表示を解消 ([#193](https://github.com/kawagh/redi/pull/193))

## [0.0.34](https://github.com/kawagh/redi/compare/0.0.33...0.0.34) (2026-05-12)

- feat(time_entry): spent_on にバリデーション追加 (#181 ) ([#182](https://github.com/kawagh/redi/pull/182))
- feat(time_entry): list に --from/--to と --limit/--offset を追加 ([#184](https://github.com/kawagh/redi/pull/184))
- feat(tui): time_entry タブにページング機能を追加 ([#187](https://github.com/kawagh/redi/pull/187))
- feat(tui): time_entry タブにユーザーフィルタを追加 ([#188](https://github.com/kawagh/redi/pull/188))
- [demo] issue create/update をデモに追加 ([#189](https://github.com/kawagh/redi/pull/189))

## [0.0.33](https://github.com/kawagh/redi/compare/0.0.32...0.0.33) (2026-05-11)

- feat(issue_journal): update/delete コマンドを追加 ([#178](https://github.com/kawagh/redi/pull/178))

## [0.0.32](https://github.com/kawagh/redi/compare/0.0.31...0.0.32) (2026-05-11)

- test(i18n): MessagesProto の未使用 key と実装漏れを検査 ([#173](https://github.com/kawagh/redi/pull/173))
- pytest-cov で coverage 計測 (#174 ) ([#175](https://github.com/kawagh/redi/pull/175))
- issue create/update (interactive) で project に紐づく tracker のみを候補にする ([#176](https://github.com/kawagh/redi/pull/176))

## [0.0.31](https://github.com/kawagh/redi/compare/0.0.30...0.0.31) (2026-05-08)

- refactor: cli/ の責務分割 (close #162 ) ([#168](https://github.com/kawagh/redi/pull/168))
- [issue create] 対話操作で任意項目を埋められるようにする (close #154 ) ([#169](https://github.com/kawagh/redi/pull/169))

## [0.0.30](https://github.com/kawagh/redi/compare/0.0.29...0.0.30) (2026-05-07)

- [issue create] attachmentを除くカスタムフィールドに対応 ([#161](https://github.com/kawagh/redi/pull/161))

## [0.0.29](https://github.com/kawagh/redi/compare/0.0.28...0.0.29) (2026-05-05)

- [update] config update でプロファイル切替を対話的に行えるようにする ([#159](https://github.com/kawagh/redi/pull/159))
- [issue create] カスタムフィールドでキーバリューリスト、バージョン、ユーザーに対応 ([#160](https://github.com/kawagh/redi/pull/160))

## [0.0.28](https://github.com/kawagh/redi/compare/0.0.27...0.0.28) (2026-05-04)

- [update] --profile オプションをサブコマンドの後ろに置けるようにする ([#147](https://github.com/kawagh/redi/pull/147))
- close #148  issue create でブラウザに値を引き継いで開く選択肢を追加 ([#150](https://github.com/kawagh/redi/pull/150))
- TUI: R キーで現在のタブを再読込する操作を追加 ([#152](https://github.com/kawagh/redi/pull/152))

## [0.0.27](https://github.com/kawagh/redi/compare/0.0.26...0.0.27) (2026-05-03)

- TUIでwiki更新がコンフリクトした時にモーダル表示 ([#140](https://github.com/kawagh/redi/pull/140))
- close #142 RedmineのAPIが422を返した場合のエラーをTUIで表示 ([#143](https://github.com/kawagh/redi/pull/143))
- close #144 issueの存在しないprojectでTUIが即終了する問題を修正 ([#145](https://github.com/kawagh/redi/pull/145))

## [0.0.26](https://github.com/kawagh/redi/compare/0.0.25...0.0.26) (2026-05-01)

- wiki update(interactive) で version を指定して conflict を検知 (resolve #133 ) ([#134](https://github.com/kawagh/redi/pull/134))
- [add] wikiの作成/更新時にcommentを指定可能にする (refs #136 ) ([#137](https://github.com/kawagh/redi/pull/137))
- add demo GIF ([#139](https://github.com/kawagh/redi/pull/139))

## [0.0.25](https://github.com/kawagh/redi/compare/0.0.24...0.0.25) (2026-04-30)

- dogfooding用のサービスを追加 ([#124](https://github.com/kawagh/redi/pull/124))
- E2Eテストの作成/CIでの実行 ([#126](https://github.com/kawagh/redi/pull/126))
- [test] project に対する list/create/update/delete の e2e テストを追加 ([#128](https://github.com/kawagh/redi/pull/128))
- 各コマンドにエイリアスを追加する ([#131](https://github.com/kawagh/redi/pull/131))

## [0.0.24](https://github.com/kawagh/redi/compare/0.0.23...0.0.24) (2026-04-28)

- [feat] 作業時間タブからの新規作成時にカーソル行のイシューを初期値とする (refs #118 ) ([#121](https://github.com/kawagh/redi/pull/121))
- [fix] 言語変更時に変更後の言語で結果メッセージを出力 (refs #119 ) ([#120](https://github.com/kawagh/redi/pull/120))
- [feat] TUI の右ペイン (preview) をスクロール可能にする (refs #97 ) ([#122](https://github.com/kawagh/redi/pull/122))

## [0.0.23](https://github.com/kawagh/redi/compare/0.0.22...0.0.23) (2026-04-27)

- [feature] 文字列のリソース化 #114 ([#115](https://github.com/kawagh/redi/pull/115))
- [feat] config update/create で --language を指定可能にする #116 ([#117](https://github.com/kawagh/redi/pull/117))

## [0.0.22](https://github.com/kawagh/redi/compare/0.0.21...0.0.22) (2026-04-26)

- イシュー更新で start_date / due_date / done_ratio / estimated_hours をサポート ([#108](https://github.com/kawagh/redi/pull/108))
- イシュー更新の対話モードで担当者を選べるようにする ([#110](https://github.com/kawagh/redi/pull/110))
- TUI に ? で開くヘルプウィンドウを追加 (closes #111 ) ([#112](https://github.com/kawagh/redi/pull/112))
- TUI に f キーでイシューフィルタの floating window を追加 (closes #102 ) ([#113](https://github.com/kawagh/redi/pull/113))

## [0.0.21](https://github.com/kawagh/redi/compare/0.0.20...0.0.21) (2026-04-25)

- #103 TUI 作業時間タブに D キー削除を追加 ([#104](https://github.com/kawagh/redi/pull/104))
- redi init コマンドの作成 ([#106](https://github.com/kawagh/redi/pull/106))

## [0.0.20](https://github.com/kawagh/redi/compare/0.0.19...0.0.20) (2026-04-24)

- [feat] time_entry create を対話的に入力できるように対応 ([#101](https://github.com/kawagh/redi/pull/101))

## [0.0.19](https://github.com/kawagh/redi/compare/0.0.18...0.0.19) (2026-04-23)

- add release.yml ([#99](https://github.com/kawagh/redi/pull/99))

## [0.0.18](https://github.com/kawagh/redi/compare/0.0.17...0.0.18) (2026-04-22)

- [fix] redi -> redtile

## [0.0.17](https://github.com/kawagh/redi/compare/0.0.16...0.0.17) (2026-04-22)

- TUI に Wiki タブを追加し issue 一覧表示を改善 (#76 ) ([#92](https://github.com/kawagh/redi/pull/92))
- [feat] TUI wiki タブから create/update を呼び出せるようにする ([#94](https://github.com/kawagh/redi/pull/94))

## [0.0.16](https://github.com/kawagh/redi/compare/0.0.15...0.0.16) (2026-04-21)

- 削除系コマンドに確認プロンプトと -y/--yes フラグを追加 ([#89](https://github.com/kawagh/redi/pull/89))
- #90 各リソースに list サブコマンド (alias: l) を追加 ([#91](https://github.com/kawagh/redi/pull/91))

## [0.0.15](https://github.com/kawagh/redi/compare/0.0.14...0.0.15) (2026-04-21)

- [add] time_entry に view/update/delete サブコマンドを追加 ([#85](https://github.com/kawagh/redi/pull/85))
- group コマンドの追加 ([#79](https://github.com/kawagh/redi/pull/79))
- news command ([#81](https://github.com/kawagh/redi/pull/81))
- [add] issue_category (list)/create/view/update/delete command ([#83](https://github.com/kawagh/redi/pull/83))
- [add] membership (list)/create/view/update/delete command ([#86](https://github.com/kawagh/redi/pull/86))
- redi user に view/update/delete、redi me に update を追加 ([#87](https://github.com/kawagh/redi/pull/87))
- issue #77 残りの未実装API 12件を追加 ([#88](https://github.com/kawagh/redi/pull/88))

## [0.0.14](https://github.com/kawagh/redi/compare/0.0.13...0.0.14) (2026-04-19)

- [add] user createコマンドを追加 ([#68](https://github.com/kawagh/redi/pull/68))
- [add] --profile オプションを追加 ([#70](https://github.com/kawagh/redi/pull/70))
- [update] issue create でformat:text,format:list の必須なカスタムフィールドに対して対応出来るようにした ([#71](https://github.com/kawagh/redi/pull/71))
- version update を対話的に実行できるようにした (refs #51 ) ([#55](https://github.com/kawagh/redi/pull/55))
- 対話フローを prompt_toolkit に統一し questionary 依存を削除 ([#73](https://github.com/kawagh/redi/pull/73))
- [add] --debug-tui で TUI スクリーン内容を YAML 形式でログ出力 ([#75](https://github.com/kawagh/redi/pull/75))

## [0.0.13](https://github.com/kawagh/redi/compare/0.0.12...0.0.13) (2026-04-18)

- #42 TUIにissueプレビューペインを追加 ([#53](https://github.com/kawagh/redi/pull/53))
- version create (prompt) ([#49](https://github.com/kawagh/redi/pull/49))
- [add] TUI で u キー押下時に issue 更新フローに入れるようにする ([#54](https://github.com/kawagh/redi/pull/54))
- TUI でコメントの追加・表示に対応 ([#58](https://github.com/kawagh/redi/pull/58))
- [add] ty による型チェックを導入 ([#59](https://github.com/kawagh/redi/pull/59))
- [add] config create サブコマンドを追加 (close #60 ) ([#61](https://github.com/kawagh/redi/pull/61))
- [refactor] config.py の他関数にも config_path 引数で DI を適用 ([#65](https://github.com/kawagh/redi/pull/65))
- [add] redi config --full で全プロファイルを表示 #63 ([#64](https://github.com/kawagh/redi/pull/64))
- init-redmine.sh の整備 (resolve #50 ) ([#66](https://github.com/kawagh/redi/pull/66))

## [0.0.12](https://github.com/kawagh/redi/compare/0.0.11...0.0.12) (2026-04-16)

- #33 サブコマンドにエイリアスを追加 ([#44](https://github.com/kawagh/redi/pull/44))
- デバッグ用のロガーを設定 ([#45](https://github.com/kawagh/redi/pull/45))
- ほぼ不変なAPIレスポンスをキャッシュする ([#46](https://github.com/kawagh/redi/pull/46))
- Github ActionsのCIを作成 ([#48](https://github.com/kawagh/redi/pull/48))

## [0.0.11](https://github.com/kawagh/redi/compare/0.0.10...0.0.11) (2026-04-15)

- issue #36 redi issue に --query_id オプションを追加 ([#37](https://github.com/kawagh/redi/pull/37))
- view --web/-w ([#38](https://github.com/kawagh/redi/pull/38))
- redi --tui ([#40](https://github.com/kawagh/redi/pull/40))

## [0.0.10](https://github.com/kawagh/redi/compare/0.0.9...0.0.10) (2026-04-14)

- profile機能を追加 ([#24](https://github.com/kawagh/redi/pull/24))
- [update;refactor] redi issue update(引数なし)でチケット一覧を候補として表示する ([#26](https://github.com/kawagh/redi/pull/26))
- [update] issue update でtime_entryを追加出来るようにした ([#28](https://github.com/kawagh/redi/pull/28))
- issue view <id> に--includeを追加 ([#30](https://github.com/kawagh/redi/pull/30))

## [0.0.9](https://github.com/kawagh/redi/compare/0.0.8...0.0.9) (2026-04-13)

- [refactor] add client.py
- [update] issue に --limit/--offset を追加
- [update] issue に --status_id/--tracker_id/--prirotiy_id を追加

## [0.0.8](https://github.com/kawagh/redi/compare/0.0.7...0.0.8) (2026-04-12)

- [update] issueにファイルをアップロードするオプションを追加
- [update] redi i view <issue_id> で添付ファイルも表示
- [update] redi attachment view <attachment_id> を実装
- [update] 添付ファイルのメタデータを更新するコマンドを実装
- [update] POST /uploads.json の呼び出しを attachment.py に移動
- [update] redi role view <role_id>
- [update] search コマンドを追加(query,limit,offsetのみ)

## [0.0.7](https://github.com/kawagh/redi/compare/0.0.6...0.0.7) (2026-04-12)

- issue create による対話的作成 ([#17](https://github.com/kawagh/redi/pull/17))
- redi issue update での対話的更新 ([#20](https://github.com/kawagh/redi/pull/20))
- wiki create/update (interactive) ([#22](https://github.com/kawagh/redi/pull/22))

## [0.0.6](https://github.com/kawagh/redi/compare/0.0.5...0.0.6) (2026-04-11)

- [update] issue create で --description を追加(エディタを起動せず作成できる)
- [update] 動作確認用のredmineのコンテナを作成、接続用の手順を記載
- [update] redi p create を追加; redi p <project_id> -> redi p view <project_id> (衝突回避)
- [update] p update を追加
- [update] wiki create で親ページの指定を任意にした
- [update] redi create/update で -d でエディタ起動せずに作成/更新できるようにした
- [update] redi wiki view と --full を追加
- [update] redi project/issue/view <non_exist_id> で見つからないメッセージを表示
- [update] redi time_entry create を追加
- [update] api_key を設定できるようにした
- [update] redmine_url を更新できるようにした
- [fix] redi config を設定がない場合に実行出来ない問題を修正した
- [update] ローカルでテスト実行する目的のredmineのセットアップスクリプトを追加
- [doc] redmineの初期化スクリプトの作成にあわせて記述を更新

## [0.0.5](https://github.com/kawagh/redi/compare/0.0.4...0.0.5) (2026-04-11)

- [fix] wrong package name
- [doc] fix language and add missing tag
- [doc] README を英語で書き直した
- [update] 日本語のREADMEを追加
- [update] tomlにeditorの設定項目を追加
- [fix] issue descriptionを空にする更新を防ぐ
- [fix] codeでファイルに書き込む前に次の処理に進むのを修正
- [update] redi i で --project_id で絞り込み
- add uv.lock diff
- [update] redi time_entry --user_id
- [update] redi custom_field を追加
- [update] custom_fields 一覧の取得に管理者権限が必要なことを扱う
- [update] redi project <id> に --include を追加
- [update] i create で --custom_fields オプションを追加
- [update] i update で --custom_fields オプションを追加
- [update] redi v に --full を追加
- [update] redi version create を作成
- [update] redi v update コマンド (対象バージョンの更新)
- [update] i update --parent_issue_id を追加(解除可)

## [0.0.4](https://github.com/kawagh/redi/compare/0.0.3...0.0.4) (2026-04-10)

- resolve #13 completion ([#15](https://github.com/kawagh/redi/pull/15))

## [0.0.3](https://github.com/kawagh/redi/compare/0.0.2...0.0.3) (2026-04-09)

- [update] uv.lock(0.0.2)
- [update] issue create を実装 #2
- [update] issue update コマンドを実装 #3
- [update] --description で 説明を渡すかエディタ記載の内容で更新できるようにした #3
- [update] issue update --description で 現在の説明を取得して表示する #3
- [update] パラメータが空の時にissue update をキャンセルする
- [fix] issue view --full が機能していないのを修正
- [update] issue view <id> --full で journals も含めるようにした
- [update] redi config(c) で設定値を出力
- [update] wiki_project_id を設定項目として追加
- [update] redi config で出力されるのをtoml形式にする
- uv run ruff format
- [update] redi wiki update で既存wikiの内容を初期値として編集できるようにした
- [dev] add taskfile.yaml

## [0.0.2](https://github.com/kawagh/redi/compare/0.0.1...0.0.2) (2026-04-08)

- [update] wiki,version コマンドでプロジェクトIDを--prject_id (-p) で指定するようにする
- [update] チケットの担当者によるフィルタリングを追加; ユーザー一覧取得を追加(プロジェクトに依らない場合は管理者権限が必要)
- [add] redi tracker でトラッカー一覧を取得
- [update] redi tracker --full で jqで処理可能な形式に出力 #11
- [add] redi issue_status でイシューのステータス一覧を表示
- [add] Enumerations(issue_priority,time_entry_activity,document_category)の一覧を表示
- [add] redi role でロール一覧を表示
- [add] redi query でカスタムクエリ一覧を取得
- [add] redi time_entry
- [update] redi users に --full を追加 #11
- [update] redi project コマンドにも --full を追加 #11
- [update] redi t, redi t <ticket_id> に --full を追加 #11
- [update] ticket -> issue
- [update] ticket -> issue
- [update] Wiki作成/更新 コマンドの実装; wiki詳細取得は w create コマンドに変更
- [update] wiki作成コマンドで親ページが見つからない場合を扱う
- [update] 閲覧をredi issue view <issue_id>, コメントをredi issue comment <issue_id> とした
- [update] コメント後にURLを表示
- [doc] show usage
- [update] editor設定をconfigコマンドで設定できるようにした
- [update] fallbackするeditorをvimにしておく
- [fix] doc

## [0.0.1](https://github.com/kawagh/redi/releases/tag/0.0.1) (2026-04-07)

- [init] uv init --package redi
- load environment
- [lib] add requests
- list projects
- fix condition
- [update] プロジェクト一覧、チケット一覧、ヘルプを表示
- [update] redi p 123 やredi t 12345 で詳細を取得する
- [update] list/read wiki
- wikiのページ一覧をツリー状に表示
- [update] チケット詳細を見やすく表示
- [doc] add README
- [refactor] ファイルを分けた
- [lib] uv add --dev ruff
- [update] チケットにコメントを追加出来るようにした
- [update] editorを起動して複数行書き込めるようにした
- 対象バージョンIDでフィルタリング resolve #1
- [update] チケット一覧表示を簡略化
- [update] 対象バージョン一覧取得 redi v <project_id>
- 設定ファイルの追加 resolve #8
- [update] redi v や redi w でtomlに設定したdefault_project_idを読み込むようにする resolve #9
- [update] 設定ファイルの項目を書き換えるコマンドを追加
- [update] プロジェクト一覧の表示を簡略化
- [update] 短縮形でないコマンドを使えるようにした resolve #10
- [refactor] cli.py に処理を移行
- [update] redi -V (redi --version) でバージョンを表示(0.0.1)

