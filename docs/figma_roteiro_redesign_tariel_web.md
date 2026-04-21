# Roteiro de Figma para Redesign do Web da Tariel

## Objetivo
Usar o Figma como ferramenta de direção visual e aprovação de layout, sem quebrar o backend atual da Tariel.

Regra principal:
- o Figma define visual, hierarquia, organização e copy
- o código real continua sendo implementado no projeto existente
- formulários, rotas, `id`, `name`, `data-*` e integrações JS não devem ser reinventados no Figma

## Como usar este roteiro
Você não precisa desenhar o sistema inteiro de uma vez.

Faça em ondas:
1. `Portal do Inspetor - Home`
2. `Portal do Inspetor - Workspace`
3. `Modal Nova inspeção`
4. `Mesa Avaliadora`
5. `Logins`
6. `Admin-Geral`
7. `Admin-Cliente`

## Estrutura recomendada do arquivo no Figma
Crie 1 página chamada:
- `Tariel Web Redesign`

Dentro dela, crie estes frames:
1. `00 - Foundation`
2. `01 - Inspetor Home`
3. `02 - Inspetor Workspace`
4. `03 - Modal Nova Inspecao`
5. `04 - Mesa Avaliadora`
6. `05 - Login Inspetor`
7. `06 - Login Mesa`
8. `07 - Admin Geral`
9. `08 - Admin Cliente`

## 00 - Foundation
Essa página serve para definir o sistema visual antes das telas.

Monte estes blocos:
- paleta principal
- paleta de superfícies
- tipografia
- botões
- inputs
- cards
- sidebar
- topbar
- modal
- tabela/lista
- chips/status

O mínimo que precisa existir:
- cor de fundo principal
- cor de superfícies secundárias
- cor primária de CTA
- cor de texto principal
- cor de texto secundário
- cor de borda
- cor de sucesso
- cor de aviso
- cor de erro

Tipografia:
- `Display / H1`
- `H2`
- `H3`
- `Body`
- `Small`
- `Label`

Componentes mínimos:
- botão primário
- botão secundário
- input normal
- input focus
- textarea
- select
- card de lista
- card de destaque
- modal
- badge de status

## 01 - Inspetor Home
Função:
- ser a primeira tela após login
- separar claramente início de trabalho e retomada de laudo

Essa tela precisa ter:
- hero principal
- CTA `Nova inspeção`
- CTA `Ver histórico`
- botão ou bloco `Última inspeção`
- seção `Laudos recentes`
- seção `Modelos para nova inspeção`
- seção `Ferramentas rápidas`

Estrutura recomendada:
1. Hero
2. Laudos recentes
3. Modelos para nova inspeção
4. Ferramentas rápidas

Não colocar:
- sidebar operacional completa
- composer do chat
- painel técnico da mesa

No frame do Figma, desenhe:
- versão desktop
- versão tablet
- versão mobile

## 02 - Inspetor Workspace
Função:
- ser o ambiente de execução da inspeção ativa

Essa tela precisa ter:
- sidebar ou histórico lateral
- cabeçalho contextual do laudo
- feed central
- área de evidências ou blocos técnicos
- painel direito operacional
- composer sticky no rodapé

O workspace deve responder visualmente a:
- inspeção ativa
- status do laudo
- pendências
- interação com mesa

## 03 - Modal Nova Inspecao
Função:
- criar uma inspeção com o mínimo de dados necessários
- levar o usuário para a coleta

Esse modal precisa ter:
- título curto
- texto de apoio curto
- `Modelo técnico`
- `Cliente`
- `Unidade`
- `Local inspecionado`
- `Objetivo e escopo inicial`
- preview de `Nome da inspeção`
- botão secundário `Cancelar`
- botão primário `Criar inspeção e iniciar coleta`

Regras:
- uma coluna
- largura confortável
- sem alertas desnecessários
- hierarquia simples

## 04 - Mesa Avaliadora
Função:
- revisão técnica
- resposta operacional
- aprovação e devolução

Essa tela precisa ter:
- fila ou lista de laudos
- painel central com contexto e mensagens
- painel de decisão
- status
- histórico auditável
- composer ou resposta técnica

Tom visual:
- técnico
- corporativo
- controlado
- menos marketing

## 05 e 06 - Logins
Separar:
- `Login Inspetor`
- `Login Mesa`

Cada um deve ter:
- painel esquerdo
- painel direito
- título curto
- subtítulo operacional
- email
- senha
- lembrar-me
- recuperar senha
- botão principal
- SSO, se existir

Evitar:
- excesso de explicação
- atalhos internos de outros portais
- linguagem promocional

## 07 - Admin Geral
Função:
- gestão do sistema
- gestão de empresas
- planos
- usuários
- auditoria

Precisa ter:
- navegação lateral
- cabeçalho
- filtros
- tabela/lista principal
- cards de resumo
- ações administrativas

## 08 - Admin Cliente
Função:
- gestão da empresa cliente
- usuários internos
- consumo/plano
- auditoria básica

Precisa ter:
- shell do sistema
- resumo
- usuários
- ações da empresa
- histórico

## Ordem recomendada de produção
Se fizer tudo de uma vez, a chance de se perder é alta.

Faça nesta ordem:
1. `00 - Foundation`
2. `01 - Inspetor Home`
3. `03 - Modal Nova Inspecao`
4. `02 - Inspetor Workspace`
5. `04 - Mesa Avaliadora`
6. `05 - Login Inspetor`
7. `06 - Login Mesa`
8. `07 - Admin Geral`
9. `08 - Admin Cliente`

## Tamanho dos frames
Use estes tamanhos:
- desktop: `1440 x auto`
- tablet: `1024 x auto`
- mobile: `390 x auto`

## O que me mandar depois
Você não precisa me mandar o arquivo inteiro do Figma.

Pode me mandar qualquer um destes:
- print do frame
- export PNG
- export PDF
- link do frame
- print com medidas e textos

O melhor formato para eu implementar rápido é:
1. nome da tela
2. print da tela
3. o que você gostou nela
4. o que não pode perder funcionalmente

## O que eu faço com isso
Quando você me mandar o frame, eu faço:
1. leio a estrutura visual
2. identifico o que pode ser aplicado sem quebrar backend
3. adapto no HTML/CSS/JS real da Tariel
4. valido a tela localmente
5. refino até fechar

## Regras de segurança para não quebrar o sistema
Mesmo com redesign forte, estas regras continuam:
- não quebrar formulários existentes
- não quebrar login
- não quebrar chat
- não quebrar modal de criação
- não quebrar mesa avaliadora
- não remover hooks usados pelo JS
- não alterar backend por estética

## Critério de qualidade
Um frame do Figma está bom quando:
- a função da tela está clara em 3 segundos
- o CTA principal é óbvio
- o layout tem hierarquia real
- a interface parece software real, não mockup genérico
- o visual é consistente com o restante do sistema

## Caminho mais simples para começar
Se quiser começar sem complicar:
1. faça `00 - Foundation`
2. faça `01 - Inspetor Home`
3. faça `03 - Modal Nova Inspecao`
4. me mande esses 3 frames

Com isso já dá para virar o produto para uma nova linguagem visual.
