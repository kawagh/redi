#!/bin/bash
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

    puts User.active[0].api_key
RUBY
)
INSTANT_API_KEY=$(echo "$INSTANT_API_KEY" | tail -1)

redi config create test
redi config update --default_profile test
redi config update test \
    --url "http://localhost:3000" \
    --api_key "$INSTANT_API_KEY"

