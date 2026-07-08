from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


CHECKS = [
    ("render-check", "scripts.maintenance.render_check"),
    ("security-scan", "scripts.maintenance.security_scan"),
    ("content-review", "scripts.maintenance.content_review"),
    ("assistant-eval", "scripts.maintenance.assistant_eval"),
    ("version-drift", "scripts.maintenance.version_drift_check"),
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Run all cookbook maintenance checks.")
    parser.add_argument("--source", default="splunk-opentelemetry-examples")
    parser.add_argument("--report-dir", default="maintenance-reports")
    parser.add_argument("--online-version-check", action="store_true")
    args = parser.parse_args()

    report_dir = Path(args.report_dir)
    report_dir.mkdir(parents=True, exist_ok=True)
    failures: list[str] = []

    for name, module in CHECKS:
        full_command = [sys.executable, "-m", module, "--report-dir", str(report_dir)]
        if name in {"render-check", "security-scan", "content-review", "version-drift"}:
            full_command.extend(["--source", args.source])
        if name == "version-drift" and args.online_version_check:
            full_command.append("--online")
        print(f"Running {name}: {' '.join(full_command)}", flush=True)
        result = subprocess.run(full_command, text=True)
        if result.returncode != 0:
            failures.append(name)

    if failures:
        print("Maintenance checks failed: " + ", ".join(failures), file=sys.stderr)
        return 1
    print(f"Maintenance checks completed. Reports: {report_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
