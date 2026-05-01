#!/bin/bash
set -e

docker compose down redmine-for-demo
docker compose up -d redmine-for-demo
sleep 5
API_KEYS_OUTPUT=$(docker exec -i redi-redmine-for-demo-1 rails runner - <<RUBY
    # 初期生成される管理者のパスワードを変更
    admin = User.find_by(login: 'admin')
    admin.password = 'adminadmin'
    admin.password_confirmation = 'adminadmin'
    admin.must_change_passwd = false
    admin.save!

    # 初期設定を読み込み
    Redmine::DefaultData::Loader.load('en')

    Setting.rest_api_enabled = '1'

    # テスト用プロジェクトを作成
    project = Project.find_or_initialize_by(identifier: 'redidemo')
    project.name = 'redidemo'
    project.description = 'project for redi demo'
    project.is_public = true
    project.enabled_module_names = %w[issue_tracking time_tracking news wiki]
    project.save!

    puts "ADMIN_KEY=#{admin.api_key}"
RUBY
)
ADMIN_API_KEY=$(echo "$API_KEYS_OUTPUT" | grep '^ADMIN_KEY=' | tail -1 | cut -d= -f2)

redi config create demo_admin || true # profile作成がべき等でないので失敗するのを当座で防ぐ
redi config update --default_profile demo_admin
redi config update demo_admin \
    --url "http://localhost:3002" \
    --api_key "$ADMIN_API_KEY" \
    --project_id "redidemo"

# create sample data for demo
redi issue create SampleBug --description ""
redi issue create SampleIssue --description "" --tracker_id 2
redi issue create "[doc] add demo GIF" --tracker_id 2 --description "
- add demo.gif to README.md
- define task to update demo.gif
- prepare new redmine service and use it
"
