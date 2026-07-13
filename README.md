# Splunk Observability Playbooks

This repository is a MkDocs Material site for implementation cookbooks, onboarding recipes, and reusable deployment blueprints for Splunk Observability Cloud.

It is not a replacement for official Splunk documentation. Each cookbook links back to the relevant Splunk docs and focuses on the operational decisions teams usually need when they move from "install the collector" to a repeatable production onboarding pattern.

## What This Repository Contains

- Scenario-based cookbooks generated from OpenTelemetry instrumentation and Collector examples.
- OpenTelemetry Collector configuration examples.
- Kubernetes Helm values and annotation blueprints.
- OBI eBPF application instrumentation guidance for Linux and Kubernetes.
- Python zero-code instrumentation examples.
- PostgreSQL receiver patterns for Splunk Database Monitoring.
- Generated recipe pages derived from the Splunk OpenTelemetry examples source set.
- Renderer-owned contribution pages, homepage search/filter UI, and proposal workflow under `site-content/`.
- Architecture guidance for collector placement, metadata enrichment, batching, scaling, and troubleshooting.

## Local Preview

Use Python 3.10 or newer.

```bash
python -m venv .venv
source .venv/bin/activate
pip install mkdocs-material
git clone --branch codex/collector-data-processing-cookbooks https://github.com/chentaow-splunk/splunk-opentelemetry-examples.git splunk-opentelemetry-examples
python scripts/render_examples_site.py
mkdocs serve
```

Then open `http://127.0.0.1:8000`.

If the examples checkout already exists, update it before syncing:

```bash
git -C splunk-opentelemetry-examples pull --ff-only
python scripts/render_examples_site.py
```

## Build

```bash
python scripts/render_examples_site.py
mkdocs build --strict
```

The generated site is written to `site/`.

## Maintenance Automation

Run the full local maintenance suite:

```bash
python -m scripts.maintenance.run_all --source splunk-opentelemetry-examples
```

The suite renders the backend, builds MkDocs, validates `scenario-index.json`, validates the frontend YAML catalog, scans for likely secrets and unsafe YAML patterns, reviews cookbook completeness, evaluates assistant routing, and inventories package/runtime versions.

Scheduled maintenance lives in `.github/workflows/cookbook-maintenance.yml`. It checks out `chentaow-splunk/splunk-opentelemetry-examples` at `codex/collector-data-processing-cookbooks`, runs the maintenance suite weekly, and uploads `maintenance-reports/` as an artifact.

Repo-local Codex skills for future agents live under `.codex/skills/`.

## Examples Backend

This repository is the renderer. The local content backend is the `chentaow-splunk/splunk-opentelemetry-examples` checkout at `splunk-opentelemetry-examples`. The active cookbook backend branch for this renderer is `codex/collector-data-processing-cookbooks`.

The rendering contract is documented in `examples-backend.yaml` and implemented by `scripts/render_examples_site.py`.

The render script:

- reads Markdown directly from the examples checkout;
- generates MkDocs pages under `.generated/docs`;
- overlays renderer-owned pages and assets from `site-content/`;
- copies referenced local files and images into `.generated/docs`;
- copies backend YAML assets into `.generated/docs/assets/example-backend/`;
- generates `.generated/docs/assets/scenario-index.json`;
- generates `.generated/docs/assets/frontend/example-backend-catalog.yaml` for product frontend consumption.

The generated directory is disposable and ignored by git. Do not edit generated Markdown.

## AI Assistant Preview

The expandable AI advisor sidebar requires a server-side endpoint because this site does not call OpenAI directly from static browser code.

```bash
python scripts/render_examples_site.py --source splunk-opentelemetry-examples
mkdocs build --strict
python scripts/serve_scenario_assistant.py --port 8010
```

Then open `http://127.0.0.1:8010/`.

The server loads `OPENAI_API_KEY` from a local `.env` file when present, or from the shell environment. Users can also enter an OpenAI API key in the assistant form for one request. The key is kept only in the current page's memory until submit, sent only to the assistant endpoint for that request, not written to localStorage, sessionStorage, cookies, logs, generated files, or git, and cleared from the form after the request completes.

The assistant endpoint uses OpenAI embeddings over the generated examples knowledge base and the OpenAI Responses API to return cookbook recommendations with links. Without either a server-side `OPENAI_API_KEY` or a per-request key, the site still renders and Browse cookbooks still works, but the AI advisor reports that a key is required.

