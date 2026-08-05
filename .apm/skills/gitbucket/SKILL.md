---
name: gitbucket
description: "GitBucket REST API経由でリポジトリ情報取得・Issue作成・PR操作・ユーザー管理などを行うスキル。Use when: GitBucketのissueを作りたい、リポジトリ一覧を取得したい、PRをマージしたい、gitbucket api、GitBucketに接続したい、issue作成、pull request操作、ブランチ一覧、コラボレーター管理。"
argument-hint: "操作内容 (例: issue一覧取得、issue作成、PR一覧取得)"
---

# GitBucket API スキル

GitBucketのREST API (`/api/v3`) を使って、Issue・PR・リポジトリ・ユーザー・グループの操作を行う。

## 前提確認

作業開始前に以下を確認する。不明な場合はユーザーに質問する。

| 項目 | 説明 | 例 |
|------|------|-----|
| `GITBUCKET_URL` | GitBucketのベースURL | `http://localhost:8080` |
| `GITBUCKET_TOKEN` | 個人アクセストークン | Account Settings → Applications で発行 |
| `OWNER` | リポジトリオーナー（ユーザー名またはグループ名） | `root` / `myorg` |
| `REPO` | リポジトリ名 | `my-project` |

## 認証方法

```bash
# トークン認証（推奨）
-H "Authorization: token $GITBUCKET_TOKEN"

# Basic認証
-u "username:password"
```

## APIエンドポイント一覧

### Issues

| 操作 | メソッド | パス |
|------|---------|------|
| Issue一覧取得 | GET | `/api/v3/repos/{owner}/{repo}/issues` |
| Issue詳細取得 | GET | `/api/v3/repos/{owner}/{repo}/issues/{number}` |
| Issue作成 | POST | `/api/v3/repos/{owner}/{repo}/issues` |
| Issueコメント一覧 | GET | `/api/v3/repos/{owner}/{repo}/issues/{number}/comments` |
| Issueコメント作成 | POST | `/api/v3/repos/{owner}/{repo}/issues/{number}/comments` |
| ラベル一覧 | GET | `/api/v3/repos/{owner}/{repo}/labels` |
| ラベル作成 | POST | `/api/v3/repos/{owner}/{repo}/labels` |
| Issueにラベル追加 | POST | `/api/v3/repos/{owner}/{repo}/issues/{number}/labels` |
| マイルストーン一覧 | GET | `/api/v3/repos/{owner}/{repo}/milestones` |
| マイルストーン作成 | POST | `/api/v3/repos/{owner}/{repo}/milestones` |

### Pull Requests

| 操作 | メソッド | パス |
|------|---------|------|
| PR一覧取得 | GET | `/api/v3/repos/{owner}/{repo}/pulls` |
| PR詳細取得 | GET | `/api/v3/repos/{owner}/{repo}/pulls/{number}` |
| PR作成 | POST | `/api/v3/repos/{owner}/{repo}/pulls` |
| PRマージ確認 | GET | `/api/v3/repos/{owner}/{repo}/pulls/{number}/merge` |
| PRマージ | PUT | `/api/v3/repos/{owner}/{repo}/pulls/{number}/merge` |
| PRコミット一覧 | GET | `/api/v3/repos/{owner}/{repo}/pulls/{number}/commits` |

### Repositories

| 操作 | メソッド | パス |
|------|---------|------|
| 認証ユーザーのリポジトリ一覧 | GET | `/api/v3/user/repos` |
| ユーザーのリポジトリ一覧 | GET | `/api/v3/users/{username}/repos` |
| グループのリポジトリ一覧 | GET | `/api/v3/orgs/{org}/repos` |
| リポジトリ詳細 | GET | `/api/v3/repos/{owner}/{repo}` |
| リポジトリ作成（個人） | POST | `/api/v3/user/repos` |
| リポジトリ作成（グループ） | POST | `/api/v3/orgs/{org}/repos` |
| ブランチ一覧 | GET | `/api/v3/repos/{owner}/{repo}/branches` |
| コミット一覧 | GET | `/api/v3/repos/{owner}/{repo}/commits` |
| ファイル内容取得 | GET | `/api/v3/repos/{owner}/{repo}/contents/{path}` |
| コラボレーター一覧 | GET | `/api/v3/repos/{owner}/{repo}/collaborators` |
| コラボレーター追加 | PUT | `/api/v3/repos/{owner}/{repo}/collaborators/{username}` |

### Users / Groups

| 操作 | メソッド | パス |
|------|---------|------|
| 認証ユーザー情報取得 | GET | `/api/v3/user` |
| ユーザー情報取得 | GET | `/api/v3/users/{username}` |
| ユーザー一覧 | GET | `/api/v3/users` |
| グループ一覧（自分） | GET | `/api/v3/user/orgs` |
| グループ一覧（全体） | GET | `/api/v3/organizations` |
| グループ詳細 | GET | `/api/v3/orgs/{org}` |

## コマンド例

### 接続確認

```bash
curl -s -H "Authorization: token $GITBUCKET_TOKEN" \
  "$GITBUCKET_URL/api/v3/user" | jq .
```

### Issue一覧取得

```bash
curl -s -H "Authorization: token $GITBUCKET_TOKEN" \
  "$GITBUCKET_URL/api/v3/repos/$OWNER/$REPO/issues?state=open" | jq .
```

### Issue作成

```bash
curl -s -X POST \
  -H "Authorization: token $GITBUCKET_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "バグ報告: ○○が動作しない",
    "body": "## 概要\n\n## 再現手順\n\n## 期待する動作",
    "labels": ["bug"]
  }' \
  "$GITBUCKET_URL/api/v3/repos/$OWNER/$REPO/issues" | jq .
```

### PR作成

```bash
curl -s -X POST \
  -H "Authorization: token $GITBUCKET_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "feature: 新機能追加",
    "body": "## 変更概要\n\n",
    "head": "feature-branch",
    "base": "main"
  }' \
  "$GITBUCKET_URL/api/v3/repos/$OWNER/$REPO/pulls" | jq .
```

### リポジトリ一覧取得

```bash
curl -s -H "Authorization: token $GITBUCKET_TOKEN" \
  "$GITBUCKET_URL/api/v3/user/repos" | jq '[.[] | {name, description, private}]'
```

## 手順

### 1. 環境確認・設定

1. `GITBUCKET_URL`・`GITBUCKET_TOKEN`・`OWNER`・`REPO` を確認する
2. 接続確認コマンドを実行してAPIが疎通できることを確認する
3. 疎通できない場合はURLとトークンを再確認する

### 2. 操作実行

ユーザーの要求に応じて上記のエンドポイント一覧から適切なAPIを選択し、curlコマンドを組み立てて実行する。

**安全性の原則:**
- GET操作（読み取り）は確認なしに実行してよい
- POST/PUT/DELETE操作（書き込み・削除）は実行前にユーザーに確認する
- トークンやパスワードはコマンド出力に表示しない

### 3. 結果処理

- JSONレスポンスは `jq` でパースして表示する
- エラー時はHTTPステータスコードとメッセージを確認する
- `401 Unauthorized` → トークンを確認
- `404 Not Found` → オーナー名・リポジトリ名を確認
- `422 Unprocessable Entity` → リクエストボディのパラメータを確認

## トークン発行手順

1. GitBucketにログインする
2. 右上のアイコン → **Account Settings** を開く
3. **Applications** タブを選択する
4. **Personal Access Tokens** セクションで **Generate new token** をクリックする
5. Token descriptionを入力してトークンを生成する
6. 表示されたトークンを安全な場所に保存する（再表示されない）
