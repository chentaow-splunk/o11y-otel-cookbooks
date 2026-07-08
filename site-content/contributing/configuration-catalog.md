# Frontend Configuration Catalog

Product frontends should use the generated YAML catalog at:

```text
assets/frontend/example-backend-catalog.yaml
```

The catalog is generated from YAML files in `chentaow-splunk/splunk-opentelemetry-examples` and published under `.generated/docs` during the render step. It is designed for product UI workflows that need to render a configuration picker, show a YAML preview, copy generated YAML, or download the original file.

## Catalog Contract

Each generated entry includes:

| Field | Purpose |
| --- | --- |
| `sourcePath` | Path of the YAML file inside the examples backend repository. |
| `rawPath` | Site-relative path the frontend can fetch to load the YAML file. |
| `kind` | Best-effort type classification such as `collector-config`, `helm-values`, `kubernetes-manifest`, or `yaml-config`. |
| `recipePath` | Generated recipe page associated with the YAML file when a nearby backend README can be resolved. |

## Frontend Usage

```javascript
import yaml from "js-yaml";

const response = await fetch("/assets/frontend/example-backend-catalog.yaml");
const catalog = yaml.load(await response.text());
const siteRoot = new URL("../../", response.url);

const asset = catalog.configurationAssets.find(
  (entry) => entry.kind === "collector-config",
);

const rawYaml = await fetch(new URL(asset.rawPath, siteRoot)).then((result) =>
  result.text(),
);
```

Use `sourcePath` and `recipePath` to route users from a configuration asset back to its cookbook. Do not write real token values into generated YAML. Use secret references, environment variable names, or platform-specific secret bindings.

## Schema Helper

The schema helper at `assets/frontend/configuration-catalog.schema.yaml` documents the expected keys for product frontend development. It is intentionally small because backend examples are not normalized into one product-specific schema.

When a backend example adds or changes YAML, update the local examples checkout and run:

```bash
python scripts/render_examples_site.py --source splunk-opentelemetry-examples
```
