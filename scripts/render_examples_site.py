#!/usr/bin/env python3
"""Render the MkDocs site from the splunk-opentelemetry-examples backend.

This repository owns the MkDocs rendering layer. The Markdown and example YAML
come from a local checkout of chentaow-splunk/splunk-opentelemetry-examples.
"""

from __future__ import annotations

import argparse
import json
import posixpath
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from urllib.parse import unquote


HEADING_RE = re.compile(r"^#\s+(.+?)\s*$", re.MULTILINE)
LINK_RE = re.compile(r"(!?)\[([^\]]+)\]\(([^)]+)\)")
SOURCE_REPO = "https://github.com/chentaow-splunk/splunk-opentelemetry-examples/tree/codex/collector-data-processing-cookbooks"
BACKEND_CATEGORIES = {
    "collector": (
        "OpenTelemetry Collector Examples",
        "opentelemetry-collector-examples",
    ),
    "instrumentation": (
        "OpenTelemetry Instrumentation Examples",
        "opentelemetry-instrumentation-examples",
    ),
}
NOTE = (
    "This page is generated at build time from the local "
    "`splunk-opentelemetry-examples` backend checkout. Edit the backend example "
    "for runnable source changes, and edit this renderer for navigation or site behavior."
)


@dataclass(frozen=True)
class Page:
    source_path: str
    output_path: Path
    title: str
    section: str
    subsection: str
    summary: str
    tags: list[str]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", default="splunk-opentelemetry-examples")
    parser.add_argument(
        "--content",
        default="site-content",
        help="Renderer-owned MkDocs content to merge into the generated docs tree.",
    )
    parser.add_argument("--output", default=".generated/docs")
    parser.add_argument("--mkdocs-output", default=".generated/mkdocs.yml")
    return parser.parse_args()


def normalize_posix(path: str) -> str:
    return posixpath.normpath(path.replace("\\", "/")).lstrip("./")


def read_text(path: Path) -> str:
    return path.read_bytes().decode("utf-8")


def normalized_text(text: str) -> str:
    text = text.replace("\r\n", "\n")
    return "\n".join(line.rstrip() for line in text.splitlines()).rstrip() + "\n"


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(normalized_text(text), encoding="utf-8")


def git_revision(path: Path) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(path), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip()
    except (FileNotFoundError, subprocess.CalledProcessError):
        return "unknown"


def backend_root(source_path: str) -> str:
    parts = PurePosixPath(source_path).parts
    return parts[0] if parts else ""


def should_render_markdown(source_path: str) -> bool:
    path = PurePosixPath(source_path)
    return backend_root(source_path) in BACKEND_CATEGORIES and path.name.lower() == "readme.md"


def should_copy_backend_yaml(source_path: str) -> bool:
    return backend_root(source_path) in BACKEND_CATEGORIES


def discover_markdown(source_root: Path) -> list[str]:
    return [
        normalize_posix(str(path.relative_to(source_root)))
        for path in sorted(source_root.rglob("*.md"))
        if ".git" not in path.parts
        if should_render_markdown(normalize_posix(str(path.relative_to(source_root))))
    ]


def first_heading(markdown: str, fallback: str) -> tuple[str, str]:
    match = HEADING_RE.search(markdown)
    if not match:
        return fallback, markdown
    title = match.group(1).strip()
    body = markdown[: match.start()] + markdown[match.end() :]
    return title, body.lstrip("\n")


