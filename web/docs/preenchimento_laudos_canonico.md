# Preenchimento Canônico de Laudos

Documento curto de referência para a frente de laudos no estado atual do `Tariel Control Consolidado`.

Este arquivo substitui checkpoints longos e só registra o que está implementado hoje, o que continua como direção correta e o que ainda não existe no código.

## Decisões que continuam corretas

- O núcleo do produto é transformar um caso real de inspeção em laudo formal consistente.
- A IA não deve escrever PDF bruto diretamente.
- O caminho certo é separar caso, estrutura documental e materialização final.
- O `editor_rico` da Mesa continua sendo a melhor base para templates semânticos.
- PDF final é saída; não é a fonte de verdade do preenchimento.

## Estado real hoje

### Templates e normalização

Fonte de verdade: `app/domains/chat/normalization.py`

Tipos de template ativos no código:

- `cbmgo`
- `rti` e alias `nr10_rti`
- `nr13` e alias `nr13_caldeira`
- `nr12maquinas` e alias `nr12_maquinas`
- `spda`
- `pie`
- `avcb`
- `padrao`

Ponto importante:

- `nr35_linha_vida` não está hoje no catálogo canônico de templates.
- Se NR35 voltar como família oficial, primeiro ela precisa entrar em normalização, gate e binding de template.

### Gate de qualidade

Fonte de verdade: `app/domains/chat/gate_helpers.py`

Hoje já existem regras mínimas por template para:

- textos mínimos;
- evidências mínimas;
- fotos mínimas;
- respostas IA mínimas;
- exigência ou não de `dados_formulario`.

O gate continua sendo o bloqueio funcional real antes do envio para a Mesa.

### Geração estruturada via IA

Fontes de verdade:

- `app/domains/chat/templates_ai.py`
- `app/domains/chat/report_finalize_stream_shadow.py`

Hoje a estruturação explícita por schema existe de forma concreta para `cbmgo`.

Isto significa:

- já existe modelo estruturado Pydantic real para esse caso;
- ainda não existe registry genérico e versionado de schemas para todas as famílias;
- o checkpoint antigo extrapolava a cobertura real quando tratava isso como capacidade geral.

### Materialização de template

Fontes de verdade:

- `app/domains/revisor/templates_laudo_editor_routes.py`
- `nucleo/template_editor_word.py`
- `nucleo/template_laudos.py`
- `app/v2/document/template_binding.py`

Estado atual:

- `editor_rico` já suporta documento semântico, `documento_editor_json`, assets do template e placeholders como `{{json_path:...}}` e `{{token:...}}`;
- `legado_pdf` continua suportado por overlay coordenado;
- o binding do template ativo já é resolvido por tenant, código e versão;
- o sistema atual é híbrido: `editor_rico` e `legado_pdf` coexistem de forma oficial.

Limite atual:

- ainda não existe suporte canônico a `{{evidence_image:...}}`;
- ainda não existe mapa formal de slots dinâmicos de imagem do caso;
- checkbox, imagem dinâmica e blocos repetíveis ainda não formam uma camada semântica unificada entre todos os renderers.

### Referencias preenchidas

Fontes de verdade:

- `app/domains/revisor/template_filled_reference_support.py`
- `app/domains/revisor/template_filled_reference_routes.py`
- `scripts/importar_referencias_preenchidas_zip.py`

Estado atual:

- a Mesa já consegue importar um pacote ZIP de `filled_reference`;
- o pacote vira uma base persistida por empresa em filesystem;
- o sistema já gera blueprints por família a partir dos laudos reais preenchidos;
- cada blueprint consolida `binding_path`, tipos de campo, grupos de checklist, slots de imagem e um `output_schema_seed`;
- a biblioteca da Mesa já tem uma tela própria para consultar esses blueprints antes do template vazio.

Isto fecha uma lacuna importante:

- os laudos preenchidos agora entram como base operacional real;
- eles deixam de ser só material externo e passam a alimentar a definição do `template_master`.

Limite atual:

- isso ainda não publica um `template_master` oficial por conta própria;
- o template vazio ainda precisa ser importado e validado depois;
- a ligação automática entre `filled_reference` e template vazio ainda não existe.

### Revisão e governança

Fontes de verdade:

- `app/v2/policy/models.py`
- `app/v2/policy/engine.py`
- `app/domains/revisor/reviewdesk_contract.py`

Estado atual:

- laudo ativo continua implicando revisão humana;
- o modo efetivo atual do policy engine é `mesa_required`;
- a Mesa continua sendo o fluxo principal de revisão;
- o portal cliente e o revisor já compartilham contrato da Mesa sem depender de HTTP interno do revisor.
- o desenho premium do mobile agora esta descrito em `web/docs/mobile_review_operating_model.md`.

Limite atual:

- `mobile_autonomous` ja aparece como sinal de policy e gate em partes do fluxo;
- a operacao premium com `mobile_review_allowed`, pacote movel de revisao e decisao organizada no app ainda precisa ser consolidada;
- allowlist, autonomia controlada e emissao sem Mesa continuam sendo frente governada, nao baseline geral.

## O que do checkpoint antigo ainda faz sentido

- defender um JSON canônico do laudo em vez de preencher PDF bruto;
- tratar template como camada de materialização;
- fortalecer o `editor_rico`;
- separar evidência, decisão técnica e renderização;
- manter governança forte para qualquer tentativa de autonomia no mobile.

## O que do checkpoint antigo não pode mais ser tratado como estado atual

- paths em `Tariel Control Consolidado`;
- referência a uma pasta `Templates` versionada no repositório como biblioteca oficial ativa;
- `nr35_linha_vida` como família já suportada no código atual;
- schema registry amplo já existente;
- `mobile_autonomous` como política já disponível;
- ideia de que o bundle completo do caso já está formalizado end-to-end.

## Lacunas reais que ainda faltam fechar

1. Registro canônico de família/versionamento de laudo, no estilo `Report Pack`.
2. Bundle formal do caso inteiro para finalização documental.
3. Schema canônico por família, além do caminho explícito já existente em `cbmgo`.
4. Slots semânticos de imagem e checklist no `editor_rico`.
5. Camada de renderização mais uniforme entre `editor_rico` e `legado_pdf`.
6. Governança real para autonomia mobile, se essa frente continuar.

## Ordem recomendada de implementação agora

1. Formalizar um registro de `Report Pack` em cima do que já existe.
2. Usar `cbmgo` como piloto do contrato canônico, porque ele já tem geração estruturada real.
3. Expandir o mesmo modelo para `nr12maquinas`.
4. Só então abrir novas famílias.
5. Se NR35 for prioridade de negócio, primeiro promover NR35 a template suportado no catálogo e no gate.
6. Usar `filled_reference` importado para derivar o blueprint da família antes de subir o template vazio.

## Regra de retomada

Se esta frente for retomada em outra sessão, partir por:

1. confirmar o catálogo atual em `normalization.py`;
2. confirmar o gate real em `gate_helpers.py`;
3. confirmar o binding e os modos `editor_rico`/`legado_pdf`;
4. só depois desenhar o próximo passo de schema por família.
