# Prompt ChatGPT Pro - NR10 Inspecao instalacoes eletricas

Cole o texto abaixo no ChatGPT Pro para gerar o pacote sintetico externo desta familia.

```text
Quero que você gere um pacote completo de referência sintética para a família Tariel `nr10_inspecao_instalacoes_eletricas`.

Contexto obrigatório:
considere um cenário profissional de inspeção técnica de instalações elétricas industriais, com RTI como referência comercial típica, mas sem vincular o material a nenhuma empresa real.

Regra de modelagem obrigatória:
- este pacote deve representar a família principal `nr10_inspecao_instalacoes_eletricas`;
- não misturar este documento principal com PIE, SPDA ou LOTO como se fossem a mesma entrega;
- PIE, diagrama unifilar, relatório anterior ou documento base podem aparecer como apoio documental ou anexo;
- o documento deve parecer um laudo real e vendável de inspeção elétrica industrial.

Você deve FAZER os arquivos, não apenas descrever.
Use suas ferramentas de geração de imagem e geração de arquivos.
Se necessário, use Python internamente para montar o PDF final.
Não quero pseudocódigo.
Não quero resumo.
Não quero explicação.
Quero os artefatos prontos para download.

Objetivo:
criar um pacote sintético profissional, visualmente convincente, em português do Brasil, com:
- imagens PNG geradas por você
- PDF técnico completo com as imagens incorporadas
- `manifest.json`
- `tariel_filled_reference_bundle.json`

Estrutura de saída obrigatória:
- `output/nr10_inspecao_instalacoes_eletricas/assets/`
- `output/nr10_inspecao_instalacoes_eletricas/pdf/`
- `output/nr10_inspecao_instalacoes_eletricas/manifest.json`
- `output/nr10_inspecao_instalacoes_eletricas/tariel_filled_reference_bundle.json`
- `output/nr10_inspecao_instalacoes_eletricas/pdf/nr10_inspecao_instalacoes_eletricas_referencia_sintetica.pdf`

Regras obrigatórias:
- tudo deve ser sintético, mas com aparência realista e profissional;
- não usar marcas reais;
- usar nomes, ARTs, códigos, números e empresa fictícios, mas plausíveis;
- o PDF deve parecer laudo técnico corporativo brasileiro de inspeção elétrica;
- inserir as imagens dentro do PDF, não apenas citar os nomes;
- todo o conteúdo deve estar em português do Brasil;
- incluir discretamente no rodapé ou metadados a marcação `REFERÊNCIA SINTÉTICA`, sem destruir o aspecto profissional;
- cabeçalho e rodapé em todas as páginas;
- paginação no formato `X/Y`;
- tabelas técnicas legíveis;
- nenhuma foto sem legenda;
- nenhuma conclusão sem amarração com achado/evidência;
- linguagem objetiva, auditável e curta.

Família alvo:
- `family_key`: `nr10_inspecao_instalacoes_eletricas`
- `template_code`: `nr10_inspecao_instalacoes_eletricas`

Caso técnico sintético obrigatório:
- inspeção técnica de instalação elétrica de baixa tensão em unidade industrial;
- área principal com painel geral de distribuição e quadro secundário;
- identificação do objeto e da localização registradas;
- verificação visual de quadro elétrico principal;
- verificação visual de quadro secundário ou circuito associado;
- barramento de aterramento registrado;
- proteção e organização geral observadas;
- diagrama unifilar disponível como documento base;
- relatório anterior disponível;
- uma não conformidade principal de média severidade;
- a não conformidade principal deve ser: abertura sem vedação adequada ou ausência pontual de identificação em circuito/painel;
- a conclusão final deve ficar com status `ajuste`;
- a recomendação deve exigir correção localizada, atualização documental e nova verificação.

Empresa sintética:
- cliente: `Planta Industrial Modelo do Centro Ltda.`
- unidade: `Unidade Industrial Leste`
- engenheiro responsável: nome sintético brasileiro
- inspetor líder: nome sintético brasileiro
- CREA/ART sintéticos
- laudo ID sintético no padrão brasileiro

Imagens PNG obrigatórias geradas por você:
1. `IMG_301_vista_geral_sala_eletrica.png`
   descrição:
   foto realista da sala elétrica industrial com painel principal e ambiente técnico organizado, aparência de inspeção de campo.

2. `IMG_302_painel_principal_frontal.png`
   descrição:
   vista frontal do painel geral de distribuição, com identificação industrial e aspecto documental.

3. `IMG_303_painel_interno.png`
   descrição:
   painel elétrico aberto mostrando componentes internos, organização de cabos e dispositivos, aparência de inspeção técnica real.

4. `IMG_304_nao_conformidade_identificacao_ou_abertura.png`
   descrição:
   close-up técnico da não conformidade principal, podendo ser ausência de identificação em circuito ou abertura sem vedação adequada no painel.

5. `IMG_305_barramento_aterramento.png`
   descrição:
   detalhe do barramento de aterramento ou ponto equivalente, fotografia técnica objetiva.

6. `IMG_306_documento_base_unifilar.png`
   descrição:
   representação visual realista de diagrama unifilar impresso ou documento técnico de apoio associado à instalação.

Regras visuais das imagens:
- estilo foto de inspeção industrial real;
- sem estética publicitária;
- sem logos reais;
- sem texto decorativo excessivo;
- consistência entre as imagens, como se fossem da mesma vistoria;
- aparência de laudo profissional de NR10.

Estrutura obrigatória do PDF:
1. capa / folha de rosto
2. controle documental / ficha da inspeção
3. objeto, escopo, base normativa e limitações
4. metodologia, execução e equipe
5. identificação da instalação / painéis inspecionados
6. verificações visuais e condição geral
7. documentação e registros avaliados
8. não conformidades, criticidade e recomendações
9. conclusão técnica
10. governança da Mesa
11. assinaturas e responsabilidade técnica
12. anexos e referências

No PDF, incluir:
- código documental
- revisão
- data da inspeção
- data da emissão
- cliente
- unidade
- responsável técnico
- inspetor líder
- ART sintética
- status final
- referências cruzadas das imagens
- menção a diagrama unifilar e relatório anterior como documentos de apoio

Contrato obrigatório de `manifest.json`:
- `schema_type`: `filled_reference_package_manifest`
- `schema_version`: `1`
- `family_key`: `nr10_inspecao_instalacoes_eletricas`
- `package_status`: `synthetic_baseline`
- `source_kind`: `synthetic_repo_baseline`
- `bundle_file`: `tariel_filled_reference_bundle.json`
- `reference_count`: `1`

Contrato obrigatório de `tariel_filled_reference_bundle.json`:
- `schema_type`: `tariel_filled_reference_bundle`
- `schema_version`: `1`
- `family_key`: `nr10_inspecao_instalacoes_eletricas`
- `template_code`: `nr10_inspecao_instalacoes_eletricas`
- `reference_id`: `nr10_inspecao_instalacoes_eletricas.synthetic.v1`
- `source_kind`: `synthetic_repo_baseline`
- `reference_summary`
- `required_slots_snapshot`
- `documental_sections_snapshot`
- `notes`
- `laudo_output_snapshot`

No `laudo_output_snapshot`, usar estrutura coerente com:
- `tokens`
- `case_context`
- `mesa_review`
- `resumo_executivo`
- `identificacao`
- `escopo_servico`
- `execucao_servico`
- `evidencias_e_anexos`
- `documentacao_e_registros`
- `nao_conformidades_ou_lacunas`
- `recomendacoes`
- `conclusao`

No final:
- gere todos os arquivos;
- me entregue os links ou arquivos;
- se possível, compacte tudo em um ZIP também.
Se alguma ferramenta falhar, continue e produza os arquivos por outro meio dentro do seu ambiente.
```
