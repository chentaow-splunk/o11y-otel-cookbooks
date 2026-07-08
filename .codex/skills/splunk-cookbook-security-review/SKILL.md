---
name: splunk-cookbook-security-review
description: Scan cookbook Markdown, YAML, scripts, and workflow files for likely secrets, unsafe endpoints, insecure TLS settings, and Collector pipeline safety risks.
---

# Splunk Cookbook Security Review

Use this skill for PR review or scheduled maintenance of cookbook examples and renderer-owned assets.

## Command

```bash
python -m scripts.maintenance.security_scan
```

The default scan covers:

- `site-content`
- `scripts`
- `.github`
- `examples-backend.yaml`
- `mkdocs.yml`
- `splunk-opentelemetry-examples`

## Review Rules

- Treat `critical` findings as blocking unless proven false positive.
- Do not echo detected secret values in comments or issues.
- For `medium` Collector findings, decide whether the recipe is intentionally local/demo-only or needs memory limiter, batching, or safer exporter settings.

## Output

Reports are written to `maintenance-reports/security-scan.json` and `maintenance-reports/security-scan.md`.
