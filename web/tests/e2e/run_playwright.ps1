$ErrorActionPreference = "Stop"

$env:RUN_E2E = "1"
if (-not $env:E2E_VISUAL) { $env:E2E_VISUAL = "1" }
if (-not $env:E2E_SLOWMO_MS) { $env:E2E_SLOWMO_MS = "350" }

python -m pytest tests/e2e -q `
  --browser chromium `
  --tracing retain-on-failure `
  --video retain-on-failure `
  --screenshot only-on-failure `
  -s
