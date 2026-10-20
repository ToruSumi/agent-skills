---
name: testrail-api
description: "TestRail API v2 を使ってプロジェクト・マイルストーン・テストランの取得やテストランのクローズなど基本操作を行うスキル。Use when: TestRail のラン一覧を見たい、テストランを完了(クローズ)したい、マイルストーンのランを確認したい、testrail api、TestRail に接続したい、trcli の代わりに API を直接呼びたい。"
argument-hint: "操作内容 (例: マイルストーン30のラン一覧、ラン210をクローズ)"
---

# TestRail API スキル

TestRail API v2 (`index.php?/api/v2/...`) を `scripts/testrail_api.sh` 経由で操作する。
trcli にはランのクローズ機能がないため、クローズなどは本スキルの API 呼び出しで行う。

## 前提確認

認証情報は環境変数から読む。未設定なら `TESTRAIL_ENV_FILE`(未指定時は `./.env`)を読み込む。

| 変数 | 説明 |
|------|------|
| `TESTRAIL_URL` | TestRail のベース URL (例: `https://xxx.testrail.io`) |
| `TESTRAIL_USER` | ログインのメールアドレス |
| `TESTRAIL_API_KEY` | API キー (TestRail の My Settings → API Keys で発行) |

認証情報はコマンド出力やログに表示しない。

## スクリプト

パス: `~/.agents/skills/testrail-api/scripts/testrail_api.sh`

| サブコマンド | 種別 | 内容 |
|--------------|------|------|
| `projects` | GET | プロジェクト一覧 (`get_projects`) |
| `milestones <project_id>` | GET | マイルストーン一覧 (`get_milestones`) |
| `runs <project_id> [milestone_id]` | GET | ラン一覧 (`get_runs`)。マイルストーン指定で絞り込み |
| `run <run_id>` | GET | ラン詳細 (`get_run`) |
| `close_run <run_id> --yes` | POST | ランをクローズ (`close_run`) |
| `request <GET\|POST> <endpoint> [json] [--yes]` | 任意 | 任意のエンドポイントを呼ぶ汎用コマンド |

`request` の endpoint は `get_case/123` のように `index.php?/api/v2/` 以降を指定する。

## 安全性の原則

- GET 操作は確認なしに実行してよい
- **POST 操作(クローズ・作成・更新など)は、実行前にユーザーに対象 ID を示して確認を取る**
- 確認後にのみ `--yes` を付けて実行する(スクリプトも `--yes` なしの書き込みを拒否する)
- 一括操作は 1 件ずつ実行し、各結果を確認する

## 手順

### 1. 接続確認

```bash
~/.agents/skills/testrail-api/scripts/testrail_api.sh projects
```

401 なら `TESTRAIL_USER` と `TESTRAIL_API_KEY` を確認する。

### 2. 対象の特定

```bash
~/.agents/skills/testrail-api/scripts/testrail_api.sh milestones 8
~/.agents/skills/testrail-api/scripts/testrail_api.sh runs 8 30
```

`runs` の応答は `{"offset","limit","size","_links","runs":[...]}` 形式。既定 250 件まで。
`runs` の各要素で `is_completed`(完了済みか)、`passed_count` / `failed_count` / `untested_count` を確認する。

### 3. 操作の実行

1. 対象 ID と内容(名前・集計)をユーザーに提示して確認を取る
2. 確認後に実行する

```bash
~/.agents/skills/testrail-api/scripts/testrail_api.sh close_run 210 --yes
```

### 4. 結果の検証

クローズ後は `run <run_id>` で `is_completed` が `true` になったことを確認する。
複数件の場合はマイルストーン単位で再取得し、未完了が残っていないか確認する。

## エラー対応

| HTTP | 対処 |
|------|------|
| 400 | ID が存在しない、またはパラメータ不正。ID を確認する |
| 401 | ユーザー名または API キーを確認する |
| 403 | 権限不足。ユーザーのロールを確認する |
| 429 | レート制限。時間をおいて再実行する |

## 拡張方法

- 新しい操作がよく必要になったら、`testrail_api.sh` に専用サブコマンドを追加し、上の表に追記する
- 1 回限りの操作は `request` コマンドで対応できる
- 参照: TestRail API ドキュメント (`https://www.gurock.com/testrail/docs/api`) のエンドポイント一覧
