# Plano Operacional de Execucao Tariel

Data de referencia: 2026-04-12
Repositorio remoto: `gstarielio-hash/tariel-web`
Branch operacional atual: `checkpoint/20260331-current-worktree`

## Objetivo

Transformar o estado atual da Tariel em um ciclo de execucao previsivel, com:

- uma fonte canonica de estado atual;
- backlog orientado por produto e nao por ansiedade;
- commits pequenos e intencionais;
- publicacao incremental no GitHub;
- fechamento progressivo das decisoes abertas de produto e arquitetura.

## Leitura executiva

O produto ja existe e ja opera fluxos reais.

O gargalo principal nao e "falta de sistema".
O gargalo principal e a combinacao de:

- documentos de estado desatualizados ou concorrentes;
- fronteiras de dominio ainda parcialmente acopladas;
- frontend web ainda muito global;
- pipeline documental em transicao;
- onboarding e personalizacao ainda sem modulo unico;
- decisoes canonicias de produto ainda abertas.

## O que esta consolidado

- multiportal real: `admin`, `cliente`, `app`, `revisao`;
- tenant boundary e RBAC compartilhados;
- contrato documental com soft gate e hard gate V2;
- catalogo governado por familia, variante, template e tenant;
- Android tratado como cliente de primeira classe do fluxo do inspetor;
- cobertura automatizada forte em backend, mobile e E2E critico.

## O que ainda falta fechar

### Bloco 1. Fonte unica de verdade

Entregas:

- criar um documento mestre unico de estado atual;
- marcar checkpoints e diagnosticos antigos como `historico`;
- fixar glossario de `caso`, `laudo`, `thread`, `template`, `release`, `tenant`;
- manter uma tabela unica de modulos com status real.

Resultado esperado:

- parar de reconstruir contexto manualmente a cada retomada.

### Bloco 2. Decisoes canonicias de produto

Entregas:

- definir unidade canonica do produto;
- definir owner do estado principal do caso;
- definir workflow oficial do caso do inicio a aprovacao final;
- definir fronteira de visibilidade entre `Mesa`, `Admin Cliente` e `Admin Geral`;
- definir quando `DOCX/Word` vira template-fonte oficial;
- definir politica minima de retencao, autoria e IA.

Resultado esperado:

- impedir que implementacao continue decidindo produto por omissao.

### Bloco 3. Fronteiras de dominio

Entregas:

- terminar o desacoplamento entre `cliente`, `chat` e `revisor`;
- reduzir `portal_bridge.py` a adaptador fino;
- extrair o fluxo principal ainda acoplado ao `rota_chat`;
- continuar a quebra de hotspots de servico no admin;
- continuar a modularizacao da camada compartilhada de banco por compatibilidade controlada.

Resultado esperado:

- reduzir custo cognitivo e risco de regressao transversal.

### Bloco 4. Frontend web operacional

Entregas:

- quebrar `chat_index_page.js` por feature real;
- reduzir dependencia de `window.*`, aliases globais e ordem manual de scripts;
- catalogar assets ativos e compat layers legadas;
- padronizar estados de erro, toast, confirmacao, empty state e carregamento;
- fechar os pontos restantes de SSE/CSP e inicializacao fragil.

Resultado esperado:

- estabilizar a experiencia do inspetor e reduzir bugs de boot e sincronizacao.

### Bloco 5. Pipeline documental premium

Entregas:

- consolidar `document_view_model -> document_editor -> render`;
- reduzir o papel do fallback legado como caminho visivel principal;
- separar melhor documento de cliente e documento administrativo;
- fortalecer template universal premium para familias sem template forte;
- manter hard gate, soft gate, readiness e provenance como guardrails.

Resultado esperado:

- PDF final mais forte e menos dependente de fallback fraco.

### Bloco 6. Onboarding e primeira venda

Entregas:

- wizard de criacao de empresa;
- wizard de primeira configuracao do tenant;
- assistente para criar `Admin Cliente`, `Inspetor` e `Mesa`;
- provisioning guiado do portfolio inicial;
- checklist persistido de `tenant pronto para operar`.

Resultado esperado:

- reduzir dependencia de memoria manual para ativacao comercial.

### Bloco 7. Personalizacao por empresa

Entregas:

- modulo unico de identidade da empresa;
- logo e branding documental governados;
- assinatura, rodape e confidencialidade configuraveis;
- portfolio contratado por empresa;
- limites de plano e entitlements visiveis.

Resultado esperado:

- tornar customizacao vendavel e operavel sem espalhar regra em runtime.

### Bloco 8. Observabilidade e operacao

Entregas:

- transformar observabilidade de debug em observabilidade operacional;
- definir eventos e metricas canonicias por dominio;
- medir latencia real de chat, mesa e render;
- medir custo e latencia de IA/OCR;
- usar os dados para decidir quando mover fluxos pesados para jobs assincronos.

