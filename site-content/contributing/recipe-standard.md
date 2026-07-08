# Recipe Standard

Every runbook should be easy to scan, compare, review, and operate. The standard below is the target format for new recipes and the review checklist for examples rendered from the backend repository.

## Required Format

Use this order for new first-party recipes:

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

## Section Requirements

| Section | Required content | Why it matters |
| --- | --- | --- |
| Scenario | Workload, platform, runtime, telemetry goal, and when to use the recipe. | Keeps recipes scenario-based instead of becoming generic product documentation. |
| Architecture Overview | Short data-flow explanation and where the Collector, SDK, OBI, receiver, or exporter runs. | Helps reviewers catch incorrect deployment boundaries early. |
| Prerequisites | Access, versions, permissions, tools, network paths, tokens, realm, and secrets policy. | Most onboarding failures are environment and permission issues. |
| Installation Instructions | Ordered commands or deployment steps with placeholders for environment-specific values. | Makes the recipe executable without hiding operational assumptions. |
| Proposed Configuration File | YAML, Helm values, Collector config, Kubernetes manifest, annotation, or environment variables. | Forces the implementation to be reusable and reviewable. |
| Validation | How to prove traces, metrics, logs, or profiles reached Splunk Observability Cloud. | Prevents recipes from stopping at installation. |
| Why This Configuration | Tradeoffs, defaults, and reasons for the recommended path. | This repository optimizes for implementation decisions, not parameter completeness. |
| Troubleshooting | Likely symptoms, first checks, and rollback guidance. | Helps operators recover without guessing. |
| Scaling Recommendations | Memory, batching, gateways, cardinality, sampling, rollout, and ownership guidance. | Keeps examples usable beyond a single demo deployment. |
| Security and Operations Notes | Secret handling, RBAC, network egress, data sensitivity, and production guardrails. | Prevents unsafe copy-and-paste deployments. |
| Official Documentation | Links to official Splunk docs and upstream project docs needed to validate support. | Keeps support claims grounded in source material. |

## Markdown Template

````markdown
# <Scenario Name>

## Scenario

Use this recipe when <team/workload> needs <telemetry outcome> for <platform/runtime>.

Do not use this recipe when <known limitation or better alternative>.

## Architecture Overview

```text
<workload or infrastructure>
  -> <instrumentation, receiver, or telemetry source>
  -> <collector mode: agent, gateway, daemonset, sidecar, or direct exporter>
  -> Splunk Observability Cloud
```

Explain where telemetry is produced, where it is enriched, and where it is exported.

## Prerequisites

- Splunk Observability Cloud realm: `<realm>`.
- Ingest token stored as `<secret name or environment variable>`.
- Required platform access: `<Kubernetes admin, host admin, cloud IAM role, database user, etc.>`.
- Required tools: `<helm, kubectl, docker, uv, pip, PowerShell, etc.>`.
- Official Splunk documentation reviewed: `<link>`.

## Installation Instructions

1. Install or enable `<collector, receiver, SDK, OBI, Helm chart, or runtime package>`.
2. Apply the configuration in the next section.
3. Restart or roll out the affected workload.
4. Generate representative traffic.

```bash
<command with placeholders>
```

## Proposed Configuration File

Save the configuration as `<path/to/file.yaml>` and replace placeholders before deployment.

```yaml
<configuration example with no real secrets>
```

## Validation

1. Confirm the collector or instrumented workload is running.
2. Check logs for export errors.
3. Verify the expected service, host, pod, database, or AI workload appears in Splunk Observability Cloud.
4. Confirm required resource attributes such as `service.name`, `deployment.environment`, and ownership tags.

## Why This Configuration

Explain the operational reason for the recommended setup, including tradeoffs.

## Troubleshooting

| Symptom | First check | Likely fix |
| --- | --- | --- |
| No telemetry appears | Token, realm, endpoint, and collector logs | Correct export path and restart the collector. |
| Telemetry appears without useful grouping | Resource attributes | Add consistent service and environment attributes. |

## Scaling Recommendations

- Define memory limits and use a memory limiter before increasing batch sizes.
- Use a gateway when many workloads export OTLP traffic.
- Control high-cardinality attributes before broad rollout.

## Security and Operations Notes

- Do not commit real tokens, API keys, database passwords, or customer data.
- Store secrets in the platform secret manager.
- Document required RBAC, IAM, firewall, or proxy rules.

## Official Documentation

- [Splunk Observability Cloud documentation](https://help.splunk.com/en/splunk-observability-cloud)
````

## Backend Example Compatibility

Recipes rendered from `chentaow-splunk/splunk-opentelemetry-examples` do not need to be rewritten upstream just to match this exact heading order. For those pages, keep the runnable example Markdown in the examples repository and let this renderer provide the wrapper, category, scenario index, navigation, and frontend catalogs.

Use the standard format as a review checklist instead of a forced upstream schema.
