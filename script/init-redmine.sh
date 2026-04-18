#!/bin/bash
set -e

docker compose down
docker compose up -d
sleep 5
INSTANT_API_KEY=$(docker exec -i redi-redmine-for-test-1 rails runner - <<RUBY
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
      { name: 'バージョン',               field_format: 'string' },
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

    puts User.active[0].api_key
RUBY
)
INSTANT_API_KEY=$(echo "$INSTANT_API_KEY" | tail -1)

redi config create test || true # profile作成がべき等でないので失敗するのを当座で防ぐ
redi config update --default_profile test
redi config update test \
    --url "http://localhost:3000" \
    --api_key "$INSTANT_API_KEY" \
    --project_id "reditest"

