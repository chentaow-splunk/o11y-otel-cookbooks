# Examples Backend

This site renders Markdown and YAML assets from a local checkout of `chentaow-splunk/splunk-opentelemetry-examples`.

The active backend branch for this renderer is `codex/collector-data-processing-cookbooks`. That is the branch that currently contains the cookbook examples produced by the cookbook generator work. Do not run scheduled maintenance against a workshop branch unless the renderer contract is intentionally changed.

## Architecture

```text
chentaow-splunk/splunk-opentelemetry-examples
  branch: codex/collector-data-processing-cookbooks
  -> scripts/render_examples_site.py
  -> generated MkDocs pages under .generated/docs/
  -> generated YAML assets under .generated/docs/assets/example-backend/
  -> generated frontend catalogs under .generated/docs/assets/
  -> MkDocs Material site
```

The examples repository remains the source for runnable example bodies and example-local YAML. This repository owns navigation, page grouping, homepage search metadata, frontend catalogs, and production-readiness review standards.

## Local Render

```bash
git clone --branch codex/collector-data-processing-cookbooks https://github.com/chentaow-splunk/splunk-opentelemetry-examples.git splunk-opentelemetry-examples
python scripts/render_examples_site.py --source splunk-opentelemetry-examples
mkdocs build --strict
```

If the checkout already exists:

```bash
git -C splunk-opentelemetry-examples pull --ff-only
python scripts/render_examples_site.py --source splunk-opentelemetry-examples
```

## Generated Outputs

| Output | Purpose |
| --- | --- |
| `.generated/docs/assets/scenario-index.json` | Searchable scenario metadata for instrumentation and Collector examples, used by the homepage finder and local assistant. |
| `.generated/docs/assets/frontend/example-backend-catalog.yaml` | Frontend-readable catalog of YAML assets copied from the examples backend. |
| `.generated/docs/assets/example-backend/` | Published YAML assets copied from the examples backend. |
| `.generated/docs/` | Disposable MkDocs input directory built from backend examples plus `site-content/`. |

## When To Change Which Repository

| Change | Repository |
| --- | --- |
| Fix runnable commands, source code, or example-local YAML | `chentaow-splunk/splunk-opentelemetry-examples` |
| Change category, navigation, homepage discovery, or site wrapper | This MkDocs renderer |
| Add contribution guidance, proposal UI, or frontend catalog behavior | This MkDocs renderer |
| Add a new runnable example | `chentaow-splunk/splunk-opentelemetry-examples` first, then render it here |

Use upstream changes only when the runnable example itself needs to change. Do not force upstream examples into this site's recipe heading order when the renderer can provide the structure.
