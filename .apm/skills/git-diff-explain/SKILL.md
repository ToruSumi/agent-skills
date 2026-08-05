---
name: git-diff-explain
description: "Explain differences between two git branches or commits. Use when user asks to explain branch diff, compare branches, show commit differences, describe changes between refs, ブランチ差分, ブランチ比較, コミット差分, 差分説明, diff説明, or mentions /diff-explain."
allowed-tools: Bash
---

# Git Diff Explain — ブランチ・コミット間の差分説明

## Overview

2つのgit参照（ブランチ名またはコミットハッシュ）間の差分を取得し、**概要サマリー** と **ファイルごとの変更説明** を日本語で出力する。

## Input

ユーザーから以下の情報を受け取る:

- **ref1** (必須): 比較元のブランチ名またはコミットハッシュ
- **ref2** (任意): 比較先のブランチ名またはコミットハッシュ。省略時は `HEAD` を使用

例:
- `main feature/new-algo` → main と feature/new-algo の差分
- `abc1234 def5678` → 2つのコミット間の差分
- `main` → main と HEAD の差分

## Workflow

### Step 1: 参照の検証

```bash
# 指定された参照が有効か確認
git rev-parse --verify <ref1>
git rev-parse --verify <ref2>
```

無効な場合はユーザーにエラーを伝え、正しい参照を確認する。

### Step 2: コミット一覧の取得

```bash
# ref1..ref2 間のコミット一覧を取得
git log --oneline --no-merges <ref1>..<ref2>
```

コミットが0件の場合は逆方向 `<ref2>..<ref1>` も試す。両方0件なら同一参照であることを伝える。

### Step 3: 変更の規模を把握

```bash
# 変更ファイル数と変更行数の統計を取得
git diff --stat <ref1>..<ref2>
```

### Step 4: 差分の取得と分析

変更ファイル数に応じて取得方法を切り替える:

#### 少量の変更（20ファイル以下）

```bash
# 全差分を一括取得
git diff <ref1>..<ref2>
```

#### 大量の変更（21ファイル以上）

```bash
# まず変更ファイル一覧を取得
git diff --name-status <ref1>..<ref2>

# カテゴリ別（ディレクトリ別）にファイルをグループ化し、グループ単位で差分を取得
git diff <ref1>..<ref2> -- <path1> <path2> ...
```

#### 非常に大きな差分（100ファイル以上）

```bash
# 統計情報とファイル一覧で概要を把握
git diff --stat <ref1>..<ref2>
git diff --name-status <ref1>..<ref2>

# 主要な変更ファイル（追加行数が多いもの）に絞って差分取得
git diff <ref1>..<ref2> -- <重要なファイル>
```

## Output Format

以下の構造で日本語の説明を出力する:

### 1. 概要サマリー

全体の変更内容を3〜5行で要約する。何を目的とした変更か、どの領域に影響があるかを簡潔に述べる。

### 2. 変更統計

| 項目 | 値 |
|------|-----|
| コミット数 | N件 |
| 変更ファイル数 | N個 |
| 追加行数 | +N行 |
| 削除行数 | -N行 |

### 3. コミット一覧

コミットを時系列で簡潔にリストアップする（10件以上の場合は主要なもののみ）。

### 4. ファイルごとの変更説明

ディレクトリやカテゴリ別にグループ化し、各ファイルの変更内容を説明する:

| ファイル | 変更種別 | 説明 |
|----------|----------|------|
| path/to/file.py | 変更 | 〇〇の処理を△△に修正 |
| path/to/new.py | 追加 | □□機能の実装 |
| path/to/old.py | 削除 | 不要になった××を削除 |

重要な変更については、テーブルの下に補足説明を追加する。

## Safety Rules

- **読み取り専用操作のみ**: `git diff`, `git log`, `git show`, `git rev-parse`, `git branch` のみ使用
- **書き込み操作は一切行わない**: `git checkout`, `git merge`, `git rebase`, `git reset`, `git push` 等は実行しない
- リポジトリの状態を変更するコマンドは絶対に実行しない
- 機密情報（パスワード、トークン、秘密鍵等）が差分に含まれていた場合、その内容は出力しない

## Tips

- 三点ドット `ref1...ref2` を使うと、共通祖先からの差分を取得できる（マージベース比較）
- `--diff-filter=A` で追加ファイルのみ、`--diff-filter=D` で削除ファイルのみに絞れる
- バイナリファイルの差分は内容を表示できないため、ファイル名と変更種別のみ報告する
