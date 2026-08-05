# Commit Message Instructions

Follow the [Conventional Commits](https://www.conventionalcommits.org/) specification when generating commit messages.

## Format

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

## Language & Style

- Write commit messages in English.
- Subject line: imperative mood, present tense (e.g. "add", not "added" or "adds").
- Keep the subject line under 72 characters.
- Do not end the subject line with a period.

## Type

Choose the most specific type based on the actual diff:

| Type       | Purpose                        |
| ---------- | ------------------------------ |
| `feat`     | New feature                    |
| `fix`      | Bug fix                        |
| `docs`     | Documentation only             |
| `style`    | Formatting/style (no logic)    |
| `refactor` | Code refactor (no feature/fix) |
| `perf`     | Performance improvement        |
| `test`     | Add/update tests               |
| `build`    | Build system/dependencies      |
| `ci`       | CI/config changes              |
| `chore`    | Maintenance/misc               |
| `revert`   | Revert a previous commit       |

## Scope

- Scope is optional; include it only when it clearly identifies the affected area.
- Prefer scopes that match the repository layout, e.g. `skills`, `agents`, `instructions`, `apm`, `docs`, `ci`.

## Body

- Add a body when the subject line alone doesn't explain the change.
- Explain **why** the change was made, not just what changed.
- Wrap body text at a reasonable width and separate it from the subject with a blank line.

## Footer

- Reference related issues/PRs when applicable: `Closes #123`, `Refs #456`.
- For breaking changes, either append `!` after the type/scope or add a `BREAKING CHANGE:` footer describing the impact:

```
feat(skills)!: rename skill directory layout

BREAKING CHANGE: `.apm/skills/<name>/SKILL.md` replaces the old `skills/<name>.md` layout.
```

## Notes

- Never include secrets or credentials (`.env`, tokens, private keys, etc.) in the commit.
