#!/usr/bin/env python3
"""Tooling for the Yemeni Open Source project catalog.

The catalog lives in data/projects.yml. README.md is generated from it, so the
project tables, the per-category counts, and the three project totals can never
drift apart -- and a pull request that adds an entry touches one small block of
YAML instead of a numbered table that every other pull request also edits.

Commands
--------
check   Validate data/projects.yml against data/categories.yml, and confirm
        README.md matches what the data renders to. With --base, also apply the
        stricter CONTRIBUTING.md rules to the entries a pull request adds.
fix     Sort and normalize data/projects.yml, then regenerate README.md.
render  Regenerate README.md only, leaving the data file untouched.
refresh Update each entry's cached GitHub metadata (stars, archived, license)
        and the snapshot date in data/meta.yml.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request

try:
    import yaml
except ImportError:  # pragma: no cover - only hit on a bare interpreter
    print("This tool needs PyYAML: python3 -m pip install pyyaml", file=sys.stderr)
    raise SystemExit(2)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECTS = os.path.join(ROOT, "data", "projects.yml")
CATEGORIES = os.path.join(ROOT, "data", "categories.yml")
META = os.path.join(ROOT, "data", "meta.yml")
README = os.path.join(ROOT, "README.md")

CATALOG_START = "<!-- YEMEN_OPEN_SOURCE_CATALOG:START -->"
CATALOG_END = "<!-- YEMEN_OPEN_SOURCE_CATALOG:END -->"

# The project total appears in the shields.io badge and once in the prose above
# the catalog block. Both live outside the block, so they are patched by regex.
BADGE_COUNT_RE = re.compile(r"(projects-)(\d+)(-1f6feb)")
PROSE_COUNT_RE = re.compile(r"\*\*(\d+) projects\*\*")

ARABIC_RE = re.compile(r"[؀-ۿ]")
PROMOTIONAL_RE = re.compile(
    r"\b(best|powerful|amazing|revolutionary|ultimate|awesome|world-class)\b",
    re.IGNORECASE,
)

MIN_DESCRIPTION_WORDS = 4
MAX_DESCRIPTION_WORDS = 30
HARD_DESCRIPTION_WORDS = 60

# The separator between technologies, so "Laravel · PHP" never becomes
# "Laravel • PHP" or "Laravel . PHP" again.
TECH_SEPARATOR = " · "
TECH_SPLIT_RE = re.compile(r"\s*[·•,/]\s*|\s+[.&]\s+|\s+-\s+")

# Exit codes: 0 = fine, 1 = the catalog is invalid, 2 = a human has to look.
EXIT_OK = 0
EXIT_INVALID = 1
EXIT_MANUAL = 2


# --- The data ---------------------------------------------------------------

class Project:
    """One entry in data/projects.yml."""

    FIELDS = ("name", "url", "category", "tech", "description",
              "stars", "archived", "license")

    def __init__(self, raw: dict, index: int, line: int = 1):
        self.index = index                       # position in the file, for errors
        self.line = line                         # the `- name:` line, for annotations
        self.raw = raw
        self.name = str(raw.get("name", "")).strip()
        self.url = str(raw.get("url", "")).strip()
        self.category = str(raw.get("category", "")).strip()
        self.tech = str(raw.get("tech", "") or "").strip()
        self.description = str(raw.get("description", "")).strip()
        self.stars = raw.get("stars")
        self.archived = bool(raw.get("archived", False))
        self.license = raw.get("license")

    @property
    def key(self) -> str:
        """Normalized repository URL, used to identify an entry across branches."""
        url = re.sub(r"\.git$", "", self.url.strip().rstrip("/"))
        return re.sub(r"^https?://(www\.)?", "", url).lower()

    @property
    def slug(self) -> tuple:
        """(owner, repo) for a GitHub URL, or None."""
        match = re.match(r"^https://github\.com/([^/]+)/([^/#?]+)", self.url)
        if not match:
            return None
        return match.group(1), re.sub(r"\.git$", "", match.group(2))

    def normalized(self) -> dict:
        """The entry with whitespace, separators, and punctuation tidied up."""
        entry = {
            "name": re.sub(r"\s+", " ", self.name),
            "url": self.url,
            "category": self.category,
        }
        if self.tech:
            parts = [p.strip() for p in TECH_SPLIT_RE.split(self.tech) if p.strip()]
            entry["tech"] = TECH_SEPARATOR.join(parts)
        description = re.sub(r"\s+", " ", self.description)
        if description and description[-1] not in ".!?":
            description += "."
        entry["description"] = description
        # Cached GitHub metadata, written by `refresh`. A zero star count is a
        # real value, so test for emptiness rather than truthiness.
        if self.stars is not None:
            entry["stars"] = self.stars
        if self.archived:
            entry["archived"] = True
        if self.license:
            entry["license"] = self.license
        return entry


class Catalog:
    """data/projects.yml and data/categories.yml, parsed together."""

    def __init__(self, projects_path: str, categories_path: str, meta_path: str = None):
        self.errors: list[str] = []
        self.categories = []
        self.projects = []
        self.meta = {}

        for path, attr, kind in ((categories_path, "categories", "category"),
                                 (projects_path, "projects", "project")):
            try:
                with open(path, encoding="utf-8") as handle:
                    data = yaml.safe_load(handle) or []
            except FileNotFoundError:
                self.errors.append(f"{os.path.relpath(path, ROOT)} does not exist")
                continue
            except yaml.YAMLError as error:
                self.errors.append(
                    f"{os.path.relpath(path, ROOT)} is not valid YAML: {error}")
                continue
            if not isinstance(data, list):
                self.errors.append(
                    f"{os.path.relpath(path, ROOT)} must be a list of {kind} entries")
                continue
            setattr(self, attr, data)

        if meta_path and os.path.exists(meta_path):
            with open(meta_path, encoding="utf-8") as handle:
                self.meta = yaml.safe_load(handle) or {}

        # Entries are emitted one per `- name:` line, so the file can be scanned
        # for the line each entry starts on and CI can annotate the right row.
        starts = []
        if os.path.exists(projects_path):
            with open(projects_path, encoding="utf-8") as handle:
                starts = [i for i, line in enumerate(handle, start=1)
                          if line.startswith("- ")]
        self.projects = [
            Project(raw, i, starts[i - 1] if i <= len(starts) else 1)
            for i, raw in enumerate(self.projects, start=1) if isinstance(raw, dict)
        ]

    @property
    def slugs(self) -> list:
        return [c.get("slug") for c in self.categories if isinstance(c, dict)]

    def title(self, slug: str) -> str:
        for category in self.categories:
            if category.get("slug") == slug:
                return category.get("title", slug)
        return slug

    def blurb(self, slug: str) -> str:
        for category in self.categories:
            if category.get("slug") == slug:
                return category.get("blurb", "")
        return ""

    @property
    def total(self) -> int:
        return len(self.projects)

    def by_key(self) -> dict:
        return {p.key: p for p in self.projects}

    def sorted_projects(self) -> list:
        order = {slug: i for i, slug in enumerate(self.slugs)}
        return sorted(self.projects,
                      key=lambda p: (order.get(p.category, len(order)), sort_key(p.name)))

    def grouped(self) -> list:
        """[(slug, [project, ...]), ...] in vocabulary order, empty groups dropped."""
        groups = []
        for slug in self.slugs:
            members = [p for p in self.sorted_projects() if p.category == slug]
            if members:
                groups.append((slug, members))
        return groups


def sort_key(name: str) -> str:
    """Case- and punctuation-insensitive, so 'tal' sorts before 'todo-app'."""
    return re.sub(r"[^a-z0-9]+", "", name.lower())


# --- Rendering --------------------------------------------------------------

INTRO = """## Projects

