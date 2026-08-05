# tea コマンド早見表

このファイルは `tea --help` 系の確認結果と、公式 README/Installation 情報を要約した参照メモ。

## 主要カテゴリ

- Entities: `issues`, `pulls`, `labels`, `milestones`, `releases`, `repos`, `branches`, `actions`, `webhooks`, `comment`
- Helpers: `open`, `notifications`, `clone`, `api`
- Setup: `logins`, `logout`
- Misc: `whoami`, `admin`

## 初期設定

```bash
tea logins list
tea logins add --oauth
tea whoami
```

非対話設定例:

```bash
tea logins add --name corp --url https://gitea.example.com --token "$GITEA_SERVER_TOKEN"
```

## Issue 運用

```bash
tea issues list --state open
tea issues create -t "Bug: ..." -d "詳細"
tea issues edit 123 --title "new title"
tea issues close 123
tea issues reopen 123
```

## PR 運用

```bash
tea pulls list --state open
tea pulls create --head feature/x --base main -t "feat: ..." -d "..."
tea pulls checkout 45 --branch
tea pulls review 45
tea pulls approve 45
tea pulls merge 45 --style merge
```

## コメント/補助

```bash
tea comment 45 "LGTM"
tea open 45
tea api /repos/{owner}/{repo}/issues
```

## 実運用でよく使う共通オプション

- `--repo, -r`: 対象 repo を明示（path または owner/repo）
- `--remote, -R`: remote から login を解決
- `--login, -l`: login を明示（必要時のみ）
- `--output, -o`: `simple|table|csv|tsv|yaml|json`

## 公式情報（Web）

- 公式リポジトリ: https://gitea.com/gitea/tea
- README の examples 節: login, pulls, milestone, open, actions, webhooks の実例あり
- Installation の login 節: トークン認証（`tea logins add`）と OAuth についての説明あり
- 補足: `tea completion <shell>` と `tea man` は hidden command として案内される