Resultado esperado:

- refatorar e escalar com dados, nao com intuicao.

## Ordem pratica de execucao

### Fase 0. Governanca imediata

1. Fixar este plano como artefato operacional.
2. Criar um `STATUS_CANONICO.md`.
3. Marcar docs antigas como historicas.
4. Responder as perguntas canonicias criticas.

### Fase 1. Pequenos acertos de alto impacto

1. Limpar inconsistencias visiveis de UI.
2. Padronizar mensagens operacionais.
3. Revisar estados vazios e estados de transicao.
4. Consolidar o mapa de modulos e seus owners.

### Fase 2. Fronteiras e hotspots

1. Reduzir dependencia do `portal_bridge.py`.
2. Fatiar `admin/services.py` por responsabilidade.
3. Continuar a quebra do runtime web do inspetor.
4. Catalogar e isolar compat layers.

### Fase 3. Documento e governanca

1. Consolidar o pipeline documental premium.
2. Fortalecer variantes e entitlements por tenant.
3. Aumentar a clareza comercial do catalogo.
4. Fechar a direcao de template-fonte.

### Fase 4. Onboarding e personalizacao

1. Fechar wizard de primeira venda.
2. Fechar modulo unico de identidade e branding.
3. Fechar portfolio contratado e limites do plano.
4. Persistir checklist de tenant pronto.

### Fase 5. Escala controlada

1. Elevar observabilidade operacional.
2. Medir e decidir jobs assincronos.
3. Expandir automacao E2E do que sobrar mais sensivel.
4. Revisar mobile/offline conforme prioridade comercial real.

## Backlog tatico inicial

### Trilha A. Documentacao canonica

- `STATUS_CANONICO.md`
- inventario de docs historicas
- glossario fixo
- mapa unico de modulos

### Trilha B. Produto canonico

- decisao de `caso` vs `laudo` vs `thread`
- workflow oficial
- visibilidade por persona
- politica de autoria, IA e retencao

### Trilha C. Backend e dominio

- `portal_bridge.py`
- `admin/services.py`
- `shared/database.py` compat facade
- contratos internos entre `cliente`, `chat` e `revisor`

### Trilha D. Frontend web

- `chat_index_page.js`
- `api.js`
- ordem manual de scripts do inspetor
- estado global do runtime do inspetor

### Trilha E. Documento

- `catalog_document_view_model.py`
- `catalog_pdf_templates.py`
- readiness, provenance e gates
- template universal premium

### Trilha F. Comercial e tenant

- onboarding
- branding
- portfolio por empresa
- entitlements e limites

## Regra operacional de Git e GitHub

Enquanto eu estiver executando trabalho neste repositorio:

- toda mudanca relevante vira commit proprio;
- eu nao vou acumular alteracoes longas sem commit;
- vou subir os commits para a branch remota atual, salvo se voce mandar trocar a estrategia;
- nao vou incluir mudancas locais fora de escopo sem confirmar;
- PR vira etapa opcional posterior, quando fizer sentido consolidar um bloco.

Convencao inicial:

- `docs:` para orientacao e contexto canonico;
- `refactor:` para quebra de hotspot sem mudar regra de negocio;
- `fix:` para bug;
- `feat:` para entrega funcional;
- `test:` para cobertura e protecao de regressao.

## Perguntas canonicias que precisam de resposta

Responder isto antes da proxima onda tecnica grande:

1. A unidade principal do produto e `caso`, `laudo`, `thread` ou uma composicao formal entre eles?
2. Quem e o dono operacional do estado principal do caso: `Chat Inspetor`, `Mesa Avaliadora` ou um nucleo independente?
3. Quais sao os estados oficiais do caso do inicio ate a aprovacao e emissao final?
4. Ate onde `Admin Cliente` pode ver comentarios, pendencias, anexos e decisoes da mesa?
5. Em que situacoes `Admin Geral` pode acessar conteudo tecnico do cliente?
6. O Android continua restrito ao fluxo do inspetor ou tambem entra mais fundo em pendencias e anexos avancados?
7. O produto vai vender so laudo final ou tambem gestao documental governada como capacidade explicita?
8. Quais partes da automacao por IA podem agir por padrao sem aumentar risco de confianca indevida?
9. Quando `DOCX/Word` vira a fonte oficial do template e o PDF passa a ser apenas saida final?
10. Qual e a politica minima de retencao, autoria e marcacao de conteudo alterado por IA?

## Definicao de pronto para a proxima etapa

O projeto entra em proxima fase quando:

- existir um documento mestre de estado atual;
- as perguntas canonicias mais perigosas tiverem resposta;
- a branch continuar com commits pequenos e publicos no GitHub;
- os hotspots mais caros tiverem plano de fatiamento definido;
- onboarding, branding e pipeline documental tiverem ordem clara de execucao.
