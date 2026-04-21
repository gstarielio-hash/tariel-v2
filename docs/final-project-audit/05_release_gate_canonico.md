# Gate canonico de release do Tariel

Data: 2026-04-04
Atualizado na Execucao 3 - estabilizacao do host Android do gate real e fechamento da lane mobile

## Resposta objetiva

O Tariel tem dois gates canonicos formais:

1. `make release-gate-hosted`
2. `make release-gate`

Eles continuam com papeis diferentes.

## Gate hospedado canonico

Comando:

```bash
make release-gate-hosted
```

Composicao:

- `make verify`
- `make mesa-acceptance`
- `make document-acceptance`
- `make observability-acceptance`

Papel:

- gate oficial executavel em CI hospedada
- valida o pronto hospedado do produto sem depender de Android real

## Gate real canonico

Comando:

```bash
make release-gate
```

Composicao:

- `make release-gate-hosted`
- `make smoke-mobile`

Papel:

- unico gate que representa pronto real de ponta a ponta
- o mobile real continua obrigatorio

## Estado atualizado

Executado verde nesta fase:

- `make smoke-mobile` em multiplas rodadas oficiais
- `make release-gate`

Leitura correta hoje:

- o gate hospedado continua sendo o gate da CI
- o gate real ficou verde no host atual apos a estabilizacao do host Android
- hosted CI continua nao substituindo a lane mobile real

## Conclusao

Hoje o gate real do produto esta operacional e validado no host local atual.

Para investigacao de host/lane mobile, consulte:

- `docs/final-project-audit/06_mobile_host_stabilization.md`
- `docs/developer-experience/05_mobile_real_lane_debugging.md`
