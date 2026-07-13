---
hide:
  - toc
---

# Splunk Observability Playbooks

This site is a scenario index over runnable Splunk OpenTelemetry instrumentation and Collector examples plus renderer-owned guidance for contribution, review, and frontend consumption.

The examples themselves come from the local `splunk-opentelemetry-examples` backend checkout at build time. This repository owns the navigation model, scenario finder, contribution flow, recipe standard, and generated catalogs that make those examples easier to use as implementation cookbooks.

<div class="support-legend" aria-label="Cookbook support status legend">
  <div>
    <span class="support-pill support-pill--splunk-maintained">Maintained by Splunk</span>
    <p>Rendered from the Splunk OpenTelemetry examples source set. Official Splunk documentation remains the product source of truth.</p>
  </div>
  <div>
    <span class="support-pill support-pill--ai-generated-beta">Experimental / AI-generated</span>
    <p>Generated with AI-assisted cookbook skills and validation checks. Review before customer use.</p>
  </div>
  <div>
    <span class="support-pill support-pill--community-supported">Community-supported</span>
    <p>Submitted by users or contributors and community-supported unless maintainers promote it.</p>
  </div>
</div>

<div class="contribution-strip">
  <div>
    <strong>Missing a scenario?</strong>
    <span>Submit a recipe proposal with scenario, installation instructions, and proposed YAML. New accepted submissions are classified as community-supported by default.</span>
  </div>
  <a class="proposal-primary" href="https://github.com/chentaow-splunk/o11y-otel-cookbooks/issues/new?template=recipe-proposal.yml">Submit community recipe</a>
  <a class="proposal-secondary" href="contributing/propose-recipe/">Draft with standard</a>
</div>

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
    <div class="scenario-chips scenario-support-filter" data-support-chips aria-label="Cookbook support status"></div>

    <div class="scenario-table-wrap">
      <table class="scenario-table">
        <thead>
          <tr>
            <th scope="col">Scenario</th>
            <th scope="col">Status</th>
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
