from __future__ import annotations

import argparse
import re
from pathlib import Path

from scripts.maintenance.common import (
    DEFAULT_BACKEND,
    DEFAULT_REPORT_DIR,
    Finding,
    count_by_severity,
    ensure_report_dir,
    first_heading,
    markdown_files,
    print_report_result,
    write_json,
    write_markdown_report,
)


RENDERED_ROOTS = {"collector", "instrumentation"}

SIGNALS = {
    "scenario": re.compile(r"(?i)\b(scenario|use this|when to use|overview|example demonstrates)\b"),
    "architecture": re.compile(r"(?i)\b(architecture|data flow|pipeline|collector|receiver|processor|exporter|daemonset|gateway|sidecar)\b"),
    "prerequisites": re.compile(r"(?i)\b(prerequisite|required|requirements|before you begin|tools required)\b"),
    "installation": re.compile(r"(?i)\b(install|deploy|apply|helm|kubectl|docker|run|build|configure)\b"),
    "configuration": re.compile(r"(?i)\b(yaml|values\.yaml|otelcol|collector config|configuration|environment variable|manifest)\b"),
    "validation": re.compile(r"(?i)\b(validate|validation|verify|confirm|check|splunk observability|apm|metrics|logs|trace)\b"),
    "troubleshooting": re.compile(r"(?i)\b(troubleshoot|debug|known issue|failure|error|logs)\b"),
    "scaling": re.compile(r"(?i)\b(scale|sizing|resource|memory|cpu|batch|sampling|cardinality|throughput)\b"),
    "security": re.compile(r"(?i)\b(secret|token|credential|rbac|iam|tls|security|permission|least privilege)\b"),
    "official_docs": re.compile(r"https://help\.splunk\.com/[^\s)]+"),
}


def rendered_markdown(path: Path, source: Path) -> bool:
    try:
        rel = path.relative_to(source)
    except ValueError:
        return False
    return bool(rel.parts) and rel.parts[0] in RENDERED_ROOTS and path.name.lower() == "readme.md"


def nearby_yaml(path: Path) -> list[str]:
    return [
        item.name
        for item in sorted(path.parent.iterdir())
        if item.is_file() and item.suffix.lower() in {".yaml", ".yml"}
    ]


def review_file(path: Path, source: Path) -> tuple[dict[str, object], list[Finding]]:
    text = path.read_text(encoding="utf-8", errors="replace")
    rel = path.relative_to(source).as_posix()
    title = first_heading(text) or rel
    normalized = re.sub(r"```.*?```", " ", text, flags=re.DOTALL)
    yaml_assets = nearby_yaml(path)
    present = {name: bool(pattern.search(normalized)) for name, pattern in SIGNALS.items()}
    if yaml_assets:
        present["configuration"] = True

    findings: list[Finding] = []
    required = ["scenario", "installation", "configuration", "validation"]
    for key in required:
        if not present[key]:
            findings.append(
                Finding(
                    "warning",
                    rel,
                    f"Cookbook may be missing {key.replace('_', ' ')} coverage.",
                    detail=f"title={title!r}",
                )
            )

    recommended = ["architecture", "troubleshooting", "scaling", "security", "official_docs"]
    for key in recommended:
        if not present[key]:
            findings.append(
                Finding(
                    "info",
                    rel,
                    f"Cookbook does not clearly include {key.replace('_', ' ')} guidance.",
                    detail=f"title={title!r}",
                )
            )

    report = {
        "path": rel,
        "title": title,
        "signals": present,
        "yamlAssets": yaml_assets,
        "findingCount": len(findings),
    }
    return report, findings


def main() -> int:
    parser = argparse.ArgumentParser(description="Review rendered backend cookbooks against the recipe standard.")
    parser.add_argument("--source", default=str(DEFAULT_BACKEND))
    parser.add_argument("--report-dir", default=str(DEFAULT_REPORT_DIR))
    parser.add_argument("--strict", action="store_true", help="Fail when warning-level findings are present.")
    args = parser.parse_args()

    source = Path(args.source)
    findings: list[Finding] = []
    reports: list[dict[str, object]] = []

    for path in markdown_files(source):
        if not rendered_markdown(path, source):
            continue
        report, file_findings = review_file(path, source)
        reports.append(report)
        findings.extend(file_findings)

    report_dir = ensure_report_dir(Path(args.report_dir))
    summary = {
        "reviewedCookbooks": len(reports),
        **count_by_severity(findings),
    }
    write_json(report_dir / "content-review.json", {"summary": summary, "cookbooks": reports, "findings": [item.as_dict() for item in findings]})
    write_markdown_report(report_dir / "content-review.md", "Cookbook Content Review", findings, summary)
    print_report_result("content-review", report_dir, findings)
    if args.strict and any(item.severity == "warning" for item in findings):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
