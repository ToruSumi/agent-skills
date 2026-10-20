#!/usr/bin/env bash
# TestRail API v2 操作スクリプト
#
# 認証情報は環境変数から読む:
#   TESTRAIL_URL      例: https://example.testrail.io
#   TESTRAIL_USER     ログインメールアドレス
#   TESTRAIL_API_KEY  API キー
# 未設定の場合は TESTRAIL_ENV_FILE (未指定時は ./.env) を読み込む。
# 認証情報は出力しない。
#
# 使い方:
#   testrail_api.sh projects
#   testrail_api.sh milestones <project_id>
#   testrail_api.sh runs <project_id> [milestone_id]
#   testrail_api.sh run <run_id>
#   testrail_api.sh close_run <run_id> --yes     # 書き込み。--yes 必須
#   testrail_api.sh request <GET|POST> <endpoint> [json_body] [--yes]
#       endpoint 例: get_case/123 , add_run/1 ( "index.php?/api/v2/" は自動付与 )
#       POST は --yes 必須

set -euo pipefail

die() { echo "error: $*" >&2; exit 1; }

load_env() {
  if [[ -z "${TESTRAIL_URL:-}" || -z "${TESTRAIL_USER:-}" || -z "${TESTRAIL_API_KEY:-}" ]]; then
    local env_file="${TESTRAIL_ENV_FILE:-./.env}"
    [[ -f "$env_file" ]] || die "認証情報が未設定です (TESTRAIL_URL/TESTRAIL_USER/TESTRAIL_API_KEY または $env_file)"
    set -a
    # shellcheck disable=SC1090
    . "$env_file"
    set +a
  fi
  TESTRAIL_URL="${TESTRAIL_URL%/}"
  [[ -n "$TESTRAIL_URL" && -n "${TESTRAIL_USER:-}" && -n "${TESTRAIL_API_KEY:-}" ]] || die "認証情報が不足しています"
}

# api METHOD ENDPOINT [JSON_BODY]
api() {
  local method="$1" endpoint="$2" body="${3:-}"
  local url="$TESTRAIL_URL/index.php?/api/v2/$endpoint"
  local args=(-s -w '\n%{http_code}' -X "$method" -u "$TESTRAIL_USER:$TESTRAIL_API_KEY" -H "Content-Type: application/json")
  if [[ -n "$body" ]]; then
    args+=(-d "$body")
  fi
  local raw code resp
  raw="$(curl "${args[@]}" "$url")"
  code="${raw##*$'\n'}"
  resp="${raw%$'\n'*}"
  if [[ "$code" -ge 400 ]]; then
    echo "HTTP $code: $resp" >&2
    case "$code" in
      401) echo "hint: ユーザー名または API キーを確認してください" >&2 ;;
      403) echo "hint: 権限がありません" >&2 ;;
      400) echo "hint: 存在しない ID、またはパラメータ不正の可能性があります" >&2 ;;
      429) echo "hint: レート制限です。時間をおいて再実行してください" >&2 ;;
    esac
    exit 1
  fi
  printf '%s' "$resp"
}

# JSON の出力整形 (空レスポンスも許容)
pretty() {
  python3 -c '
import sys, json
t = sys.stdin.read()
if not t.strip():
    print("(empty response)")
    sys.exit()
try:
    print(json.dumps(json.loads(t), ensure_ascii=False, indent=2))
except ValueError:
    print(t)
'
}

cmd="${1:-help}"
shift || true

case "$cmd" in
  projects)
    load_env
    api GET "get_projects" | pretty
    ;;
  milestones)
    [[ $# -ge 1 ]] || die "使い方: milestones <project_id>"
    load_env
    api GET "get_milestones/$1" | pretty
    ;;
  runs)
    [[ $# -ge 1 ]] || die "使い方: runs <project_id> [milestone_id]"
    load_env
    ep="get_runs/$1"
    [[ $# -ge 2 ]] && ep="$ep&milestone_id=$2"
    api GET "$ep" | pretty
    ;;
  run)
    [[ $# -ge 1 ]] || die "使い方: run <run_id>"
    load_env
    api GET "get_run/$1" | pretty
    ;;
  close_run)
    [[ $# -ge 1 ]] || die "使い方: close_run <run_id> --yes"
    [[ "${2:-}" == "--yes" ]] || die "書き込み操作です。ユーザー確認後に --yes を付けて実行してください"
    load_env
    api POST "close_run/$1" '{}' | pretty
    ;;
  request)
    [[ $# -ge 2 ]] || die "使い方: request <GET|POST> <endpoint> [json_body] [--yes]"
    method="$1"; endpoint="$2"; shift 2
    body=""
    yes=0
    for a in "$@"; do
      if [[ "$a" == "--yes" ]]; then yes=1; else body="$a"; fi
    done
    if [[ "$method" != "GET" ]]; then
      [[ $yes -eq 1 ]] || die "$method は書き込み操作です。ユーザー確認後に --yes を付けて実行してください"
    fi
    load_env
    api "$method" "$endpoint" "$body" | pretty
    ;;
  help|-h|--help|*)
    sed -n '2,20p' "$0"
    ;;
esac
