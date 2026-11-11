#!/usr/bin/env python3
"""PreToolUse guardrail hook for enforcing company and project safety policies.

Categories enforced:
1. Secrets & credential protection (deny read/write/shell access, allow templates)
2. Destructive shell commands & privilege escalation (deny catastrophic, ask DB/infra reset)
3. Dangerous Git / Jujutsu operations & hook bypass (deny force/--no-verify, ask protected push/reset)
4. Guardrail & CI configuration self-tampering protection (deny hook edits, ask CI edits)
"""

from __future__ import annotations

import json
import posixpath
import re
import shlex
import sys
from typing import Any, Literal

Decision = Literal["deny", "ask"]

# ---------------------------------------------------------------------------
# Tool classification
# ---------------------------------------------------------------------------

SHELL_TOOLS = {
    "bash",
    "sh",
    "shell",
    "powershell",
    "pwsh",
    "cmd",
    "terminal",
    "run_in_terminal",
    "run_terminal_cmd",
    "execute_command",
    "exec",
}

WRITE_TOOLS = {
    "write",
    "edit",
    "multiedit",
    "multi_edit",
    "create",
    "create_file",
    "write_file",
    "edit_file",
    "replace_string_in_file",
    "insert_edit_into_file",
    "str_replace_editor",
    "apply_patch",
    "edit_notebook_file",
    "notebookedit",
    "delete_file",
    "remove_file",
}

READ_TOOLS = {
    "read",
    "view",
    "read_file",
    "readfile",
    "grep",
    "rg",
    "grep_search",
    "glob",
    "file_search",
    "list_dir",
}

# ---------------------------------------------------------------------------
# File path policy definitions
# ---------------------------------------------------------------------------

SAFE_TEMPLATE_SUFFIXES = (
    ".example",
    ".sample",
    ".template",
    ".dist",
    ".defaults",
    ".schema",
)

SENSITIVE_EXACT_NAMES = {
    ".env",
    ".netrc",
    ".npmrc",
    ".pypirc",
    ".git-credentials",
    "credentials.json",
    "terraform.tfstate",
    "terraform.tfstate.backup",
    "id_rsa",
    "id_dsa",
    "id_ecdsa",
    "id_ed25519",
}

SENSITIVE_EXTENSIONS = (
    ".pem",
    ".key",
    ".p12",
    ".pfx",
    ".jks",
    ".keystore",
    ".tfvars",
)

SENSITIVE_PATH_PATTERNS = (
    re.compile(r"(^|/)\.aws/(credentials|config)$", re.IGNORECASE),
    re.compile(r"(^|/)\.ssh/(config|authorized_keys|id_[^/]+)$", re.IGNORECASE),
    re.compile(r"(^|/)\.docker/config\.json$", re.IGNORECASE),
    re.compile(r"(^|/)\.kube/config$", re.IGNORECASE),
    re.compile(r"(^|/)client_secret[^/]*\.json$", re.IGNORECASE),
    re.compile(r"(^|/)[^/]*service[-_]?account[^/]*\.json$", re.IGNORECASE),
)

HOOK_TAMPER_PATTERNS = (
    re.compile(r"(^|/)\.github/hooks(/|$)", re.IGNORECASE),
    re.compile(r"(^|/)\.apm/hooks(/|$)", re.IGNORECASE),
    re.compile(r"(^|/)\.claude/(hooks(/|$)|settings(\.local)?\.json$)", re.IGNORECASE),
    re.compile(r"(^|/)\.github/copilot/settings(\.local)?\.json$", re.IGNORECASE),
    re.compile(r"(^|/)\.cursor/hooks(\.json|/|$)", re.IGNORECASE),
    re.compile(r"(^|/)\.codex/hooks(\.json|/|$)", re.IGNORECASE),
    re.compile(r"(^|/)\.windsurf/hooks(\.json|/|$)", re.IGNORECASE),
    re.compile(r"(^|/)\.gemini/(hooks(/|$)|settings\.json$)", re.IGNORECASE),
)

