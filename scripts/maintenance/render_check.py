from __future__ import annotations

import argparse
import posixpath
import subprocess
from pathlib import Path

from scripts.maintenance.common import (
    DEFAULT_BACKEND,
    DEFAULT_REPORT_DIR,
    EXPECTED_BACKEND_BRANCH,
    EXPECTED_SOURCE_REPOSITORY,
    FRONTEND_CATALOG,
    GENERATED_DOCS,
    SCENARIO_INDEX,
    Finding,
    current_branch,
    current_commit,
    ensure_report_dir,
    load_json,
    mkdocs_command,
    parse_simple_yaml_catalog,
    print_report_result,
    python_command,
    remote_url,
    repo_status,
    run,
    write_json,
    write_markdown_report,
)


EXPECTED_CATEGORIES = {
    "OpenTelemetry Collector Examples",
    "OpenTelemetry Instrumentation Examples",
}


def page_exists(generated_docs: Path, url: str) -> bool:
    clean = url.split("#", 1)[0].strip("/")
    if not clean:
        return (generated_docs / "index.md").exists()
    return (generated_docs / clean / "index.md").exists() or (generated_docs / f"{clean}.md").exists()


def validate_index(generated_docs: Path) -> tuple[dict, list[Finding]]:
    findings: list[Finding] = []
    if not SCENARIO_INDEX.exists():
        return {}, [Finding("error", str(SCENARIO_INDEX), "Scenario index was not generated.")]

    index = load_json(SCENARIO_INDEX)
    scenarios = index.get("scenarios")
    if not isinstance(scenarios, list):
        findings.append(Finding("error", str(SCENARIO_INDEX), "`scenarios` must be a list."))
        scenarios = []

    if index.get("scenarioCount") != len(scenarios):
        findings.append(
            Finding(
                "error",
                str(SCENARIO_INDEX),
                "`scenarioCount` does not match the number of scenario entries.",
                detail=f"scenarioCount={index.get('scenarioCount')} actual={len(scenarios)}",
            )
        )

    categories = set(index.get("categories") or [])
    if categories != EXPECTED_CATEGORIES:
        findings.append(
            Finding(
                "error",
                str(SCENARIO_INDEX),
                "Generated categories do not match the two supported cookbook categories.",
                detail=f"categories={sorted(categories)}",
            )
        )

    if index.get("generatedFrom") != EXPECTED_SOURCE_REPOSITORY:
        findings.append(
            Finding(
                "warning",
                str(SCENARIO_INDEX),
                "Scenario index source repository does not match the renderer contract.",
                detail=f"generatedFrom={index.get('generatedFrom')}",
            )
        )

    for entry in scenarios:
        title = str(entry.get("title") or "").strip()
        url = str(entry.get("url") or "").strip()
        source_path = str(entry.get("sourcePath") or "").strip()
        if not title:
            findings.append(Finding("error", str(SCENARIO_INDEX), "Scenario is missing a title."))
        if not url or not page_exists(generated_docs, url):
            findings.append(
                Finding(
                    "error",
                    str(SCENARIO_INDEX),
                    "Scenario URL does not resolve to a generated page.",
                    detail=f"title={title!r} url={url!r}",
                )
            )
        if not source_path.startswith(("collector/", "instrumentation/")):
            findings.append(
                Finding(
                    "error",
                    str(SCENARIO_INDEX),
                    "Scenario source path is outside the rendered backend categories.",
                    detail=f"title={title!r} sourcePath={source_path!r}",
                )
            )
    return index, findings


