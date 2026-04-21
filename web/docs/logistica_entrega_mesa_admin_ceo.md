# Logistica de Entrega da Mesa e do Admin-CEO

Documento curto para alinhar como a entrega passa a funcionar operacionalmente depois da reestruturacao.

## Autoridade

O fluxo agora parte de uma autoridade central:

- `Admin-CEO` cria e publica a familia oficial;
- `Admin-CEO` libera familia e template por empresa;
- a empresa nao vira dona da estrutura tecnica;
- a `Mesa Avaliadora` opera em cima do catalogo liberado.

## Objetos de entrega

Toda nova entrega comercial deve sair nestas quatro camadas:

1. familia oficial no catalogo Tariel;
2. politica de revisao e evidencia da familia;
3. liberacao da familia para a empresa;
4. liberacao dos codigos de template que podem operar nessa empresa.
5. emissao final versionada com trilha auditavel.

Sem isso, o template pode existir no tenant, mas nao deve ser tratado como liberado para binding canônico.

## Fluxo pratico por empresa

1. Tariel define o recorte do piloto.
   Exemplo: `nr13_vaso_pressao`.

2. Admin-CEO importa a familia canonica do repositorio para o catalogo.
   Aqui entram `family_key`, politica de evidencia, seed de saida e regra de revisao.

3. Admin-CEO bootstrapa o `template_master` canonico no tenant.
   O template entra como base operacional inicial da familia, preferencialmente em `rascunho`.

4. Admin-CEO libera a familia para a empresa.
   Aqui entram observacoes comerciais e, se necessario, a lista dos codigos permitidos naquele rollout.

5. Admin-CEO libera os codigos de template.
   Isso fecha o que a empresa pode de fato usar no binding documental.

6. Mesa opera o caso com `family_lock`.
   Pendencia, evidencia, bloqueio e override passam a existir por caso, nao por chat solto.

7. Documento final e emitido em armazenamento versionado.
   Cada emissao gera uma versao explicita (`v0001`, `v0002`...), `manifest.json`, snapshot do payload e registro auditavel no banco.

## Regra de rollout

A entrega recomendada e gradual:

- primeiro liberar a familia;
- depois liberar um conjunto pequeno de templates;
- operar casos reais com a Mesa estruturada;
- emitir e revisar pelo menos uma versao final auditada;
- so entao ampliar o pacote de codigos para a empresa.

## Papel da Mesa

A Mesa nao e mais o lugar onde a regra nasce.

A Mesa:

- valida evidencia;
- abre pendencia estruturada;
- detecta desvio de escopo;
- decide quando o caso esta pronto para aprovar;
- registra override quando realmente precisar sair da trilha.

## Critério de entrega fechada

Uma entrega so pode ser considerada fechada quando:

- a familia oficial existe no catalogo;
- a empresa recebeu liberacao formal;
- o binding do template respeita essa liberacao;
- o caso da Mesa ja expõe bloqueios e prontidao operacional;
- a aprovacao deixa de depender de leitura manual de chat solto;
- o PDF final fica rastreavel por versao, sem depender de `/tmp`.
