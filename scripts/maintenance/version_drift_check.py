from __future__ import annotations

import argparse
import json
import re
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from scripts.maintenance.common import (
    DEFAULT_BACKEND,
    DEFAULT_REPORT_DIR,
    Finding,
    count_by_severity,
    ensure_report_dir,
    print_report_result,
    write_json,
    write_markdown_report,
)


PY_REQ_RE = re.compile(r"^\s*([A-Za-z0-9_.-]+)==([A-Za-z0-9_.!+-]+)")
NPM_DEP_KEYS = {"dependencies", "devDependencies", "optionalDependencies", "peerDependencies"}
ACTION_RE = re.compile(r"uses:\s*([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)@([A-Za-z0-9_.-]+)")
FROM_RE = re.compile(r"^\s*FROM\s+([^\s:@]+)(?::([^\s@]+))?", re.IGNORECASE)
COLLECTOR_IMAGE_RE = re.compile(r"(?i)(?:image|repository)\s*:\s*['\"]?([^'\"\s]+(?:splunk|otel|collector)[^'\"\s]*)")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def http_json(url: str) -> dict[str, Any]:
    request = urllib.request.Request(url, headers={"User-Agent": "o11y-cookbook-maintenance/1.0"})
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def latest_pypi(package: str) -> str | None:
    try:
        return str(http_json(f"https://pypi.org/pypi/{package}/json").get("info", {}).get("version") or "")
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError):
        return None


def latest_npm(package: str) -> str | None:
    encoded = package.replace("/", "%2F")
    try:
        return str(http_json(f"https://registry.npmjs.org/{encoded}/latest").get("version") or "")
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError):
        return None


def strip_range(value: str) -> str:
    return value.strip().lstrip("^~>=< ").split(" ", 1)[0]


def scan_python_requirements(root: Path, online: bool) -> tuple[list[dict[str, Any]], list[Finding]]:
    records: list[dict[str, Any]] = []
    findings: list[Finding] = []
    for path in sorted(root.rglob("requirements*.txt")) if root.exists() else []:
        if ".git" in path.parts:
            continue
        for line_no, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), start=1):
            match = PY_REQ_RE.match(line)
            if not match:
                continue
            package, version = match.groups()
            latest = latest_pypi(package) if online else None
            status = "inventory-only"
            if latest and latest != version:
                status = "update-available"
                findings.append(
                    Finding(
                        "info",
                        str(path),
                        "Pinned Python package has a newer PyPI version.",
                        line_no,
                        f"{package} current={version} latest={latest}",
                    )
                )
            records.append({"ecosystem": "pypi", "path": str(path), "line": line_no, "package": package, "current": version, "latest": latest, "status": status})
    return records, findings


def scan_npm(root: Path, online: bool) -> tuple[list[dict[str, Any]], list[Finding]]:
    records: list[dict[str, Any]] = []
    findings: list[Finding] = []
    for path in sorted(root.rglob("package.json")) if root.exists() else []:
        if ".git" in path.parts or "node_modules" in path.parts:
            continue
        try:
            payload = read_json(path)
        except json.JSONDecodeError as exc:
            findings.append(Finding("warning", str(path), "Could not parse package.json.", detail=str(exc)))
            continue
        for dep_key in NPM_DEP_KEYS:
            deps = payload.get(dep_key) or {}
            if not isinstance(deps, dict):
                continue
            for package, raw_version in sorted(deps.items()):
                current = strip_range(str(raw_version))
                latest = latest_npm(package) if online else None
                status = "inventory-only"
                if latest and latest != current:
                    status = "update-available"
                    findings.append(
                        Finding(
                            "info",
                            str(path),
                            "NPM dependency has a newer registry version.",
                            detail=f"{package} current={raw_version} latest={latest}",
                        )
                    )
                records.append({"ecosystem": "npm", "path": str(path), "dependencyType": dep_key, "package": package, "current": str(raw_version), "latest": latest, "status": status})
    return records, findings


def scan_actions(root: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    workflows = root / ".github/workflows"
    for path in sorted(workflows.rglob("*.yml")) + sorted(workflows.rglob("*.yaml")) if workflows.exists() else []:
        for line_no, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), start=1):
            match = ACTION_RE.search(line)
            if match:
                action, version = match.groups()
                records.append({"ecosystem": "github-actions", "path": str(path), "line": line_no, "package": action, "current": version, "latest": None, "status": "inventory-only"})
    return records


def scan_images(root: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*")) if root.exists() else []:
        if not path.is_file() or ".git" in path.parts:
            continue
        if path.name != "Dockerfile" and path.suffix.lower() not in {".yaml", ".yml"}:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for line_no, line in enumerate(text.splitlines(), start=1):
            for pattern in [FROM_RE, COLLECTOR_IMAGE_RE]:
                match = pattern.search(line)
                if not match:
                    continue
                image = match.group(1)
                tag = match.group(2) if len(match.groups()) > 1 else None
                records.append({"ecosystem": "container-image", "path": str(path), "line": line_no, "package": image, "current": tag or "unspecified", "latest": None, "status": "inventory-only"})
    return records


def main() -> int:
    parser = argparse.ArgumentParser(description="Inventory runtime, package, action, and image versions used by cookbook examples.")
    parser.add_argument("--source", default=str(DEFAULT_BACKEND))
    parser.add_argument("--renderer-root", default=".")
    parser.add_argument("--report-dir", default=str(DEFAULT_REPORT_DIR))
    parser.add_argument("--online", action="store_true", help="Query PyPI and npm for current latest versions.")
    args = parser.parse_args()

    source = Path(args.source)
    renderer = Path(args.renderer_root)
    records: list[dict[str, Any]] = []
    findings: list[Finding] = []

    for root in [renderer, source]:
        py_records, py_findings = scan_python_requirements(root, args.online)
        npm_records, npm_findings = scan_npm(root, args.online)
        records.extend(py_records)
        records.extend(npm_records)
        findings.extend(py_findings)
        findings.extend(npm_findings)
        records.extend(scan_images(root))
    records.extend(scan_actions(renderer))

    report_dir = ensure_report_dir(Path(args.report_dir))
    summary = {
        "records": len(records),
        "online": args.online,
        **count_by_severity(findings),
    }
    write_json(report_dir / "version-drift.json", {"summary": summary, "records": records, "findings": [item.as_dict() for item in findings]})
    write_markdown_report(report_dir / "version-drift.md", "Version Drift Inventory", findings, summary)
    print_report_result("version-drift", report_dir, findings)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
