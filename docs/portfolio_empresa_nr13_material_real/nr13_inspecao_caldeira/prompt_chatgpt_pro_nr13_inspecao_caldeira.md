# Prompt ChatGPT Pro - NR13 Inspecao de Caldeira

Cole o texto abaixo no ChatGPT Pro para gerar o pacote sintetico externo desta familia.

```text
Quero que você gere um pacote completo de referência sintética para a família Tariel `nr13_inspecao_caldeira`, com foco em uma carteira industrial profissional de inspeção NR13.

Contexto obrigatório:
considere um cenário profissional em que a empresa executante atua em:
- inspeção inicial, periódica e extraordinária;
- elaboração de laudos de conformidade;
- medições de espessura por ultrassom;
- calibração de válvulas de segurança e manômetros;
- emissão de laudos técnicos;
- emissão de livros de registro;
- testes hidrostáticos e de estanqueidade.

Regra de modelagem obrigatória:
- este pacote deve representar a família principal `nr13_inspecao_caldeira`;
- não misturar no documento principal outras famílias;
- ultrassom, calibração, testes e livro de registro entram como evidência, anexo, registro complementar ou recomendação futura, não como família principal misturada ao laudo;
- o documento deve parecer um laudo real e vendável de inspeção industrial.

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
- `output/nr13_inspecao_caldeira/assets/`
- `output/nr13_inspecao_caldeira/pdf/`
- `output/nr13_inspecao_caldeira/manifest.json`
- `output/nr13_inspecao_caldeira/tariel_filled_reference_bundle.json`
- `output/nr13_inspecao_caldeira/pdf/nr13_inspecao_caldeira_referencia_sintetica.pdf`

Regras obrigatórias:
- tudo deve ser sintético, mas com aparência realista e profissional;
- não usar marcas reais;
- usar nomes, ARTs, códigos, números e empresa fictícios, mas plausíveis;
- o PDF deve parecer laudo técnico corporativo brasileiro de NR13;
- inserir as imagens dentro do PDF, não apenas citar os nomes;
- todo o conteúdo deve estar em português do Brasil;
- incluir discretamente no rodapé ou metadados a marcação `REFERÊNCIA SINTÉTICA`, sem destruir o aspecto profissional;
- cabeçalho e rodapé em todas as páginas;
- paginação no formato `X/Y`;
- tabelas técnicas legíveis;
- nenhuma foto sem legenda;
- nenhuma conclusão sem amarração com achado/evidência;
- linguagem objetiva, auditável e curta;
- aparência de documento técnico industrial sério e comercialmente utilizável.

Família alvo:
- `family_key`: `nr13_inspecao_caldeira`
- `template_code`: `nr13_caldeira`

Caso técnico sintético obrigatório:
- caldeira industrial flamotubular ou aquatubular de médio porte;
- inspeção periódica em casa de caldeiras de unidade industrial;
- identificação da caldeira registrada;
- código interno do ativo;
- localização definida;
- vista geral da caldeira registrada;
- painel e comandos registrados;
- indicador de nível presente;
- manômetro presente;
- válvula ou dispositivo de segurança presente;
- condição geral estrutural adequada;
- integridade aparente preservada;
- marcas leves de fuligem em trecho da exaustão;
- desgaste localizado do revestimento externo do isolamento térmico;
- queimador ou sistema térmico registrado;
- prontuário disponível;
- certificado não apresentado em campo;
- relatório anterior disponível;
- recomendação de recomposição do revestimento externo do isolamento e acompanhamento do trecho com fuligem;
- conclusão final com status `ajuste`.

Empresa sintética:
- cliente: `Planta Industrial Modelo do Centro Ltda.`
- unidade: `Casa de Caldeiras - Unidade Norte`
- engenheiro responsável: nome sintético brasileiro
- inspetor líder: nome sintético brasileiro
- CREA/ART sintéticos
- laudo ID sintético no padrão brasileiro

Imagens PNG obrigatórias geradas por você:
1. `IMG_021_vista_geral_caldeira.png`
   descrição:
   foto realista de caldeira industrial de médio porte instalada em casa de caldeiras, ambiente técnico industrial, tubulações, estrutura metálica e instrumentação visível, aparência de inspeção de campo.

2. `IMG_022_painel_comandos.png`
   descrição:
   close-up técnico do painel frontal e comandos principais da caldeira, botões, indicadores e comandos industriais, foto documental.

3. `IMG_023_indicador_nivel.png`
   descrição:
   close-up do indicador de nível da caldeira, instrumento industrial montado no equipamento, foto realista de inspeção.

4. `IMG_024_fuligem_exaustao.png`
   descrição:
   detalhe técnico de marcas leves de fuligem em trecho aparente da exaustão ou chaminé da caldeira, aparência realista e moderada, sem exagero.

5. `IMG_025_isolamento_termico.png`
   descrição:
   close-up do revestimento externo do isolamento térmico com desgaste localizado, aparência de manutenção pendente, foto técnica objetiva.

6. `IMG_026_queimador_sistema_termico.png`
   descrição:
   detalhe do queimador ou frente do sistema térmico da caldeira, fotografia industrial de inspeção, enquadramento técnico.

7. `IMG_027_dispositivo_seguranca.png`
   descrição:
   close-up de dispositivo de segurança da caldeira, válvula ou instrumentação de segurança, foto documental.

8. `IMG_028_manometro.png`
   descrição:
   close-up de manômetro analógico industrial instalado na caldeira, visor legível, aparência de vistoria técnica.

Regras visuais das imagens:
- estilo foto de inspeção industrial real;
- sem estética publicitária;
- sem logos reais;
- sem texto decorativo excessivo;
- consistência entre as imagens, como se fossem do mesmo ativo e da mesma vistoria;
- aparência de laudo profissional de integridade e inspeção.

Estrutura obrigatória do PDF:
1. capa / folha de rosto
2. controle documental / ficha da inspeção
3. objeto, escopo, base normativa e limitações
4. metodologia, condições operacionais e equipe
5. identificação técnica da caldeira
6. inspeção visual e integridade aparente
7. dispositivos de segurança e controles
8. documentação, registros e evidências
9. não conformidades, criticidade e recomendações
10. conclusão, parecer e próxima ação
11. governança da Mesa
12. assinaturas e responsabilidade técnica
13. anexos e referências

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
- linguagem técnica curta e auditável
- menção controlada a prontuário e relatório anterior
- espaço para recomendação de próxima verificação ou continuidade operacional

Contrato obrigatório de `manifest.json`:
- `schema_type`: `filled_reference_package_manifest`
- `schema_version`: `1`
- `family_key`: `nr13_inspecao_caldeira`
- `package_status`: `synthetic_baseline`
- `source_kind`: `synthetic_repo_baseline`
- `bundle_file`: `tariel_filled_reference_bundle.json`
- `reference_count`: `1`

Contrato obrigatório de `tariel_filled_reference_bundle.json`:
- `schema_type`: `tariel_filled_reference_bundle`
- `schema_version`: `1`
- `family_key`: `nr13_inspecao_caldeira`
- `template_code`: `nr13_caldeira`
- `reference_id`: `nr13_inspecao_caldeira.synthetic.v1`
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
- `caracterizacao_do_equipamento`
- `inspecao_visual`
- `dispositivos_e_controles`
- `documentacao_e_registros`
- `nao_conformidades`
- `recomendacoes`
- `conclusao`

No `laudo_output_snapshot`, incluir coerentemente:
- identificação da caldeira
- localização
- placa ou identificador quando aplicável
- vista geral da caldeira
- descrição sumária
- condição de operação no momento
- condição geral
- integridade aparente
- painel e comandos
- indicador de nível
- queimador ou sistema térmico
- manômetro
- dispositivos de segurança
- pontos de vazamento ou fuligem
- isolamento térmico
- prontuário
- certificado
- relatório anterior
- não conformidade principal
- recomendação
- conclusão técnica
- justificativa
- status `ajuste`

Quero consistência com uma carteira profissional de inspeção industrial:
- documento com cara de serviço de inspeção industrial vendável;
- sem aparência de demo genérica;
- sem misturar este laudo com teste hidrostático, estanqueidade ou livro de registro como se fossem o mesmo produto;
- esses itens podem aparecer apenas como apoio, histórico, referência ou recomendação.

No final:
- gere todos os arquivos;
- me entregue os links ou arquivos;
- se possível, compacte tudo em um ZIP também.
Se alguma ferramenta falhar, continue e produza os arquivos por outro meio dentro do seu ambiente.
```
