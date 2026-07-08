---
name: splunk-cookbook-render-check
description: Render the Splunk Observability Playbooks site from the cookbook examples backend and validate generated MkDocs artifacts, scenario index routes, and frontend YAML catalog paths.
---

# Splunk Cookbook Render Check

Use this skill when validating that the renderer branch can build the latest cookbook examples from `chentaow-splunk/splunk-opentelemetry-examples`.

## Source Contract

- Renderer branch: `codex/upstream-examples-renderer`
- Backend checkout path: `splunk-opentelemetry-examples`
- Backend branch: `codex/collector-data-processing-cookbooks`

Do not edit `.generated/docs` directly. It is disposable output.

## Command

```bash
python -m scripts.maintenance.render_check --source splunk-opentelemetry-examples
```

## What To Review

- Render command completion.
- `mkdocs build --strict` result.
- `.generated/docs/assets/scenario-index.json` scenario count, categories, source commit, and route existence.
- `.generated/docs/assets/frontend/example-backend-catalog.yaml` raw YAML paths and recipe links.
- Backend branch and remote drift.

## Output

Reports are written to `maintenance-reports/render-check.json` and `maintenance-reports/render-check.md`.
