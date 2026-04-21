#!/usr/bin/env bash
set -euo pipefail

source "$(cd -- "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib.sh"

STATE_ROOT="$DEVKIT_RUNTIME_DIR/mobile_codex_agent"
RUN_ID="$(date +%Y%m%d_%H%M%S)_$$"
RUN_DIR="$STATE_ROOT/$RUN_ID"
MAX_ITERATIONS=6
MODEL="${CODEX_MODEL:-gpt-5.4}"
GOAL=""
GOAL_FILE=""
WITH_SMOKE=0
DETACHED=0
DRY_RUN=0
VALIDATE_AGENT=0
SESSION_NAME="tariel-mobile-codex-agent"
CONTRACT_FILE="$REPO_ROOT/docs/mobile_codex_agent_contract_v1.md"
IDEAS_FILE="$REPO_ROOT/docs/mobile_agent_ideas_backlog.md"
LOT1_CHECKLIST_FILE="$REPO_ROOT/docs/mobile_lote1_acceptance_checklist.md"
LOT1_REPORT_FILE="$REPO_ROOT/docs/mobile_lote1_delivery_report.md"
LOT1_READINESS_CHECK="$REPO_ROOT/scripts/dev/check_mobile_codex_lote1_ready.py"

readonly DEFAULT_GOAL="Concluir profissionalmente a frente mobile Android do Tariel, priorizando estabilidade, baseline verde, integrações mobile/backend consistentes, UX aceitável e eliminação de regressões móveis comprováveis pelos gates do repositório."

usage() {
  cat <<'EOF'
Uso:
  scripts/dev/run_mobile_codex_agent.sh [opcoes]

Opcoes:
  --goal "texto"              Objetivo principal do agente.
  --goal-file arquivo         Lê o objetivo a partir de um arquivo.
  --model nome                Modelo do Codex CLI. Padrao: gpt-5.4
  --max-iterations N          Limite de iteracoes agente -> validacao. Padrao: 6
  --with-smoke                Inclui `make smoke-mobile` no gate externo.
  --validate-agent            Executa um smoke minimo do `codex exec` antes do loop principal.
  --detached                  Sobe o runner em uma sessao tmux destacada.
  --session nome              Nome da sessao tmux usada com --detached.
  --dry-run                   Nao executa o agente; apenas gera o plano e os comandos.
  -h, --help                  Mostra esta ajuda.

Exemplos:
  scripts/dev/run_mobile_codex_agent.sh --validate-agent --max-iterations 4
  scripts/dev/run_mobile_codex_agent.sh --with-smoke --detached --session tariel-mobile
EOF
}

log() {
  local timestamp
  timestamp="$(date +%H:%M:%S)"
  printf '[mobile-codex-agent %s] %s\n' "$timestamp" "$*"
}

die() {
  echo "$*" >&2
  exit 1
}

ensure_state_dir() {
  mkdir -p "$RUN_DIR"
}

require_cmd() {
  local cmd_name="$1"
  have_cmd "$cmd_name" || die "Comando obrigatorio ausente: $cmd_name"
}

resolve_json_python() {
  if have_cmd python3; then
    printf '%s\n' "python3"
    return 0
  fi

  if have_cmd python; then
    printf '%s\n' "python"
    return 0
  fi

  die "Python nao encontrado para serializacao JSON do runner."
}

json_quote() {
  local value="$1"
  local python_bin
  python_bin="$(resolve_json_python)"
  "$python_bin" -c 'import json, sys; print(json.dumps(sys.argv[1], ensure_ascii=False))' "$value"
}

quote_args() {
  local quoted=""
  local item
  for item in "$@"; do
    printf -v item '%q' "$item"
    quoted+="${item} "
  done
  printf '%s' "${quoted% }"
}

resolve_goal() {
  if [[ -n "$GOAL_FILE" ]]; then
    [[ -f "$GOAL_FILE" ]] || die "Arquivo de objetivo nao encontrado: $GOAL_FILE"
    GOAL="$(<"$GOAL_FILE")"
  fi

  GOAL="$(printf '%s' "${GOAL:-$DEFAULT_GOAL}" | sed 's/^[[:space:]]*//; s/[[:space:]]*$//')"
  [[ -n "$GOAL" ]] || die "Objetivo do agente nao pode ficar vazio."
}