CI_CONFIG_PATTERNS = (
    re.compile(r"(^|/)\.github/workflows(/|$)", re.IGNORECASE),
    re.compile(r"(^|/)\.gitlab-ci\.ya?ml$", re.IGNORECASE),
    re.compile(r"(^|/)Jenkinsfile$", re.IGNORECASE),
    re.compile(r"(^|/)\.circleci(/|$)", re.IGNORECASE),
    re.compile(r"(^|/)azure-pipelines\.ya?ml$", re.IGNORECASE),
    re.compile(r"(^|/)bitbucket-pipelines\.ya?ml$", re.IGNORECASE),
    re.compile(r"(^|/)\.husky(/|$)", re.IGNORECASE),
    re.compile(r"(^|/)\.pre-commit-config\.ya?ml$", re.IGNORECASE),
    re.compile(r"(^|/)lefthook\.ya?ml$", re.IGNORECASE),
)

PROTECTED_BRANCH_RE = re.compile(
    r"^(refs/heads/)?(main|master|develop|production|prod|release/.+)$"
)


# ---------------------------------------------------------------------------
# Path inspection helpers
# ---------------------------------------------------------------------------

def normalize_path(raw_path: str) -> str:
    """Normalize slashes and relative segments while preserving leading markers."""
    cleaned = raw_path.strip().strip("\"'").replace("\\", "/")
    if not cleaned:
        return ""
    normed = posixpath.normpath(cleaned)
    return normed


def is_safe_template(norm_path: str) -> bool:
    """Return True if the file is an example/sample template rather than real secrets."""
    lower_name = posixpath.basename(norm_path).lower()
    if lower_name.endswith(".pub"):
        return True
    return any(
        lower_name.endswith(suffix) or f"{suffix}." in lower_name
        for suffix in SAFE_TEMPLATE_SUFFIXES
    )


def check_sensitive_path(raw_path: str) -> str | None:
    """Return a denial reason if raw_path points to a secret or credential file."""
    norm = normalize_path(raw_path)
    if not norm or is_safe_template(norm):
        return None

    basename = posixpath.basename(norm)
    lower_base = basename.lower()

    if lower_base in SENSITIVE_EXACT_NAMES or lower_base.startswith(".env."):
        return f"機密ファイル ({basename}) へのアクセスはポリシーにより禁止されています。"

    if any(lower_base.endswith(ext) for ext in SENSITIVE_EXTENSIONS):
        return f"秘密鍵・証明書・機密設定ファイル ({basename}) へのアクセスは禁止されています。"

    for pattern in SENSITIVE_PATH_PATTERNS:
        if pattern.search(norm):
            return f"認証情報パス ({norm}) へのアクセスはポリシーにより禁止されています。"

    return None


def check_protected_write_path(raw_path: str) -> tuple[Decision, str] | None:
    """Check if writing/editing raw_path violates hook or CI protection rules."""
    norm = normalize_path(raw_path)
    if not norm:
        return None

    for pattern in HOOK_TAMPER_PATTERNS:
        if pattern.search(norm):
            return (
                "deny",
                f"ガードレール設定・Hookファイル ({norm}) のエージェントによる変更は禁止されています。",
            )

    for pattern in CI_CONFIG_PATTERNS:
        if pattern.search(norm):
            return (
                "ask",
                f"CI/CD・品質ゲート設定 ({norm}) を変更しようとしています。実行してよいか確認してください。",
            )

    return None


# ---------------------------------------------------------------------------
# Shell command inspection helpers
# ---------------------------------------------------------------------------

HEREDOC_RE = re.compile(
    r"<<-?\s*['\"]?([A-Za-z_][A-Za-z0-9_]*)['\"]?.*?\n.*?\n\s*\1\b",
    re.DOTALL,
)

PIPE_TO_SHELL_RE = re.compile(
    r"\b(curl|wget)\b[^|\n]*\|\s*(sudo\s+)?(ba|z|da|k)?sh\b",
    re.IGNORECASE,
)

