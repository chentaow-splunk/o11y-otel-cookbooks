# AI Assistant Backend

The AI advisor is an expandable sidebar that is intentionally separate from the Browse cookbooks filter.

Browse cookbooks uses the generated `assets/scenario-index.json` file in the browser. The AI advisor calls a server-side endpoint for semantic retrieval and recommendation.

Users can enter their own OpenAI API key in the advisor form. The key is kept only in the current page's memory until submit. This implementation does not save it in localStorage, sessionStorage, cookies, generated files, logs, or git. The browser sends it only in the current `POST /api/scenario-assistant` request, and the form clears the field after the request finishes.

The static GitHub Pages site still needs an assistant backend endpoint. The frontend does not call OpenAI directly from browser code.

## Local Architecture

```text
site-content frontend
  -> POST /api/scenario-assistant
  -> scripts/serve_scenario_assistant.py
  -> OpenAI embeddings over generated backend examples
  -> OpenAI Responses API recommendation
  -> cookbook links returned to the browser
```

The knowledge base is built from:

- `.generated/docs/assets/scenario-index.json`
- Markdown files in the local `splunk-opentelemetry-examples` checkout
- generated cookbook URLs in `.generated/docs`

## Local Run

```bash
python scripts/render_examples_site.py --source splunk-opentelemetry-examples
mkdocs build --strict
python scripts/serve_scenario_assistant.py --port 8010
```

Then open:

```text
http://127.0.0.1:8010/
```

Health check:

```bash
curl http://127.0.0.1:8010/api/scenario-assistant/health
```

The response should include `"openaiConfigured": true`. If it is `false`, stop the existing server process and start it again after `.env` is in place.

## Runtime Configuration

| Variable | Default | Purpose |
| --- | --- | --- |
| `OPENAI_API_KEY` | none | Optional server-side API key. The local server loads it from `.env` or the shell environment. If it is absent, users can provide a per-request key in the assistant form. |
| `OPENAI_SCENARIO_MODEL` | `gpt-5.5` | Model used by the Responses API for recommendation reasoning. |
| `OPENAI_EMBEDDING_MODEL` | `text-embedding-3-small` | Embedding model used for semantic retrieval over backend examples. |

The embedding cache is stored under `.cache/scenario-assistant/` and is ignored by git. A server-side `OPENAI_API_KEY` can populate that cache. A key supplied in the browser form is used for the current request only and does not write persistent embeddings to disk.

## API Contract

Request:

```http
POST /api/scenario-assistant
Content-Type: application/json
```

```json
{
  "question": "I need collector sizing guidance for a Windows .NET app and AKS PoC.",
  "apiKey": "optional per-request OpenAI API key"
}
```

Response:

```json
{
  "answer": "Start with the collector deployment and Kubernetes gateway examples...",
  "recommendations": [
    {
      "title": "Kubernetes Collector with Gateway",
      "url": "foundations/collector-deployment/k8s-collector-with-gateway/",
      "category": "OpenTelemetry Collector Examples",
      "sourcePath": "collector/k8s-collector-with-gateway/README.md",
      "supportStatus": "splunk-maintained",
      "supportLabel": "Maintained by Splunk",
      "why": "Matches the AKS gateway collector part of the scenario."
    }
  ],
  "sourceCommit": "<examples backend commit>",
  "retrieval": "openai-embeddings"
}
```

## Production Notes

- Keep the OpenAI API key in the server environment or secret manager.
- If allowing users to bring their own key, treat the key as request-only data and never log it.
- Rate limit the endpoint before exposing it beyond trusted users.
- Log request IDs and errors, not full user prompts, unless policy allows prompt logging.
- Rebuild the site and restart the assistant when the examples backend changes.
- Do not return recommendations that are not present in the generated scenario index.