If the sidebar still reports that `OPENAI_API_KEY` is missing, stop the old server process and start it again. A server that was already running before `.env` was added will not reload the file automatically. Confirm the active backend with:

```bash
curl http://127.0.0.1:8010/api/scenario-assistant/health
```

The response should include `"openaiConfigured": true` when the backend has a server-side key. It also includes `"acceptsRequestApiKey": true` when the backend accepts a one-request key from the form.

## Cookbooks

Scenario cookbook content is generated from two backend categories: OpenTelemetry instrumentation examples and OpenTelemetry Collector examples. This repo should not store copied backend recipe Markdown as committed source.

Renderer-owned pages remain committed here under `site-content/`. That includes the homepage scenario finder, local assistant, contribution standard, proposal workflow, and frontend catalog guidance.

## Support Status Labels

The renderer labels every cookbook so readers can distinguish source ownership:

- `Maintained by Splunk`: rendered from the Splunk OpenTelemetry examples source set. Official Splunk documentation remains the product source of truth.
- `Experimental / AI-generated`: generated with AI-assisted cookbook skills and intended as beta guidance that needs review before customer use.
- `Community-supported`: submitted by users or contributors unless maintainers reclassify it.

New community submissions should include this front matter in the backend `README.md`:

```yaml
---
cookbook_status: community-supported
---
```

## GitHub Pages Deployment

The workflow in `.github/workflows/deploy.yml` checks out this renderer, checks out the examples backend, runs the render script, builds the MkDocs site, and publishes it to GitHub Pages when changes are pushed to `main`.

Before the first deployment:

1. In GitHub repository settings, set Pages source to `GitHub Actions`.
2. Confirm the default branch is `main`, or update the workflow branch filter.
3. Keep secrets out of the repository. The YAML examples use placeholder tokens and environment variables intentionally.

## Official Documentation References

Start with these official references when validating or extending a playbook:

- [Splunk Distribution of the OpenTelemetry Collector for Kubernetes](https://help.splunk.com/en/splunk-observability-cloud/manage-data/splunk-distribution-of-the-opentelemetry-collector/get-started-with-the-splunk-distribution-of-the-opentelemetry-collector/collector-for-kubernetes)
- [Splunk Distribution of the OpenTelemetry Collector for Linux](https://help.splunk.com/splunk-observability-cloud/manage-data/splunk-distribution-of-the-opentelemetry-collector/get-started-with-the-splunk-distribution-of-the-opentelemetry-collector/collector-for-linux)
- [Configure the Splunk Distribution of OpenTelemetry Collector on a Linux host](https://help.splunk.com/en/splunk-observability-cloud/manage-data/splunk-distribution-of-the-opentelemetry-collector/get-started-with-the-splunk-distribution-of-the-opentelemetry-collector/collector-for-linux/configure-the-splunk-distribution-of-opentelemetry-collector-on-a-linux-host)
- [Splunk Distribution of the OpenTelemetry Collector for Windows](https://help.splunk.com/en/splunk-observability-cloud/manage-data/splunk-distribution-of-the-opentelemetry-collector/get-started-with-the-splunk-distribution-of-the-opentelemetry-collector/collector-for-windows)
- [Instrument an application using OBI](https://help.splunk.com/en/splunk-observability-cloud/manage-data/instrument-back-end-services/instrument-back-end-applications-to-send-spans-to-splunk-apm/instrument-an-application-using-obi)
- [Monitor your Kubernetes environment](https://help.splunk.com/en/splunk-observability-cloud/manage-data/splunk-distribution-of-the-opentelemetry-collector/get-started-with-the-splunk-distribution-of-the-opentelemetry-collector/collector-for-kubernetes/monitor-your-kubernetes-environment)
- [Python AI zero-code instrumentation](https://help.splunk.com/en/splunk-observability-cloud/observability-for-ai/splunk-ai-agent-monitoring/set-up-ai-agent-monitoring/zero-code-instrumentation)
- [PostgreSQL receiver](https://help.splunk.com/en/splunk-observability-cloud/manage-data/splunk-distribution-of-the-opentelemetry-collector/get-started-with-the-splunk-distribution-of-the-opentelemetry-collector/collector-components/receivers/postgresql-receiver)

## Repository Philosophy

Traditional documentation optimizes for complete reference coverage. This repository optimizes for adoption velocity, successful onboarding, operational outcomes, and reusable deployment patterns.

Use it as an implementation accelerator, not as the source of truth for every product parameter.
