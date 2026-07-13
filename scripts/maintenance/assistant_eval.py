from __future__ import annotations

import argparse
import json
import re
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from scripts.maintenance.common import (
    DEFAULT_REPORT_DIR,
    SCENARIO_INDEX,
    Finding,
    ensure_report_dir,
    load_json,
    print_report_result,
    write_json,
    write_markdown_report,
)


DEFAULT_PROMPTS = [
    {
        "name": "kubernetes gateway collector",
        "question": "I need to size and deploy a Kubernetes collector with a gateway for AKS.",
        "expected_terms": ["k8s", "kubernetes", "gateway", "collector"],
    },
    {
        "name": "windows dotnet app",
        "question": "I have a Windows .NET Framework application and need OpenTelemetry traces.",
        "expected_terms": ["dotnet", "windows"],
    },
    {
        "name": "prometheus scrape to splunk",
        "question": "I need the collector to scrape Prometheus metrics and send them to Splunk.",
        "expected_terms": ["prometheus", "scrape", "splunk"],
    },
    {
        "name": "sensitive data redaction",
        "question": "I need to redact passwords or tokens before exporting telemetry.",
        "expected_terms": ["redact", "sensitive", "logs"],
    },
    {
        "name": "python kubernetes app",
        "question": "I need to instrument a Python service running in Kubernetes.",
        "expected_terms": ["python", "k8s", "kubernetes"],
    },
]


def tokenize(text: str) -> set[str]:
    return {item for item in re.split(r"[^a-z0-9]+", text.lower()) if len(item) > 1}


def offline_recommendations(index: dict[str, Any], question: str, limit: int = 5) -> list[dict[str, str]]:
    query = tokenize(question)
    scored = []
    for scenario in index.get("scenarios", []):
        text = " ".join(
            str(scenario.get(key) or "")
            for key in ["title", "category", "summary", "sourcePath"]
        )
        tags = set(scenario.get("tags") or [])
        tokens = tokenize(text) | {str(tag).lower() for tag in tags}
        score = len(query & tokens)
        scored.append((score, scenario))
    scored.sort(key=lambda item: (item[0], str(item[1].get("title") or "")), reverse=True)
    return [
        {
            "title": str(item.get("title") or ""),
            "url": str(item.get("url") or ""),
            "sourcePath": str(item.get("sourcePath") or ""),
            "category": str(item.get("category") or ""),
            "supportStatus": str(item.get("supportStatus") or ""),
            "supportLabel": str(item.get("supportLabel") or ""),
            "why": "Offline token-overlap baseline used because no assistant server URL was supplied.",
        }
        for score, item in scored[:limit]
        if score > 0
    ]


def call_assistant(server_url: str, question: str) -> dict[str, Any]:
    endpoint = server_url.rstrip("/") + "/api/scenario-assistant"
    request = urllib.request.Request(
        endpoint,
        data=json.dumps({"question": question}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=90) as response:
        return json.loads(response.read().decode("utf-8"))


def evaluate_prompt(index: dict[str, Any], prompt: dict[str, Any], server_url: str | None) -> tuple[dict[str, Any], list[Finding]]:
    urls = {str(item.get("url") or "") for item in index.get("scenarios", [])}
    findings: list[Finding] = []
    question = str(prompt["question"])
    mode = "offline"

    if server_url:
        try:
            response = call_assistant(server_url, question)
            recommendations = response.get("recommendations", [])
            mode = "assistant"
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError) as exc:
            findings.append(Finding("warning", "assistant", "Assistant endpoint could not be evaluated.", detail=str(exc)))
            recommendations = offline_recommendations(index, question)
    else:
        recommendations = offline_recommendations(index, question)

    if not recommendations:
        findings.append(Finding("warning", "scenario-index", "No recommendations returned for prompt.", detail=prompt["name"]))

    expected_terms = {str(item).lower() for item in prompt.get("expected_terms", [])}
    combined = " ".join(
        " ".join(str(rec.get(key) or "") for key in ["title", "url", "sourcePath", "category", "supportLabel", "why"])
        for rec in recommendations
    ).lower()
    if expected_terms and not any(term in combined for term in expected_terms):
        findings.append(
            Finding(
                "warning",
                "scenario-index",
                "Recommendations do not appear to match expected scenario terms.",
                detail=f"prompt={prompt['name']!r} expected={sorted(expected_terms)}",
            )
        )

    for rec in recommendations:
        url = str(rec.get("url") or "")
        if url not in urls:
            findings.append(
                Finding(
                    "error",
                    "assistant",
                    "Assistant returned a URL that is not present in scenario-index.json.",
                    detail=f"prompt={prompt['name']!r} url={url!r}",
                )
            )

    report = {
        "name": prompt["name"],
        "question": question,
        "mode": mode,
        "recommendationCount": len(recommendations),
        "recommendations": recommendations,
    }
    return report, findings


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate scenario assistant routing against generated cookbook links.")
    parser.add_argument("--scenario-index", default=str(SCENARIO_INDEX))
    parser.add_argument("--server-url", default=None, help="Optional local assistant server URL, for example http://127.0.0.1:8010.")
    parser.add_argument("--prompts", default=None, help="Optional JSON file containing prompt objects.")
    parser.add_argument("--report-dir", default=str(DEFAULT_REPORT_DIR))
    args = parser.parse_args()

    index_path = Path(args.scenario_index)
    index = load_json(index_path)
    prompts = DEFAULT_PROMPTS
    if args.prompts:
        prompts = json.loads(Path(args.prompts).read_text(encoding="utf-8"))

    findings: list[Finding] = []
    prompt_reports: list[dict[str, Any]] = []
    for prompt in prompts:
        report, prompt_findings = evaluate_prompt(index, prompt, args.server_url)
        prompt_reports.append(report)
        findings.extend(prompt_findings)

    report_dir = ensure_report_dir(Path(args.report_dir))
    summary = {
        "promptCount": len(prompt_reports),
        "mode": "assistant" if args.server_url else "offline",
        "error": sum(1 for item in findings if item.severity == "error"),
        "warning": sum(1 for item in findings if item.severity == "warning"),
    }
    write_json(report_dir / "assistant-eval.json", {"summary": summary, "prompts": prompt_reports, "findings": [item.as_dict() for item in findings]})
    write_markdown_report(report_dir / "assistant-eval.md", "Assistant Routing Evaluation", findings, summary)
    print_report_result("assistant-eval", report_dir, findings)
    return 1 if any(item.severity == "error" for item in findings) else 0


if __name__ == "__main__":
    raise SystemExit(main())
