---
name: lint-and-test
description: "ruff による lint・format を実施してからテストを実行するワークフロー。Use when: テスト実行, lint してからテスト, ruff + pytest, コード品質チェック, /lint-and-test"
---

# Lint & Format → Test ワークフロー

## 概要

ruff による静的解析とフォーマットを実施し、問題がなければ pytest を実行する。
lint/format エラーがある状態でテストを走らせる無駄を防ぐ。

## 手順

### 1. ruff format（フォーマット）

```bash
ruff format app/ tests/
```

- 自動的にフォーマットが適用される
- 変更があった場合はファイル名が表示される

### 2. ruff check --fix（lint + 自動修正）

```bash
ruff check --fix app/ tests/
```

- `--fix` で自動修正可能なルール違反を修正する
- 自動修正できない違反が残った場合は **ここで停止** し、ユーザーに報告する
- 報告時は違反箇所とルールコード（例: `F841`）を提示する

### 3. pytest 実行

lint が全てパスしたら pytest を実行する:

```bash
pytest
```

- `pyproject.toml` の `[tool.pytest.ini_options]` に従いカバレッジ付きで実行される
- テスト失敗があればユーザーに報告する

## 判断フロー

```
ruff format → 変更あり？ → ログ表示して続行
                ↓
ruff check --fix → エラー残存？ → 停止・報告
                ↓ (All passed)
pytest → 結果報告
```

## 注意事項

- 対象ディレクトリはデフォルトで `app/` と `tests/`
- ユーザーが特定ファイルを指定した場合はそのパスに限定する
- ruff の設定は `pyproject.toml` の `[tool.ruff]` セクションに定義済み
