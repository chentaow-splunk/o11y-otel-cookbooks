---
hide:
  - toc
---

# Splunk Observability Playbooks

This site is a scenario index over runnable Splunk OpenTelemetry instrumentation and Collector examples plus renderer-owned guidance for contribution, review, and frontend consumption.

The examples themselves come from the local `splunk-opentelemetry-examples` backend checkout at build time. This repository owns the navigation model, scenario finder, contribution flow, recipe standard, and generated catalogs that make those examples easier to use as implementation cookbooks.

<div class="scenario-home" data-scenario-home>
  <section class="scenario-finder" id="scenario-finder" aria-labelledby="scenario-finder-title">
    <div class="scenario-section-heading">
      <div>
        <p class="scenario-eyebrow">Browse cookbooks</p>
        <h2 id="scenario-finder-title">Filter implementation scenarios</h2>
      </div>
      <p data-scenario-count>Loading local scenarios...</p>
    </div>

    <label class="scenario-search">
      <span>Search title, category, signal, platform, or source path</span>
      <input type="search" data-scenario-search placeholder="Try: Lambda, Kubernetes, Java, RUM, gateway, Docker logs" autocomplete="off" />
    </label>

    <div class="scenario-chips" data-scenario-chips aria-label="Scenario categories"></div>

    <div class="scenario-table-wrap">
      <table class="scenario-table">
        <thead>
          <tr>
            <th scope="col">Scenario</th>
            <th scope="col">Category</th>
            <th scope="col">Signals and terms</th>
          </tr>
        </thead>
        <tbody data-scenario-results></tbody>
      </table>
    </div>

    <p class="scenario-empty" data-scenario-empty hidden>No generated scenario matched. Try a broader platform, language, or signal name.</p>
    <button class="scenario-show-all" type="button" data-scenario-show-all hidden>Show all matches</button>
  </section>
</div>

<noscript>
JavaScript is disabled, so the filterable scenario finder cannot run. Start with [OpenTelemetry Instrumentation Examples](opentelemetry-instrumentation-examples/index.md), [OpenTelemetry Collector Examples](opentelemetry-collector-examples/index.md), or [Contribution](contributing/index.md).
</noscript>

## How This Site Is Built

```text
chentaow-splunk/splunk-opentelemetry-examples
  -> generated recipe pages and YAML assets
site-content/
  -> local homepage, contribution pages, CSS, and JavaScript
.generated/docs/
  -> MkDocs build input
```

## Recommended Starting Points

| Scenario | Start here | Why |
| --- | --- | --- |
| Instrument an application | [OpenTelemetry Instrumentation Examples](opentelemetry-instrumentation-examples/index.md) | Groups language, cloud, mobile, and RUM instrumentation examples from the backend. |
| Configure a Collector pipeline | [OpenTelemetry Collector Examples](opentelemetry-collector-examples/index.md) | Focuses on Collector deployment, receiver, processor, exporter, and platform collection examples from the backend. |
| Contribute a new scenario | [Propose a Recipe](contributing/propose-recipe.md) | Captures scenario, installation instructions, proposed YAML, validation, and review notes before opening a backend PR. |

## Contribution Model

Use the examples backend for runnable source examples, example Markdown bodies, and example-local YAML. Use this renderer for navigation, scenario categorization, contribution standards, homepage behavior, and frontend catalogs.

When an example is missing, propose it in the backend repository and follow this site's [recipe standard](contributing/recipe-standard.md) as the review checklist.
