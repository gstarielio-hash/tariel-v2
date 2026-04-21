# Terminal Handoff Queue

Fila local para coordenar `backend -> frontend` e `frontend -> backend` quando dois terminais/agentes trabalham no mesmo workspace.

## Objetivo

Evitar alinhamento oral ou memoria solta quando uma mudanca de uma frente exigir trabalho da outra.

Exemplos:

- backend alterou contrato e agora o frontend precisa expor uma tela nova;
- frontend encontrou um gap visual ou de UX e precisa de ajuste no backend;
- um terminal precisa sinalizar claramente: `preciso fazer o front desse item novo agora`.

## Arquivos

- script: `scripts/dev/terminal_handoff_queue.py`
- fila runtime local: `artifacts/terminal_handoff/queue.json`

Observacao:

- a fila fica em `artifacts/`, entao nao entra no Git;
- os dois terminais enxergam o mesmo arquivo porque trabalham no mesmo workspace.

## Fluxo recomendado

### Backend registra uma pendencia para frontend

```bash
python3 scripts/dev/terminal_handoff_queue.py add \
  --source backend \
  --target frontend \
  --priority high \
  --title "Polir onboarding de acesso inicial da empresa" \
  --summary "A tela /admin/clientes/{empresa_id}/acesso-inicial ja existe no backend e precisa de acabamento visual/UX." \
  --frontend-request "preciso fazer o front desse item novo agora" \
  --route /admin/novo-cliente \
  --route /admin/clientes/{empresa_id}/acesso-inicial \
  --route /cliente/login \
  --backend-path web/app/domains/admin/client_routes.py \
  --backend-path web/templates/admin/cliente_acesso_inicial.html
```

### Frontend lista o que esta pendente

```bash
python3 scripts/dev/terminal_handoff_queue.py list --target frontend --status pending
```

### Frontend observa em tempo real

```bash
watch -n 2 "python3 scripts/dev/terminal_handoff_queue.py list --target frontend --status pending"
```

### Frontend assume um item

```bash
python3 scripts/dev/terminal_handoff_queue.py update HF-0001 \
  --status claimed \
  --owner terminal-front \
  --note "assumido para implementacao visual"
```

### Frontend conclui

```bash
python3 scripts/dev/terminal_handoff_queue.py update HF-0001 \
  --status done \
  --owner terminal-front \
  --note "front entregue e pronto para validacao"
```

## Status

- `pending`: aguardando outro terminal assumir
- `claimed`: alguem ja pegou
- `done`: concluido
- `cancelled`: descartado ou absorvido de outra forma

## Regra pratica

Sempre que uma mudanca de backend exigir front novo, ajuste visual ou CTA novo, registre o item na fila no mesmo momento da mudanca. Isso elimina o risco de o outro terminal nao perceber que existe trabalho novo para ele.
