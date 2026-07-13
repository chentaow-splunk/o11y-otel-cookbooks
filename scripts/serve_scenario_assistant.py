#!/usr/bin/env python3
"""Serve the rendered site with an OpenAI-backed cookbook advisor endpoint.

The static MkDocs site cannot safely hold an OpenAI API key. This server keeps
the key on the server side, uses embeddings over the generated examples
knowledge base for semantic retrieval, and asks the Responses API to recommend
the best cookbook links.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


DEFAULT_MODEL = "gpt-5.5"
DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"
OPENAI_BASE_URL = "https://api.openai.com/v1"


def load_env_file(path: Path) -> bool:
    """Load simple KEY=VALUE pairs from a local .env file without overriding the shell."""
    if not path.is_file():
        return False

    for raw_line in read_text(path).splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key or key in os.environ:
            continue

        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        os.environ[key] = value
    return True


def load_default_env_files() -> list[Path]:
    project_root = Path(__file__).resolve().parents[1]
    candidates = [Path.cwd() / ".env", project_root / ".env"]
    loaded: list[Path] = []
    seen: set[Path] = set()

    for candidate in candidates:
        path = candidate.resolve()
        if path in seen:
            continue
        seen.add(path)
        if load_env_file(path):
            loaded.append(path)
    return loaded


@dataclass(frozen=True)
class ScenarioDoc:
    doc_id: str
    title: str
    url: str
    category: str
    source_path: str
    summary: str
    body: str
    support_status: str
    support_label: str
    support_description: str
    support_source: str

    @property
    def embedding_text(self) -> str:
        body = self.body[:5000]
        return (
            f"Title: {self.title}\n"
            f"Category: {self.category}\n"
            f"Support status: {self.support_label}\n"
            f"Source path: {self.source_path}\n"
            f"Summary: {self.summary}\n"
            f"Example content:\n{body}"
        )

    def candidate_payload(self) -> dict[str, str]:
        return {
            "id": self.doc_id,
            "title": self.title,
            "url": self.url,
            "category": self.category,
            "sourcePath": self.source_path,
            "summary": self.summary,
            "excerpt": self.body[:1800],
            "supportStatus": self.support_status,
            "supportLabel": self.support_label,
            "supportDescription": self.support_description,
            "supportSource": self.support_source,
        }


class AssistantError(RuntimeError):
    def __init__(self, message: str, status: int = 500) -> None:
        super().__init__(message)
        self.status = status


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8010)
    parser.add_argument("--site", default="site")
    parser.add_argument("--generated-docs", default=".generated/docs")
    parser.add_argument("--examples", default="splunk-opentelemetry-examples")
    parser.add_argument("--cache", default=".cache/scenario-assistant/embeddings.json")
    parser.add_argument("--model", default=os.environ.get("OPENAI_SCENARIO_MODEL", DEFAULT_MODEL))
    parser.add_argument(
        "--embedding-model",
        default=os.environ.get("OPENAI_EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL),
    )
    return parser.parse_args()


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def strip_markdown(markdown: str) -> str:
    text = re.sub(r"```.*?```", " ", markdown, flags=re.DOTALL)
    text = re.sub(r"!\[[^\]]*\]\([^)]+\)", " ", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"^#{1,6}\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"[>*_`|]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def related_yaml_context(examples_root: Path, source_path: str) -> str:
    if not source_path or source_path == "README.md":
        return ""

    base_dir = (examples_root / source_path).parent
    if not base_dir.exists():
        return ""

    snippets: list[str] = []
    for path in sorted(base_dir.rglob("*")):
        if len(snippets) >= 6:
            break
        if path.suffix.lower() not in {".yaml", ".yml"} or ".git" in path.parts:
            continue
        rel = path.relative_to(examples_root).as_posix()
        text = read_text(path)
        snippets.append(f"{rel}\n{text[:1800]}")
    if not snippets:
        return ""
    return "\n\nRelated YAML assets:\n" + "\n\n---\n\n".join(snippets)


def load_scenarios(generated_docs: Path, examples_root: Path) -> tuple[str, list[ScenarioDoc]]:
    index_path = generated_docs / "assets/scenario-index.json"
    if not index_path.exists():
        raise AssistantError(
            f"Scenario index not found at {index_path}. Run scripts/render_examples_site.py first.",
            status=500,
        )

    index = json.loads(read_text(index_path))
    source_commit = str(index.get("sourceCommit") or "unknown")
    docs: list[ScenarioDoc] = []

    for idx, scenario in enumerate(index.get("scenarios", [])):
        source_path = str(scenario.get("sourcePath") or "")
        backend_file = examples_root / source_path
        if backend_file.is_file():
            body = strip_markdown(read_text(backend_file)) + related_yaml_context(examples_root, source_path)
        else:
            body = strip_markdown(str(scenario.get("summary") or ""))

        docs.append(
            ScenarioDoc(
                doc_id=f"doc_{idx}",
                title=str(scenario.get("title") or source_path or f"Scenario {idx}"),
                url=str(scenario.get("url") or ""),
                category=str(scenario.get("category") or ""),
                source_path=source_path,
                summary=str(scenario.get("summary") or ""),
                body=body,
                support_status=str(scenario.get("supportStatus") or "splunk-maintained"),
                support_label=str(scenario.get("supportLabel") or "Maintained by Splunk"),
                support_description=str(scenario.get("supportDescription") or ""),
                support_source=str(scenario.get("supportSource") or ""),
            )
        )

    return source_commit, docs


def openai_json(path: str, payload: dict[str, Any], api_key: str) -> dict[str, Any]:
    request = urllib.request.Request(
        f"{OPENAI_BASE_URL}{path}",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise AssistantError(f"OpenAI API returned HTTP {exc.code}: {detail}", status=502) from exc
    except urllib.error.URLError as exc:
        raise AssistantError(f"OpenAI API request failed: {exc.reason}", status=502) from exc


def cache_key(source_commit: str, model: str, docs: list[ScenarioDoc]) -> str:
    digest = hashlib.sha256()
    digest.update(source_commit.encode("utf-8"))
    digest.update(model.encode("utf-8"))
    for doc in docs:
        digest.update(doc.source_path.encode("utf-8"))
        digest.update(doc.embedding_text[:6000].encode("utf-8"))
    return digest.hexdigest()


def batched(items: list[str], size: int) -> list[list[str]]:
    return [items[index : index + size] for index in range(0, len(items), size)]


def embed_texts(texts: list[str], api_key: str, model: str) -> list[list[float]]:
    vectors: list[list[float]] = []
    for chunk in batched(texts, 64):
        response = openai_json(
            "/embeddings",
            {
                "model": model,
                "input": chunk,
                "encoding_format": "float",
            },
            api_key,
        )
        data = sorted(response.get("data", []), key=lambda item: item.get("index", 0))
        vectors.extend(item["embedding"] for item in data)
    if len(vectors) != len(texts):
        raise AssistantError("Embedding response did not contain the expected number of vectors.", status=502)
    return vectors


def dot(a: list[float], b: list[float]) -> float:
    return sum(left * right for left, right in zip(a, b))


def norm(a: list[float]) -> float:
    return math.sqrt(sum(value * value for value in a)) or 1.0


def cosine(a: list[float], b: list[float]) -> float:
    return dot(a, b) / (norm(a) * norm(b))


class ScenarioKnowledgeBase:
    def __init__(
        self,
        source_commit: str,
        docs: list[ScenarioDoc],
        cache_path: Path,
        embedding_model: str,
    ) -> None:
        self.source_commit = source_commit
        self.docs = docs
        self.cache_path = cache_path
        self.embedding_model = embedding_model
        self._vectors: list[list[float]] | None = None
        self._cache_key = cache_key(source_commit, embedding_model, docs)

    def embeddings(self, api_key: str, persist: bool = True) -> list[list[float]]:
        if self._vectors is not None:
            return self._vectors

        if self.cache_path.exists():
            cache = json.loads(read_text(self.cache_path))
            if cache.get("cacheKey") == self._cache_key:
                self._vectors = cache.get("vectors", [])
                if len(self._vectors) == len(self.docs):
                    return self._vectors

        vectors = embed_texts([doc.embedding_text for doc in self.docs], api_key, self.embedding_model)
        if persist:
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            self.cache_path.write_text(
                json.dumps(
                    {
                        "cacheKey": self._cache_key,
                        "sourceCommit": self.source_commit,
                        "embeddingModel": self.embedding_model,
                        "generatedAt": int(time.time()),
                        "vectors": vectors,
                    }
                ),
                encoding="utf-8",
            )
            self._vectors = vectors
        return vectors

    def semantic_candidates(
        self,
        question: str,
        api_key: str,
        limit: int = 12,
        persist_embeddings: bool = True,
    ) -> list[ScenarioDoc]:
        query_vector = embed_texts([question], api_key, self.embedding_model)[0]
        scored = [
            (cosine(query_vector, vector), doc)
            for vector, doc in zip(self.embeddings(api_key, persist=persist_embeddings), self.docs)
        ]
        scored.sort(key=lambda item: item[0], reverse=True)
        return [doc for _, doc in scored[:limit]]


RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "answer": {
            "type": "string",
            "description": "A concise recommendation summary grounded in the candidate cookbook list.",
        },
        "recommendations": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "id": {"type": "string"},
                    "why": {"type": "string"},
                },
                "required": ["id", "why"],
            },
        },
    },
    "required": ["answer", "recommendations"],
}


def extract_output_text(response: dict[str, Any]) -> str:
    if isinstance(response.get("output_text"), str):
        return response["output_text"]

    parts: list[str] = []
    for item in response.get("output", []):
        for content in item.get("content", []):
            if content.get("type") == "output_text":
                parts.append(str(content.get("text") or ""))
    return "\n".join(parts).strip()


def ask_openai(question: str, candidates: list[ScenarioDoc], api_key: str, model: str) -> dict[str, Any]:
    candidate_payloads = [doc.candidate_payload() for doc in candidates]
    response = openai_json(
        "/responses",
        {
            "model": model,
            "input": [
                {
                    "role": "developer",
                    "content": (
                        "You are an observability cookbook routing assistant. "
                        "Recommend only from the supplied candidate cookbooks. "
                        "Use the candidate source excerpts as the knowledge base. "
                        "Do not invent cookbook URLs, Splunk product claims, commands, or support status. "
                        "If the scenario is ambiguous, explain the ambiguity and recommend the safest starting points."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "question": question,
                            "candidateCookbooks": candidate_payloads,
                        },
                        ensure_ascii=False,
                    ),
                },
            ],
            "reasoning": {"effort": "low"},
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "cookbook_recommendations",
                    "strict": True,
                    "schema": RESPONSE_SCHEMA,
                },
                "verbosity": "low",
            },
        },
        api_key,
    )

    raw_text = extract_output_text(response)
    if not raw_text:
        raise AssistantError("OpenAI response did not contain text output.", status=502)

    try:
        model_payload = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise AssistantError(f"OpenAI response was not valid JSON: {raw_text[:300]}", status=502) from exc

    candidates_by_id = {doc.doc_id: doc for doc in candidates}
    recommendations: list[dict[str, str]] = []
    for item in model_payload.get("recommendations", []):
        doc = candidates_by_id.get(str(item.get("id") or ""))
        if not doc:
            continue
        recommendations.append(
            {
                "title": doc.title,
                "url": doc.url,
                "category": doc.category,
                "sourcePath": doc.source_path,
                "supportStatus": doc.support_status,
                "supportLabel": doc.support_label,
                "supportDescription": doc.support_description,
                "supportSource": doc.support_source,
                "why": str(item.get("why") or ""),
            }
        )

    return {
        "answer": str(model_payload.get("answer") or ""),
        "recommendations": recommendations,
        "retrieval": "openai-embeddings",
    }


def make_handler(kb: ScenarioKnowledgeBase, site_dir: Path, model: str) -> type[SimpleHTTPRequestHandler]:
    class ScenarioAssistantHandler(SimpleHTTPRequestHandler):
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            super().__init__(*args, directory=str(site_dir), **kwargs)

        def end_headers(self) -> None:
            self.send_header("Cache-Control", "no-store")
            super().end_headers()

        def send_json(self, status: int, payload: dict[str, Any]) -> None:
            body = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:
            if urlparse(self.path).path == "/api/scenario-assistant/health":
                self.send_json(
                    200,
                    {
                        "ok": True,
                        "scenarioCount": len(kb.docs),
                        "sourceCommit": kb.source_commit,
                        "openaiConfigured": bool(os.environ.get("OPENAI_API_KEY")),
                        "acceptsRequestApiKey": True,
                        "model": model,
                        "embeddingModel": kb.embedding_model,
                    },
                )
                return
            super().do_GET()

        def do_POST(self) -> None:
            if urlparse(self.path).path != "/api/scenario-assistant":
                self.send_error(404)
                return

            try:
                length = int(self.headers.get("Content-Length") or "0")
                request_body = self.rfile.read(length).decode("utf-8")
                payload = json.loads(request_body or "{}")
                question = str(payload.get("question") or "").strip()
                request_api_key = str(payload.get("apiKey") or "").strip()
                api_key = request_api_key or os.environ.get("OPENAI_API_KEY")
                if not api_key:
                    raise AssistantError(
                        (
                            "OPENAI_API_KEY is not set on the assistant backend. "
                            "Enter an OpenAI API key in the assistant form for a one-request use, "
                            "or run this server with the key in the server environment."
                        ),
                        status=503,
                    )
                if not question:
                    raise AssistantError("Question is required.", status=400)
                if len(question) > 4000:
                    raise AssistantError("Question is too long. Keep it under 4000 characters.", status=400)

                candidates = kb.semantic_candidates(
                    question,
                    api_key,
                    persist_embeddings=not bool(request_api_key),
                )
                answer = ask_openai(question, candidates, api_key, model)
                answer["sourceCommit"] = kb.source_commit
                self.send_json(200, answer)
            except AssistantError as exc:
                self.send_json(exc.status, {"error": str(exc)})
            except Exception as exc:  # pragma: no cover - defensive server boundary
                self.send_json(500, {"error": f"Assistant request failed: {exc}"})

    return ScenarioAssistantHandler


def main() -> int:
    loaded_env_files = load_default_env_files()
    args = parse_args()
    site_dir = Path(args.site).resolve()
    generated_docs = Path(args.generated_docs).resolve()
    examples_root = Path(args.examples).resolve()

    if not site_dir.exists():
        print(f"Site directory not found: {site_dir}. Run mkdocs build first.", file=sys.stderr)
        return 2

    source_commit, docs = load_scenarios(generated_docs, examples_root)
    kb = ScenarioKnowledgeBase(
        source_commit=source_commit,
        docs=docs,
        cache_path=Path(args.cache).resolve(),
        embedding_model=args.embedding_model,
    )
    handler = make_handler(kb, site_dir, args.model)
    server = ThreadingHTTPServer((args.host, args.port), handler)
    print(f"Serving site and OpenAI assistant on http://{args.host}:{args.port}/", flush=True)
    print(f"Loaded {len(docs)} scenarios from {source_commit}.", flush=True)
    if loaded_env_files:
        print("Loaded local environment from: " + ", ".join(str(path) for path in loaded_env_files), flush=True)
    if os.environ.get("OPENAI_API_KEY"):
        print("OPENAI_API_KEY is configured for the assistant backend.", flush=True)
    else:
        print("Set OPENAI_API_KEY in .env or this server process to enable /api/scenario-assistant.", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server.")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
