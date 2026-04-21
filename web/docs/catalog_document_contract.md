# Contrato Documental e Templates Mestres do Catálogo

Contrato oficial do pipeline `JSON -> template mestre -> PDF`.

## Regra estrutural

- o `laudo_output` canônico continua sendo a fonte de verdade do caso;
- o `template mestre` define a estrutura documental e a apresentação;
- a `família` aplica o overlay técnico do documento real;
- o `tenant` injeta branding, identidade documental e preferências controladas.

## Quatro camadas obrigatórias

- suficiência normativa;
- rastreabilidade técnica;
- evidência objetiva;
- apresentação documental profissional.

## Templates mestres

| ID | Tipo | Uso principal |
| --- | --- | --- |
| `inspection_conformity` | Laudo de inspeção de conformidade | inspeções de campo, checklist, conclusão, próxima inspeção |
| `risk_analysis` | Laudo de análise ou apreciação de risco | NR12, NR17, avaliações com matriz de risco |
| `integrity_specialized` | Laudo de integridade ou ensaio especializado | NR13 e END com medições, testes, anomalias e parecer |
| `controlled_permit` | Documento controlado por permissão | PET, permissões formais, validade, autorizados e encerramento |
| `technical_dossier` | Prontuário ou dossiê técnico | NR10, NR20 e pacotes documentais controlados |
| `program_plan` | Programa, plano ou inventário | NR1, NR7, NR18, NR31 e documentos de gestão |

## Estrutura universal

- capa / folha de rosto
- controle documental / sumário
- objeto, escopo, base normativa e limitações
- metodologia, instrumentos e equipe
- identificação técnica do objeto
- checklist técnico ou bloco analítico principal
- evidências / registros fotográficos
- não conformidades / criticidade
- conclusão
- recomendações / plano de ação
- assinaturas / responsabilidade técnica
- anexos

## Branding por tenant

Campos preparados no runtime:

- `tenant_branding.display_name`
- `tenant_branding.legal_name`
- `tenant_branding.cnpj`
- `tenant_branding.location_label`
- `tenant_branding.contact_name`
- `tenant_branding.confidentiality_notice`
- `tenant_branding.signature_status`
- `tenant_branding.logo_asset`

Tokens derivados para o renderer:

- `cliente_nome`
- `cliente_razao_social`
- `cliente_cnpj`
- `cliente_localizacao`
- `cliente_responsavel`
- `cliente_logo_asset_id`
- `confidencialidade_documento`
- `status_assinatura`
- `documento_codigo`
- `documento_revisao`
- `documento_titulo`
- `documento_tipo_mestre`

## Regra de emissão

O PDF não deve ser emitido quando houver:

- campo crítico ausente;
- checklist obrigatório incompleto;
- evidência mínima obrigatória ausente;
- conflito grave entre evidência e conclusão;
- família indefinida;
- pendência crítica em aberto.

## Modelo operacional

- `template mestre` não é duplicado a cada laudo;
- o caso persiste `template_id + versão` e o `laudo_output` final;
- a emissão gera uma instância materializada do documento;
- o PDF final e o snapshot do payload permanecem auditáveis.
