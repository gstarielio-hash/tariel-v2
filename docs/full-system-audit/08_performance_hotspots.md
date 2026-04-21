# 08. Hotspots e Suspeitas de Performance

Este documento separa fatos observáveis no código de hipóteses plausíveis de gargalo. Sem profiling de produção, esta seção deve ser lida como mapa de suspeitas bem fundamentadas, não como sentença final.

## 1. Resumo executivo

Os hotspots mais prováveis do sistema estão em:

- orquestração pesada no request do chat do inspetor;
- consultas e agregações de fila no painel do revisor;
- métricas e dashboards calculados em tempo de request;
- frontend web do inspetor e do cliente, pelo volume de JS/CSS e pela centralização de estado;
- geração de PDF e preview de templates;
- integrações síncronas com IA e OCR;
- runtime web sem bundler moderno.

## 1.1 Medição local objetiva da Fase 1

Em `2026-04-15` foi executado um profiling local controlado com `PERF_MODE=1` e `TARIEL_BACKEND_HOTSPOT_OBSERVABILITY=1`, atravessando os fluxos já instrumentados da Fase 1. O coletor usado foi `scripts/dev/profile_phase1_hotspots.py` e o artefato bruto ficou em `artifacts/observability_phase_acceptance/20260415_174837/phase1_hotspots_profile.json`.

Top 5 hotspots objetivos da amostra local, ordenados por `avg_duration_ms` no request e confirmados pelo sumário `backend_hotspots`:

| Ranking | Endpoint | Evidência local | Leitura |
| --- | --- | --- | --- |
| 1 | `cliente_bootstrap` | `avg_duration_ms=32.999`, `max_duration_ms=42.760`, `avg_sql_count=61` | O bootstrap completo do admin-cliente virou o hotspot mais claro da amostra. O custo vem de composição de payload e fan-out de leitura, não de uma query isolada lenta. |
| 2 | `mesa_export_package_pdf` | `avg_duration_ms=29.561`, `max_duration_ms=44.710`, `avg_sql_count=29` | A exportação PDF da mesa continua pesada dentro do request síncrono, combinando montagem de pacote e geração documental. |
| 3 | `review_panel_html` | `avg_duration_ms=25.590`, `max_duration_ms=56.398`, `avg_sql_count=16`, `avg_render_ms=25.590` | O painel SSR da mesa já aparece como hotspot real de composição e renderização, confirmando a suspeita do código. |
| 4 | `admin_dashboard_html` | `avg_duration_ms=17.758`, `max_duration_ms=46.908`, `avg_sql_count=15`, `avg_render_ms=17.758` | O dashboard do Admin-CEO é menos pesado que a mesa e o bootstrap, mas continua caro por agregação e render em tempo de request. |
| 5 | `inspector_pdf_generation` | `avg_duration_ms=14.333`, `max_duration_ms=17.509`, `avg_sql_count=5` | A geração de PDF do inspetor permanece no grupo crítico por ainda ser síncrona e documental, mesmo com menos fan-out SQL. |

Próximo item logo abaixo do top 5:

- `review_template_preview`: `avg_duration_ms=11.554`, `avg_sql_count=5`, `avg_render_ms=4.588`

Achados relevantes da amostra:

- Não apareceu `slow_sql` no corte local. O problema observado é fan-out e composição por request, não uma query individualmente ruim.
- As queries mais frequentes recaem sobre `usuarios`, `laudos` e `sessoes_ativas`, reforçando que os hotspots atuais atravessam contexto de sessão, listagens e composição de payload.
- Em operações de render, o item dominante da amostra foi `template_laudos.gerar_preview_pdf_template`, com `total_ms=13.765` e `avg_ms=4.588`.
- O ranking local confirma objetivamente que a frente mais cara hoje está no encontro entre bootstrap/painéis SSR e operações documentais síncronas.

## 2. Backend

## 2.1 Fatos confirmados no código

| Evidência confirmada | Onde aparece | Leitura |
| --- | --- | --- |
| `chat_stream_routes.py` concentra validação, criação de laudo, persistência, comandos, mesa e IA | `web/app/domains/chat/chat_stream_routes.py` | Request path muito carregado. |
| O runtime do chat usa `ThreadPoolExecutor(max_workers=4)` | `web/app/domains/chat/chat_runtime.py` | Há limite explícito de paralelismo para parte do fluxo. |
| O cliente de IA chama Gemini e OCR no backend | `web/nucleo/cliente_ia.py` | Latência depende de rede externa e processamento adicional. |
| O painel do revisor monta fila, filtros e contadores em tempo de request | `web/app/domains/revisor/panel.py` | Página potencialmente cara para empresa com muitos laudos. |
| `admin/services.py` calcula métricas e agregações | `web/app/domains/admin/services.py` | Dashboard administrativo depende de SQL em tempo real. |
| `security_session_store.py` mantém estado em memória e banco | `web/app/shared/security_session_store.py` | Sessões têm lógica própria relevante. |
| Exportações e previews geram PDFs | `web/nucleo/gerador_laudos.py`, `web/nucleo/template_editor_word.py` | Operações potencialmente pesadas dentro do fluxo síncrono. |