This directory lists **{total} projects** by Yemeni developers, grouped by what each project is for
and listed alphabetically within every group. Every entry links to the project's **original
repository**, so credit stays with its author, and descriptions are taken from those repositories.

> [!NOTE]
> Where a project is mirrored as a fork by the independent [Yemen Open Source](https://github.com/YemenOpenSource)
> organization, the link points to the upstream original rather than the mirror. Metadata is a
> snapshot taken from GitHub on **{snapshot}**. A ⚠️ marks a repository its maintainer has archived.
"""


def anchor(heading: str) -> str:
    """The id GitHub gives a heading, so the browse index links actually work."""
    text = heading.strip().lower()
    text = re.sub(r"[^\w\s-]", "", text, flags=re.UNICODE)
    return text.replace(" ", "-")


def cell(text: str) -> str:
    """Escape a value for a markdown table cell."""
    return text.replace("|", "\\|").strip()


def render_row(project: Project) -> str:
    """One row of a category table. The category itself is the heading above it."""
    name = cell(project.name) + (" ⚠️" if project.archived else "")
    return (f"| [{name}]({project.url}) | {cell(project.tech) or '—'} "
            f"| {cell(project.description)} |")


def render_block(catalog: Catalog) -> str:
    groups = catalog.grouped()

    lines = [CATALOG_START]
    lines.append(INTRO.format(
        total=catalog.total,
        snapshot=catalog.meta.get("snapshot", "an earlier date"),
    ).rstrip())
    lines.append("")

    # The browse index: one scannable table, so a reader can pick a category by
    # what is in it rather than by guessing from a run-on list of links.
    lines.append("### Browse by Category")
    lines.append("")
    lines.append("| Category | Projects | What you will find |")
    lines.append("|---|---:|---|")
    for slug, members in groups:
        title = catalog.title(slug)
        lines.append(f"| [{title}](#{anchor(title)}) | {len(members)} | "
                     f"{cell(catalog.blurb(slug))} |")
    lines.append("")

    back = f"<sub>[↑ Back to categories](#{anchor('Browse by Category')})</sub>"

    for slug, members in groups:
        lines.append(f"### {catalog.title(slug)}")
        lines.append("")
        lines.append("| Project | Tech | Description |")
        lines.append("|---|---|---|")
        lines.extend(render_row(p) for p in members)
        lines.append("")
        lines.append(back)
        lines.append("")

    lines.append(CATALOG_END)
    return "\n".join(lines)


def render_readme(catalog: Catalog, readme_text: str) -> str:
    """Splice the generated block into the README and sync the counts around it."""
    start = readme_text.find(CATALOG_START)
    end = readme_text.find(CATALOG_END)
    if start < 0 or end < 0:
        raise ValueError("the catalog markers are missing from README.md")

    text = readme_text[:start] + render_block(catalog) + \
        readme_text[end + len(CATALOG_END):]
    total = catalog.total
    text = BADGE_COUNT_RE.sub(lambda m: f"{m.group(1)}{total}{m.group(3)}", text)
    return PROSE_COUNT_RE.sub(f"**{total} projects**", text)


# --- Writing the data file back ---------------------------------------------

def yaml_scalar(value) -> str:
    """Quote a scalar only when YAML needs it, so diffs stay readable."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    text = str(value)
    if not text:
        return '""'
    risky = (text[0] in "-?:,[]{}#&*!|>'\"%@`" or ": " in text or text.endswith(":")
             or text.strip() != text
             or text.lower() in ("true", "false", "null", "yes", "no", "on", "off"))
    if risky or "'" in text and '"' not in text:
        return "'" + text.replace("'", "''") + "'"
    return text


def header_of(path: str) -> str:
    """The comment block at the top of the data file, preserved across rewrites."""
    lines = []
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            if line.startswith("- "):
                break
            lines.append(line.rstrip("\n"))
    while lines and not lines[-1].strip():
        lines.pop()
    return "\n".join(lines)


def dump_projects(catalog: Catalog, path: str) -> str:
    header = header_of(path) if os.path.exists(path) else ""
    lines = [header, ""] if header else []
    for project in catalog.sorted_projects():
        entry = project.normalized()
        first = True
        for field in Project.FIELDS:
            if field not in entry:
                continue
            prefix = "- " if first else "  "
            lines.append(f"{prefix}{field}: {yaml_scalar(entry[field])}")
            first = False
    return "\n".join(lines) + "\n"


def read(path: str) -> str:
    with open(path, encoding="utf-8") as handle:
        return handle.read()


def write(path: str, text: str) -> None:
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)


