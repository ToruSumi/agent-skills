# agent-skills

Agent and Skills repository for AI agents

[APM (Agent Package Manager)](https://microsoft.github.io/apm/) 経由でインストールできる skills / agents / instructions / hooks を管理するリポジトリです。
このリポジトリは複数の独立したプリミティブを提供する [`.apm/` レイアウト](https://microsoft.github.io/apm/reference/package-types/#apm-package-apm-directory) を採用しています。

```text
agent-skills/
├── apm.yml
├── .apm/
│   ├── skills/<skill-name>/SKILL.md
│   ├── instructions/<name>.instructions.md
│   └── hooks/
│       ├── <name>.json
│       └── scripts/<script>
└── packages/
    ├── copilot/
    │   ├── apm.yml
    │   └── .apm/agents/<agent-name>.agent.md
    └── opencode/
        ├── apm.yml
        └── .apm/agents/<agent-name>.agent.md
```

`apm install` を実行すると、`.apm/` 配下の各プリミティブが個別に消費側プロジェクトのランタイムディレクトリ
（例: `.agents/skills/`, `.github/agents/`, `.github/instructions/`, `.github/hooks/`）に展開されます。

## インストール

APM 0.34.0 と OpenCode V2 を基準にしています。OpenCode V1 は対象外です。
`<tag-or-sha>` は、この変更を含む公開済みタグまたはコミット SHA に置き換えてください。

```bash
apm install 'ToruSumi/agent-skills#<tag-or-sha>' --target copilot,opencode
apm compile --target opencode --dry-run
apm compile --target opencode
```

OpenCode 向け instructions はインストールだけでは `AGENTS.md` に反映されないため、
コンパイルが必要です。既存の手書き `AGENTS.md` がある場合は、dry-run の結果を確認し、
[APM の managed-section モード](https://microsoft.github.io/apm/producer/compile/#managed-section-mode)
で既存内容を保持してください。

Copilot のみを利用する場合は `--target copilot` を指定します。
エージェントの配布先は依存ごとの `targets` で制限しており、両ターゲットを指定しても混在しません。

| ターゲット | エージェントのソース | 展開先 |
| --- | --- | --- |
| Copilot | `packages/copilot/.apm/agents/` | `.github/agents/*.agent.md` |
| OpenCode V2 | `packages/opencode/.apm/agents/` | `.opencode/agents/*.md` |

OpenCode 版は `permissions` 形式を使用し、モデルはセッションから継承します。
Architect は設計書だけを編集でき、`implementer` サブエージェントへ実装を委譲します。
Jira 操作はシェル承認を要求し、書き込み前の明示承認もエージェントに指示しています。

## 更新と警告

- 既存の導入先でも、上記コマンドの `<tag-or-sha>` に更新先のリビジョンを指定して再導入し、
    OpenCode 向けコンパイルを再実行してください。ロック済みの古いリビジョンは自動で更新されません。
- 外部依存は `apm.yml` の `ref` で固定しています。更新時は `ref` と `apm.lock.yaml` を同期します。
    Gitea は APM 0.34.0 が64桁 SHA をブランチ名として扱うため、取得可能なタグ `v1.2.0` を使用しています。
    タグは付け替え可能なため、利用先でもロックファイルを管理してください。
- CI では利用先の `apm.lock.yaml` をコミットし、`apm install --frozen --target copilot,opencode` を使用します。
- `Could not fetch org policy` は、インストール先の `origin` から推定した取得先への接続エラーです。
    取得先、VPN・プロキシ、HTTPS 接続、認証を確認してください。組織ポリシーを利用しない運用だと
    確認できた場合のみ `--no-policy` を追加できます。リポジトリ側では無効化しません。
- `Skipped inactive experimental resolver` は未使用の実験的ターゲットをスキップした情報表示です。
    警告を消すために実験機能を有効化する必要はありません。
- 既存ファイルの競合が報告された場合は内容を比較してください。無条件に `--force` を使わず、
    手動編集を保持したうえで APM 管理ファイルを更新してください。

## 追加方法

- **Skill**: `.apm/skills/<skill-name>/SKILL.md` を作成（関連アセットは同じディレクトリ配下に同梱可能）
- **Agent**: `packages/<copilot|opencode>/.apm/agents/<agent-name>.agent.md` を作成。
    両環境を対象とする場合は、それぞれの形式で定義します。APM は frontmatter を自動変換しません。
- **Instructions**: `.apm/instructions/<name>.instructions.md` を作成
- **Hooks**: `.apm/hooks/<name>.json` を作成（補助スクリプトは `.apm/hooks/scripts/` 配下に配置）

## 検証

```bash
uv run --with apm-cli==0.34.0 python -m unittest discover -s tests -v
```

テストは依存の固定、配布先の分離、リモート導入時の親リビジョン継承、
frontmatter、Architect の委譲先を検証します。
OpenCode の読み込み確認は、一時導入先で `opencode debug agents --standalone` を実行します。
