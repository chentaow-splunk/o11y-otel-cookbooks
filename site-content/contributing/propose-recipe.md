# Propose a Recipe

Use this page when a scenario is missing or an existing recipe needs a new implementation path. The target source repository for runnable examples is `chentaow-splunk/splunk-opentelemetry-examples`.

## What To Submit

A proposal must include:

- Scenario: platform, workload, runtime, telemetry goal, and target operator.
- Installation instructions: commands or deployment steps with placeholders.
- Proposed configuration file: YAML, Helm values, Collector config, Kubernetes manifest, annotations, or environment variables.
- Validation steps: how to prove telemetry reaches Splunk Observability Cloud.
- Official documentation links: Splunk docs first, upstream docs only when needed.
- Operational notes: tradeoffs, scaling concerns, security requirements, and known limitations.

## AI-Assisted Draft

Use this assistant to turn existing source material into the standard recipe format. It accepts `.txt`, `.md`, `.pdf`, and `.docx` files.

Plain text and Markdown files can be read locally in the browser. PDF and DOCX uploads require a product backend endpoint, because this static GitHub Pages site cannot securely call ChatGPT or store an API key.

<div class="proposal-assistant" data-runbook-proposal>
  <div class="proposal-grid">
    <label>
      <span>Source file</span>
      <input type="file" data-runbook-file accept=".txt,.text,.md,.markdown,.pdf,.docx,text/plain,text/markdown,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document" />
    </label>

    <label>
      <span>Backend endpoint</span>
      <input type="url" data-runbook-endpoint placeholder="/api/runbook-draft" />
    </label>
  </div>

  <label>
    <span>Additional context</span>
    <textarea data-runbook-notes rows="7" placeholder="Paste notes, official docs links, YAML snippets, installation commands, or extracted text here."></textarea>
  </label>

  <div class="proposal-actions">
    <button type="button" data-runbook-generate>Generate draft</button>
    <button type="button" data-runbook-copy-prompt>Copy ChatGPT prompt</button>
    <button type="button" data-runbook-download hidden>Download Markdown</button>
  </div>

  <p class="proposal-status" data-runbook-status>Upload a text file or configure a backend endpoint for PDF/DOCX parsing.</p>

  <label>
    <span>Generated recipe draft</span>
    <textarea data-runbook-output rows="20" spellcheck="false" placeholder="The generated standard-format recipe will appear here."></textarea>
  </label>
</div>

## Product Backend Contract

For product frontend development, wire the upload form to a backend endpoint that keeps model provider credentials server-side.

Request:

```text
POST /api/runbook-draft
Content-Type: multipart/form-data

file=<uploaded .txt, .md, .pdf, or .docx>
notes=<additional context from the user>
recipeStandard=<standard Markdown section list>
outputFormat=markdown
```

Response:

```json
{
  "markdown": "# Scenario Name\n\n## Scenario\n...",
  "warnings": [
    "Source document did not include scaling guidance."
  ]
}
```

The backend should:

- reject unsupported file types and oversized uploads;
- extract DOCX and PDF text server-side;
- instruct the model not to invent product support, prerequisites, commands, or YAML;
- return Markdown only in the [recipe standard](recipe-standard.md);
- redact or reject secrets before sending content to any model provider.

## Proposal Template

````markdown
## Scenario

Describe the workload, platform, runtime, and telemetry outcome.

## Installation Instructions

List the exact deployment steps. Use placeholders for tokens, realms, cluster names, and environment names.

```bash
<install or deploy commands>
```

## Proposed Configuration File

```yaml
<collector config, Helm values, Kubernetes manifest, annotation, receiver config, or environment variables>
```

## Validation

Explain how the reviewer can confirm the recipe works in Splunk Observability Cloud.

## Official Documentation

- <Splunk official documentation link>

## Operational Notes

Explain tradeoffs, scaling limits, security requirements, and rollback guidance.
````

## Add It To The Backend

1. Create or update the scenario in `chentaow-splunk/splunk-opentelemetry-examples`.
2. Add any reusable YAML asset next to the example.
3. Use placeholders instead of real secrets.
4. Link to official Splunk documentation rather than copying large sections.
5. Run this renderer locally to verify the generated site:

```bash
python scripts/render_examples_site.py --source splunk-opentelemetry-examples
mkdocs build --strict
```
