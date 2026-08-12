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
    project.enabled_module_names = %w[issue_tracking time_tracking news wiki]
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

    puts "ADMIN_KEY=#{admin.api_key}"
    puts "DEVELOPER_KEY=#{developer.api_key}"
RUBY
)
ADMIN_API_KEY=$(echo "$API_KEYS_OUTPUT" | grep '^ADMIN_KEY=' | tail -1 | cut -d= -f2)
DEVELOPER_API_KEY=$(echo "$API_KEYS_OUTPUT" | grep '^DEVELOPER_KEY=' | tail -1 | cut -d= -f2)

redi config create "$ADMIN_PROFILE" || true # profile作成がべき等でないので失敗するのを当座で防ぐ
redi config update --default_profile "$ADMIN_PROFILE"
redi config update "$ADMIN_PROFILE" \
    --url "$URL" \
    --api_key "$ADMIN_API_KEY" \
    --project_id "reditest"

redi config create "$DEVELOPER_PROFILE" || true
redi config update "$DEVELOPER_PROFILE" \
    --url "$URL" \
    --api_key "$DEVELOPER_API_KEY" \
    --project_id "reditest"

