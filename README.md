# agent-skills

Agent and Skills repository for AI agents

[APM (Agent Package Manager)](https://microsoft.github.io/apm/) 経由でインストールできる skills / agents / instructions / hooks を管理するリポジトリです。
このリポジトリは複数の独立したプリミティブを提供する [`.apm/` レイアウト](https://microsoft.github.io/apm/reference/package-types/#apm-package-apm-directory) を採用しています。

```text
agent-skills/
├── apm.yml
└── .apm/
    ├── skills/
    │   └── <skill-name>/
    │       └── SKILL.md
    ├── agents/
    │   └── <agent-name>.agent.md
    ├── instructions/
    │   └── <name>.instructions.md
    └── hooks/
        ├── <name>.json
        └── scripts/
            └── <script>
```

`apm install` を実行すると、`.apm/` 配下の各プリミティブが個別に消費側プロジェクトのランタイムディレクトリ
（例: `.github/skills/`, `.github/agents/`, `.github/instructions/`, `.github/hooks/`）にコピーされます。

## 追加方法

- **Skill**: `.apm/skills/<skill-name>/SKILL.md` を作成（関連アセットは同じディレクトリ配下に同梱可能）
- **Agent**: `.apm/agents/<agent-name>.agent.md` を作成
- **Instructions**: `.apm/instructions/<name>.instructions.md` を作成
- **Hooks**: `.apm/hooks/<name>.json` を作成（補助スクリプトは `.apm/hooks/scripts/` 配下に配置）