# --- GitHub annotations -----------------------------------------------------

class Report:
    def __init__(self, file: str):
        self.file = file
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def error(self, message: str, line: int = 1, file: str = None) -> None:
        self.errors.append(message)
        print(f"::error file={file or self.file},line={line}::{message}")

    def warn(self, message: str, line: int = 1, file: str = None) -> None:
        self.warnings.append(message)
        print(f"::warning file={file or self.file},line={line}::{message}")

    def summary(self) -> None:
        if self.errors:
            print(f"\n{len(self.errors)} problem(s) must be fixed before this can merge.")
        elif self.warnings:
            print(f"\nNo blocking problems. {len(self.warnings)} suggestion(s) above.")
        else:
            print("\nThe catalog is valid.")


# --- Checks on the repositories a pull request links to ---------------------

def github_api(path: str):
    request = urllib.request.Request(f"https://api.github.com{path}")
    request.add_header("Accept", "application/vnd.github+json")
    request.add_header("User-Agent", "yemeni-open-source-catalog")
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    # A malformed token must not crash the request; unauthenticated still works.
    if token and not re.search(r"\s", token):
        request.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return response.status, json.load(response)
    except urllib.error.HTTPError as error:
        return error.code, None
    except Exception:
        return None, None


def url_is_reachable(url: str) -> bool:
    request = urllib.request.Request(url, method="HEAD")
    request.add_header("User-Agent", "yemeni-open-source-catalog")
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return response.status < 400
    except urllib.error.HTTPError as error:
        return error.code < 400
    except Exception:
        # A network hiccup must not block a pull request.
        return True


