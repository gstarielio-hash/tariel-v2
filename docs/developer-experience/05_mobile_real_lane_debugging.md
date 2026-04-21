# Mobile real lane debugging

Date: 2026-04-04

## Official commands

Real lane:

```bash
make smoke-mobile
```

Canonical real gate:

```bash
make release-gate
```

## Current lane policy

The official runner now assumes a stable-host policy:

- fresh cold boot for the emulator lane
- headless by default
- stronger Android health checks before install
- one controlled environmental recovery if install fails for host reasons

## Runtime state files

Official lane state:

- `.tmp_online/devkit/mobile_pilot_lane_status.json`

Supporting DevKit files:

- `.tmp_online/devkit/android_emulator_status.json`
- `.tmp_online/devkit/android_emulator_lane_status.json`
- `.tmp_online/devkit/android_baseline_status.json`

## How to interpret failure

### Host failure

Typical signals:

- package service missing
- ADB probe timeout
- boot not stable
- emulator process hangs or stale serial does not clear

Action:

- rerun `make smoke-mobile`
- inspect the latest `host_phase_events.json` in the newest `artifacts/mobile_pilot_run/*`
- inspect `.tmp_online/devkit/android_emulator.log`

### Functional failure

Typical signals:

- Maestro opens the app but expected surfaces are not covered
- `result` in `final_report.md` is not `success_human_confirmed`
- backend evidence or human ack does not close

Action:

- inspect the latest `final_report.md`
- inspect `ui_marker_summary.json`, `backend_summary_after.json` and Maestro debug output

## Useful local commands

Check Android baseline:

```bash
scripts/dev/check_android.sh --json
```

Check consolidated DevKit status:

```bash
scripts/dev/status.sh --json
```

Force visual mode when needed:

```bash
MOBILE_VISUAL=1 make smoke-mobile
```

## Rollback

If the fresh cold boot policy must be disabled temporarily:

```bash
MOBILE_FORCE_FRESH_BOOT=0 make smoke-mobile
```

If install recovery should not wipe emulator data:

```bash
MOBILE_WIPE_ON_INSTALL_RECOVERY=0 make smoke-mobile
```

These are debugging escape hatches, not the recommended release policy.

## Current recommendation

Use the official default policy for release validation.

It is slower, but it is the policy that made the host lane reproducible on 2026-04-04.
