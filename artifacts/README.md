# Artifacts Locais

Este diretório é reservado para outputs operacionais locais gerados por runners, smokes, validações e revisões.

Regras:

- o formato canônico é `artifacts/<lane>/<timestamp>/`
- outputs novos são locais e não devem ser commitados
- apenas este `README.md` e `.gitignore` ficam versionados
- se um artifact precisar ser citado em documentação, cite o caminho absoluto do diretório gerado, sem tentar promover o conteúdo bruto ao Git

Quando a evidência precisar ser durável para o time:

- promover um resumo humano em `docs/`
- promover contratos, fixtures pequenas ou screenshots finais intencionais em diretórios próprios
- manter o payload bruto fora do fluxo normal do repositório
