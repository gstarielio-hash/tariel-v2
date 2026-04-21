# Piloto NR35 Linha de Vida

Data: 2026-04-05

## Template de referência

- Arquivo piloto escolhido: `Templates/WF-MC-115-04-23-1.pdf`
- Motivo: é o exemplar mais recente da pasta e segue o mesmo layout estrutural dos demais laudos NR35 de linha de vida.
- Tipo canônico no sistema: `nr35_linha_vida`

## Estrutura real do laudo

O modelo observado nos PDFs reais converge para estes blocos:

1. Identificação geral
   - unidade
   - local
   - número do laudo do fabricante
   - número do laudo de inspeção
   - número da ART
   - contratante
   - contratada
   - engenheiro responsável
   - inspetor líder
   - data da vistoria

2. Objeto da inspeção
   - identificação da linha de vida
   - tipo do ativo: `Vertical`, `Horizontal` ou `Ponto de Ancoragem`
   - escopo resumido da inspeção

3. Componentes / acessórios inspecionados
   - fixação dos pontos
   - condição do cabo de aço
   - condição do esticador
   - condição da sapatilha
   - condição do olhal
   - condição dos grampos
   - cada item precisa de `condicao` (`C`, `NC`, `N/A`) e observação opcional

4. Registros fotográficos
   - título curto
   - legenda curta
   - referência do anexo

5. Conclusão
   - status: `Aprovado`, `Reprovado` ou `Pendente`
   - próxima inspeção periódica
   - observações finais
   - resumo executivo

## Mapeamento para o mobile guiado

As etapas do checklist guiado do app foram alinhadas a esse laudo:

1. `identificacao_laudo`
   - preenche metadados iniciais e referência do ativo
2. `contexto_vistoria`
   - fecha responsáveis e data da vistoria
3. `objeto_inspecao`
   - classifica o tipo da linha de vida e o escopo
4. `componentes_inspecionados`
   - fecha os seis itens C/NC/N/A
5. `registros_fotograficos`
   - amarra fotos e legendas ao relatório
6. `conclusao`
   - fecha status, próxima inspeção e observações

## Artefatos de código ligados a este piloto

- Schema backend: `web/app/domains/chat/templates_ai.py`
  - `RelatorioNR35LinhaVida`
- Alias e nome do template: `web/app/domains/chat/normalization.py`
- Regra mínima de gate e roteiro de coleta: `web/app/domains/chat/gate_helpers.py`
- Checklist guiado do mobile: `android/src/features/inspection/guidedInspection.ts`

## Limitação técnica atual

O renderer atual de preview em PDF baseado em overlay textual ainda não insere imagens dinâmicas.

Isso significa:

- já é possível estruturar `dados_formulario` do laudo NR35;
- ainda falta a etapa de materialização rica das fotos no template final;
- para o PDF final deste piloto, o próximo slice deve incluir suporte a imagens ou um template editor mais adequado para blocos fotográficos.

## Próximos passos do MVP

1. Persistir a sessão guiada do mobile no backend.
2. Transformar anexos do chat em `registros_fotograficos` estruturados.
3. Gerar `dados_formulario` do laudo a partir da coleta guiada.
4. Exibir revisão dos campos antes da emissão.
5. Materializar preview/PDF com suporte aos blocos fotográficos.
6. Aplicar a política: emitir no mobile ou enviar para mesa.
