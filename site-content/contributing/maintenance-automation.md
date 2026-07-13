# Maintenance Automation

This repository now includes concrete automation for keeping the cookbook renderer and examples backend maintainable. The automation is intentionally split into deterministic local scripts, repo-local Codex skill definitions, and a scheduled GitHub Actions workflow.

## What Exists

| Automation | Location | Purpose |
| --- | --- | --- |
| Render check | `scripts/maintenance/render_check.py` | Renders the backend examples, runs `mkdocs build --strict`, validates `scenario-index.json`, validates support status metadata, and validates the frontend YAML catalog. |
| Security scan | `scripts/maintenance/security_scan.py` | Scans renderer-owned files plus the rendered backend `collector/` and `instrumentation/` categories for likely secrets, unsafe endpoints, insecure TLS flags, and Collector pipeline safety issues. |
| Content review | `scripts/maintenance/content_review.py` | Reviews rendered backend README files against the recipe standard without requiring every upstream example to use identical headings. |
| Assistant evaluation | `scripts/maintenance/assistant_eval.py` | Checks that offline or live assistant recommendations resolve to generated cookbook URLs. |
| Version drift inventory | `scripts/maintenance/version_drift_check.py` | Inventories Python, NPM, GitHub Action, and container image references. It can optionally query PyPI and NPM. |
| Suite wrapper | `scripts/maintenance/run_all.py` | Runs the full maintenance suite and writes reports under `maintenance-reports/`. |
| Scheduled workflow | `.github/workflows/cookbook-maintenance.yml` | Runs the maintenance suite weekly against the configured examples backend branch and uploads reports as artifacts. |
| Codex skills | `.codex/skills/` | Provides agent-facing instructions for render checks, security review, content review, assistant evaluation, and version drift checks. |

## Backend Branch Contract

The renderer is currently aligned to:

```text
https://github.com/chentaow-splunk/splunk-opentelemetry-examples/tree/codex/collector-data-processing-cookbooks
```

The branch matters because this renderer is designed to render the cookbook examples created in that backend branch. Do not point scheduled maintenance to a workshop branch or an unrelated default branch unless the backend examples have been merged there.

## Local Run

Run the full suite:

```bash
python -m scripts.maintenance.run_all --source splunk-opentelemetry-examples
```

Run individual checks:

```bash
python -m scripts.maintenance.render_check --source splunk-opentelemetry-examples
python -m scripts.maintenance.security_scan
python -m scripts.maintenance.content_review --source splunk-opentelemetry-examples
python -m scripts.maintenance.assistant_eval
python -m scripts.maintenance.version_drift_check --source splunk-opentelemetry-examples
```

Use online package checks only when network access is available:

```bash
python -m scripts.maintenance.version_drift_check --source splunk-opentelemetry-examples --online
```

## Reports

Reports are written to `maintenance-reports/` and ignored by git.

| Report | Use |
| --- | --- |
| `render-check.md` / `render-check.json` | Build, route, support status, scenario index, and catalog integrity. |
| `security-scan.md` / `security-scan.json` | Secret and operational-risk findings. |
| `content-review.md` / `content-review.json` | Recipe-standard coverage by backend cookbook. |
| `assistant-eval.md` / `assistant-eval.json` | Assistant routing checks and returned cookbook links. |
| `version-drift.md` / `version-drift.json` | Dependency, runtime, action, and image inventory. |

## Scheduled Workflow

`.github/workflows/cookbook-maintenance.yml` runs every Monday at 13:00 UTC and can also be run manually. The workflow:

1. Checks out this renderer branch.
2. Checks out `chentaow-splunk/splunk-opentelemetry-examples` at `codex/collector-data-processing-cookbooks`.
3. Installs MkDocs Material.
4. Runs `python -m scripts.maintenance.run_all`.
5. Uploads `maintenance-reports/` as a workflow artifact.

Manual runs can enable online PyPI and NPM checks with the `online_version_check` workflow input. Scheduled runs default to offline version inventory so package registry outages do not create noisy failures.

## Security Scanning Behavior

The security scanner fails on `critical` findings by default. Lower-severity findings are reported but do not automatically fail the run. By default it scans only renderer-owned files and the backend categories that this site renders: `collector/` and `instrumentation/`.

Critical findings include likely API keys, Splunk tokens, cloud access keys, private keys, inline credentials, and hard-coded password-like values. Synthetic redaction test values such as `synthetic-token` are treated as placeholders, because those examples need safe fake sensitive values to prove masking behavior. The scanner intentionally does not print secret values beyond the matched line context in the report. Reviewers should avoid copying suspected secret values into issues or comments.

Operational findings include plain HTTP exporters, `insecure: true`, Collector configs that do not reference `memory_limiter`, and Collector configs that do not reference `batch`. These are not always wrong for local demos, but production-ready cookbooks should either fix them or explain the tradeoff.

## Codex Skills

The repo-local skills under `.codex/skills/` are lightweight operating contracts for future Codex agents:

- `splunk-cookbook-render-check`
- `splunk-cookbook-security-review`
- `splunk-cookbook-content-review`
- `splunk-cookbook-assistant-eval`
- `splunk-cookbook-version-drift-check`

Each skill maps to one maintenance script and defines what evidence to inspect.

## Definition Of Done

A cookbook maintenance run is acceptable when:

- the renderer builds successfully from the configured backend branch;
- every scenario URL in `scenario-index.json` resolves to a generated page;
- every frontend catalog `rawPath` resolves to a generated YAML asset;
- no critical secret findings are present;
- content review findings are understood and either fixed or accepted as known gaps;
- assistant recommendations, when tested live, return only generated cookbook URLs;
- version drift output is treated as an update candidate list, not as proof that every dependency can be safely upgraded.
