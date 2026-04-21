# Checkpoint Pré-Laudo Mobile e PDF

Data: 2026-04-13
Branch: `feature/canonical-case-lifecycle-v1`
HEAD de referência: `effbf9a`

## Objetivo do corte

Este checkpoint congela o estado da frente mais importante do momento:

- usar a referência canônica do `web/AdminCEO` para montar pré-laudos no mobile;
- levar `foto -> contexto -> IA -> pré-laudo -> quality gate -> PDF` para um fluxo governado;
- validar isso no app Android em aparelho real.

## O que já foi feito

### 1. Backend canônico do pré-laudo e PDF

O backend já consolidou a trilha documental principal:

- `analysis_basis` passou a consolidar fotos, contexto do chat, documentos e sinais do workflow;
- `report_pack_draft` passou a carregar `pre_laudo_outline`, `pre_laudo_summary` e `pre_laudo_document`;
- o catálogo de PDF passou a reaproveitar a base analítica e o payload estruturado para preencher melhor o documento final;
- nomes originais de imagens/documentos passaram a subir melhor para `registros_fotograficos`;
- o `delivery_package` e o `report_pack` ficaram mais coerentes para rastreabilidade interna.

Arquivos centrais do backend:

- `web/app/domains/chat/report_pack_helpers.py`
- `web/app/domains/chat/catalog_pdf_templates.py`
- `web/app/domains/chat/chat_service.py`
- `web/app/domains/chat/laudo_service.py`
- `web/app/shared/operational_memory_hooks.py`

### 2. Base canônica do AdminCEO aplicada ao caso mobile

Foi preparado um seed canônico para o mobile, usando o schema e o exemplo de NR35 do `web`:

- script: `web/scripts/seed_mobile_canonical_pre_laudo_data.py`
- família: `nr35_inspecao_linha_de_vida`
- template mobile: `nr35_linha_vida`
- usuário de teste: `inspetor@tariel.ia`
- caso seedado de referência: `laudo_id = 4`

Arquivos de referência usados:

- `web/canonical_docs/family_schemas/nr35_inspecao_linha_de_vida.json`
- `web/canonical_docs/family_schemas/nr35_inspecao_linha_de_vida.laudo_output_seed.json`
- `web/canonical_docs/family_schemas/nr35_inspecao_linha_de_vida.laudo_output_exemplo.json`

### 3. Mobile consumindo o pré-laudo canônico

O app Android já consome e renderiza o contrato canônico do pré-laudo em vez de depender só de resumo solto:

- tipagem mais forte de `report_pack_draft` e `pre_laudo_document`;
- card canônico do pré-laudo no chat com:
  - família
  - template
  - cobertura
  - blocos
  - seções do documento
  - slots de evidência
  - base analítica
  - `next_questions`
- ação para usar `next_questions` direto no composer;
- ação para abrir a mesa a partir do card;
- ação para abrir o quality gate a partir do card.

Arquivos centrais do mobile:

- `android/src/types/mobile.ts`
- `android/src/features/chat/reportPackHelpers.ts`
- `android/src/features/chat/ThreadConversationPane.tsx`
- `android/src/features/chat/buildThreadContextState.ts`
- `android/src/features/chat/useInspectorChatController.ts`
- `android/src/features/common/buildAuthenticatedLayoutSections.ts`
- `android/src/features/common/buildInspectorScreenProps.ts`
- `android/src/features/buildInspectorRootFinalScreenState.ts`

### 4. Bug real encontrado e corrigido no aparelho

Durante o teste físico, o botão `Validar e finalizar` do card do pré-laudo aparecia, mas não abria o modal.

Diagnóstico:

- o botão do card estava ligado à ação errada;
- em vez de chamar `handleAbrirQualityGate`, ele chamava `handleConfirmarQualityGate`;
- em retomada de sessão, o quality gate ainda dependia demais de `conversation.laudoId`.

Correções aplicadas:

- fallback seguro de `laudoId` para `conversation.laudoCard.id` e `qualityGateLaudoId`;
- wiring corrigido da ação `onAbrirQualityGate` até a superfície do chat.

Arquivos centrais dessa correção:

- `android/src/features/chat/useInspectorChatController.ts`
- `android/src/features/chat/useInspectorChatController.entryMode.test.ts`
- `android/src/features/common/inspectorUiBuilderTypes.ts`
- `android/src/features/common/buildAuthenticatedLayoutSections.ts`
- `android/src/features/common/buildInspectorScreenProps.ts`
- `android/src/features/common/buildInspectorScreenProps.test.ts`
- `android/src/features/buildInspectorRootFinalScreenState.ts`

### 5. Ambiente de teste liberado

O tenant/caso de teste no celular ficou preparado para a frente canônica:

- modo premium ativo para o tenant de teste;
- catálogo governado liberado no mobile;
- templates liberados para teste;
- política de anexos já governada pelo backend, em vez de heurística local.

### 6. Fixtures visuais já organizadas

As imagens que você gerou já foram organizadas em bundle local para próximos testes:

- origem fornecida:
  - `~/Downloads/imagens_inspecao_industrial (2)/...`
- bundle preparado:
  - `.tmp_online/vision-fixtures/industrial_inspection_2026_04_13/`

## O que já foi validado

