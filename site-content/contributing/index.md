# Contributing Cookbooks

Use this section to propose, review, and add new implementation recipes. A recipe is not general product documentation. It is a scenario-specific runbook that helps a team deploy, validate, and operate one observability pattern.

New external submissions are community-supported by default. AI-generated cookbooks must stay marked as experimental or beta until maintainers intentionally reclassify them.

## Start Here

- [Recipe standard](recipe-standard.md): required structure for new first-party recipes and the review checklist for backend-rendered examples.
- [Propose a recipe](propose-recipe.md): what to collect before opening an issue or pull request against the examples backend.
- [Examples backend](examples-backend.md): how this MkDocs site renders Markdown and YAML from `chentaow-splunk/splunk-opentelemetry-examples`.
- [Architecture and maintenance plan](maintenance-plan.md): generation architecture, ownership boundaries, validation gates, and maintenance operating model.
- [Maintenance automation](maintenance-automation.md): scheduled checks, repo-local Codex skills, security scanning, and version drift inventory.
- [AI assistant backend](ai-assistant.md): how the expandable advisor sidebar calls OpenAI without exposing API keys in static frontend code.
- [Frontend configuration catalog](configuration-catalog.md): how product frontends can consume generated YAML catalogs.

## Review Rule

A recipe should be accepted only when it includes a real scenario, installation instructions, a proposed configuration file or reusable YAML asset, validation steps, troubleshooting guidance, scaling notes, and links to official documentation.

Do not merge recipes that only link to an upstream example without explaining the operational decision.
