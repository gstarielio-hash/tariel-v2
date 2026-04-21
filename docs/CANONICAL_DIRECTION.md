# Direção Canônica

## Fonte de verdade

O produto Tariel tem uma única fonte de verdade:

- `Tariel Control Consolidado/`

Não existe mais workspace secundário de arquitetura nem frontend paralelo oficial.

## Estrutura oficial

- `web/`: backend FastAPI e frontend web oficial.
- `android/`: app mobile oficial do inspetor.
- `docs/`: documentação curta e canônica.
- `docs/family_schemas/`: JSONs canônicos de família.

## Documentos canônicos deste tema

- `web/docs/CANONICAL_SYSTEM.md`
- `docs/direcao_produto_laudos.md`
- `docs/roadmap_nrs_brasil.md`
- `docs/nr_programming_registry.json`
- `web/docs/portfolio_nacional_nrs_artefatos.md`
- `web/docs/portfolio_nacional_nrs_provisionamento.md`
- `web/docs/onda_1_homologacao_profissional.md`
- `web/docs/onda_2_homologacao_profissional.md`
- `web/docs/onda_3_homologacao_profissional.md`
- `web/docs/onda_4_fechamento_governanca.md`
- `docs/portfolio_empresa_nr13.md`
- `docs/family_schemas/README.md`
- `web/docs/preenchimento_laudos_canonico.md`
- `web/docs/nr13_inspecao_vaso_pressao_laudo_output_e_template.md`
- `web/docs/nr13_inspecao_caldeira_laudo_output_e_template.md`
- `web/docs/portfolio_empresa_nr13_artefatos.md`
- `web/docs/portfolio_empresa_nr13_provisionamento.md`
- `web/docs/portfolio_empresa_nr13_material_real.md`
- `web/docs/portfolio_empresa_nr13_material_sintetico_base.md`
- `web/docs/biblioteca_templates_inspecao_profissionais.md`
- `docs/portfolio_empresa_nr13_material_real/README.md`
- `web/docs/mesa_avaliadora.md`
- `web/docs/direcao_operacional_mesa.md`
- `web/docs/ordem_implementacao_mesa_laudos.md`
- `web/docs/logistica_entrega_mesa_admin_ceo.md`
- `web/docs/regras_de_encerramento.md`
- `web/docs/checklist_qualidade.md`

## Decisões fechadas

- A evolução segue como monólito modular.
- A Mesa continua no frontend web oficial do workspace `web/`.
- Todo código novo deve entrar em módulos explícitos de domínio, não em bridges improvisadas nem em wrappers de compatibilidade.
- `Tarie 2` passa a ser apenas arquivo histórico.

## O que não faz mais parte da linha oficial

- wrappers legados no root de `web/`;
- entradas desktop antigas;
- journals, handoffs, audits e prompts como documentação ativa;
- protótipos paralelos de frontend sem adoção oficial.

## Regras de documentação

Só manter documentação que sirva a pelo menos um destes objetivos:

- orientar setup e operação;
- explicar a arquitetura atual;
- registrar regra funcional ou operacional ainda válida.

Tudo que for histórico de execução, brainstorm, prompt de IA, checkpoint ou auditoria extensa deve sair do fluxo principal.

Checkpoints longos só sobrevivem se forem reduzidos e reescritos como documentação canônica curta, com paths atuais e distinção explícita entre:

- estado real já implementado;
- direção futura ainda não entregue.