run_detached() {
  local args=("$0")
  local arg
  for arg in "$@"; do
    if [[ "$arg" != "--detached" ]]; then
      args+=("$arg")
    fi
  done

  local command
  command="cd \"$REPO_ROOT\" && $(quote_args "${args[@]}")"

  if have_cmd tmux; then
    if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
      die "Sessao tmux ja existe: $SESSION_NAME"
    fi

    tmux new-session -d -s "$SESSION_NAME" "$command"
    log "Runner iniciado em background na sessao tmux: $SESSION_NAME"
    log "Anexe com: tmux attach -t $SESSION_NAME"
    return 0
  fi

  local detached_log="$RUN_DIR/detached.log"
  local detached_pid="$RUN_DIR/detached.pid"
  mkdir -p "$RUN_DIR"
  nohup bash -lc "$command" >"$detached_log" 2>&1 &
  printf '%s\n' "$!" >"$detached_pid"
  log "tmux nao encontrado; runner iniciado em background via nohup"
  log "PID: $(<"$detached_pid")"
  log "Log: $detached_log"
}

write_status() {
  local status="$1"
  local detail="$2"
  cat >"$RUN_DIR/status.json" <<EOF
{
  "generated_at": "$(date --iso-8601=seconds 2>/dev/null || date)",
  "status": "$status",
  "detail": $(json_quote "$detail"),
  "run_dir": $(json_quote "$RUN_DIR")
}
EOF
}

build_checks() {
  CHECK_NAMES=(
    "mobile_typecheck"
    "mobile_lint"
    "mobile_format_check"
    "mobile_test"
    "web_mobile_contracts"
    "mobile_lote1_readiness"
  )

  CHECK_COMMANDS=(
    "cd \"$ANDROID_ROOT\" && npm run typecheck"
    "cd \"$ANDROID_ROOT\" && npm run lint"
    "cd \"$ANDROID_ROOT\" && npm run format:check"
    "cd \"$ANDROID_ROOT\" && npm run test -- --runInBand"
    "cd \"$WEB_ROOT\" && PYTHONPATH=. \"$(resolve_web_python)\" -m pytest -q tests/test_mesa_mobile_sync.py tests/test_inspection_entry_mode_phase_d_mobile.py tests/test_catalog_pdf_templates.py tests/test_operational_memory.py tests/test_semantic_report_pack_catalog_fallback.py tests/test_semantic_report_pack_nr35_autonomy.py tests/test_v2_android_public_contract.py tests/test_chat_normalization_templates.py tests/test_templates_ia_generic_catalog.py"
    "\"$(resolve_web_python)\" \"$LOT1_READINESS_CHECK\""
  )

  if [[ "$WITH_SMOKE" == "1" ]]; then
    CHECK_NAMES+=("mobile_smoke")
    CHECK_COMMANDS+=("cd \"$REPO_ROOT\" && make smoke-mobile")
  fi
}

run_validation_step() {
  local iteration_dir="$1"
  local check_name="$2"
  local command="$3"
  local log_file="$iteration_dir/${check_name}.log"
  local rc_file="$iteration_dir/${check_name}.rc"
  local rc=0

  log "Validando: $check_name"
  bash -lc "$command" >"$log_file" 2>&1 || rc=$?

  if [[ "$rc" == "0" ]]; then
    printf '0\n' >"$rc_file"
    return 0
  fi

  printf '%s\n' "$rc" >"$rc_file"
  return "$rc"
}

summarize_validations() {
  local iteration_dir="$1"
  local summary_md="$iteration_dir/validation_summary.md"
  local failures_txt="$iteration_dir/validation_failures.txt"
  local summary_json="$iteration_dir/validation_summary.json"
  local pass_count=0
  local fail_count=0
  local first=1

  : >"$failures_txt"
  {
    echo "# Validation Summary"
    echo
  } >"$summary_md"

  printf '{\n  "checks": [\n' >"$summary_json"

  local i
  for i in "${!CHECK_NAMES[@]}"; do
    local name="${CHECK_NAMES[$i]}"
    local rc
    rc="$(<"$iteration_dir/${name}.rc")"
    local status
    if [[ "$rc" == "0" ]]; then
      status="pass"
      pass_count=$((pass_count + 1))
    else
      status="fail"
      fail_count=$((fail_count + 1))
      {
        printf 'CHECK: %s\n' "$name"
        printf 'COMMAND: %s\n' "${CHECK_COMMANDS[$i]}"
        printf 'EXIT_CODE: %s\n' "$rc"
        printf 'LOG: %s\n' "$iteration_dir/${name}.log"
        echo
      } >>"$failures_txt"
    fi

    printf -- '- `%s`: %s\n' "$name" "$status" >>"$summary_md"

    if [[ "$first" == "0" ]]; then
      printf ',\n' >>"$summary_json"
    fi
    first=0
    printf '    {"name": "%s", "status": "%s", "exit_code": %s}' "$name" "$status" "$rc" >>"$summary_json"
  done

  printf '\n  ],\n  "pass_count": %s,\n  "fail_count": %s\n}\n' "$pass_count" "$fail_count" >>"$summary_json"

  [[ "$fail_count" == "0" ]]
}