def check_repository(project: Project, report: Report) -> None:
    """Verify the repository a newly added entry links to."""
    line = project.line
    if not project.url.startswith("https://"):
        report.error(f"{project.name}: the project link must be an https:// URL", line)
        return

    slug = project.slug
    if not slug:
        if not url_is_reachable(project.url):
            report.error(f"{project.name}: the project link is not reachable", line)
        return

    owner, name = slug
    status, data = github_api(f"/repos/{owner}/{name}")
    if status is None:
        report.warn(f"{project.name}: could not reach the GitHub API to verify this "
                    "repository", line)
        return
    if status == 404:
        report.error(f"{project.name}: github.com/{owner}/{name} does not exist or is "
                     "not public", line)
        return
    if status != 200 or data is None:
        report.warn(f"{project.name}: could not verify github.com/{owner}/{name} "
                    f"(HTTP {status})", line)
        return

    if data.get("fork"):
        parent = (data.get("parent") or {}).get("html_url", "the original repository")
        report.error(f"{project.name}: this links to a fork — link to the original: "
                     f"{parent}", line)
    if not data.get("license"):
        report.error(f"{project.name}: the repository has no explicit open-source license, "
                     "which the eligibility criteria require", line)
    if data.get("archived"):
        report.warn(f"{project.name}: the repository is archived", line)
    if data.get("full_name", "").lower() != f"{owner}/{name}".lower():
        report.warn(f"{project.name}: the repository has moved to {data.get('html_url')}", line)


