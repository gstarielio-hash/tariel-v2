# Mobile smoke real e gate de release

Data: 2026-04-04

Este documento registra a canonizacao do gate feita na Execucao 2.

Status operacional mais recente:

- consulte `docs/developer-experience/05_mobile_real_lane_debugging.md`
- consulte `docs/final-project-audit/06_mobile_host_stabilization.md`

## Comando oficial do mobile real

```bash
make smoke-mobile
```

Runner oficial:

- `scripts/run_mobile_pilot_runner.py`

Flow oficial:

- `android/maestro/mobile-v2-pilot-run.yaml`

## Gate oficial do produto

### Baseline rapida

```bash
make verify
```

### Gate hospedado da CI

```bash
make release-gate-hosted
```

### Gate real de release

```bash
make release-gate
```

## Leitura atual

- `make verify` continua obrigatorio, mas nao representa sozinho o pronto real
- `make release-gate-hosted` representa o pronto hospedado
- `make release-gate` representa o pronto real
- a lane mobile real foi estabilizada na Execucao 3 com politica oficial de cold boot
