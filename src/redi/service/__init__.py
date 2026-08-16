"""CLI と TUI が共有するサービス層。

Redmine への要求 (URL の組み立てとステータスコードの解釈) をここに集約し、
呼び出し元は結果の見せ方 (CLI は print / sys.exit、TUI は flash_message) だけを持つ。
"""
