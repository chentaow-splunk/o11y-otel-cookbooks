---
name: splunk-cookbook-assistant-eval
description: Evaluate the cookbook AI advisor against generated scenario-index links and fixed observability scenario prompts.
---

# Splunk Cookbook Assistant Evaluation

Use this skill when validating the expandable AI advisor or checking that recommendations stay grounded in generated cookbook links.

## Offline Baseline

```bash
python -m scripts.maintenance.assistant_eval
```

The offline mode uses token overlap against `.generated/docs/assets/scenario-index.json`. It is a baseline, not a substitute for model behavior.

## Live Assistant Check

Start the local assistant-backed server first:

```bash
python scripts/serve_scenario_assistant.py --port 8010
python -m scripts.maintenance.assistant_eval --server-url http://127.0.0.1:8010
```

The live check fails if the assistant returns a URL that is not present in `scenario-index.json`.

## Output

Reports are written to `maintenance-reports/assistant-eval.json` and `maintenance-reports/assistant-eval.md`.