def validate_catalog(generated_docs: Path) -> tuple[list[dict[str, str]], list[Finding]]:
    findings: list[Finding] = []
    if not FRONTEND_CATALOG.exists():
        return [], [Finding("error", str(FRONTEND_CATALOG), "Frontend YAML catalog was not generated.")]

    entries = parse_simple_yaml_catalog(FRONTEND_CATALOG)
    if not entries:
        findings.append(Finding("warning", str(FRONTEND_CATALOG), "Frontend YAML catalog contains no configuration assets."))

    for entry in entries:
        raw_path = entry.get("rawPath", "")
        source_path = entry.get("sourcePath", "")
        kind = entry.get("kind", "")
        if not source_path:
            findings.append(Finding("error", str(FRONTEND_CATALOG), "Catalog entry is missing sourcePath."))
        if not raw_path or not (generated_docs / raw_path).exists():
            findings.append(
                Finding(
                    "error",
                    str(FRONTEND_CATALOG),
                    "Catalog rawPath does not resolve to a generated asset.",
                    detail=f"sourcePath={source_path!r} rawPath={raw_path!r}",
                )
            )
        if kind not in {"collector-config", "helm-values", "kubernetes-manifest", "docker-compose", "helm-chart", "yaml-config"}:
            findings.append(
                Finding(
                    "warning",
                    str(FRONTEND_CATALOG),
                    "Catalog entry has an unexpected kind.",
                    detail=f"sourcePath={source_path!r} kind={kind!r}",
                )
            )
        recipe_path = entry.get("recipePath")
        if recipe_path and not page_exists(generated_docs, recipe_path.removesuffix("/index.md")):
            normalized = posixpath.dirname(recipe_path) if recipe_path.endswith("/index.md") else recipe_path
            if not page_exists(generated_docs, normalized):
                findings.append(
                    Finding(
                        "warning",
                        str(FRONTEND_CATALOG),
                        "Catalog recipePath does not resolve to a generated page.",
                        detail=f"sourcePath={source_path!r} recipePath={recipe_path!r}",
                    )
                )
    return entries, findings


def main() -> int:
    parser = argparse.ArgumentParser(description="Render the examples backend and validate generated MkDocs artifacts.")
    parser.add_argument("--source", default=str(DEFAULT_BACKEND))
    parser.add_argument("--report-dir", default=str(DEFAULT_REPORT_DIR))
    parser.add_argument("--expected-branch", default=EXPECTED_BACKEND_BRANCH)
    parser.add_argument("--mkdocs", default=None, help="Path to mkdocs executable. Defaults to .venv/bin/mkdocs or PATH.")
    parser.add_argument("--skip-build", action="store_true")
    parser.add_argument("--require-clean-backend", action="store_true")
    args = parser.parse_args()

    source = Path(args.source)
    report_dir = ensure_report_dir(Path(args.report_dir))
    findings: list[Finding] = []

    if not source.exists():
        findings.append(Finding("error", str(source), "Backend source checkout does not exist."))
    else:
        branch = current_branch(source)
        if args.expected_branch and branch != args.expected_branch:
            findings.append(
                Finding(
                    "warning",
                    str(source),
                    "Backend branch does not match the expected cookbook branch.",
                    detail=f"expected={args.expected_branch} actual={branch}",
                )
            )
        status = repo_status(source)
        if args.require_clean_backend and "\n?? " in f"\n{status}":
            findings.append(Finding("error", str(source), "Backend checkout has untracked files.", detail=status))

    if source.exists():
        render = run([python_command(), "scripts/render_examples_site.py", "--source", str(source)], check=False)
        if render.returncode != 0:
            findings.append(
                Finding(
                    "error",
                    "scripts/render_examples_site.py",
                    "Render script failed.",
                    detail=(render.stderr or render.stdout)[-1000:],
                )
            )

    if source.exists() and not args.skip_build:
        try:
            build = run([*mkdocs_command(args.mkdocs), "build", "--strict"], check=False)
        except FileNotFoundError as exc:
            build = subprocess.CompletedProcess(args=["mkdocs"], returncode=127, stdout="", stderr=str(exc))
        if build.returncode != 0:
            findings.append(
                Finding(
                    "error",
                    "mkdocs.yml",
                    "MkDocs strict build failed.",
                    detail=(build.stderr or build.stdout)[-1000:],
                )
            )

    index, index_findings = validate_index(GENERATED_DOCS)
    catalog, catalog_findings = validate_catalog(GENERATED_DOCS)
    findings.extend(index_findings)
    findings.extend(catalog_findings)

    summary = {
        "backendRemote": remote_url(source) if source.exists() else "missing",
        "backendBranch": current_branch(source) if source.exists() else "missing",
        "backendCommit": current_commit(source) if source.exists() else "missing",
        "scenarioCount": index.get("scenarioCount", 0) if index else 0,
        "catalogAssetCount": len(catalog),
    }
    write_json(report_dir / "render-check.json", {"summary": summary, "findings": [item.as_dict() for item in findings]})
    write_markdown_report(report_dir / "render-check.md", "Render Check", findings, summary)
    print_report_result("render-check", report_dir, findings)
    return 1 if any(item.severity == "error" for item in findings) else 0


if __name__ == "__main__":
    raise SystemExit(main())
