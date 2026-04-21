#!/bin/bash
set -e

docker compose down
docker compose up -d
sleep 5
API_KEYS_OUTPUT=$(docker exec -i redi-redmine-for-test-1 rails runner - <<RUBY
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

redi config create sandbox_admin || true # profile作成がべき等でないので失敗するのを当座で防ぐ
redi config update --default_profile sandbox_admin
redi config update sandbox_admin \
    --url "http://localhost:3000" \
    --api_key "$ADMIN_API_KEY" \
    --project_id "reditest"

redi config create sandbox_developer || true
redi config update sandbox_developer \
    --url "http://localhost:3000" \
    --api_key "$DEVELOPER_API_KEY" \
    --project_id "reditest"

