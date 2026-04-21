#!/usr/bin/env bash
set -uo pipefail

ROOT_DIR="$(cd -- "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
OUTPUT_ROOT="$ROOT_DIR/.tmp_online/baseline"
STAMP="$(date +%Y%m%d_%H%M%S)"
OUTPUT_DIR="$OUTPUT_ROOT/$STAMP"
REPORT_PATH="$OUTPUT_DIR/baseline_snapshot.md"
SUMMARY_PATH="$OUTPUT_DIR/baseline_status.json"

mkdir -p "$OUTPUT_DIR"

run_and_capture() {
  local label="$1"
  shift
  local log_path="$OUTPUT_DIR/${label}.log"
  local status="passed"

  {
    printf "## %s\n\n" "$label"
    printf '```text\n'
  } >>"$REPORT_PATH"

  if ! (
    cd "$ROOT_DIR"
    "$@"
  ) >"$log_path" 2>&1; then
    status="failed"
  fi

  cat "$log_path" >>"$REPORT_PATH"
  printf '\n```\n\n' >>"$REPORT_PATH"
  printf '%s' "$status"
}

git_status_path="$OUTPUT_DIR/git_status.log"
git_breakdown_path="$OUTPUT_DIR/git_status_breakdown.txt"

{
  printf "# Baseline Snapshot\n\n"
  printf -- '- gerado em `%s`\n' "$(date --iso-8601=seconds)"
  printf -- '- raiz: `%s`\n\n' "$ROOT_DIR"
} >"$REPORT_PATH"

(
  cd "$ROOT_DIR"
  git status --short
) >"$git_status_path" 2>&1 || true

total_changes="$(wc -l <"$git_status_path" | tr -d ' ')"
tracked_changes="$(grep -Evc '^\?\?' "$git_status_path" || true)"
untracked_changes="$(grep -Ec '^\?\?' "$git_status_path" || true)"

if [[ -s "$git_status_path" ]]; then
  sed -E 's/^.. //' "$git_status_path" \
    | sed 's# -> .*##' \
    | awk -F/ '
        NF == 1 { count["(root)"]++; next }
        { count[$1]++ }
        END {
          for (key in count) {
            printf "%7d %s\n", count[key], key
          }
        }
      ' \
    | sort -nr >"$git_breakdown_path"
else
  : >"$git_breakdown_path"
fi

{
  printf "## git status summary\n\n"
  printf -- '- total de entradas: `%s`\n' "$total_changes"
  printf -- '- arquivos rastreados alterados: `%s`\n' "$tracked_changes"
  printf -- '- arquivos nao rastreados: `%s`\n' "$untracked_changes"
  printf -- '- detalhe completo: `git_status.log`\n\n'
  printf '```text\n'
  sed -n '1,20p' "$git_breakdown_path"
  printf '```\n\n'
} >>"$REPORT_PATH"

doctor_status="$(run_and_capture doctor make --no-print-directory doctor)"
web_status="$(run_and_capture web-ci make --no-print-directory web-ci)"
mobile_status="$(run_and_capture mobile-ci make --no-print-directory mobile-ci)"
mesa_status="$(run_and_capture mesa-quality make --no-print-directory mesa-quality)"
contract_status="$(run_and_capture contract-check make --no-print-directory contract-check)"

overall_status="passed"
if [[ "$web_status" != "passed" || "$mobile_status" != "passed" || "$mesa_status" != "passed" ]]; then
  overall_status="failed"
fi

cat >"$SUMMARY_PATH" <<EOF
{
  "generated_at": "$(date --iso-8601=seconds)",
  "root_dir": "$ROOT_DIR",
  "output_dir": "$OUTPUT_DIR",
  "doctor": "$doctor_status",
  "web_ci": "$web_status",
  "mobile_ci": "$mobile_status",
  "mesa_quality": "$mesa_status",
  "contract_check": "$contract_status",
  "overall_verify_equivalent": "$overall_status"
}
EOF

printf '## summary\n\n' >>"$REPORT_PATH"
printf -- '- doctor: `%s`\n' "$doctor_status" >>"$REPORT_PATH"
printf -- '- web-ci: `%s`\n' "$web_status" >>"$REPORT_PATH"
printf -- '- mobile-ci: `%s`\n' "$mobile_status" >>"$REPORT_PATH"
printf -- '- mesa-quality: `%s`\n' "$mesa_status" >>"$REPORT_PATH"
printf -- '- contract-check: `%s`\n' "$contract_status" >>"$REPORT_PATH"
printf -- '- overall-verify-equivalent: `%s`\n' "$overall_status" >>"$REPORT_PATH"

echo "Baseline snapshot salvo em: $OUTPUT_DIR"
echo "Relatorio: $REPORT_PATH"
echo "Resumo: $SUMMARY_PATH"