def slug(text: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()
    return value or "page"


def title_from_path(source_path: str) -> str:
    parts = [part for part in PurePosixPath(source_path).parts if part.lower() != "readme.md"]
    if not parts:
        return "Splunk OpenTelemetry Examples"
    return parts[-1].replace("-", " ").replace("_", " ").title()


def classify(source_path: str) -> tuple[str, str, str]:
    parts = PurePosixPath(source_path).parts
    root = parts[0] if parts else ""
    if root in BACKEND_CATEGORIES:
        section, route_root = BACKEND_CATEGORIES[root]
        target = slug("/".join(parts[1:-1]) or "overview")
        return section, "", f"{route_root}/{target}"
    return "Examples", "Other", f"examples/{slug('/'.join(parts[:-1]) or source_path)}"


def output_for_source(source_path: str) -> Path:
    section, subsection, base = classify(source_path)
    name = PurePosixPath(source_path).name
    if name.lower() == "readme.md":
        return Path(base) / "index.md"
    return Path(base) / slug(PurePosixPath(source_path).stem) / "index.md"


def summary_from_body(body: str) -> str:
    in_fence = False
    lines: list[str] = []
    for raw in body.splitlines():
        line = raw.strip()
        if line.startswith("```") or line.startswith("````"):
            in_fence = not in_fence
            continue
        if in_fence or not line or line.startswith(("#", ">", "|", "-", "*", "!", "`")):
            continue
        lines.append(re.sub(r"\s+", " ", line))
        if len(" ".join(lines)) > 180:
            break
    summary = " ".join(lines)
    return summary[:240] + ("..." if len(summary) > 240 else "")


def tags_for(source_path: str, title: str, section: str, subsection: str) -> list[str]:
    values = set()
    for value in [source_path, title, section, subsection]:
        values.update(part for part in re.split(r"[^a-zA-Z0-9]+", value.lower()) if len(part) > 1)
    return sorted(values)[:16]


def category_label(page: Page) -> str:
    return page.section if not page.subsection else f"{page.section} / {page.subsection}"


def is_local_url(url: str) -> bool:
    return not url.startswith(("#", "http://", "https://", "mailto:", "tel:"))


def copy_text_or_binary(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        text = source.read_bytes().decode("utf-8")
    except UnicodeDecodeError:
        shutil.copy2(source, target)
        return
    target.write_text(normalized_text(text), encoding="utf-8")


def copy_tree(source: Path, target: Path) -> int:
    copied = 0
    if not source.exists():
        return copied
    for path in sorted(source.rglob("*")):
        if not path.is_file() or ".git" in path.parts:
            continue
        copy_text_or_binary(path, target / path.relative_to(source))
        copied += 1
    return copied


def copy_linked_asset(source_root: Path, output_root: Path, source_path: str, output_path: Path, url: str) -> bool:
    if not is_local_url(url):
        return False
    path_part = unquote(url).split("#", 1)[0].split("?", 1)[0]
    if not path_part:
        return False
    source_file = source_root / PurePosixPath(source_path).parent / path_part
    if not source_file.is_file():
        return False
    target_file = output_root / output_path.parent / path_part
    if target_file.name == "index.html" and output_path.name == "index.md" and target_file.parent == (output_root / output_path.parent):
        return False
    copy_text_or_binary(source_file, target_file)
    return True


def resolve_markdown_target(source_root: Path, source_path: str, url: str, source_to_output: dict[str, Path]) -> Path | None:
    if not is_local_url(url):
        return None
    path_part, sep, anchor = unquote(url).partition("#")
    if not path_part:
        return None
    candidate = normalize_posix(str(PurePosixPath(source_path).parent / path_part))
    source_candidate = source_root / candidate
    if source_candidate.is_dir():
        candidate = normalize_posix(str(PurePosixPath(candidate) / "README.md"))
    elif source_candidate.suffix.lower() != ".md":
        readme_candidate = normalize_posix(str(PurePosixPath(candidate) / "README.md"))
        if (source_root / readme_candidate).exists():
            candidate = readme_candidate
    target = source_to_output.get(candidate)
    if target and sep:
        return Path(f"{target.as_posix()}#{anchor}")
    return target


def rewrite_links(
    body: str,
    source_root: Path,
    output_root: Path,
    source_path: str,
    output_path: Path,
    source_to_output: dict[str, Path],
) -> str:
    in_fence = False
    output_lines: list[str] = []
    output_parent = PurePosixPath(output_path.parent.as_posix())

    for line in body.splitlines():
        stripped = line.lstrip()
        if stripped.startswith("```") or stripped.startswith("````"):
            in_fence = not in_fence
            output_lines.append(line)
            continue
        if in_fence:
            output_lines.append(line)
            continue

        def replace(match: re.Match[str]) -> str:
            is_image, label, raw_target = match.group(1), match.group(2), match.group(3)
            url = raw_target.strip().split(maxsplit=1)[0]
            suffix = raw_target[len(url):]
            if is_image:
                if copy_linked_asset(source_root, output_root, source_path, output_path, url):
                    return match.group(0)
                if is_local_url(url):
                    return f"*Image reference not present in backend source: `{url}`.*"
                return match.group(0)

            markdown_target = resolve_markdown_target(source_root, source_path, url, source_to_output)
            if markdown_target:
                target_text = markdown_target.as_posix()
                anchor = ""
                if "#" in target_text:
                    target_text, anchor = target_text.split("#", 1)
                    anchor = f"#{anchor}"
                relative = posixpath.relpath(target_text, start=output_parent.as_posix())
                return f"[{label}]({relative}{anchor}{suffix})"

            if copy_linked_asset(source_root, output_root, source_path, output_path, url):
                return match.group(0)
            if is_local_url(url):
                return f"`{label}`"
            return match.group(0)

        output_lines.append(LINK_RE.sub(replace, line))
    return "\n".join(output_lines)


def render_page(
    source_root: Path,
    output_root: Path,
    source_path: str,
    output_path: Path,
    source_to_output: dict[str, Path],
    source_commit: str,
) -> Page:
    source_text = read_text(source_root / source_path)
    title, body = first_heading(source_text, title_from_path(source_path))
    section, subsection, _ = classify(source_path)
    rewritten = rewrite_links(body, source_root, output_root, source_path, output_path, source_to_output)
    summary = summary_from_body(rewritten)
    tags = tags_for(source_path, title, section, subsection)
    rendered = (
        f"# {title}\n\n"
        f"> Backend source: `{source_path}` at `{source_commit}`.\n\n"
        f"> {NOTE}\n\n"
        f"{rewritten.lstrip()}"
    )
    write_text(output_root / output_path, rendered)
    return Page(source_path, output_path, title, section, subsection, summary, tags)


def yaml_kind(path: Path) -> str:
    name = path.name.lower()
    try:
        text = read_text(path)[:2048].lower()
    except UnicodeDecodeError:
        text = ""
    if name == "chart.yaml":
        return "helm-chart"
    if name in {"values.yaml", "values.yml"} or name.startswith("values-"):
        return "helm-values"
    if name.startswith("docker-compose"):
        return "docker-compose"
    if "receivers:" in text or "processors:" in text or "exporters:" in text:
        return "collector-config"
    if "apiversion:" in text and "kind:" in text:
        return "kubernetes-manifest"
    return "yaml-config"


def copy_backend_yaml(source_root: Path, output_root: Path, source_to_output: dict[str, Path]) -> list[dict[str, str]]:
    assets: list[dict[str, str]] = []
    for path in sorted(source_root.rglob("*")):
        if path.suffix.lower() not in {".yaml", ".yml"} or ".git" in path.parts:
            continue
        source_rel = normalize_posix(str(path.relative_to(source_root)))
        if not should_copy_backend_yaml(source_rel):
            continue
        target_rel = Path("assets/example-backend") / source_rel
        copy_text_or_binary(path, output_root / target_rel)
        recipe_path = ""
        cursor = PurePosixPath(source_rel).parent
        for parent in [cursor, *cursor.parents]:
            candidate = normalize_posix(str(parent / "README.md"))
            if candidate in source_to_output:
                recipe_path = source_to_output[candidate].as_posix()
                break
        entry = {
            "sourcePath": source_rel,
            "rawPath": target_rel.as_posix(),
            "kind": yaml_kind(path),
        }
        if recipe_path:
            entry["recipePath"] = recipe_path
        assets.append(entry)
    return assets


def page_url(path: Path) -> str:
    text = path.as_posix()
    if text.endswith("/index.md"):
        return text[:-8]
    return text[:-3]


def render_home(output_root: Path, pages: list[Page], source_commit: str) -> None:
    rows = []
    cards = []
    for page in sorted(pages, key=lambda item: (item.section, item.subsection, item.title.lower())):
        url = page_url(page.output_path)
        rows.append(
            f"| [{page.title}]({url}) | {category_label(page)} | `{page.source_path}` |"
        )
        cards.append(
            f'<a class="scenario-card" href="{url}" data-search="{page.title} {page.section} {page.subsection} {" ".join(page.tags)}">'
            f"<strong>{page.title}</strong><span>{category_label(page)}</span></a>"
        )
    body = "\n".join(
        [
            "# Splunk Observability Playbooks",
            "",
            f"> Generated from `{SOURCE_REPO}` at `{source_commit}`.",
            "",
            "Use this site as a scenario index over the Splunk OpenTelemetry examples backend. The Markdown and YAML examples are not copied as source into this renderer; they are generated from the backend checkout at build time.",
            "",
            '<input class="scenario-filter" id="scenario-filter" type="search" placeholder="Filter scenarios by platform, language, signal, or integration">',
            "",
            '<div class="scenario-grid">',
            *cards,
            "</div>",
            "",
            "## Scenario Index",
            "",
            "| Scenario | Category | Backend source |",
            "| --- | --- | --- |",
            *rows,
        ]
    )
    write_text(output_root / "index.md", body)


def render_category_indexes(output_root: Path, pages: list[Page]) -> list[Path]:
    groups: dict[tuple[str, str], list[Page]] = {}
    for page in pages:
        groups.setdefault((page.section, page.subsection), []).append(page)

    index_paths: list[Path] = []
    section_roots = {
        "OpenTelemetry Instrumentation Examples": Path("opentelemetry-instrumentation-examples/index.md"),
        "OpenTelemetry Collector Examples": Path("opentelemetry-collector-examples/index.md"),
    }
    for section, index_path in section_roots.items():
        section_pages = [page for page in pages if page.section == section]
        if not section_pages:
            continue
        lines = [f"# {section}", "", "| Scenario | Backend source |", "| --- | --- |"]
        for page in sorted(section_pages, key=lambda item: (item.subsection, item.title.lower())):
            lines.append(f"| [{page.title}]({posixpath.relpath(page.output_path.as_posix(), start=index_path.parent.as_posix())}) | `{page.source_path}` |")
        write_text(output_root / index_path, "\n".join(lines))
        index_paths.append(index_path)

    for (section, subsection), items in sorted(groups.items()):
        if not subsection:
            continue
        base = Path(classify(items[0].source_path)[2]).parent
        index_path = base / "index.md"
        lines = [f"# {subsection}", "", "| Scenario | Backend source |", "| --- | --- |"]
        for page in sorted(items, key=lambda item: item.title.lower()):
            lines.append(f"| [{page.title}]({posixpath.relpath(page.output_path.as_posix(), start=index_path.parent.as_posix())}) | `{page.source_path}` |")
        write_text(output_root / index_path, "\n".join(lines))
        index_paths.append(index_path)
    return index_paths


def render_catalogs(output_root: Path, pages: list[Page], assets: list[dict[str, str]], source_commit: str) -> None:
    categories = sorted({category_label(page) for page in pages})
    scenario_index = {
        "generatedFrom": SOURCE_REPO,
        "sourceCommit": source_commit,
        "scenarioCount": len(pages),
        "categories": categories,
        "scenarios": [
            {
                "title": page.title,
                "category": category_label(page),
                "url": page_url(page.output_path),
                "summary": page.summary,
                "tags": page.tags,
                "sourcePath": page.source_path,
            }
            for page in sorted(pages, key=lambda item: item.title.lower())
        ],
    }
    write_text(output_root / "assets/scenario-index.json", json.dumps(scenario_index, indent=2, sort_keys=True))

    lines = [
        f'sourceRepository: "{SOURCE_REPO}"',
        f'sourceCommit: "{source_commit}"',
        "configurationAssets:",
    ]
    for asset in assets:
        lines.append(f'  - sourcePath: "{asset["sourcePath"]}"')
        lines.append(f'    rawPath: "{asset["rawPath"]}"')
        lines.append(f'    kind: "{asset["kind"]}"')
        if "recipePath" in asset:
            lines.append(f'    recipePath: "{asset["recipePath"]}"')
    write_text(output_root / "assets/frontend/example-backend-catalog.yaml", "\n".join(lines))


def render_assets(output_root: Path) -> None:
    css = """
:root {
  --cookbook-accent: #007a5a;
}

.scenario-filter {
  width: 100%;
  padding: 0.8rem 1rem;
  border: 1px solid var(--md-default-fg-color--lightest);
  border-radius: 6px;
  font: inherit;
  margin: 1rem 0;
}

.scenario-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(230px, 1fr));
  gap: 0.75rem;
  margin: 1rem 0 2rem;
}

.scenario-card {
  border: 1px solid var(--md-default-fg-color--lightest);
  border-radius: 6px;
  padding: 0.9rem;
  color: var(--md-default-fg-color);
}

.scenario-card strong,
.scenario-card span {
  display: block;
}

.scenario-card span {
  color: var(--md-default-fg-color--light);
  font-size: 0.78rem;
  margin-top: 0.35rem;
}
"""
    js = """
document.addEventListener("DOMContentLoaded", () => {
  const filter = document.querySelector("#scenario-filter");
  if (!filter) return;
  const cards = Array.from(document.querySelectorAll(".scenario-card"));
  filter.addEventListener("input", () => {
    const query = filter.value.trim().toLowerCase();
    cards.forEach((card) => {
      const text = card.getAttribute("data-search") || card.textContent || "";
      card.hidden = query.length > 0 && !text.toLowerCase().includes(query);
    });
  });
});
"""
    css_path = output_root / "stylesheets/extra.css"
    js_path = output_root / "javascripts/scenario-filter.js"
    if not css_path.exists():
        write_text(css_path, css)
    if not js_path.exists():
        write_text(js_path, js)


def render_mkdocs_config(path: Path) -> None:
    config = """
site_name: Splunk Observability Playbooks
site_description: Scenario-based rendering of Splunk OpenTelemetry examples as implementation playbooks.
site_author: Observability Platform Team
docs_dir: docs

nav:
  - Playbooks List: index.md
  - OpenTelemetry Instrumentation Examples: opentelemetry-instrumentation-examples/index.md
  - OpenTelemetry Collector Examples: opentelemetry-collector-examples/index.md
  - Contribution:
      - Overview: contributing/index.md
      - Recipe Standard: contributing/recipe-standard.md
      - Examples Backend: contributing/examples-backend.md
      - Architecture and Maintenance Plan: contributing/maintenance-plan.md
      - Maintenance Automation: contributing/maintenance-automation.md
      - AI Assistant Backend: contributing/ai-assistant.md
      - Frontend Configuration Catalog: contributing/configuration-catalog.md
      - Propose a Recipe: contributing/propose-recipe.md

theme:
  name: material
  language: en
  features:
    - navigation.sections
    - navigation.indexes
    - navigation.top
    - content.code.copy
    - content.tabs.link
    - search.highlight
    - search.suggest
  palette:
    - scheme: default
      primary: black
      accent: green
  font:
    text: Inter
    code: Roboto Mono

extra_css:
  - stylesheets/extra.css

extra_javascript:
  - javascripts/scenario-assistant.js
  - javascripts/runbook-proposal.js

markdown_extensions:
  - admonition
  - attr_list
  - def_list
  - md_in_html
  - tables
  - toc:
      permalink: true
  - pymdownx.details
  - pymdownx.highlight:
      anchor_linenums: true
  - pymdownx.inlinehilite
  - pymdownx.superfences
  - pymdownx.tabbed:
      alternate_style: true

plugins:
  - search
"""
    write_text(path, config)


def main() -> int:
    args = parse_args()
    source_root = Path(args.source).resolve()
    content_root = Path(args.content).resolve()
    output_root = Path(args.output).resolve()
    mkdocs_output = Path(args.mkdocs_output).resolve()

    if not source_root.exists():
        print(f"Backend source does not exist: {source_root}", file=sys.stderr)
        return 2

    if output_root.exists():
        shutil.rmtree(output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    mkdocs_output.parent.mkdir(parents=True, exist_ok=True)

    source_commit = git_revision(source_root)
    markdown_sources = discover_markdown(source_root)
    source_to_output = {source_path: output_for_source(source_path) for source_path in markdown_sources}

    pages = [
        render_page(source_root, output_root, source_path, output_path, source_to_output, source_commit)
        for source_path, output_path in sorted(source_to_output.items(), key=lambda item: item[1].as_posix())
    ]
    render_category_indexes(output_root, pages)
    if not (content_root / "index.md").exists():
        render_home(output_root, pages, source_commit)
    assets = copy_backend_yaml(source_root, output_root, source_to_output)
    render_catalogs(output_root, pages, assets, source_commit)
    render_assets(output_root)
    copied_content = copy_tree(content_root, output_root)
    render_mkdocs_config(mkdocs_output)

    print(
        f"Rendered {len(pages)} Markdown pages and {len(assets)} YAML assets "
        f"from {SOURCE_REPO} at {source_commit}."
    )
    if copied_content:
        print(f"Merged {copied_content} renderer-owned content files from {content_root}.")
    print(f"Generated docs: {output_root}")
    print(f"Generated MkDocs config: {mkdocs_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
