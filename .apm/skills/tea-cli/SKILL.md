---
name: tea-cli
description: 'Gitea CLI tea を使って OAuth ログイン、Issue/PR 操作、レビュー補助を行う手順。Use when: tea, gitea cli, issue 作成, pull request 作成, checkout, merge, comment, API 呼び出し。'
argument-hint: 'やりたい操作を指定: login|issues|pulls|review|merge|repo|api'
---

# Gitea tea CLI ワークフロー

## このスキルが行うこと

`tea` のヘルプと公式情報を元に、以下を安全に実行するための手順を提供する。

- 初期セットアップ（ログイン追加、デフォルト切替、疎通確認）
- Issue 運用（一覧、作成、編集、クローズ/再オープン）
- Pull Request 運用（一覧、作成、checkout、レビュー、マージ）
- 補助操作（コメント投稿、Web UI オープン、API 直接呼び出し）
- 単一インスタンス前提のシンプル運用

## いつ使うか

- Gitea 上の作業をブラウザ中心から CLI 中心に移したいとき
- CI 前に PR を素早く作成・確認・マージしたいとき
- スクリプト化しやすい `json/tsv` 出力で連携したいとき

## 前提

- `tea` がインストール済みであること
- Gitea のアクセストークンを発行できること
- 対象リポジトリがローカルに clone 済み、または `--repo` で指定可能であること

## 手順

### 1. 初期確認

1. `tea --version` と `tea --help` を実行して利用可能コマンドを確認する。
2. 既存ログインを確認する: `tea logins list`。
3. ログインが無ければ OAuth で作成する: `tea logins add --oauth`。

Decision:
- 基本: `tea logins add --oauth`
- OAuth が使えない環境のみ: `tea logins add --name <name> --url <url> --token <token>`

### 2. ログイン検証と既定化

1. 必要なら既定を設定: `tea logins default <name>`。
2. 認証確認: `tea whoami`。
3. 以後は単一インスタンス前提で通常運用する（`--login` 明示は原則不要）。

### 3. リポジトリ文脈の決定

1. 対象リポジトリ配下で実行できるなら、そのまま実行する（`$PWD` 文脈を利用）。
2. 別パス/別リポジトリ対象なら `--repo <path|owner/repo>` を使う。
3. 必要に応じて `--remote <name>` を使う。

Decision:
- ローカル作業リポジトリで実行: `--repo` 省略
- 外部対象を明示: `--repo` を必ず指定

### 4. Issue ワークフロー

1. 一覧: `tea issues list --state open`
2. フィルタ: `--keyword`, `--labels`, `--assignee`, `--milestones`
3. 作成: `tea issues create -t "<title>" -d "<body>"`
4. 更新: `tea issues edit <index> --title ... --description ...`
5. 状態変更: `tea issues close <index>` / `tea issues reopen <index>`
6. 補助: `tea open <index>` で Web UI を開く

### 5. Pull Request ワークフロー

1. 一覧: `tea pulls list --state open`
2. 作成: `tea pulls create --head <branch> --base <base> -t "<title>" -d "<body>"`
3. ローカル確認: `tea pulls checkout <index> --branch`
4. レビュー/承認: `tea pulls review <index>` / `tea pulls approve <index>` / `tea pulls reject <index>`
5. マージ: `tea pulls merge <index> --style merge`（基本）
6. 後片付け: `tea pulls clean <index>`

### 6. コメント・API・出力連携

1. コメント追加: `tea comment <index> "<comment>"`
2. API 呼び出し: `tea api <path>`
3. 外部連携向け出力: `--output json|tsv|csv|yaml|table|simple`

## 品質チェック

- `tea whoami` が期待ユーザーを返す
- 実行対象が意図した repo である（`--repo` の指定漏れがない）
- PR 作成時に `--head` と `--base` が期待ブランチである
- マージ前に `tea pulls <index> --comments` などで最終確認し、`--style merge` を使った
- 自動化用途では `--output json` を使い、パース前提を固定した

## トラブルシュート

- TLS 検証で失敗する場合: 検証環境に限って `--insecure` を検討
- 認証失敗時: OAuth フロー再実行、必要ならトークン認証にフォールバック
- サブコマンド仕様差異: `tea <command> --help` を最優先の一次情報とする

## 参照

- [コマンド早見表](./references/tea-command-reference.md)
