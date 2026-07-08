---
name: splunk-cookbook-content-review
description: Review backend cookbook README files against the Splunk Observability Playbooks recipe standard without forcing every upstream example into the same heading order.
---

# Splunk Cookbook Content Review

Use this skill when reviewing a cookbook PR or scheduled quality audit.

## Command

```bash
python -m scripts.maintenance.content_review --source splunk-opentelemetry-examples
```

## Review Standard

Check for practical coverage of:

- scenario and when to use the recipe
- architecture or telemetry flow
- prerequisites
- installation steps
- reusable configuration or nearby YAML assets
- validation in Splunk Observability Cloud or Collector logs
- troubleshooting
- scaling and sizing notes
- security or operational notes
- official Splunk documentation links

Rendered backend examples do not need to use one exact heading order if the content is operationally complete.

## Output

Reports are written to `maintenance-reports/content-review.json` and `maintenance-reports/content-review.md`.