SQL_DESTRUCTIVE_RE = re.compile(
    r"\b(DROP\s+(DATABASE|SCHEMA|TABLE)|TRUNCATE\s+TABLE)\b",
    re.IGNORECASE,
)

SHELL_WRITE_OPERATORS_RE = re.compile(
    r"(>{1,2}|\b(tee|cp|mv|rm|unlink|chmod|chown|sed|perl|python3?|node)\b)"
)


def strip_non_executed_heredocs(command: str) -> str:
    """Strip heredoc bodies unless piped directly into an interpreter."""
    first_line = command.splitlines()[0] if command.splitlines() else ""
    if re.search(r"\b(ba|z|da)?sh\b|\bpython3?\b|\bnode\b", first_line):
        return command
    return HEREDOC_RE.sub("<<HEREDOC_STRIPPED", command)


def split_shell_segments(command: str) -> list[str]:
    """Split a shell command string into individual pipeline/chained segments."""
    segments: list[str] = []
    current: list[str] = []
    quote: str | None = None
    escaped = False
    i = 0
    while i < len(command):
        ch = command[i]
        if escaped:
            current.append(ch)
            escaped = False
            i += 1
            continue
        if ch == "\\":
            current.append(ch)
            escaped = True
            i += 1
            continue
        if quote:
            current.append(ch)
            if ch == quote:
                quote = None
            i += 1
            continue
        if ch in ("'", '"'):
            quote = ch
            current.append(ch)
            i += 1
            continue
        if ch in (";", "\n"):
            segments.append("".join(current).strip())
            current = []
            i += 1
            continue
        if ch in ("&", "|"):
            if i + 1 < len(command) and command[i + 1] == ch:
                segments.append("".join(current).strip())
                current = []
                i += 2
                continue
            if ch == "|":
                segments.append("".join(current).strip())
                current = []
                i += 1
                continue
        current.append(ch)
        i += 1

    tail = "".join(current).strip()
    if tail:
        segments.append(tail)
    return [seg for seg in segments if seg]


def tokenize_segment(segment: str) -> list[str]:
    """Tokenize a shell command segment safely, stripping leading env assignments."""
    try:
        tokens = shlex.split(segment, posix=True)
    except ValueError:
        tokens = segment.split()

    # Strip leading VAR=value assignments
    idx = 0
    while idx < len(tokens) and re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", tokens[idx]):
        idx += 1
    return tokens[idx:]


def strip_message_option_values(tokens: list[str]) -> list[str]:
    """Remove commit/describe message arguments (-m / --message) to avoid false positives."""
    cleaned: list[str] = []
    skip_next = False
    for tok in tokens:
        if skip_next:
            skip_next = False
            continue
        if tok in ("-m", "--message"):
            skip_next = True
            continue
        if tok.startswith("--message="):
            continue
        cleaned.append(tok)
    return cleaned


def is_dangerous_rm_target(target: str) -> bool:
    """Return True if an rm -rf target is root, home, parent, wildcard, or VCS metadata."""
    cleaned = target.strip().strip("\"'")
    if cleaned in ("/", "/*", "~", "~/", "$HOME", "${HOME}", ".", "..", "../", "*"):
        return True
    if cleaned.startswith("../") or re.match(r"^/\w*$", cleaned):
        # Root or top-level system directory such as /etc, /usr, /var, /home
        return True
    norm = normalize_path(cleaned)
    base = posixpath.basename(norm)
    return base in (".git", ".jj")


def check_rm_command(tokens: list[str]) -> tuple[Decision, str] | None:
    """Inspect rm invocations for catastrophic recursive/force deletions."""
    has_recursive = False
    targets: list[str] = []
    after_double_dash = False

    for tok in tokens[1:]:
        if after_double_dash:
            targets.append(tok)
            continue
        if tok == "--":
            after_double_dash = True
            continue
        if tok.startswith("--"):
            if tok in ("--recursive", "--no-preserve-root"):
                has_recursive = True
            continue
        if tok.startswith("-") and len(tok) > 1:
            flags = tok[1:]
            if "r" in flags or "R" in flags:
                has_recursive = True
            continue
        targets.append(tok)

    if has_recursive:
        for target in targets:
            if is_dangerous_rm_target(target):
                return (
                    "deny",
                    f"広範囲または重要ディレクトリの再帰削除 (rm {target}) は禁止されています。",
                )
    return None