def check_entry(project: Project, report: Report, strict: bool) -> None:
    """Rules every entry obeys. `strict` adds the ones only new entries must pass.

    The soft rules are deliberately new-entries-only: entries written under older
    conventions are not re-litigated on every unrelated pull request.
    """
    where = project.name or "this entry"
    line = project.line

    def error(message):
        report.error(f"{where}: {message}", line)

    if not project.name:
        report.error(f"entry {project.index} has no name", line)
    if not project.url:
        error("this entry has no url")
    if not project.description:
        error("this entry has no description")

    if ARABIC_RE.search(project.name) or ARABIC_RE.search(project.description):
        error("the catalog is English-only — write the name and description in English")

    if project.description and project.description[-1] not in ".!?":
        error("end the description with a full stop "
              "(`python3 scripts/catalog.py fix` does this for you)")
    if project.description.strip().lower() == project.name.strip().lower():
        error("the description just repeats the project name — say what the project does")
    if re.match(r"^https?://\S+$", project.description.strip()):
        error("the description is a bare link — say what the project does")

    words = len(project.description.split())
    if words and words < MIN_DESCRIPTION_WORDS:
        error(f"the description is {words} word(s); write a full sentence")
    if words > HARD_DESCRIPTION_WORDS:
        error(f"the description is {words} words; keep it to one sentence "
              f"(under {MAX_DESCRIPTION_WORDS} words)")

    for field in project.raw:
        if field not in Project.FIELDS:
            error(f"unknown field '{field}'; allowed fields are "
                  f"{', '.join(Project.FIELDS)}")

    if not strict:
        return

    if words > MAX_DESCRIPTION_WORDS:
        report.warn(f"{where}: the description is {words} words; under "
                    f"{MAX_DESCRIPTION_WORDS} reads better", line)
    promotional = PROMOTIONAL_RE.search(project.description)
    if promotional:
        report.warn(f'{where}: "{promotional.group(0)}" is promotional — say what the '
                    "project does instead", line)
    check_repository(project, report)


# --- Commands ---------------------------------------------------------------

def load(args) -> Catalog:
    return Catalog(args.data, args.categories, args.meta)


def command_check(args) -> int:
    report = Report(os.path.relpath(args.data, ROOT))
    catalog = load(args)

    for message in catalog.errors:
        report.error(message)
    if report.errors:
        report.summary()
        return EXIT_INVALID

    # The vocabulary itself.
    seen_slugs = set()
    for category in catalog.categories:
        if not isinstance(category, dict) or not category.get("slug") or not category.get("title"):
            report.error("every category needs a slug and a title",
                         file=os.path.relpath(args.categories, ROOT))
            continue
        if category["slug"] in seen_slugs:
            report.error(f"the category '{category['slug']}' is defined twice",
                         file=os.path.relpath(args.categories, ROOT))
        seen_slugs.add(category["slug"])

    if not catalog.projects:
        report.error("data/projects.yml has no entries")
        report.summary()
        return EXIT_INVALID

    base_keys = set()
    if args.base:
        base = Catalog(args.base, args.categories)
        if base.errors:
            report.error("the base data file could not be parsed; a human should look at this")
            report.summary()
            return EXIT_INVALID
        base_keys = set(base.by_key())
        removed = base_keys - set(catalog.by_key())
        if removed and not args.allow_removals:
            report.error(f"this removes {len(removed)} existing entry/entries; label the "
                         "pull request 'entry-removal' if that is intended")

    new_keys = {p.key for p in catalog.projects} - base_keys if args.base else set()
    if args.base:
        print(f"This pull request adds {len(new_keys)} entry/entries.")

    seen_urls, seen_names = {}, {}
    for project in catalog.projects:
        if project.category not in seen_slugs:
            report.error(f"{project.name}: '{project.category}' is not a category in "
                         f"data/categories.yml ({', '.join(sorted(seen_slugs))})",
                         project.line)
        if project.key in seen_urls:
            report.error(f"{project.name}: {project.url} is already listed on line "
                         f"{seen_urls[project.key]}", project.line)
        else:
            seen_urls[project.key] = project.line
        lowered = project.name.lower()
        if lowered in seen_names:
            report.error(f"the name '{project.name}' is already used on line "
                         f"{seen_names[lowered]}", project.line)
        else:
            seen_names[lowered] = project.line

        check_entry(project, report, strict=project.key in new_keys)

    # README.md must be what the data renders to.
    try:
        expected = render_readme(catalog, read(args.readme))
    except ValueError as error:
        report.error(str(error), file=os.path.relpath(args.readme, ROOT))
    else:
        if expected != read(args.readme):
            report.error("README.md is out of date with data/projects.yml — run "
                         "`python3 scripts/catalog.py fix` and commit the result",
                         file=os.path.relpath(args.readme, ROOT))

    report.summary()
    return EXIT_INVALID if report.errors else EXIT_OK


