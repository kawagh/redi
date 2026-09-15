#!/bin/bash
set -e

# 引数で対象の Redmine バージョンを選ぶ (例: ./script/init-redmine.sh 7.0)
# バージョンごとにサービス・ポート・profile を分けているため、
# 他バージョンのコンテナを落とさずに初期化できる
REDMINE_VERSION="${1:-6.1}"
case "$REDMINE_VERSION" in
6.1) PORT=3061 ;;
7.0) PORT=3070 ;;
*)
    echo "not a target redmine version: $REDMINE_VERSION (target: 6.1, 7.0)" >&2
    exit 1
    ;;
esac
SERVICE="redmine-for-test-${REDMINE_VERSION}"
URL="http://localhost:${PORT}"
ADMIN_PROFILE="sandbox_admin_${REDMINE_VERSION}"
DEVELOPER_PROFILE="sandbox_developer_${REDMINE_VERSION}"

# 作り直した Redmine に対して古いキャッシュを参照しないよう消す
rm -rf "$HOME/.cache/redi/localhost_${PORT}"

docker compose down "$SERVICE"
docker compose up -d "$SERVICE"
sleep 5
API_KEYS_OUTPUT=$(docker compose exec -T "$SERVICE" rails runner - <<RUBY
    # 初期生成される管理者のパスワードを変更
    admin = User.find_by(login: 'admin')
    admin.password = 'adminadmin'
    admin.password_confirmation = 'adminadmin'
    admin.must_change_passwd = false
    admin.save!

    # 初期設定を読み込み
    Redmine::DefaultData::Loader.load('ja')

    Setting.rest_api_enabled = '1'

    # テスト用プロジェクトを作成
    project = Project.find_or_initialize_by(identifier: 'reditest')
    project.name = 'reditestプロジェクト'
    project.description = 'rediのtest用に作成されたプロジェクト'
    project.is_public = true
    project.enabled_module_names = %w[issue_tracking time_tracking news wiki files]
    project.save!

    # カスタムフィールドを作成（全プロジェクト・バグトラッカーのみに適用）
    cf_defs = [
      {
        name: 'バージョン',
        field_format: 'string',
        description: 'redi --version の出力',
      },
    ]
    bug_tracker_ids = Tracker.where(name: 'バグ').pluck(:id)
    cf_defs.each do |attrs|
      cf = IssueCustomField.find_or_initialize_by(name: attrs[:name])
      cf.assign_attributes(attrs)
      cf.is_for_all = true
      cf.is_required = true
      cf.tracker_ids = bug_tracker_ids
      cf.save!
    end

    # reditest プロジェクトにのみ適用するカスタムフィールドを作成
    # (redmine 7.0 の custom field API が返す projects の検証に使う)
    project_cf = IssueCustomField.find_or_initialize_by(name: 'プロジェクト限定メモ')
    project_cf.field_format = 'string'
    project_cf.description = 'reditest プロジェクトにのみ適用されるカスタムフィールド'
    project_cf.is_for_all = false
    project_cf.is_required = false
    project_cf.tracker_ids = bug_tracker_ids
    project_cf.project_ids = [project.id]
    project_cf.save!

    # sandbox_developer ユーザーを作成
    developer = User.find_or_initialize_by(login: 'sandbox_developer')
    developer.firstname = 'Sandbox'
    developer.lastname = 'Developer'
    developer.mail = 'sandbox_developer@example.com'
    developer.password = 'sandboxdeveloper'
    developer.password_confirmation = 'sandboxdeveloper'
    developer.must_change_passwd = false
    developer.status = User::STATUS_ACTIVE
    developer.save!

    # sandbox_developer を reditest プロジェクトのメンバーに追加（開発者ロール）
    developer_role = Role.find_by(name: '開発者')
    if developer_role
      member = Member.find_or_initialize_by(user_id: developer.id, project_id: project.id)
      member.role_ids = [developer_role.id]
      member.save!
    end

    # reditest 以外のプロジェクトを作成
    # (他プロジェクト固有のクエリを query_id に渡したときの挙動を確かめるために使う)
    other_project = Project.find_or_initialize_by(identifier: 'reditother')
    other_project.name = 'reditest以外のプロジェクト'
    other_project.description = 'rediのtest用に作成された、reditest以外のプロジェクト'
    other_project.is_public = true
    other_project.enabled_module_names = %w[issue_tracking]
    other_project.save!

    # カスタムクエリを作成
    # Redmine の REST API にクエリの作成系エンドポイントが無い (/queries.json は GET のみ) ため、
    # クエリまわりの E2E はここで仕込んだものを redi query list で引いて検証する。
    # 検証したい軸ごとに 1 件ずつ用意する。
    feature_and_support_tracker_ids = Tracker.where(name: %w[機能 サポート]).pluck(:id).map(&:to_s)
    # 実行のたびに増えるイシューに左右されないよう、E2E が作る件名だけを対象にする
    e2e_subject_filter = ['subject', '~', ['e2e-query']]
    # トラッカーの OR は TUI のフィルタモーダル (単一選択) では表現できないので、
    # query_id を渡したときだけ効く条件として使う
    tracker_or_filter = ['tracker_id', '=', feature_and_support_tracker_ids]
    query_defs = [
      # 全プロジェクトで見えるグローバルクエリ
      {
        name: 'e2e 全プロジェクト (機能 or サポート)',
        project: nil,
        visibility: Query::VISIBILITY_PUBLIC,
        filters: [e2e_subject_filter, tracker_or_filter],
      },
      # 現在プロジェクトの選択肢に出るプロジェクト固有のクエリ
      {
        name: 'e2e reditest 限定 (機能 or サポート)',
        project: project,
        visibility: Query::VISIBILITY_PUBLIC,
        filters: [e2e_subject_filter, tracker_or_filter],
      },
      # 他プロジェクト固有のクエリ (reditest のイシュー一覧に渡すと Redmine が 404 を返す)
      {
        name: 'e2e 別プロジェクト限定 (reditother)',
        project: other_project,
        visibility: Query::VISIBILITY_PUBLIC,
        filters: [e2e_subject_filter],
      },
      # 作成者 (admin) にしか見えない非公開クエリ
      {
        name: 'e2e 非公開 (作成者のみ)',
        project: nil,
        visibility: Query::VISIBILITY_PRIVATE,
        filters: [e2e_subject_filter],
      },
    ]
    query_defs.each do |attrs|
      query = IssueQuery.find_or_initialize_by(name: attrs[:name])
      query.project = attrs[:project]
      query.user = admin
      query.visibility = attrs[:visibility]
      query.filters = {}
      attrs[:filters].each { |field, operator, values| query.add_filter(field, operator, values) }
      query.column_names = %i[id tracker status subject]
      query.save!
    end

    puts "ADMIN_KEY=#{admin.api_key}"
    puts "DEVELOPER_KEY=#{developer.api_key}"
RUBY
)
ADMIN_API_KEY=$(echo "$API_KEYS_OUTPUT" | grep '^ADMIN_KEY=' | tail -1 | cut -d= -f2)
DEVELOPER_API_KEY=$(echo "$API_KEYS_OUTPUT" | grep '^DEVELOPER_KEY=' | tail -1 | cut -d= -f2)

# profile作成がべき等でないので失敗するのを当座で防ぐ。
redi config create "$ADMIN_PROFILE" --url "$URL" --api_key "$ADMIN_API_KEY" || true
redi config update --default_profile "$ADMIN_PROFILE"
redi config update "$ADMIN_PROFILE" \
    --url "$URL" \
    --api_key "$ADMIN_API_KEY" \
    --project_id "reditest"

redi config create "$DEVELOPER_PROFILE" --url "$URL" --api_key "$DEVELOPER_API_KEY" || true
redi config update "$DEVELOPER_PROFILE" \
    --url "$URL" \
    --api_key "$DEVELOPER_API_KEY" \
    --project_id "reditest"