def check_git_command(tokens: list[str]) -> tuple[Decision, str] | None:
    """Inspect git subcommands for forbidden flags, force pushes, and destructive resets."""
    # Find subcommand (skip global git options like -C <dir>, -c key=val, --no-pager)
    idx = 1
    while idx < len(tokens):
        tok = tokens[idx]
        if tok in ("-C", "-c", "--git-dir", "--work-tree"):
            idx += 2
            continue
        if tok.startswith("-"):
            idx += 1
            continue
        break

    if idx >= len(tokens):
        return None

    subcmd = tokens[idx]
    args = strip_message_option_values(tokens[idx + 1 :])

    # 1. Hook bypass (--no-verify / commit -n)
    if "--no-verify" in args:
        return ("deny", f"git {subcmd} での --no-verify によるフック・検証回避は禁止されています。")
    if subcmd == "commit" and any(
        a == "-n" or (a.startswith("-") and not a.startswith("--") and "n" in a[1:])
        for a in args
    ):
        return ("deny", "git commit -n (--no-verify) によるフック回避は禁止されています。")

    # 2. git push checks
    if subcmd == "push":
        has_force_lease = any(
            a.startswith("--force-with-lease") or a == "--force-if-includes" for a in args
        )
        has_raw_force = any(
            a in ("--force", "-f")
            or (a.startswith("-") and not a.startswith("--") and "f" in a[1:])
            for a in args
        )
        positional = [a for a in args if not a.startswith("-")]
        has_plus_refspec = any(a.startswith("+") for a in positional)

        if (has_raw_force and not has_force_lease) or has_plus_refspec:
            return (
                "deny",
                "git push --force（強制push）は禁止されています。必要な場合は --force-with-lease を使用し承認を得てください。",
            )

        # Check protected branch target (e.g. git push origin main, git push origin HEAD:main)
        for pos in positional[1:] if len(positional) >= 2 else positional:
            ref_target = pos.lstrip("+").split(":")[-1]
            if PROTECTED_BRANCH_RE.match(ref_target):
                return (
                    "ask",
                    f"保護ブランチ ({ref_target}) への直接 git push が検出されました。実行してよいか確認してください。",
                )

        if has_force_lease:
            return (
                "ask",
                "git push --force-with-lease はリモート履歴を上書きする可能性があります。実行前に確認してください。",
            )

    # 3. Destructive working tree / history operations -> ask
    if subcmd == "reset" and ("--hard" in args or "--merge" in args):
        return ("ask", "git reset --hard/--merge は未コミットの変更を破棄します。実行前に確認してください。")

    if subcmd == "clean" and any(
        a == "--force" or (a.startswith("-") and not a.startswith("--") and "f" in a[1:])
        for a in args
    ):
        return ("ask", "git clean -f は未追跡ファイルを完全に削除します。実行前に確認してください。")

    if subcmd == "branch" and "-D" in args:
        return ("ask", "git branch -D は未マージブランチを強制削除します。実行前に確認してください。")

    if subcmd in ("checkout", "restore") and "." in args:
        return ("ask", f"git {subcmd} . は作業ツリー全体の変更を破棄します。実行前に確認してください。")

    return None