## 2.2 Hipóteses prováveis de gargalo backend

| Suspeita | Por que é plausível | Impacto provável |
| --- | --- | --- |
| Saturação do fluxo do chat sob concorrência | O request combina I/O externo, persistência e streaming; o executor tem apenas 4 workers | Aumento de fila, latência e timeout em picos |
| Painel do revisor degradando com crescimento da base | Monta listas, contadores, filters e loads relacionais por request | Lentidão de abertura da fila |
| Métricas administrativas ficando caras com muitos clientes | Agregações por dashboard e saúde operacional | Picos no `/admin/painel` e APIs derivadas |
| Geração de PDF travando requests interativos | Não há fila dedicada explícita para exportações | Experiência lenta em preview/export |
| Overhead de políticas de sessão | Sessão ativa mistura memória, TTL, persistência e checagens extras | Custo transversal em autenticação e validação |

## 3. Frontend

## 3.1 Fatos confirmados no código

| Evidência confirmada | Onde aparece | Leitura |
| --- | --- | --- |
| `chat_index_page.js` tem mais de 5 mil linhas | `web/static/js/chat/chat_index_page.js` | Controller monolítico do inspetor. |
| `cliente/portal.js` tem cerca de 3 mil linhas | `web/static/js/cliente/portal.js` | Portal cliente centralizado demais. |
| O inspetor carrega 20 scripts explícitos na página principal | `web/templates/index.html` | Runtime depende de ordem e volume de assets. |
| `api.js`, `api-core.js`, `chat-network.js` e `ui.js` compartilham globais em `window` | `web/static/js/shared/*.js` | Acoplamento client-side por namespace global. |
| CSS do inspetor e do chat é muito volumoso | `web/static/css/chat/chat_base.css`, `web/static/css/inspetor/reboot.css`, `web/static/css/inspetor/workspace.css` | Custo de parse e sobreposição de regras. |
| Não há bundler moderno explícito | workspace `web/` | Não há tree shaking ou code splitting automatizado. |

## 3.2 Hipóteses prováveis de gargalo frontend

| Suspeita | Por que é plausível | Impacto provável |
| --- | --- | --- |
| Tempo alto de parse/executar JS no inspetor | Muitos scripts, um controller muito grande e runtime global | Lentidão no primeiro carregamento e em devices modestos |
| Alto custo de manutenção de estado no cliente | Inspetor e cliente concentram muita coordenação de UI | Bugs sutis, re-render manual excessivo e regressões |
| CSS com sobreposição e regras antigas | Há arquivos novos, arquivos grandes e CSS de migração | Dificuldade de previsibilidade visual e custo de pintura |
| Cliente web funcionando como “mini SPA artesanal” | `cliente_portal.html` + `portal.js` | Complexidade cresce mais rápido que a legibilidade |

## 4. Banco

## 4.1 Fatos confirmados no código

- Há índices importantes nas entidades centrais.
- `Laudo`, `MensagemLaudo`, `TemplateLaudo`, `SessaoAtiva` e `AnexoMesa` já possuem índices e restrições relevantes.
- O runtime local padrão agora usa Postgres, enquanto SQLite segue restrito a fluxos isolados de teste e preview.

## 4.2 Hipóteses prováveis de gargalo de banco

| Suspeita | Por que é plausível | Impacto provável |
| --- | --- | --- |
| N+1 ou quase-N+1 em painéis compostos | Telas como revisor e cliente combinam várias contagens e relacionamentos | Aumento de round trips e tempo de render |
| Consultas agregadas frequentes sem cache | Dashboards e filas montam resumos a cada request | CPU/IO de banco maior que o necessário |
| Crescimento do histórico de mensagens | Chat, mesa e revisões acumulam dados por laudo | Paginação e filtros podem degradar ao longo do tempo |
| Uso excessivo de SQLite em fluxos isolados esconder gargalos de concorrência | Ambientes temporários simplificam lock/concurrency em comparação ao Postgres real | Risco de falsa sensação de performance durante desenvolvimento |

## 5. Rede e integrações externas

## 5.1 Fatos confirmados no código

