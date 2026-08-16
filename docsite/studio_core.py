"""studio_core -- the Qt-free half of the Docs Studio (docsite/studio.py).

Everything a test can exercise without a display lives here: the nav.toml model (parse, reorder,
serialize -- header comment preserved verbatim), the corpus census (delegated to build.py, the one
owner of source discovery), page create/rename/delete, and the build-error parser that turns the
gate output into clickable problems.

The GUI imports this module; this module never imports Qt.
"""

from __future__ import annotations

import importlib.util
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

HERE = Path(__file__).resolve().parent          # docsite/
REPO = HERE.parent

try:  # stdlib on 3.11+
    import tomllib
except ImportError:  # pragma: no cover
    import tomli as tomllib  # type: ignore


# ------------------------------------------------------------------------------ the build module

_BUILD = None


def load_build():
    """docsite/build.py under a stable module name, importable from any cwd. build.py stays the
    single owner of source discovery, rendering, and slugging -- the Studio only consumes it."""
    global _BUILD
    if _BUILD is None:
        spec = importlib.util.spec_from_file_location("dwix_docsite_build", HERE / "build.py")
        mod = importlib.util.module_from_spec(spec)
        sys.modules["dwix_docsite_build"] = mod
        spec.loader.exec_module(mod)
        _BUILD = mod
    return _BUILD


# ------------------------------------------------------------------------------------ the corpus

@dataclass
class DocPage:
    src: Path        # absolute source path
    repo_rel: str    # "ff9mapkit/docs/FORMAT.md"
    out_rel: str     # site-relative output: "ff9mapkit/docs/FORMAT.html"
    title: str


def page_title(src: Path) -> str:
    B = load_build()
    try:
        raw = src.read_text(encoding="utf-8")
    except OSError:
        return src.stem
    _, text = B.parse_tutorial_front(raw)
    m = re.search(r"^#\s+(.+)$", text, re.M)
    return re.sub(r"<[^>]+>", "", m.group(1)).replace("`", "").strip() if m else src.stem


def corpus() -> list[DocPage]:
    B = load_build()
    return [DocPage(src=src, repo_rel=src.relative_to(B.REPO).as_posix(),
                    out_rel=B.out_rel(src), title=page_title(src))
            for src in B.collect_sources()]


# -------------------------------------------------------------------------------- the nav model

@dataclass
class NavSection:
    title: str
    entries: list[str] = field(default_factory=list)


@dataclass
class Nav:
    header: str                                  # the comment block above the first [[section]]
    sections: list[NavSection] = field(default_factory=list)


def load_nav(path: Path | None = None) -> Nav:
    path = path or HERE / "nav.toml"
    raw = path.read_text(encoding="utf-8")
    header = raw.split("[[section]]", 1)[0].rstrip("\n")
    cfg = tomllib.loads(raw)
    return Nav(header=header,
               sections=[NavSection(s["title"], list(s.get("pages", []))) for s in cfg["section"]])


def dumps_nav(nav: Nav) -> str:
    """Serialize back to nav.toml. json.dumps is a valid TOML basic string for these paths."""
    parts: list[str] = []
    if nav.header.strip():
        parts += [nav.header, ""]
    for sec in nav.sections:
        lines = ["[[section]]", f"title = {json.dumps(sec.title)}"]
        if not sec.entries:
            lines.append("pages = []")
        elif len(sec.entries) == 1:
            lines.append(f"pages = [{json.dumps(sec.entries[0])}]")
        else:
            lines.append("pages = [")
            lines += [f"  {json.dumps(e)}," for e in sec.entries]
            lines.append("]")
        parts.append("\n".join(lines))
        parts.append("")
    return "\n".join(parts).rstrip("\n") + "\n"


def save_nav(nav: Nav, path: Path | None = None) -> None:
    (path or HERE / "nav.toml").write_text(dumps_nav(nav), encoding="utf-8")


# --- reorder ops (pure; the GUI calls these and re-resolves) -----------------------------------

def move_entry(nav: Nav, sec_i: int, ent_i: int, delta: int) -> int:
    """Move an entry within its section; returns the new index (clamped)."""
    entries = nav.sections[sec_i].entries
    new_i = max(0, min(len(entries) - 1, ent_i + delta))
    entries.insert(new_i, entries.pop(ent_i))
    return new_i


def transfer_entry(nav: Nav, sec_i: int, ent_i: int, dst_sec: int) -> None:
    """Move an entry to the end of another section."""
    entry = nav.sections[sec_i].entries.pop(ent_i)
    nav.sections[dst_sec].entries.append(entry)


def add_entry(nav: Nav, sec_i: int, entry: str, at: int | None = None) -> None:
    entries = nav.sections[sec_i].entries
    entries.insert(len(entries) if at is None else at, entry)


def remove_entry(nav: Nav, sec_i: int, ent_i: int) -> str:
    return nav.sections[sec_i].entries.pop(ent_i)


def remove_page_everywhere(nav: Nav, entry: str) -> int:
    """Drop every literal occurrence of an entry string; returns how many were removed."""
    n = 0
    for sec in nav.sections:
        while entry in sec.entries:
            sec.entries.remove(entry)
            n += 1
    return n


def rename_page_entries(nav: Nav, old: str, new: str) -> int:
    n = 0
    for sec in nav.sections:
        for i, e in enumerate(sec.entries):
            if e == old:
                sec.entries[i] = new
                n += 1
    return n


# ------------------------------------------------------------------------------- nav resolution

