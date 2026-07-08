from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


DEFAULT_BACKEND = Path("splunk-opentelemetry-examples")
DEFAULT_REPORT_DIR = Path("maintenance-reports")
GENERATED_DOCS = Path(".generated/docs")
SCENARIO_INDEX = GENERATED_DOCS / "assets/scenario-index.json"
FRONTEND_CATALOG = GENERATED_DOCS / "assets/frontend/example-backend-catalog.yaml"
EXPECTED_SOURCE_REPOSITORY = "https://github.com/chentaow-splunk/splunk-opentelemetry-examples/tree/codex/collector-data-processing-cookbooks"
EXPECTED_BACKEND_BRANCH = "codex/collector-data-processing-cookbooks"


@dataclass
class Finding:
    severity: str
    path: str
    message: str
    line: int | None = None
    detail: str | None = None

    def as_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "severity": self.severity,
            "path": self.path,
            "message": self.message,
        }
        if self.line is not None:
            payload["line"] = self.line
        if self.detail:
            payload["detail"] = self.detail
        return payload


def run(cmd: list[str], cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, check=check, text=True, capture_output=True)


def git_value(repo: Path, *args: str) -> str:
    try:
        return run(["git", "-C", str(repo), *args], check=True).stdout.strip()
    except (FileNotFoundError, subprocess.CalledProcessError):
        return "unknown"


def current_branch(repo: Path) -> str:
    return git_value(repo, "branch", "--show-current")


def current_commit(repo: Path) -> str:
    return git_value(repo, "rev-parse", "HEAD")


def remote_url(repo: Path) -> str:
    return git_value(repo, "remote", "get-url", "origin")


def repo_status(repo: Path) -> str:
    return git_value(repo, "status", "--short", "--branch")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def ensure_report_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_markdown_report(path: Path, title: str, findings: list[Finding], summary: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"# {title}", ""]
    if summary:
        lines.append("## Summary")
        lines.append("")
        for key, value in summary.items():
            lines.append(f"- **{key}**: `{value}`")
        lines.append("")
    if not findings:
        lines.extend(["## Findings", "", "No findings."])
    else:
        lines.extend(["## Findings", ""])
        lines.append("| Severity | Path | Line | Finding |")
        lines.append("| --- | --- | ---: | --- |")
        for finding in findings:
            line = "" if finding.line is None else str(finding.line)
            message = finding.message.replace("|", "\\|")
            detail = f" {finding.detail}" if finding.detail else ""
            lines.append(f"| {finding.severity} | `{finding.path}` | {line} | {message}{detail} |")
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def markdown_files(root: Path) -> Iterable[Path]:
    if not root.exists():
        return []
    return (
        path
        for path in sorted(root.rglob("*.md"))
        if ".git" not in path.parts
        if not any(part in {".generated", "site", ".venv", "node_modules"} for part in path.parts)
    )


def text_files(root: Path, suffixes: set[str]) -> Iterable[Path]:
    if root.is_file():
        paths = [root]
    elif root.exists():
        paths = sorted(root.rglob("*"))
    else:
        paths = []
    ignored = {".git", ".generated", "site", ".venv", "node_modules", ".cache"}
    return (
        path
        for path in paths
        if path.is_file()
        if not any(part in ignored for part in path.parts)
        if path.suffix.lower() in suffixes or path.name in {"Dockerfile", ".env.example"}
    )


def first_heading(text: str) -> str:
    match = re.search(r"^#\s+(.+?)\s*$", text, re.MULTILINE)
    return match.group(1).strip() if match else ""


def count_by_severity(findings: list[Finding]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for finding in findings:
        counts[finding.severity] = counts.get(finding.severity, 0) + 1
    return counts


def fail_if_findings(findings: list[Finding], fail_on: set[str]) -> int:
    return 1 if any(finding.severity in fail_on for finding in findings) else 0


def print_report_result(name: str, report_dir: Path, findings: list[Finding]) -> None:
    counts = count_by_severity(findings)
    print(f"{name}: {len(findings)} findings; reports written to {report_dir}")
    if counts:
        print("Finding counts: " + ", ".join(f"{key}={value}" for key, value in sorted(counts.items())))


def parse_simple_yaml_catalog(path: Path) -> list[dict[str, str]]:
    """Parse the generated catalog shape without requiring a YAML dependency."""
    entries: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.rstrip()
        if line.startswith("  - "):
            if current:
                entries.append(current)
            current = {}
            key, _, value = line[4:].partition(":")
            if key:
                current[key.strip()] = value.strip().strip('"')
            continue
        if current is not None and line.startswith("    ") and ":" in line:
            key, _, value = line.strip().partition(":")
            current[key.strip()] = value.strip().strip('"')
    if current:
        entries.append(current)
    return entries


def mkdocs_command(explicit: str | None = None) -> list[str]:
    if explicit:
        return [explicit]
    local = Path(".venv/bin/mkdocs")
    if local.exists():
        return [str(local)]
    return ["mkdocs"]


def python_command() -> str:
    return sys.executable
