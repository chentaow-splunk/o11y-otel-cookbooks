# Cookbook Architecture and Maintenance Plan

This page documents how the Splunk Observability Playbooks site is generated, how cookbook ownership is split between repositories, and how the implemented maintenance automation keeps the site reviewable over time.

## Executive Summary

This repository is the MkDocs Material renderer. It does not own runnable cookbook Markdown as committed source. Runnable scenarios, example-local configuration files, and reusable YAML assets come from the examples backend:

```text
chentaow-splunk/splunk-opentelemetry-examples
branch: codex/collector-data-processing-cookbooks
```

The renderer owns:

- MkDocs navigation and theme configuration
- scenario search and filtering
- the expandable AI advisor frontend
- the server-side local assistant endpoint
- contribution guidance and proposal workflow
- frontend YAML catalog generation
- maintenance automation and validation checks

This split keeps runnable examples close to their source repository while allowing this site to provide a curated, scenario-oriented cookbook experience.

## Architecture

```text
splunk-opentelemetry-examples
  collector/**/README.md
  instrumentation/**/README.md
  collector/**/*.yaml
  instrumentation/**/*.yaml
        |
        v
scripts/render_examples_site.py
        |
        +--> .generated/docs/<rendered cookbook pages>
        +--> .generated/docs/assets/scenario-index.json
        +--> .generated/docs/assets/frontend/example-backend-catalog.yaml
        +--> .generated/docs/assets/example-backend/<copied YAML assets>
        |
        v
site-content/ overlay
        |
        v
MkDocs Material build
        |
        v
site/ -> GitHub Pages
```

The generated `.generated/docs/` tree is disposable. Do not edit generated Markdown directly. Change backend examples when the runnable source is wrong, and change this renderer when navigation, discovery, catalogs, assistant behavior, or contribution workflow needs to change.

## Generation Flow

1. The renderer checks out `chentaow-splunk/splunk-opentelemetry-examples` at `codex/collector-data-processing-cookbooks`.
2. `scripts/render_examples_site.py` discovers `README.md` files under `collector/` and `instrumentation/`.
3. Each backend README becomes a generated MkDocs page with a backend-source note and rewritten local links.
4. YAML assets under the rendered backend categories are copied into `.generated/docs/assets/example-backend/`.
5. The renderer assigns support status metadata: Splunk-maintained, AI-generated beta, or community-supported.
6. The renderer generates `assets/scenario-index.json` for scenario search and assistant grounding.
7. The renderer generates `assets/frontend/example-backend-catalog.yaml` for product frontend YAML pickers.
8. Renderer-owned pages from `site-content/` are overlaid into `.generated/docs/`.
9. MkDocs builds the final static site into `site/`.

## Ownership Rules

| Change | Repository | Reason |
| --- | --- | --- |
| Fix runnable commands, source code, Dockerfiles, or example-local YAML | examples backend | The backend is the source of truth for examples users can run. |
| Add a new runnable cookbook scenario | examples backend first | The renderer discovers backend README files and YAML assets. |
| Change navigation, scenario filtering, homepage behavior, or assistant UI | renderer | These are site experience concerns. |
| Change generated catalog shape or frontend asset indexing | renderer | Product frontend consumption is a renderer responsibility. |
| Change recipe standard, proposal workflow, or maintenance automation | renderer | These are governance and review concerns. |
| Update support or version-specific claims | backend plus official-source review | Do not rely on memory for product details that can drift. |

## Implemented Maintenance Automation

The maintenance suite lives under `scripts/maintenance/`.

| Check | Script | Purpose |
| --- | --- | --- |
| Render check | `render_check.py` | Renders backend examples, runs `mkdocs build --strict`, validates generated routes, validates support status metadata, validates scenario index, and validates frontend YAML catalog paths. |
| Security scan | `security_scan.py` | Scans rendered backend categories and renderer-owned files for likely secrets, unsafe endpoints, insecure TLS flags, and Collector pipeline safety issues. |
| Content review | `content_review.py` | Reviews backend cookbook README files against the recipe standard without forcing every example into one exact heading order. |
| Assistant eval | `assistant_eval.py` | Verifies offline or live assistant recommendations resolve to generated cookbook links. |
| Version drift | `version_drift_check.py` | Inventories Python, NPM, GitHub Action, and container image versions, with optional online registry checks. |
| Full suite | `run_all.py` | Runs all maintenance checks and writes reports under `maintenance-reports/`. |

Run the suite locally:

```bash
python -m scripts.maintenance.run_all --source splunk-opentelemetry-examples
```

## Scheduled Jobs

Two scheduling layers are in place.

### GitHub Actions

`.github/workflows/cookbook-maintenance.yml` runs weekly and on demand. It:

1. Checks out this renderer.
2. Checks out the examples backend at `codex/collector-data-processing-cookbooks`.
3. Installs MkDocs Material.
4. Runs the maintenance suite.
5. Uploads `maintenance-reports/` as a workflow artifact.

### Codex Scheduled Job

The local Codex automation `cookbook-maintenance-audit` runs the same maintenance suite weekly and summarizes render, security, content-review, assistant-eval, and version-drift results.

## Security Scanning

The security scanner fails on high-confidence `critical` findings by default. Lower-severity operational findings are reported for review.

Critical findings include likely:

- OpenAI API keys
- Splunk tokens
- cloud access keys
- private keys
- hard-coded password-like values
- URI inline credentials

Synthetic redaction values such as `synthetic-token` are treated as placeholders because redaction cookbooks need safe fake sensitive values to validate masking behavior.

Operational findings include:

- plain HTTP exporter endpoints
- `insecure: true`
- Collector configs that do not reference `memory_limiter`
- Collector configs that do not reference `batch`

These are not automatically wrong in local examples, but production-ready recipes should fix them or explain the tradeoff.

## Codex Agent Skills

Repo-local skills under `.codex/skills/` define repeatable agent workflows:

- `splunk-cookbook-render-check`
- `splunk-cookbook-security-review`
- `splunk-cookbook-content-review`
- `splunk-cookbook-assistant-eval`
- `splunk-cookbook-version-drift-check`

Each skill maps to a concrete maintenance script and defines what evidence to inspect.

## Validation Gates

A maintenance run is acceptable when:

- the renderer builds successfully from the configured backend branch;
- every scenario URL in `scenario-index.json` resolves to a generated page;
- every frontend catalog `rawPath` resolves to a generated YAML asset;
- no critical secret findings are present;
- content-review findings are understood as quality review items;
- live assistant recommendations return only generated cookbook URLs;
- version drift output is treated as update candidates, not automatic proof that upgrades are safe.

## Current Validation Snapshot

The latest local maintenance run on this branch completed with:

```text
render-check: 0 findings
security-scan: 0 findings
assistant-eval: 0 findings
version-drift: 0 findings
content-review: non-blocking review findings for existing examples
```

Local caveat: the local backend checkout currently contains an untracked `collector/workshop-managed-vm-app-stack/` folder. A clean CI checkout will render only committed files from `codex/collector-data-processing-cookbooks`.