- Gemini é chamado pelo backend.
- OCR usa Google Vision quando disponível.
- O revisor pode usar Redis para realtime distribuído.
- Admin dashboard usa Chart.js por CDN.
- Biblioteca de templates usa PDF.js por CDN.
- O frontend web depende de Google Fonts.

## 5.2 Hipóteses prováveis de gargalo de rede

| Suspeita | Por que é plausível | Impacto provável |
| --- | --- | --- |
| Latência da IA dominar o tempo percebido do chat | Gemini está no caminho síncrono do request | Tempo de resposta variável no fluxo principal |
| OCR aumentar tempo de resposta em mensagens com imagem | OCR é executado no backend antes ou durante a resposta | Lentidão maior em inspeções com evidência visual |
| Dependência de CDN atrasar carregamento inicial | Fontes e bibliotecas externas são necessárias em algumas páginas | Pior TTI em redes mais lentas |
| WebSocket/SSE sofrer sob infraestrutura parcial | Realtime depende de estado de sessão, Redis opcional e conexão aberta | Instabilidade percebida em notificações |

## 6. Renderização e UX

## 6.1 Fatos confirmados no código

- O inspetor renderiza uma shell grande com overlays, quick actions, barra de rede e várias regiões.
- `painel_revisor.html` e `cliente_portal.html` são templates grandes e ricos.
- Há páginas com listas, filtros, cards, chips e blocos extensos já no HTML inicial.

## 6.2 Hipóteses prováveis de gargalo de renderização

| Suspeita | Por que é plausível | Impacto provável |
| --- | --- | --- |
| DOM inicial pesado no inspetor | Página inclui muita estrutura de workspace e modais | Custo de layout e hidratação maior |
| Fila do revisor custosa para redesenhar | Muitos cards e métricas na mesma tela | Sensação de painel “pesado” |
| Portal cliente com trocas internas densas | Uma tela grande faz papel de múltiplas páginas | Reflows e custo cognitivo maiores |

## 7. Build e configuração

## 7.1 Fatos confirmados no código

- O web não expõe bundler moderno.
- O mobile tem pipeline moderna com Expo/EAS.
- O CI do web cobre lint, mypy, pytest, Playwright e stack com Postgres/Redis.

## 7.2 Hipóteses prováveis de gargalo de build/config

| Suspeita | Por que é plausível | Impacto provável |
| --- | --- | --- |
| Otimização limitada de assets web | Sem bundler não há pipeline robusta de splitting/minificação por feature | Frontend carrega mais do que precisaria |
| Custo alto de mudança em arquivos grandes | Grandes monólitos de JS e Python têm raio de impacto maior | Releases mais arriscadas e lentas |

## 8. Áreas com maior chance de lentidão

- Chat do inspetor com IA e anexos
- Painel do revisor
- Biblioteca/editor de templates
- Portal cliente na aba Chat e Mesa
- Exportações PDF
- Mobile em sincronização com rede instável

## 9. Áreas com maior chance de bug/regressão associada a performance

- `web/app/domains/chat/chat_stream_routes.py`
- `web/app/domains/revisor/panel.py`
- `web/app/domains/revisor/templates_laudo_support.py`
- `web/static/js/chat/chat_index_page.js`
- `web/static/js/cliente/portal.js`
- `android/src/features/InspectorMobileApp.tsx`

## 10. Melhorias que exigem medição antes de qualquer mudança

- Profiling do tempo de `/app/api/chat` por tipo de payload
- Tempo de render e número de queries em `/revisao/painel`
- Distribuição de tamanho e tempo de export de PDFs
- Peso real dos assets do inspetor no first load
- Taxa de falha/latência do realtime com e sem Redis
- Volume de mensagens e revisões por laudo em produção

## Confirmado no código

- Há vários hotspots estruturais antes mesmo de medir produção.
- O sistema já tem qualidade razoável, mas não tem sinais de uma arquitetura orientada primariamente a throughput máximo.
- O web frontend carrega bastante responsabilidade no navegador e o backend carrega bastante responsabilidade dentro do request.

## Inferência provável

- As maiores perdas de desempenho percebido virão de combinação entre backend síncrono pesado e frontend web grande, não de um único query lento isolado.
- O sistema pode funcionar bem em volume moderado, mas tenderá a sofrer quando o crescimento exigir paralelismo maior, filas mais ricas ou páginas com muitas entidades por empresa.

## Dúvida aberta

- Sem dados reais de produção, não é possível afirmar se o principal gargalo hoje está em IA, banco, payloads HTML/JS ou operações documentais. O código permite suspeitar de todos esses pontos, mas não hierarquizá-los por uso real.