def check_jj_command(tokens: list[str]) -> tuple[Decision, str] | None:
    """Inspect Jujutsu (jj) subcommands for destructive or wide-impact operations."""
    idx = 1
    while idx < len(tokens):
        tok = tokens[idx]
        if tok in ("-R", "--repository", "--at-op"):
            idx += 2
            continue
        if tok.startswith("-"):
            idx += 1
            continue
        break

    if idx >= len(tokens):
        return None

    subcmd = tokens[idx]
    rest = strip_message_option_values(tokens[idx + 1 :])

    if subcmd == "git" and rest and rest[0] == "push":
        push_args = rest[1:]
        if "--all" in push_args or "--deleted" in push_args:
            return (
                "ask",
                "jj git push --all/--deleted は複数または削除済みbookmarkを一括更新します。実行前に確認してください。",
            )
        for i, arg in enumerate(push_args):
            bookmark: str | None = None
            if arg in ("-b", "--bookmark", "--branch") and i + 1 < len(push_args):
                bookmark = push_args[i + 1]
            elif arg.startswith("--bookmark="):
                bookmark = arg.split("=", 1)[1]
            if bookmark and PROTECTED_BRANCH_RE.match(bookmark):
                return (
                    "ask",
                    f"保護bookmark ({bookmark}) への jj git push が検出されました。実行してよいか確認してください。",
                )

    if subcmd in ("abandon", "restore", "undo"):
        return (
            "ask",
            f"jj {subcmd} は変更や履歴状態を取り消します。対象リビジョンが意図どおりか確認してください。",
        )

    if subcmd in ("op", "operation") and rest and rest[0] == "restore":
        return (
            "ask",
            "jj op restore はリポジトリ操作履歴を巻き戻します。実行前に確認してください。",
        )

    return None


def check_shell_command(command: str) -> tuple[Decision, str] | None:
    """Analyze a full shell command string and return the highest-priority decision."""
    if not command or not command.strip():
        return None

    # 1. Pipe-to-shell remote execution check across full command
    if PIPE_TO_SHELL_RE.search(command):
        return (
            "deny",
            "curl/wget の出力を直接シェルへパイプ実行する操作はセキュリティ上禁止されています。",
        )

    sanitized_cmd = strip_non_executed_heredocs(command)
    ask_candidate: tuple[Decision, str] | None = None

    def record_ask(reason: str) -> None:
        nonlocal ask_candidate
        if ask_candidate is None:
            ask_candidate = ("ask", reason)

    if SQL_DESTRUCTIVE_RE.search(sanitized_cmd):
        record_ask("破壊的なSQL操作（DROP / TRUNCATE）が含まれています。実行前に確認してください。")

    segments = split_shell_segments(sanitized_cmd)
    for seg in segments:
        tokens = tokenize_segment(seg)
        if not tokens:
            continue

        # Unwrap 'command' builtin
        if tokens[0] == "command" and len(tokens) > 1 and not tokens[1].startswith("-"):
            tokens = tokens[1:]

        prog = posixpath.basename(tokens[0])

        # Category 2: Privilege escalation & dangerous permissions
        if prog in ("sudo", "su", "doas", "pkexec"):
            return ("deny", f"特権昇格コマンド ({prog}) の実行は禁止されています。")

        if prog == "chmod" and any(
            t in ("777", "a+rwx", "ugo+rwx") for t in tokens[1:]
        ):
            return ("deny", "chmod 777 等の過剰な権限付与はセキュリティ上禁止されています。")

        if prog in ("mkfs", "fdisk", "parted") or prog.startswith("mkfs."):
            return ("deny", f"ディスクフォーマット・パーティション操作 ({prog}) は禁止されています。")

        if prog == "dd" and any(t.startswith("of=/dev/") for t in tokens[1:]):
            return ("deny", "ブロックデバイスへの直接書き込み (dd of=/dev/...) は禁止されています。")

        # Category 1: Environment secret dumping
        if prog == "printenv":
            return ("deny", "環境変数の一覧・値の出力 (printenv) は機密情報漏洩防止のため禁止されています。")
        if prog == "env" and len(tokens) == 1:
            return ("deny", "環境変数の一括出力 (env) は機密情報漏洩防止のため禁止されています。")
        if prog == "export" and tokens[1:] == ["-p"]:
            return ("deny", "環境変数の一括出力 (export -p) は機密情報漏洩防止のため禁止されています。")
        if prog == "set" and len(tokens) == 1:
            return ("deny", "シェル変数・環境変数の一括出力 (set) は機密情報漏洩防止のため禁止されています。")

        # Category 2: Catastrophic rm
        if prog == "rm":
            rm_res = check_rm_command(tokens)
            if rm_res:
                if rm_res[0] == "deny":
                    return rm_res
                record_ask(rm_res[1])

        # Category 3: Git & Jujutsu
        if prog == "git":
            git_res = check_git_command(tokens)
            if git_res:
                if git_res[0] == "deny":
                    return git_res
                record_ask(git_res[1])

        if prog == "jj":
            jj_res = check_jj_command(tokens)
            if jj_res:
                if jj_res[0] == "deny":
                    return jj_res
                record_ask(jj_res[1])

        # Category 2: ORM / DB / Docker destructive resets -> ask
        joined_lower = " ".join(tokens).lower()
        if (
            "prisma migrate reset" in joined_lower
            or ("prisma db push" in joined_lower and "--force-reset" in joined_lower)
            or re.search(r"\brails\s+db:(drop|reset)\b", joined_lower)
            or "supabase db reset" in joined_lower
            or "alembic downgrade base" in joined_lower
        ):
            record_ask("データベースを初期化・リセットするコマンドが含まれています。実行前に確認してください。")

        if re.search(
            r"\bdocker\s+(system\s+prune\s+.*-a|volume\s+prune|compose\s+down\s+.*(-v|--volumes))\b",
            joined_lower,
        ) or re.search(r"\bdocker-compose\s+down\s+.*(-v|--volumes)\b", joined_lower):
            record_ask("Dockerボリュームまたはイメージを一括削除するコマンドが含まれています。実行前に確認してください。")

        # Category 1 & 4: File paths referenced inside shell commands
        cleaned_tokens = strip_message_option_values(tokens)
        may_modify_files = bool(SHELL_WRITE_OPERATORS_RE.search(seg))

        for tok in cleaned_tokens[1:]:
            if tok.startswith("-") and "=" not in tok:
                continue
            candidate = tok.split("=", 1)[1] if tok.startswith("-") and "=" in tok else tok
            candidate = candidate.lstrip("+")

            secret_reason = check_sensitive_path(candidate)
            if secret_reason:
                return ("deny", secret_reason)

            if may_modify_files:
                write_res = check_protected_write_path(candidate)
                if write_res:
                    if write_res[0] == "deny":
                        return write_res
                    record_ask(write_res[1])

    return ask_candidate


