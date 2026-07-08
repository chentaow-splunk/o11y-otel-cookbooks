# Contributing

This repository accepts implementation playbooks, operational recipes, and reusable configuration blueprints for Splunk Observability Cloud.

Do not copy large sections of official Splunk documentation into this repository. Link to the official page and explain the implementation decision this repository recommends.

## Contribution Standards

Every first-party scenario page must follow the repository recipe standard in [site-content/contributing/recipe-standard.md](site-content/contributing/recipe-standard.md).

At minimum, every recipe should include:

- Scenario.
- Architecture overview.
- Prerequisites.
- Installation instructions.
- Proposed configuration file or reusable YAML asset reference.
- Validation steps.
- Troubleshooting guidance.
- Scaling recommendations.
- Links to official Splunk documentation.
- A clear explanation of why the recommended configuration exists.

## Technical Accuracy

Before opening a pull request:

1. Verify product-specific details against official Splunk documentation.
2. Prefer the Splunk Distribution of the OpenTelemetry Collector when the target is Splunk Observability Cloud.
3. Avoid claiming Splunk support for upstream components unless Splunk documentation explicitly says so.
4. Use placeholders for secrets and realms.
5. Validate YAML syntax.
6. Run `python scripts/render_examples_site.py` and `mkdocs build --strict`.

## Writing Style

Write for platform engineers, SREs, observability architects, and service owners who need to onboard systems quickly and operate them safely.

Use this structure for new pages:

```markdown
# Scenario Name

## Scenario
## Architecture Overview
## Prerequisites
## Installation Instructions
## Proposed Configuration File
## Validation
## Why This Configuration
## Troubleshooting
## Scaling Recommendations
## Security and Operations Notes
## Official Documentation
```

To propose a recipe before writing a pull request, use the `Recipe proposal` GitHub issue form. The proposal must include the scenario, installation instructions, and proposed configuration file.

## Working With Backend Examples

Pages rendered from `chentaow-splunk/splunk-opentelemetry-examples` are generated from the local backend checkout at `splunk-opentelemetry-examples`. The current cookbook backend branch is `codex/collector-data-processing-cookbooks`.

Use this flow when backend examples change:

```bash
git clone --branch codex/collector-data-processing-cookbooks https://github.com/chentaow-splunk/splunk-opentelemetry-examples.git splunk-opentelemetry-examples
python scripts/render_examples_site.py
mkdocs build --strict
```

If a rendered page needs better navigation, category, scenario finder metadata, or frontend configuration catalog behavior, make that change in this repository. If the runnable example instructions, Markdown body, source files, or YAML examples are wrong, prepare that change in the examples repository instead.

Renderer-owned pages live in `site-content/` and are merged into `.generated/docs` during render. Keep contribution guidance, proposal UI, CSS, JavaScript, and frontend catalog documentation there.

## Pull Request Checklist

- [ ] The page does not duplicate official Splunk documentation.
- [ ] Official documentation links are included.
- [ ] YAML examples use placeholders, not real secrets.
- [ ] Backend YAML assets render through `.generated/docs/assets/frontend/example-backend-catalog.yaml`.
- [ ] Installation instructions and validation steps are included.
- [ ] A proposed configuration file or YAML asset is included.
- [ ] The guidance states operational tradeoffs.
- [ ] `python scripts/render_examples_site.py` passes.
- [ ] `mkdocs build --strict` passes.
