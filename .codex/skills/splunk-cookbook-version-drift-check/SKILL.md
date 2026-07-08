---
name: splunk-cookbook-version-drift-check
description: Inventory cookbook runtime, package, GitHub Action, and container image versions, with optional live PyPI and NPM latest-version checks.
---

# Splunk Cookbook Version Drift Check

Use this skill when checking whether cookbook examples reference stale runtimes, dependencies, actions, or images.

## Offline Inventory

```bash
python -m scripts.maintenance.version_drift_check --source splunk-opentelemetry-examples
```

Offline mode inventories versions but does not claim that a newer version exists.

## Online Registry Check

```bash
python -m scripts.maintenance.version_drift_check --source splunk-opentelemetry-examples --online
```

Online mode queries PyPI and the NPM registry. Only use it when network access is available. Treat results as update candidates that still need recipe validation.

## Output

Reports are written to `maintenance-reports/version-drift.json` and `maintenance-reports/version-drift.md`.
