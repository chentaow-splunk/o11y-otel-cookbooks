(function () {
  const root = document.querySelector("[data-runbook-proposal]");
  if (!root) {
    return;
  }

  const els = {
    file: root.querySelector("[data-runbook-file]"),
    endpoint: root.querySelector("[data-runbook-endpoint]"),
    notes: root.querySelector("[data-runbook-notes]"),
    generate: root.querySelector("[data-runbook-generate]"),
    copyPrompt: root.querySelector("[data-runbook-copy-prompt]"),
    download: root.querySelector("[data-runbook-download]"),
    output: root.querySelector("[data-runbook-output]"),
    status: root.querySelector("[data-runbook-status]"),
  };

  const recipeStandard = `---
cookbook_status: community-supported
---

# <Scenario Name>

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
## Official Documentation`;

  let extractedText = "";
  let lastMarkdown = "";

  function setStatus(message, isError) {
    if (!els.status) return;
    els.status.textContent = message;
    els.status.classList.toggle("is-error", Boolean(isError));
  }

  function selectedFile() {
    return els.file && els.file.files && els.file.files.length ? els.file.files[0] : null;
  }

  function isLocalTextFile(file) {
    if (!file) return false;
    const name = file.name.toLowerCase();
    return file.type.startsWith("text/") || name.endsWith(".txt") || name.endsWith(".md") || name.endsWith(".markdown");
  }

  function buildPrompt() {
    const file = selectedFile();
    const notes = els.notes ? els.notes.value.trim() : "";
    const sourceParts = [];

    if (file) {
      sourceParts.push(`Uploaded file name: ${file.name}`);
      sourceParts.push(`Uploaded file type: ${file.type || "unknown"}`);
    }
    if (extractedText) {
      sourceParts.push(`Extracted source text:\\n${extractedText}`);
    }
    if (notes) {
      sourceParts.push(`Additional user context:\\n${notes}`);
    }

    return `You are helping format a Splunk Observability implementation playbook recipe.

Use only the source material provided. Do not invent Splunk product support, prerequisites, commands, configuration fields, or official documentation links. If information is missing, write "Needs validation" in the relevant section.

Return Markdown only using exactly this standard:

${recipeStandard}

Requirements:
- Keep the front matter and use \`cookbook_status: community-supported\` for user-submitted recipes unless maintainers explicitly change it.
- The Scenario section must state platform, workload, telemetry goal, and when to use the recipe.
- Installation Instructions must be ordered and use placeholders for secrets, realms, cluster names, namespaces, and service names.
- Proposed Configuration File must contain YAML or clearly state "Needs validation: configuration file not provided."
- Validation must explain how to confirm telemetry in Splunk Observability Cloud.
- Why This Configuration must explain tradeoffs.
- Troubleshooting must include a Markdown table.
- Security and Operations Notes must reject real secrets in examples.

Source material:

${sourceParts.join("\\n\\n") || "No source material provided."}`;
  }

  function fallbackDraft() {
    return `---
cookbook_status: community-supported
---

# Scenario Name

## Scenario

Needs validation: summarize the workload, platform, runtime, telemetry goal, and target operator from the uploaded source.

## Architecture Overview

\`\`\`text
<workload or infrastructure>
  -> <instrumentation, receiver, or telemetry source>
  -> <collector mode>
  -> Splunk Observability Cloud
\`\`\`

## Prerequisites

- Splunk Observability Cloud realm: \`<realm>\`.
- Ingest token stored as a secret reference.
- Required platform access: Needs validation.
- Official Splunk documentation reviewed: Needs validation.

## Installation Instructions

1. Needs validation: extract ordered install steps from the source material.
2. Replace all secrets and environment-specific values with placeholders.
3. Deploy in a non-production environment first.
4. Generate representative traffic or workload activity.

## Proposed Configuration File

\`\`\`yaml
# Needs validation: paste or generate the proposed YAML configuration here.
\`\`\`

## Validation

1. Confirm the collector, instrumentation, or receiver is running.
2. Check logs for export errors.
3. Verify telemetry appears in Splunk Observability Cloud.
4. Confirm resource attributes such as \`service.name\` and \`deployment.environment\`.

## Why This Configuration

Needs validation: explain the operational reason and tradeoffs.

## Troubleshooting

| Symptom | First check | Likely fix |
| --- | --- | --- |
| No telemetry appears | Token, realm, endpoint, and collector logs | Correct the export path and restart the collector. |

## Scaling Recommendations

- Needs validation: document memory limits, batching, gateway, sampling, and cardinality controls.

## Security and Operations Notes

- Do not commit real tokens, API keys, customer data, or private endpoints.
- Use secret references or environment variables.

## Official Documentation

- Needs validation: add official Splunk documentation links.`;
  }

  async function readLocalText(file) {
    extractedText = "";
    if (!file) {
      setStatus("No file selected. You can still paste notes or configure a backend endpoint.", false);
      return;
    }
    if (!isLocalTextFile(file)) {
      setStatus("PDF and DOCX uploads require the backend endpoint. The file will be sent when you click Generate draft.", false);
      return;
    }
    extractedText = await file.text();
    setStatus(`Loaded ${file.name} locally. Configure an endpoint for model generation, or copy the prompt.`, false);
  }

  async function generateWithBackend(endpoint, file, prompt) {
    const formData = new FormData();
    if (file) formData.append("file", file, file.name);
    formData.append("notes", els.notes ? els.notes.value : "");
    formData.append("prompt", prompt);
    formData.append("recipeStandard", recipeStandard);
    formData.append("outputFormat", "markdown");

    const response = await fetch(endpoint, {
      method: "POST",
      body: formData,
    });
    if (!response.ok) {
      throw new Error(`Backend returned HTTP ${response.status}`);
    }

    const contentType = response.headers.get("content-type") || "";
    if (contentType.includes("application/json")) {
      const data = await response.json();
      return data.markdown || data.recipeMarkdown || data.output || "";
    }
    return response.text();
  }

  async function generateDraft() {
    const file = selectedFile();
    const endpoint = els.endpoint ? els.endpoint.value.trim() : "";
    const prompt = buildPrompt();

    try {
      setStatus("Preparing recipe draft...", false);
      let markdown = "";
      if (endpoint) {
        markdown = await generateWithBackend(endpoint, file, prompt);
        if (!markdown.trim()) {
          throw new Error("Backend response did not include Markdown.");
        }
        setStatus("Generated draft from backend model workflow.", false);
      } else {
        markdown = fallbackDraft();
        setStatus("No backend endpoint configured. Generated a standard template and prompt.", false);
      }

      lastMarkdown = markdown;
      if (els.output) els.output.value = markdown;
      if (els.download) els.download.hidden = false;
    } catch (error) {
      setStatus(error.message, true);
    }
  }

  async function copyPrompt() {
    const prompt = buildPrompt();
    try {
      await navigator.clipboard.writeText(prompt);
      setStatus("Copied prompt to clipboard.", false);
    } catch {
      if (els.output) els.output.value = prompt;
      setStatus("Clipboard unavailable. Prompt written to the output box.", false);
    }
  }

  function downloadMarkdown() {
    const markdown = lastMarkdown || (els.output ? els.output.value : "");
    if (!markdown.trim()) return;
    const blob = new Blob([markdown], { type: "text/markdown" });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = "proposed-recipe.md";
    link.click();
    URL.revokeObjectURL(link.href);
  }

  if (els.file) {
    els.file.addEventListener("change", () => readLocalText(selectedFile()));
  }
  if (els.generate) {
    els.generate.addEventListener("click", generateDraft);
  }
  if (els.copyPrompt) {
    els.copyPrompt.addEventListener("click", copyPrompt);
  }
  if (els.download) {
    els.download.addEventListener("click", downloadMarkdown);
  }
})();
