# Inspecao Visual do Portal do Inspetor

Este fluxo transforma a revisão visual do inspetor em um processo repetível:

- captura screenshots desktop e mobile dos estados-chave
- coleta sinais objetivos de layout
- compara opcionalmente com um baseline visual
- gera galeria HTML para revisão rápida

## Estados capturados

- Home desktop
- Modal `Nova Inspecao`
- Workspace desktop
- Workspace com widget da Mesa aberto
- Modal de Perfil
- Gate de Qualidade
- Home mobile
- Workspace mobile

## Como rodar

Com servidor temporário isolado:

```bash
./.venv-linux/bin/python scripts/inspecao_visual_inspetor.py
```

Contra uma instância já rodando:

```bash
./.venv-linux/bin/python scripts/inspecao_visual_inspetor.py \
  --base-url http://127.0.0.1:8000
```

Gerando baseline:

```bash
./.venv-linux/bin/python scripts/inspecao_visual_inspetor.py \
  --replace-baseline-dir artifacts/visual/inspetor/baseline
```

Comparando contra baseline:

```bash
./.venv-linux/bin/python scripts/inspecao_visual_inspetor.py \
  --baseline-dir artifacts/visual/inspetor/baseline
```

## Saidas

Cada execução gera uma pasta em `artifacts/visual/inspetor/<timestamp>/` com:

- `*.png`: capturas dos estados
- `report.json`: auditoria estrutural de cada tela
- `report.md`: resumo legível em texto
- `index.html`: galeria para revisão visual
- `diffs/*.png`: diffs contra baseline, quando aplicável

## O que a auditoria verifica

- overflow horizontal da página
- elementos visíveis parcialmente fora da viewport
- possíveis casos de clipping de texto
- alvos clicáveis menores que `40x40`
- erros de console e `pageerror`

## Contrato visual base

O tema do inspetor agora usa como contrato-base a paleta e a escala definidas em [tokens.css](/home/gabriel/Área%20de%20trabalho/TARIEL/Tariel%20Control%20Consolidado/web/static/css/inspetor/tokens.css):

- `--bg-app`, `--bg-subtle`, `--bg-surface` e `--bg-surface-2` para a pilha dark principal
- `--text-primary`, `--text-secondary`, `--text-muted` e `--text-strong` para hierarquia tipográfica
- `--primary`, `--primary-hover` e `--primary-active` como eixo das ações
- `--radius-*`, `--space-*`, `--header-h`, `--sidebar-w`, `--chat-max-w` e `--input-min-h` como escala estrutural

Observação intencional:

- a referência base mantém `--button-h-sm: 36px` e `--icon-btn: 36px`
- no runtime do inspetor esses dois tokens sobem para `40px` para atender a auditoria objetiva de alvos clicáveis e melhorar ergonomia em uso prolongado

## Checklist de acabamento visual profissional

- Hierarquia: títulos, subtítulos e badges têm ordem clara e consistente.
- Espaçamento: blocos equivalentes usam o mesmo ritmo vertical.
- Densidade: não há cards ou barras competindo visualmente pelo mesmo peso.
- Ações: botões primários, ghost e inline seguem o mesmo padrão de altura e foco.
- Alinhamento: ícones, labels e metadados fecham no mesmo eixo.
- Conteúdo longo: nomes extensos não quebram cards nem headers.
- Estados vazios: anexos, mesa e histórico sem dados continuam elegantes.
- Modal: overlay, borda, respiro interno e CTA estão coesos.
- Mobile: sem corte lateral, sem botão pequeno demais, sem rail invadindo conteúdo.
- Consistência: home, workspace, perfil e mesa parecem partes do mesmo produto.
