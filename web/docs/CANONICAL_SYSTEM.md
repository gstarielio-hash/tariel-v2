# Sistema Canônico

## Backend e domínios

- entrada: `main.py`
- domínios: `app/domains/chat`, `app/domains/revisor`, `app/domains/admin`, `app/domains/cliente`, `app/domains/mesa`
- contratos e governança V2: `app/v2`
- compartilhado: `app/shared`

## Fluxo canônico de caso, documento e revisão

1. O inspetor coleta o caso em `app/domains/chat`.
2. O `tipo_template` é normalizado em `app/domains/chat/normalization.py`.
3. O encerramento passa por gate de qualidade e serviços de laudo em `app/domains/chat/gate_helpers.py`, `app/domains/chat/laudo.py` e `app/domains/chat/laudo_service.py`.
4. A fachada documental incremental do V2 deriva política e binding de template em `app/v2/policy/*` e `app/v2/document/*`.
5. A Mesa do revisor opera por contrato compartilhado em `app/domains/revisor/reviewdesk_contract.py`.
6. A materialização do laudo usa template ativo por tenant e código, com suporte a `editor_rico` e `legado_pdf`.

## Estratégia atual de templates e laudos

- `editor_rico` em `nucleo/template_editor_word.py` é o caminho semântico preferido para evolução.
- `legado_pdf` em `nucleo/template_laudos.py` continua suportado para overlay e preview coordenado.
- O template ativo é resolvido em `app/v2/document/template_binding.py`.
- Geração estruturada via IA existe hoje de forma explícita para `cbmgo`; não existe ainda registry genérico e versionado de schemas para todas as famílias.
- A política canônica atual do V2 resolve casos com laudo ativo como `mesa_required`.
- `mobile_autonomous` ainda é direção futura, não modo de revisão ativo no código.

## Frontend web

- SSR oficial em `templates/`
- runtime oficial em `static/js/`
- sem frontend paralelo da Mesa

## Mobile

- cliente oficial em `../android/`
- consome o backend atual do workspace `web/`

## Regras de manutenção

- imports apontam para `app/*`, nunca para wrappers no root;
- não duplicar fluxo entre portal cliente, contract compartilhado e HTTP interno do revisor;
- não declarar família de template como oficial se ela não estiver normalizada e suportada no código atual;
- documentação técnica deve explicar o estado atual do sistema, não uma intenção futura solta.
