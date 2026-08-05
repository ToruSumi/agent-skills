---
name: jujutsu
description: 'Use when the user wants to inspect, edit, commit, sync, or manage changes with Jujutsu (jj). Triggers on jujutsu, jj, bookmark, fetch, push, commit, log, diff, status, squash, amend, describe, restore, split, undo, rebase, operation, remote, or workspace-change workflows.'
allowed-tools: Bash
---

# Jujutsu Workflow

## Overview

`jj` を使って作業ツリー、bookmark、Git リモート同期を安全に扱うための skill。
まず状態を確認し、次に差分と操作履歴を見て、必要な変更だけを実行する。

## Core Workflow

### 1. 状態確認

作業前に現在の状態を把握する。

```bash
jj status
jj log -r @..@
jj diff
```

必要に応じて以下も確認する。

```bash
jj log -n 10
jj op log -n 10
jj bookmark list
```

### 2. 変更の把握

- どのファイルが変わっているか確認する
- どの変更をまとめるか判断する
- 未完了の変更が他に混ざっていないか確認する
- どの bookmark がどの revision を指しているか確認する

### 3. 操作の選択

目的に応じて、最小限の `jj` コマンドを選ぶ。

| 目的 | 主なコマンド |
|------|--------------|
| 変更確認 | `jj status`, `jj diff`, `jj show` |
| 新しい変更を作る | `jj new` |
| 既存変更を修正する | `jj edit`, `jj describe`, `jj squash`, `jj amend` |
| 変更を分割する | `jj split` |
| bookmark を動かす | `jj bookmark move`, `jj bookmark set`, `jj bookmark advance` |
| bookmark を追跡する | `jj bookmark track`, `jj bookmark untrack` |
| Git から取得する | `jj git fetch` |
| Git に送る | `jj git push` |
| 取り消す | `jj restore`, `jj undo` |
| 履歴を見る | `jj log`, `jj op log` |

### 4. 編集と整理

よくある使い方。

```bash
# 現在の変更点を説明付きで整える
jj describe -m "<summary>"

# 現在の変更に新しい親を作る
jj new

# 変更を現在の変更に取り込む
jj squash

# 内容を1つの変更として整える
jj amend
```

bookmark を使う代表的な流れ。

```bash
# 現在の change を bookmark に結び付ける
jj bookmark set <name> -r @

# bookmark を別の revision に移動する
jj bookmark move <name> -r <revision>

# 複数の bookmark を対象 revision へ追随させる
jj bookmark advance <name> -r <revision>
```

Git リモートとの同期。

```bash
# リモートの最新状態を取り込む
jj git fetch

# 特定のリモートから取得する
jj git fetch --remote origin

# bookmark をリモートへ送る
jj git push --bookmark <name>

# tracked bookmark をまとめて送る
jj git push --tracked
```

bookmark の名前と追跡状態が不明なときは、先に `jj bookmark list` と `jj git fetch` を確認する。

### 5. 安全な確認

変更後は必ず再確認する。

```bash
jj status
jj diff
jj log -r @
jj bookmark list
```

## Decision Rules

- まず `jj status` と `jj diff` を見る
- 変更が混ざっている場合は、先に分割できるか判断する
- 履歴の修正で済むなら、新しい変更を増やしすぎない
- 破壊的な操作は避け、必要なら理由を確認する
- リモートとの差分が絡むときは、先に `jj git fetch` で見え方を更新する
- bookmark を動かす前に、対象 revision が本当に正しいか `jj log` で確認する
- push 前に tracked 状態を確認し、必要なら `jj bookmark track` を先に行う

## Completion Checks

作業完了時は次を満たすこと。

- `jj status` が期待通りである
- `jj diff` に不要な変更が残っていない
- 必要なら `jj log -r @` で変更内容を再確認できる
- `jj bookmark list` で bookmark の位置が意図どおりである
- リモート同期がある場合は、`jj git fetch` 後の状態と `jj git push` の対象が一致している

## Safety Rules

- リポジトリ状態を不用意に変える前に、必ず現在の差分を確認する
- `jj undo` や `jj restore` の対象は慎重に確認する
- 重要な変更を失う可能性がある操作は、実行前に影響範囲を明示する
- `jj git push` は Git 側の remote bookmark を更新するため、対象 bookmark を明示する
- `jj git fetch` 後に bookmark が競合したら、`jj bookmark list` で ? が付いた bookmark を確認し、`jj bookmark set <name> -r <revision>` で解消する

## Tips

- `jj` は `git` と違い、変更単位を柔軟に分けたりまとめたりしやすい
- まず状態確認、次に整理、最後に説明、の順で進めると事故が少ない
- `bookmark` は Git の branch に近い役割を持つので、共有したい変更は bookmark を基準に扱うとわかりやすい
- Git 連携では `jj git fetch` で取り込み、`jj git push` で公開する、の順で考えると整理しやすい