# Mobile Lote 1 Acceptance Checklist

Status: aberto
Data de referência: 2026-04-14

## Regras

- este checklist representa o mínimo para declarar o lote 1 pronto para revisão humana;
- o agente só deve marcar um item como concluído quando houver evidência concreta no código, teste, log ou documento;
- itens marcados aqui precisam ser refletidos também no relatório de entrega do lote 1.

## Baseline e estabilidade

- [x] `make mobile-ci` está verde
- [ ] recorte web/mobile crítico está verde
- [ ] `make smoke-mobile` está verde quando a lane estiver disponível
- [ ] não há bug silencioso conhecido em login, upload, geração de PDF, abertura de PDF, histórico, finalização ou persistência de estado

## Chat livre e PDF

- [ ] o chat livre aceita até 10 fotos e bloqueia acima desse limite
- [ ] fotos redundantes são tratadas como ângulos complementares, sem análise repetitiva
- [ ] o fluxo `chat -> fotos -> análise -> PDF` está operacional no emulador
- [ ] o PDF do chat livre contém capa, sumário, contexto, evidências fotográficas, análise técnica, achados, recomendações e conclusão
- [ ] o PDF do chat livre abre corretamente pelo app / fluxo autenticado
- [ ] o histórico reabre a conversa e mantém o documento gerado

## Guiado e templates prioritários

- [ ] `NR10` está operacional no lote 1
- [ ] `NR12` está operacional no lote 1
- [ ] `NR13` está operacional no lote 1
- [ ] `NR35` está operacional no lote 1
- [ ] quando uma evidência não corresponde ao campo esperado, o sistema marca o estado como `incompatível`
- [ ] o fluxo guiado gera laudos organizados, padronizados e profissionais nas famílias do lote 1

## Configurações

- [ ] perfil e conta operacional estão funcionando corretamente
- [ ] preferências da IA e do relatório estão funcionando corretamente
- [ ] segurança, sessão e permissões estão funcionando corretamente
- [ ] exportação, downloads e histórico documental estão funcionando corretamente
- [ ] diagnóstico e suporte operacional estão funcionando corretamente

## UX premium

- [ ] login tem visual limpo e coerente com o produto industrial
- [ ] chat principal está em padrão visual premium
- [ ] finalizar / PDF está em padrão visual premium
- [ ] configurações estão em padrão visual premium
- [ ] histórico / menu lateral está em padrão visual premium

## Evidências e documentação

- [ ] o relatório de entrega do lote 1 está preenchido com evidências reais
- [ ] riscos residuais foram documentados explicitamente
- [ ] ideias novas fora do contrato foram registradas no backlog de ideias
