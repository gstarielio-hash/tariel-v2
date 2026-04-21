# Mobile host stabilization

Date: 2026-04-04
Phase: Execucao 3 - estabilizacao do host Android do gate real e fechamento da lane mobile

## Executive result

The Android host lane is no longer blocked by the old package-service degradation pattern.

Current classification:

- `estavel`

This classification is based on repeated official green runs on the current host after the host changes.

## What was diagnosed

The previous blocker was host state contamination:

- stale emulator reuse
- snapshot-backed startup (`default_boot`)
- weak boot readiness checks
- ADB probes that could hang on a bad emulator
- install failures before Maestro with `cmd: Can't find service: package`

## What was changed

- official runner now defaults to fresh cold boot for the emulator lane
- an existing emulator is restarted when fresh boot or wipe-data is required
- ADB probes in devkit use timeout protection
- boot readiness now requires stable Android health, not only `sys.boot_completed`
- install lane has one controlled environmental recovery path
- official lane writes runtime state for DevKit status consumption
- DevKit status now shows the official lane and marks old auxiliary Maestro state as stale

## Validation executed

Passed in this phase:

- `cd android && npm run android:preview`
- `make smoke-mobile` -> `artifacts/mobile_pilot_run/20260404_140933`
- `make smoke-mobile` -> `artifacts/mobile_pilot_run/20260404_141247`
- `make release-gate` -> mobile artifact `artifacts/mobile_pilot_run/20260404_141923`
- `python3 scripts/run_mobile_pilot_runner.py` -> `artifacts/mobile_pilot_run/20260404_142431`
- `scripts/dev/check_android.sh --json`
- `scripts/dev/status.sh --json`

## Interpretation

The lane is now suitable for the real gate on this host.

Important nuance:

- this did not make hosted CI equivalent to the real gate
- it made the local Android host lane reproducible enough to support `make release-gate`

## Remaining non-host limitations

- the mobile product rollout still reports `observing`; that is rollout state, not host instability
- the real gate still requires an Android-capable host and cannot be delegated to hosted CI alone

## Artifacts

- `artifacts/mobile_host_stabilization/20260404_142743/mobile_host_diagnosis.md`
- `artifacts/mobile_host_stabilization/20260404_142743/mobile_lane_matrix.json`
- `artifacts/mobile_host_stabilization/20260404_142743/source_index.txt`