def command_render(args) -> int:
    catalog = load(args)
    if catalog.errors:
        for message in catalog.errors:
            print(f"cannot render: {message}", file=sys.stderr)
        return EXIT_INVALID
    original = read(args.readme)
    rendered = render_readme(catalog, original)
    if rendered == original:
        print("Nothing to do: README.md already matches the data.")
        return EXIT_OK
    write(args.readme, rendered)
    print(f"Regenerated README.md: {catalog.total} projects in "
          f"{len(catalog.grouped())} categories.")
    return EXIT_OK


def command_fix(args) -> int:
    catalog = load(args)
    if catalog.errors:
        for message in catalog.errors:
            print(f"cannot fix: {message}", file=sys.stderr)
        return EXIT_INVALID

    changed = []
    data = dump_projects(catalog, args.data)
    if data != read(args.data):
        write(args.data, data)
        changed.append(f"sorted and normalized {catalog.total} entries in "
                       f"{os.path.relpath(args.data, ROOT)}")

    original = read(args.readme)
    rendered = render_readme(catalog, original)
    if rendered != original:
        write(args.readme, rendered)
        changed.append("regenerated README.md and synced every project count")

    print("; ".join(changed) if changed else
          "Nothing to fix: the data is sorted and README.md is up to date.")
    return EXIT_OK


def command_refresh(args) -> int:
    """Re-read each repository's public metadata into the data file."""
    catalog = load(args)
    if catalog.errors:
        for message in catalog.errors:
            print(f"cannot refresh: {message}", file=sys.stderr)
        return EXIT_INVALID

    checked = missing = 0
    for project in catalog.projects:
        slug = project.slug
        if not slug:
            continue
        status, data = github_api(f"/repos/{slug[0]}/{slug[1]}")
        checked += 1
        if status is None:
            print(f"::warning::could not reach GitHub for {project.name}")
            continue
        if status == 404:
            missing += 1
            print(f"::warning::{project.name}: github.com/{slug[0]}/{slug[1]} is gone "
                  f"(404) — it may need removing")
            continue
        if status != 200 or data is None:
            continue
        project.raw["stars"] = data.get("stargazers_count", 0)
        project.raw["archived"] = bool(data.get("archived"))
        project.raw["license"] = (data.get("license") or {}).get("spdx_id") or None
        project.archived = project.raw["archived"]
        project.stars = project.raw["stars"]
        project.license = project.raw["license"]

    if args.snapshot:
        write(args.meta, f"# Metadata for the generated catalog block in README.md.\n"
                         f"# `catalog.py refresh` rewrites the snapshot date.\n"
                         f"snapshot: {args.snapshot}\n")
        catalog.meta["snapshot"] = args.snapshot

    write(args.data, dump_projects(catalog, args.data))
    write(args.readme, render_readme(catalog, read(args.readme)))
    print(f"Refreshed {checked} repositories; {missing} no longer resolve.")
    return EXIT_OK


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)

    def common(sub):
        sub.add_argument("--data", default=PROJECTS)
        sub.add_argument("--categories", default=CATEGORIES)
        sub.add_argument("--meta", default=META)
        sub.add_argument("--readme", default=README)
        return sub

    check = common(commands.add_parser("check", help="validate the catalog"))
    check.add_argument("--base", help="data/projects.yml from the base branch, "
                                      "to find the entries a pull request adds")
    check.add_argument("--allow-removals", action="store_true")
    check.set_defaults(func=command_check)

    fix = common(commands.add_parser("fix", help="sort the data and regenerate README.md"))
    fix.set_defaults(func=command_fix)

    render = common(commands.add_parser("render", help="regenerate README.md only"))
    render.set_defaults(func=command_render)

    refresh = common(commands.add_parser("refresh", help="re-read GitHub metadata"))
    refresh.add_argument("--snapshot", help="the snapshot date to record, "
                                            'e.g. "16 August 2026"')
    refresh.set_defaults(func=command_refresh)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