# ---------------------------------------------------------------------------
# Payload extraction & multi-harness output formatting
# ---------------------------------------------------------------------------

PATCH_FILE_HEADER_RE = re.compile(
    r"^(?:\*\*\*\s+(?:Update|Add|Delete)\s+File:\s+|\+\+\+\s+b/)(.+)$",
    re.MULTILINE,
)


def extract_paths_from_args(tool_args: dict[str, Any]) -> list[str]:
    """Extract target file or directory paths from tool arguments across harnesses."""
    paths: list[str] = []
    single_keys = (
        "file_path",
        "filePath",
        "path",
        "target_file",
        "file",
        "notebook_path",
        "dirPath",
        "directory",
        "includePattern",
    )
    list_keys = ("paths", "filePaths", "files")

    for key in single_keys:
        val = tool_args.get(key)
        if isinstance(val, str) and val.strip():
            paths.append(val)

    for key in list_keys:
        val = tool_args.get(key)
        if isinstance(val, list):
            paths.extend(item for item in val if isinstance(item, str) and item.strip())

    # Extract paths embedded in unified/apply_patch payloads
    for patch_key in ("patch", "diff", "input"):
        patch_val = tool_args.get(patch_key)
        if isinstance(patch_val, str):
            for match in PATCH_FILE_HEADER_RE.finditer(patch_val):
                paths.append(match.group(1).strip())

    return paths