### Backend

Já foi validado em teste local:

- `pytest` do recorte documental e canônico;
- `report_pack` e `catalog_pdf_templates`;
- uso do `pre_laudo_summary` e da trilha operacional.

### Mobile local

Já passaram localmente:

- `npm run typecheck`
- `npx jest src/features/chat/reportPackHelpers.test.ts src/features/chat/ThreadConversationPane.test.tsx src/features/chat/buildThreadContextState.test.ts src/features/common/buildInspectorScreenProps.test.ts --runInBand`
- `npx jest src/features/chat/conversationHelpers.test.ts src/features/history/HistoryDrawerPanel.test.tsx src/features/settings/exportDataFlow.test.ts src/features/common/buildInspectorBaseDerivedStateSections.test.ts --runInBand`
- `npx jest src/features/chat/useInspectorChatController.entryMode.test.ts --runInBand`

### Aparelho real

Já foi validado no USB:

- app instalado com build preview;
- caso canônico aberto no chat;
- card `chat-report-pack-card` visível;
- botão `Abrir Mesa` funcionando;
- `mesa-thread-surface` visível;
- botão `Validar e finalizar` abrindo o modal;
- `quality-gate-report-pack-section` visível;
- `next_question` preenchendo o composer;
- botão de envio habilitando depois da pergunta sugerida.

Comando de smoke do aparelho que passou:

- `npm run maestro:pre-laudo:resume -- --device RQCW20887GV`

Arquivo do smoke:

- `android/maestro/pre-laudo-canonical-resume-smoke.yaml`

## O que ainda falta fazer

### 1. Fechar o E2E visual até o PDF

Ainda falta ligar as fotos sintéticas ao caso canônico e validar a trilha inteira:

- imagem entrando no caso;
- referência visual entrando no `analysis_basis`;
- isso aparecendo no `pre_laudo_document`;
- isso refletindo no PDF final.

Hoje a base está pronta, mas a prova E2E completa com as imagens ainda não foi fechada.

### 2. Elevar o pré-laudo para "laudo preenchido completíssimo"

O sistema já tem um pré-laudo canônico útil, mas a próxima evolução importante é deixá-lo mais próximo do laudo final completo:

- aumentar preenchimento automático por seção;
- registrar proveniência por campo:
  - foto
  - documento
  - contexto
  - inferência
- usar completude do `pre_laudo_document` como gate formal de finalização.

### 3. Validar emissão real do PDF no mobile

O modal do quality gate já abre no aparelho, mas ainda falta fechar a última milha:

- confirmar finalização real;
- emitir PDF;
- validar download/abertura do artefato final;
- validar o estado pós-emissão no app.

### 4. Validar anexos físicos completos

Ainda falta a rodada física completa no aparelho para:

- câmera
- galeria
- upload real de documento
- comportamento nativo do Android

## Como continuar

### Passo 1. Subir backend local

No diretório `web`:

```bash
./.venv-linux/bin/python -m uvicorn main:app --app-dir . --host 0.0.0.0 --port 8000
```

Checagem:

```bash
curl -sf http://127.0.0.1:8000/health
```

### Passo 2. Reseedar o caso canônico mobile

No diretório `web`:

```bash
./.venv-linux/bin/python scripts/seed_mobile_canonical_pre_laudo_data.py
```

Resultado esperado:

- atualizar ou recriar o caso canônico NR35 do mobile;
- manter `laudo_id = 4` como principal referência de teste, salvo mudança futura do banco.

### Passo 3. Reinstalar o app no aparelho

No diretório `android`:

```bash
npm run android:preview
```

### Passo 4. Validar o smoke principal do pré-laudo no USB

No diretório `android`:

```bash
npm run maestro:pre-laudo:resume -- --device RQCW20887GV
```

Isso deve validar:

- card canônico;
- ida para mesa;
- abertura do quality gate.

### Passo 5. Acoplar as imagens sintéticas ao caso

Próxima frente prática:

- usar o bundle em `.tmp_online/vision-fixtures/industrial_inspection_2026_04_13/`;
- anexar essas imagens ao caso canônico;
- validar se elas aparecem em:
  - `analysis_basis`
  - `pre_laudo_document`
  - `registros_fotograficos`
  - PDF final

### Passo 6. Fechar a emissão final

Depois do passo visual:

- abrir quality gate;
- confirmar finalização do caso;
- emitir o PDF;
- validar estado `emitido` no mobile;
- validar download/abertura do documento.

## Próxima sequência recomendada

1. criar o seed/anexo E2E com as imagens sintéticas já geradas;
2. validar `analysis_basis -> pre_laudo_document -> PDF`;
3. testar finalização real do caso no mobile;
4. validar download/abertura do PDF emitido;
5. só depois fazer a rodada física de câmera/galeria/upload real.

## Resumo curto

O núcleo mais importante já está de pé:

- backend canônico do pré-laudo;
- mobile consumindo esse contrato;
- card canônico no chat;
- `next_questions`, mesa e quality gate funcionando no aparelho.

O que falta agora não é mais estrutura básica. O que falta é fechar a última milha:

- evidência visual real entrando no caso;
- pré-laudo virando documento cada vez mais completo;
- emissão final do PDF validada de ponta a ponta.
