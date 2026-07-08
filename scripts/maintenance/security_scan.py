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
    fail_if_findings,
    print_report_result,
    text_files,
    write_json,
    write_markdown_report,
)


TEXT_SUFFIXES = {
    ".cs",
    ".go",
    ".gradle",
    ".groovy",
    ".java",
    ".js",
    ".json",
    ".kts",
    ".md",
    ".properties",
    ".py",
    ".sh",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
    ".xml",
}

PLACEHOLDER_RE = re.compile(
    r"(?i)(<[^>]+>|\$\{[^}]+}|your_|replace|placeholder|example|dummy|changeme|redacted|synthetic|xxxx|xxx|token_here|realm)"
)

PATTERNS: list[tuple[str, str, re.Pattern[str], str]] = [
    ("critical", "Possible OpenAI API key", re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"), "Do not commit model provider credentials."),
    ("critical", "Possible AWS access key", re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "Move cloud credentials to a secret manager."),
    ("critical", "Possible private key material", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"), "Remove private key material from the repository."),
    (
        "critical",
        "Possible Splunk token value",
        re.compile(r"(?i)\b(?:splunk[_-]?)?(?:access[_-]?)?token\b\s*[:=]\s*['\"]?([A-Za-z0-9._-]{20,})"),
        "Use placeholders, environment variables, or platform secret references.",
    ),
    (
        "critical",
        "Possible password value",
        re.compile(r"(?i)\bpassword\b\s*[:=]\s*['\"]?([^'\"\s#]{10,})"),
        "Do not commit database or service passwords.",
    ),
    (
        "high",
        "URI appears to contain inline credentials",
        re.compile(r"\b[a-z][a-z0-9+.-]+://[^/\s:@]+:[^@\s]+@"),
        "Use secret references instead of embedding credentials in URLs.",
    ),
    (
        "medium",
        "Exporter endpoint uses plain HTTP",
        re.compile(r"(?i)\bendpoint\s*:\s*['\"]?http://(?!127\.0\.0\.1|localhost|\$\{|<)"),
        "Use HTTPS for non-local endpoints unless the example explicitly explains why HTTP is required.",
    ),
    (
        "medium",
        "Insecure TLS setting enabled",
        re.compile(r"(?i)\binsecure\s*:\s*true\b"),
        "Only use insecure TLS settings in local-only examples and explain the tradeoff.",
    ),
]


def is_placeholder(value: str) -> bool:
    return bool(PLACEHOLDER_RE.search(value))


def scan_file(path: Path) -> list[Finding]:
    findings: list[Finding] = []
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return [Finding("warning", str(path), "Could not read file.", detail=str(exc))]

    for line_no, line in enumerate(text.splitlines(), start=1):
        for severity, message, pattern, detail in PATTERNS:
            match = pattern.search(line)
            if not match:
                continue
            captured = match.group(1) if match.groups() else match.group(0)
            if is_placeholder(captured):
                continue
            findings.append(Finding(severity, str(path), message, line_no, detail))

    if path.suffix.lower() in {".yaml", ".yml"}:
        lowered = text.lower()
        looks_like_collector = "receivers:" in lowered and "exporters:" in lowered and "service:" in lowered
        if looks_like_collector and "memory_limiter" not in lowered:
            findings.append(
                Finding(
                    "medium",
                    str(path),
                    "Collector configuration does not reference the memory_limiter processor.",
                    detail="High-volume examples should explain or include memory protection before export.",
                )
            )
        if looks_like_collector and "batch" not in lowered:
            findings.append(
                Finding(
                    "medium",
                    str(path),
                    "Collector configuration does not reference the batch processor.",
                    detail="Most production pipelines should batch before export to reduce exporter pressure.",
                )
            )

    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description="Scan cookbook renderer and backend examples for security risks.")
    parser.add_argument("paths", nargs="*", default=None)
    parser.add_argument("--source", default=str(DEFAULT_BACKEND))
    parser.add_argument("--report-dir", default=str(DEFAULT_REPORT_DIR))
    parser.add_argument(
        "--fail-on",
        default="critical",
        help="Comma-separated severities that should fail the command. Default: critical.",
    )
    args = parser.parse_args()

    scan_paths = args.paths
    if scan_paths is None:
        source = Path(args.source)
        scan_paths = [
            "site-content",
            "scripts",
            ".github",
            "examples-backend.yaml",
            "mkdocs.yml",
            str(source / "collector"),
            str(source / "instrumentation"),
        ]

    findings: list[Finding] = []
    for raw in scan_paths:
        root = Path(raw)
        for path in text_files(root, TEXT_SUFFIXES):
            findings.extend(scan_file(path))

    report_dir = ensure_report_dir(Path(args.report_dir))
    summary = count_by_severity(findings)
    write_json(report_dir / "security-scan.json", {"summary": summary, "findings": [item.as_dict() for item in findings]})
    write_markdown_report(report_dir / "security-scan.md", "Security Scan", findings, summary)
    print_report_result("security-scan", report_dir, findings)
    fail_on = {item.strip().lower() for item in args.fail_on.split(",") if item.strip()}
    return fail_if_findings(findings, fail_on)


if __name__ == "__main__":
    raise SystemExit(main())