def extract_command_from_args(tool_args: dict[str, Any]) -> str:
    """Extract shell command string from shell/terminal tool arguments."""
    for key in ("command", "cmd", "script"):
        val = tool_args.get(key)
        if isinstance(val, str) and val.strip():
            return val

    exec_val = tool_args.get("exec")
    args_val = tool_args.get("args")
    if isinstance(exec_val, str):
        if isinstance(args_val, list):
            str_args = [str(a) for a in args_val]
            return " ".join([exec_val, *str_args])
        return exec_val

    return ""


def evaluate_event(event: dict[str, Any]) -> tuple[Decision, str] | None:
    """Evaluate a PreToolUse / preToolUse event payload and return (decision, reason) or None."""
    raw_tool_name = event.get("toolName") or event.get("tool_name") or ""
    if not isinstance(raw_tool_name, str) or not raw_tool_name:
        return None

    tool_lower = raw_tool_name.strip().lower()
    raw_args = event.get("toolArgs") if "toolArgs" in event else event.get("tool_input")

    if isinstance(raw_args, str):
        try:
            parsed = json.loads(raw_args)
            tool_args = parsed if isinstance(parsed, dict) else {"input": raw_args}
        except json.JSONDecodeError:
            tool_args = {"command": raw_args, "input": raw_args}
    elif isinstance(raw_args, dict):
        tool_args = raw_args
    else:
        tool_args = {}

    # 1. Shell / Terminal execution tools
    if tool_lower in SHELL_TOOLS or "terminal" in tool_lower or "bash" in tool_lower:
        cmd = extract_command_from_args(tool_args)
        return check_shell_command(cmd)

    # 2. File paths inspection (both read & write tools, plus unknown MCP/IDE file tools)
    paths = extract_paths_from_args(tool_args)
    is_write = (
        tool_lower in WRITE_TOOLS
        or "write" in tool_lower
        or "edit" in tool_lower
        or "create" in tool_lower
        or "replace" in tool_lower
        or "patch" in tool_lower
        or "delete" in tool_lower
    )

    ask_result: tuple[Decision, str] | None = None

    for path in paths:
        # Category 1: Secrets are always denied on both read and write
        secret_reason = check_sensitive_path(path)
        if secret_reason:
            return ("deny", secret_reason)

        # Category 4: Hook / CI protection applies to write/edit/delete operations
        if is_write:
            write_res = check_protected_write_path(path)
            if write_res:
                if write_res[0] == "deny":
                    return write_res
                if ask_result is None:
                    ask_result = write_res

    return ask_result


def format_decision_output(
    event: dict[str, Any],
    decision: Decision,
    reason: str,
) -> dict[str, Any]:
    """Format stdout JSON according to the calling harness's PreToolUse contract."""
    # Copilot camelCase (`preToolUse`) or Copilot CLI PascalCase (`PreToolUse` has timestamp, no tool_use_id)
    if "toolName" in event or ("timestamp" in event and "tool_use_id" not in event):
        return {
            "permissionDecision": decision,
            "permissionDecisionReason": reason,
        }

    # Cursor native `preToolUse`
    if event.get("hook_event_name") == "preToolUse":
        return {
            "decision": decision,
            "reason": reason,
        }

    # Claude Code / VS Code Local / Codex / Gemini `PreToolUse`
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": decision,
            "permissionDecisionReason": reason,
        }
    }


def main() -> int:
    """Read hook event JSON from stdin and write permission decision JSON to stdout."""
    raw_stdin = sys.stdin.read()
    if not raw_stdin or not raw_stdin.strip():
        sys.stdout.write("{}")
        return 0

    try:
        event = json.loads(raw_stdin)
    except json.JSONDecodeError as exc:
        sys.stderr.write(f"guardrails hook: invalid JSON on stdin: {exc}\n")
        return 1

    if not isinstance(event, dict):
        sys.stderr.write("guardrails hook: expected JSON object on stdin\n")
        return 1

    verdict = evaluate_event(event)
    if verdict is None:
        sys.stdout.write("{}")
        return 0

    decision, reason = verdict
    output = format_decision_output(event, decision, reason)
    sys.stdout.write(json.dumps(output, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
