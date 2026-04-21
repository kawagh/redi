---
name: dogfooding-redi
description: redi を使用して見つけた課題・機能要望を `redi issue create` で Redmine に起票する
---

- ユーザーが指定した--profile `profile_name`でrediコマンドを使用してください
- 重複起票を防ぐため`redi issue`で現在起票されているチケットを把握してください
- バグは以下のようにして起票出来ます
    - `redi issue create <title> --description <description> --custom_field "1=$(redi -V | awk '{print $2}')"
    - 再現方法をコマンド実行可能な形で記載してください
- 機能要望は以下のように起票出来ます
    - `redi issue create <title> --description <description> --tracker_id 2