@dataclass
class NavRow:
    """One rendered sidebar row: where it came from and what it points at."""
    kind: str                    # "literal" | "auto" (glob-matched) | "generated" | "missing"
    entry_index: int | None      # index into the section's entries (literal/generated/missing)
    entry: str                   # the entry string, or the matched page's nav-style rel for auto
    page: DocPage | None         # None for generated/missing


@dataclass
class ResolvedSection:
    title: str
    rows: list[NavRow] = field(default_factory=list)


def _entry_to_html(entry: str) -> str:
    return re.sub(r"\.md$", ".html", entry)


def nav_entry_for(page: DocPage) -> str:
    """The nav.toml string that names this page (nav speaks source-rel with docsite/pages at
    the site root -- the same convention build.load_nav resolves)."""
    rel = page.repo_rel
    if rel.startswith("docsite/pages/"):
        rel = rel[len("docsite/pages/"):]
    return rel


def resolve_nav(nav: Nav, pages: list[DocPage]) -> tuple[list[ResolvedSection], list[DocPage]]:
    """Mirror build.load_nav's semantics (html-rel lookup, globs over the remainder, first use
    wins) and return the resolved sections plus the auto 'More' bucket."""
    by_html = {p.out_rel: p for p in pages}
    used: set[str] = set()
    sections: list[ResolvedSection] = []
    for sec in nav.sections:
        rs = ResolvedSection(title=sec.title)
        for i, pat in enumerate(sec.entries):
            if "*" in pat:
                pat_html = _entry_to_html(pat)
                rx = re.escape(pat_html).replace(r"\*", "[^/]*")
                hits = sorted(r for r in by_html
                              if re.fullmatch(rx, r) and r not in used)
                for r in hits:
                    used.add(r)
                    rs.rows.append(NavRow(kind="auto", entry_index=i,
                                          entry=nav_entry_for(by_html[r]), page=by_html[r]))
                continue
            rel = _entry_to_html(pat)
            page = by_html.get(rel)
            if page is not None:
                used.add(rel)
                rs.rows.append(NavRow(kind="literal", entry_index=i, entry=pat, page=page))
            elif pat.endswith(".html"):
                rs.rows.append(NavRow(kind="generated", entry_index=i, entry=pat, page=None))
            else:
                rs.rows.append(NavRow(kind="missing", entry_index=i, entry=pat, page=None))
        sections.append(rs)
    more = sorted((p for p in pages if p.out_rel not in used and p.out_rel != "index.html"),
                  key=lambda p: p.out_rel)
    return sections, more


# ---------------------------------------------------------------------------------- page files

# Where a new page may be born. Keys are the combo labels the GUI shows.
LOCATIONS: dict[str, str] = {
    "Site page (docsite/pages/)": "docsite/pages",
    "Docs topic (ff9mapkit/docs/)": "ff9mapkit/docs",
    "Tutorial (ff9mapkit/docs/tutorials/)": "ff9mapkit/docs/tutorials",
}

_FILENAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*\.md$")


def slug_filename(title: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return (s or "untitled") + ".md"


def blank_page_text(title: str) -> str:
    return f"# {title}\n\nWrite the page here.\n"


def tutorial_page_text(title: str) -> str:
    tmpl = (HERE / "templates" / "tutorial.md").read_text(encoding="utf-8")
    return re.sub(r"^# .+$", f"# {title}", tmpl, count=1, flags=re.M)


def create_page(dir_path: Path, filename: str, title: str, template: str = "blank") -> Path:
    """Create a new markdown page. Refuses to overwrite; validates the filename."""
    if not _FILENAME_RE.match(filename):
        raise ValueError(f"bad filename {filename!r} (letters/digits/._- and a .md suffix)")
    if not dir_path.is_dir():
        raise ValueError(f"not a directory: {dir_path}")
    dst = dir_path / filename
    if dst.exists():
        raise FileExistsError(f"{dst} already exists")
    text = tutorial_page_text(title) if template == "tutorial" else blank_page_text(title)
    dst.write_text(text, encoding="utf-8")
    return dst


def rename_page(src: Path, new_name: str) -> Path:
    if not _FILENAME_RE.match(new_name):
        raise ValueError(f"bad filename {new_name!r} (letters/digits/._- and a .md suffix)")
    dst = src.with_name(new_name)
    if dst.exists():
        raise FileExistsError(f"{dst} already exists")
    src.rename(dst)
    return dst


# ------------------------------------------------------------------------------ problem parsing

_ERR_HEAD_RE = re.compile(r"(build|nav) errors")


@dataclass
class Problem:
    rel: str | None       # the page/output rel the gate named ("docs/FORMAT.html", "nav.toml")
    message: str


def parse_problems(text: str) -> list[Problem]:
    """The build gates print `build errors (N):` / `nav errors:` followed by two-space-indented
    `<rel>: <message>` lines. Anything else in the stream is ignored."""
    out: list[Problem] = []
    in_block = False
    for line in text.splitlines():
        if _ERR_HEAD_RE.search(line):
            in_block = True
            continue
        if in_block:
            if not line.startswith("  ") or not line.strip():
                in_block = False
                continue
            body = line.strip()
            head, sep, msg = body.partition(": ")
            if sep and " " not in head:
                out.append(Problem(rel=head, message=msg))
            else:
                out.append(Problem(rel=None, message=body))
    return out


def problem_source(problem: Problem, pages: list[DocPage]) -> Path | None:
    """Map a problem's rel back to the editable source file, when there is one."""
    if problem.rel is None:
        return None
    if problem.rel == "nav.toml":
        return HERE / "nav.toml"
    for p in pages:
        if p.out_rel == problem.rel or p.repo_rel == problem.rel:
            return p.src
    return None