validate_agent_smoke() {
  local smoke_dir="$RUN_DIR/agent_smoke"
  mkdir -p "$smoke_dir"

  log "Validando smoke minimo do agente Codex"
  codex login status >"$smoke_dir/login_status.txt"

  local prompt_file="$smoke_dir/prompt.md"
  cat >"$prompt_file" <<'EOF'
Sem editar arquivos, sem rodar comandos mutaveis e sem alterar o repositorio, responda apenas com:
AGENT_READY
EOF

  if ! codex exec \
    --ephemeral \
    --cd "$REPO_ROOT" \
    --model "$MODEL" \
    --sandbox read-only \
    --color never \
    --output-last-message "$smoke_dir/last_message.txt" \
    - <"$prompt_file" >"$smoke_dir/stdout.log" 2>"$smoke_dir/stderr.log"; then
    die "Smoke do agente falhou. Veja: $smoke_dir"
  fi

  if ! grep -q "AGENT_READY" "$smoke_dir/last_message.txt"; then
    die "Smoke do agente nao confirmou AGENT_READY. Veja: $smoke_dir/last_message.txt"
  fi

  log "Smoke do agente validado com sucesso"
}

write_prompt() {
  local iteration="$1"
  local iteration_dir="$2"
  local summary_file="$iteration_dir/validation_summary.md"
  local failures_file="$iteration_dir/validation_failures.txt"
  local prompt_file="$iteration_dir/prompt.md"

  cat >"$prompt_file" <<EOF
Voce esta trabalhando no repositorio Tariel em:
$REPO_ROOT

Missao principal:
$GOAL

Escopo permitido:
- mobile Android em \`android/\`
- backend/testes que integram diretamente com mobile em \`web/\`
- scripts operacionais que suportam o trilho mobile

Documentos obrigatórios de referência:
- contrato principal: \`$CONTRACT_FILE\`
- backlog de ideias novas: \`$IDEAS_FILE\`
- checklist do lote 1: \`$LOT1_CHECKLIST_FILE\`
- relatório do lote 1: \`$LOT1_REPORT_FILE\`

Regras de execucao:
- comece lendo contexto antes de editar
- preserve mudancas locais do usuario
- nao reverta mudancas que nao foram suas
- nao declare conclusao se algum gate externo ainda estiver falhando
- priorize regressao funcional e baseline antes de acabamento cosmetico
- quando houver conflito entre UI e contrato, corrija o contrato/teste/implementacao de forma coerente
- se surgir ideia nova de produto, UX ou fluxo fora do contrato aprovado, registre primeiro em \`$IDEAS_FILE\`
- nao marque o lote 1 como pronto sem atualizar \`$LOT1_CHECKLIST_FILE\` e \`$LOT1_REPORT_FILE\` com evidências reais
- se todos os testes estiverem verdes mas o gate \`mobile_lote1_readiness\` estiver falhando, continue trabalhando até fechar o contrato do lote 1 ou documentar claramente o bloqueio

Gates externos que este runner usa para decidir sucesso:
$(printf -- '- %s\n' "${CHECK_NAMES[@]}")

Status atual do gate externo na iteracao $iteration:
EOF

  if [[ -s "$summary_file" ]]; then
    {
      echo
      cat "$summary_file"
      echo
    } >>"$prompt_file"
  fi

  if [[ -s "$failures_file" ]]; then
    cat >>"$prompt_file" <<EOF
Falhas atuais detalhadas:

\`\`\`text
$(cat "$failures_file")
\`\`\`
EOF
  else
    cat >>"$prompt_file" <<'EOF'
Todos os gates externos atuais passaram. Nao assuma que o trabalho acabou: procure o melhor proximo ganho no eixo mobile, execute algo material e depois deixe o repositorio pronto para a proxima validacao.
EOF
  fi

  cat >>"$prompt_file" <<'EOF'

Entregavel esperado desta iteracao:
- corrigir o problema mais importante do eixo mobile agora
- atualizar o checklist e o relatório do lote 1 sempre que houver progresso material
- rodar verificacoes locais relevantes antes de encerrar
- responder com:
  - status: completed | partial | blocked
  - summary: o que mudou
  - residual_risks: o que ainda falta
  - suggested_next_step: proximo passo objetivo
EOF
}

run_codex_iteration() {
  local iteration="$1"
  local iteration_dir="$2"
  local prompt_file="$iteration_dir/prompt.md"

  log "Executando agente Codex na iteracao $iteration"
  if codex exec \
    --cd "$REPO_ROOT" \
    --model "$MODEL" \
    --full-auto \
    --color never \
    --output-last-message "$iteration_dir/last_message.txt" \
    --json \
    - <"$prompt_file" >"$iteration_dir/events.jsonl" 2>"$iteration_dir/stderr.log"; then
    printf '0\n' >"$iteration_dir/codex.rc"
    return 0
  fi

  local rc=$?
  printf '%s\n' "$rc" >"$iteration_dir/codex.rc"
  return "$rc"
}

capture_git_snapshot() {
  local iteration_dir="$1"
  git -C "$REPO_ROOT" status --short >"$iteration_dir/git_status.txt" || true
  git -C "$REPO_ROOT" diff --stat >"$iteration_dir/git_diff_stat.txt" || true
}

write_run_plan() {
  local plan_file="$RUN_DIR/run_plan.md"
  {
    echo "# Mobile Codex Agent Run"
    echo
    printf -- '- run_dir: `%s`\n' "$RUN_DIR"
    printf -- '- model: `%s`\n' "$MODEL"
    printf -- '- max_iterations: `%s`\n' "$MAX_ITERATIONS"
    printf -- '- with_smoke: `%s`\n' "$WITH_SMOKE"
    echo
    echo "## Goal"
    echo
    echo "$GOAL"
    echo
    echo "## External Gates"
    echo
    printf -- '- %s\n' "${CHECK_NAMES[@]}"
  } >"$plan_file"
}

parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --goal)
        GOAL="${2:?Valor ausente para --goal}"
        shift 2
        ;;
      --goal-file)
        GOAL_FILE="${2:?Valor ausente para --goal-file}"
        shift 2
        ;;
      --model)
        MODEL="${2:?Valor ausente para --model}"
        shift 2
        ;;
      --max-iterations)
        MAX_ITERATIONS="${2:?Valor ausente para --max-iterations}"
        shift 2
        ;;
      --with-smoke)
        WITH_SMOKE=1
        shift
        ;;
      --validate-agent)
        VALIDATE_AGENT=1
        shift
        ;;
      --detached)
        DETACHED=1
        shift
        ;;
      --session)
        SESSION_NAME="${2:?Valor ausente para --session}"
        shift 2
        ;;
      --dry-run)
        DRY_RUN=1
        shift
        ;;
      -h|--help)
        usage
        exit 0
        ;;
      *)
        die "Argumento nao reconhecido: $1"
        ;;
    esac
  done
}

main() {
  parse_args "$@"
  resolve_goal

  if [[ "$DETACHED" == "1" ]]; then
    run_detached "$@"
    exit 0
  fi

  require_cmd git
  require_cmd codex
  require_cmd npm
  ensure_state_dir
  build_checks
  write_run_plan

  log "Run dir: $RUN_DIR"
  write_status "starting" "Inicializando runner do agente mobile"

  if [[ "$DRY_RUN" == "1" ]]; then
    write_status "dry_run" "Plano gerado sem execucao do agente"
    cat "$RUN_DIR/run_plan.md"
    exit 0
  fi

  if [[ "$VALIDATE_AGENT" == "1" ]]; then
    validate_agent_smoke
  fi

  local iteration=1
  while [[ "$iteration" -le "$MAX_ITERATIONS" ]]; do
    local iteration_dir="$RUN_DIR/iteration_$(printf '%02d' "$iteration")"
    mkdir -p "$iteration_dir"

    capture_git_snapshot "$iteration_dir"

    local i
    for i in "${!CHECK_NAMES[@]}"; do
      run_validation_step "$iteration_dir" "${CHECK_NAMES[$i]}" "${CHECK_COMMANDS[$i]}" || true
    done

    if summarize_validations "$iteration_dir"; then
      log "Todos os gates externos passaram na iteracao $iteration"
      write_status "success" "Todos os gates externos configurados passaram"
      exit 0
    fi

    write_prompt "$iteration" "$iteration_dir"

    if ! run_codex_iteration "$iteration" "$iteration_dir"; then
      log "Codex retornou falha na iteracao $iteration"
      write_status "agent_failed" "Falha na execucao do Codex na iteracao $iteration"
    else
      write_status "in_progress" "Iteracao $iteration concluida; iniciando nova rodada de validacao"
    fi

    iteration=$((iteration + 1))
  done

  write_status "max_iterations_reached" "Limite de iteracoes atingido sem fechar todos os gates"
  die "Limite de iteracoes atingido. Veja os artefatos em: $RUN_DIR"
}

main "$@"
