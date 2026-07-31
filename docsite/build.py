"""build -- render the Dream World IX Manual: the repo's markdown docs as an explorable static site.

The design contract lives at studies/interactive-docs/PLAN.md. The laws this file enforces:

  * THE ONE-COPY LAW -- ff9mapkit/docs/*.md stay canonical; every site page is a build artifact of
    a source file (or of kit introspection). Nothing here forks prose.
  * A REFERENCE ROW NOBODY CHECKS IS A WISH -- the build FAILS on a broken internal link, a missing
    anchor, or a nav entry naming a file that does not exist. Rot is a build error, not a surprise.
  * GitHub-parity anchors -- headings get ids from a GitHub-slugger-compatible slugify (punctuation
    STRIPPED, spaces to hyphens, consecutive hyphens NOT collapsed -- the double-hyphen trap the
    2026-07 docs pass paid for), so anchors authored against GitHub keep working on the site.
  * The output mirrors the repo tree (`page.md` -> `_site/page.html`, assets beside them), so
    relative links between sources survive with only the `.md` -> `.html` suffix rewrite.

Usage:
  py docsite/build.py                 # build into docsite/_site/
  py docsite/build.py --out DIR       # build elsewhere (tests use a tempdir)
  py -m http.server -d docsite/_site  # preview

Build-time deps (never shipped in the output): markdown + pygments. The output is dependency-free
static HTML + one small ES module -- previewable from file server, deployable by plain copy.
"""

from __future__ import annotations

import argparse
import html as _html
import json
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
SITE_TITLE = "Dream World IX Manual"

try:  # stdlib on 3.11+
    import tomllib
except ImportError:  # pragma: no cover
    import tomli as tomllib  # type: ignore

import markdown as _markdown

# ------------------------------------------------------------------------------------ source census

# Explicit roots, not an exclude list: dev briefs (CLAUDE.md), studies/ and .claude/ must never
# leak into user docs, and an allowlist cannot rot open the way a denylist can.
SOURCE_ROOTS = (
    ("README.md", False),
    ("SETUP.md", False),
    ("FORKING_FF9.md", False),            # the kept-for-old-links root stub
    ("ff9mapkit/docs", True),
    ("docsite/pages", True),
)


def kit_version() -> str:
    with open(REPO / "ff9mapkit" / "pyproject.toml", "rb") as f:
        return tomllib.load(f)["project"]["version"]


def collect_sources() -> list[Path]:
    out: list[Path] = []
    for rel, is_dir in SOURCE_ROOTS:
        p = REPO / rel
        if is_dir:
            if p.is_dir():
                out.extend(sorted(p.rglob("*.md")))
        elif p.is_file():
            out.append(p)
    return out


def out_rel(src: Path) -> str:
    """Site-relative output path for a source. docsite/pages/* publish at the SITE ROOT (they are
    authored as if at the repo root, so their relative links resolve like any root file's)."""
    rel = src.relative_to(REPO).as_posix()
    if rel.startswith("docsite/pages/"):
        rel = rel[len("docsite/pages/"):]
    return re.sub(r"\.md$", ".html", rel)


# ------------------------------------------------------------------------- GitHub-compatible slugs

def github_slug(text: str) -> str:
    """GitHub's anchor slug: lowercase, punctuation STRIPPED (not replaced), spaces to hyphens,
    `-`/`_` kept, consecutive hyphens NOT collapsed. The corpus' own anchors were authored against
    GitHub, so parity here is a correctness requirement, not a style choice."""
    out = []
    for ch in text.strip().lower():
        if ch in " \t":
            out.append("-")
        elif ch.isalnum() or ch in "-_":
            out.append(ch)
        # anything else (punctuation, symbols, emoji) is dropped
    return "".join(out)


_H_RE = re.compile(r"<h([1-6])(\s[^>]*)?>(.*?)</h\1>", re.S)
_TAG_RE = re.compile(r"<[^>]+>")


def assign_heading_ids(html: str) -> tuple[str, list[dict], dict[str, int]]:
    """Post-pass over converted HTML: give every heading a GitHub-parity id, return the page ToC
    and the anchor census. Done here, not via the toc extension, because python-markdown dedupes
    duplicates as `_1` while GitHub dedupes as `-1` -- and the census must match what authors used."""
    toc: list[dict] = []
    census: dict[str, int] = {}

    def _sub(m: re.Match) -> str:
        level, attrs, inner = int(m.group(1)), m.group(2) or "", m.group(3)
        text = _html.unescape(_TAG_RE.sub("", inner))
        slug = github_slug(text) or "section"
        if slug in census:
            census[slug] += 1
            slug = f"{slug}-{census[slug]}"
        census[slug] = 0
        toc.append({"level": level, "text": text, "id": slug})
        return f'<h{level}{attrs} id="{slug}">{inner}<a class="hlink" href="#{slug}" aria-label="Link to this section">#</a></h{level}>'

    return _H_RE.sub(_sub, html), toc, census


# ----------------------------------------------------------------------------------- page pipeline

MD_EXTENSIONS = ["extra", "codehilite", "sane_lists"]
MD_CONFIG = {"codehilite": {"guess_lang": False, "css_class": "codehilite"}}


@dataclass
class Page:
    src: Path | None            # None for generated pages (CLI reference)
    rel: str                    # output path, site-relative ("docs/FORMAT.html")
    title: str
    body: str                   # converted body html (pre link-rewrite)
    toc: list[dict] = field(default_factory=list)
    census: dict[str, int] = field(default_factory=dict)
    search_text: str = ""
    generated: bool = False


def render_markdown(text: str) -> str:
    md = _markdown.Markdown(extensions=MD_EXTENSIONS, extension_configs=MD_CONFIG)
    return md.convert(text)


def page_from_source(src: Path) -> Page:
    text = src.read_text(encoding="utf-8")
    m = re.search(r"^#\s+(.+)$", text, re.M)
    title = _TAG_RE.sub("", m.group(1)).replace("`", "").strip() if m else src.stem
    body = render_markdown(text)
    body, toc, census = assign_heading_ids(body)
    plain = _html.unescape(_TAG_RE.sub(" ", body))
    return Page(src=src, rel=out_rel(src), title=title, body=body, toc=toc, census=census,
                search_text=re.sub(r"\s+", " ", plain)[:20000])


# ----------------------------------------------------------------------------------- link rewriting

_HREF_RE = re.compile(r'(href|src)="([^"]+)"')


def _github_base() -> str | None:
    """The public repo's blob-URL base, for links to repo files the site does not carry (source
    files, directories). Offline-derived from the git remote; None when there is no GitHub remote."""
    try:
        url = subprocess.run(["git", "-C", str(REPO), "remote", "get-url", "origin"],
                             capture_output=True, text=True, timeout=10).stdout.strip()
    except Exception:  # noqa: BLE001 -- no git is the same answer as no remote
        return None
    m = re.match(r"(?:git@github\.com:|https://github\.com/)([^/]+/[^/.]+)", url)
    return f"https://github.com/{m.group(1)}" if m else None


class LinkRewriter:
    def __init__(self, pages: dict[str, Page], shots_dir: Path):
        self.pages = pages                       # keyed by output rel
        self.by_repo_rel = {p.src.relative_to(REPO).as_posix(): p
                            for p in pages.values() if p.src is not None}
        self.errors: list[str] = []
        self.assets: dict[str, Path] = {}        # out rel -> source file to copy
        self.gh = _github_base()
        self.shots_dir = shots_dir
        self.shot_figures: list[str] = []        # shot ids referenced by any page

    def rewrite(self, page: Page) -> str:
        # A generated page authors site-relative hrefs itself; only source pages need resolution.
        # docsite/pages/* publish at the site root and are authored as if at the repo root.
        base = None
        if page.src is not None:
            base = REPO if page.src.parent == HERE / "pages" else page.src.parent

        def _sub(m: re.Match) -> str:
            attr, target = m.group(1), m.group(2)
            new = self._resolve(page, base, attr, target)
            return f'{attr}="{new}"'

        return _HREF_RE.sub(_sub, page.body)

    def _resolve(self, page: Page, base: Path | None, attr: str, target: str) -> str:
        if re.match(r"^(https?:|mailto:|data:)", target):
            return target
        if target.startswith("#"):
            if target[1:] not in page.census:
                self.errors.append(f"{page.rel}: broken same-page anchor {target}")
            return target
        path_part, _, anchor = target.partition("#")
        if base is None:
            # A generated page authors SITE-relative hrefs -- validated, never rewritten. Rot in a
            # generated page is still rot.
            here = page.rel.split("/")[:-1]
            parts = path_part.split("/")
            while parts and parts[0] == "..":
                parts, here = parts[1:], here[:-1]
            site_rel = "/".join(here + parts)
            tgt = self.pages.get(site_rel)
            if tgt is None:
                self.errors.append(f"{page.rel}: broken generated link {target}")
            elif anchor and anchor not in tgt.census:
                self.errors.append(f"{page.rel}: anchor #{anchor} not found in {tgt.rel}")
            return target
        resolved = (base / path_part).resolve()
        try:
            repo_rel = resolved.relative_to(REPO).as_posix()
        except ValueError:
            self.errors.append(f"{page.rel}: link escapes the repo: {target}")
            return target

        # A generated page's rel can be authored from a source page too (the front page links the
        # CLI reference, which exists on the site only).
        gen_rel = re.sub(r"\.md$", ".html", repo_rel)
        if gen_rel in self.pages and self.pages[gen_rel].generated:
            tgt = self.pages[gen_rel]
            if anchor and anchor not in tgt.census:
                self.errors.append(f"{page.rel}: anchor #{anchor} not found in {tgt.rel}")
            return _relpath(gen_rel, page.rel) + (f"#{anchor}" if anchor else "")

        if repo_rel in self.by_repo_rel:         # an internal doc -> its page
            tgt = self.by_repo_rel[repo_rel]
            if anchor and anchor not in tgt.census:
                self.errors.append(f"{page.rel}: anchor #{anchor} not found in {tgt.rel}")
            href = _relpath(tgt.rel, page.rel) + (f"#{anchor}" if anchor else "")
            return href
        if not resolved.exists():
            self.errors.append(f"{page.rel}: broken link {target}")
            return target
        if resolved.is_dir():                    # no dir listings on a static site -> GitHub
            if self.gh:
                return f"{self.gh}/tree/master/{repo_rel}"
            self.errors.append(f"{page.rel}: directory link {target} needs a GitHub remote")
            return target
        if attr == "src" or resolved.suffix.lower() in (
                ".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".json", ".css", ".mjs", ".toml"):
            self.assets[repo_rel] = resolved     # carried into the site, tree-mirrored
            return _relpath(repo_rel, page.rel) + (f"#{anchor}" if anchor else "")
        if self.gh:                              # source files etc. -> the repo
            return f"{self.gh}/blob/master/{repo_rel}"
        self.assets[repo_rel] = resolved
        return _relpath(repo_rel, page.rel)


def _relpath(target_rel: str, from_rel: str) -> str:
    """Relative href from one site-relative file to another (posix, no os.path drama)."""
    t, f = target_rel.split("/"), from_rel.split("/")[:-1]
    while t and f and t[0] == f[0]:
        t, f = t[1:], f[1:]
    return "/".join([".."] * len(f) + t) or "."


# -------------------------------------------------------------------------- shot figure upgrading

_SHOT_IMG_RE = re.compile(
    r'<img([^>]*?)src="([^"]*?docsite/assets/shots/([A-Za-z0-9_-]+)_([a-z]+)\.png)"([^>]*?)/?>')


def upgrade_shot_figures(page_html: str, page_rel: str, shots_dir: Path,
                         errors: list[str], assets: dict | None = None) -> tuple[str, list[str]]:
    """An <img> pointing into docsite/assets/shots/ (which GitHub renders as a plain picture)
    becomes a themed <figure>: light+dark variants swapped by CSS, plus an SVG overlay drawn from
    the shot's sidecar (widget-anchored annotation rects resolved at grab time by shots.py).
    The PNG stays clean and diffable; the callouts live here, as vectors."""
    used: list[str] = []

    def _sub(m: re.Match) -> str:
        pre, src, shot, theme, post = m.groups()
        alt_m = re.search(r'alt="([^"]*)"', pre + post)
        alt = alt_m.group(1) if alt_m else shot
        sidecar = shots_dir / f"{shot}_{theme}.json"
        if not sidecar.is_file():
            errors.append(f"{page_rel}: shot figure {shot} has no sidecar {sidecar.name}")
            return m.group(0)
        meta = json.loads(sidecar.read_text(encoding="utf-8"))
        w, h = meta["size"]
        pair = meta.get("theme_pair", {})
        light_rel = src
        dark_theme = pair.get("dark", "mist")
        dark_rel = src.replace(f"_{theme}.png", f"_{dark_theme}.png") \
            if theme == pair.get("light", "light") else src
        # The markdown references only the light PNG (GitHub shows that one); the dark twin the
        # figure swaps to must be carried into the site as an asset too, or dark theme 404s.
        twin = shots_dir / f"{shot}_{dark_theme}.png"
        if not twin.is_file():
            errors.append(f"{page_rel}: shot figure {shot} is missing its dark twin {twin.name}")
            return m.group(0)
        if assets is not None:
            assets[f"docsite/assets/shots/{twin.name}"] = twin
        notes = []
        for i, a in enumerate(meta.get("annotations", []), 1):
            x, y, rw, rh = a["rect"]
            label = a.get("label", str(i))
            notes.append(
                f'<rect x="{x - 6}" y="{y - 6}" width="{rw + 12}" height="{rh + 12}" rx="9"/>'
                f'<g><circle cx="{x - 6}" cy="{y - 6}" r="14"/>'
                f'<text x="{x - 6}" y="{y - 1}">{_html.escape(label)}</text></g>')
        svg = (f'<svg class="shot-notes" viewBox="0 0 {w} {h}" aria-hidden="true">'
               + "".join(notes) + "</svg>") if notes else ""
        used.append(shot)
        stamp = f'auto-generated · ff9mapkit {_html.escape(str(meta.get("kit_version", "?")))}'
        return (f'<figure class="shot"><div class="shot-frame" style="aspect-ratio:{w}/{h}">'
                f'<img class="shot-light" src="{light_rel}" alt="{_html.escape(alt)}" width="{w}" height="{h}">'
                f'<img class="shot-dark" src="{dark_rel}" alt="{_html.escape(alt)}" width="{w}" height="{h}" loading="lazy">'
                f'{svg}</div><figcaption>{_html.escape(alt)} <span class="stamp">{stamp}</span></figcaption></figure>')

    return _SHOT_IMG_RE.sub(_sub, page_html), used


# ------------------------------------------------------------------------------- the CLI reference

def build_cli_pages() -> list[Page]:
    """One page per CLI verb, from `cli.build_parser()` introspection -- never from prose. The
    grouped human curation stays SETUP.md section 7's job for now; these pages are the complete,
    always-current census (the gate: the index row count IS the parser's verb count)."""
    sys.path.insert(0, str(REPO / "ff9mapkit"))  # the local package shadows any editable install
    argv0, sys.argv = sys.argv, ["ff9mapkit"]    # argparse bakes prog from argv[0] at construction
    try:
        from ff9mapkit import cli as _cli
        parser = _cli.build_parser()
    finally:
        sys.argv = argv0
    sub = next(a for a in parser._actions if isinstance(a, argparse._SubParsersAction))
    one_liners = {c.dest: (c.help or "") for c in sub._choices_actions}
    pages: list[Page] = []
    rows = []
    for name, sp in sorted(sub.choices.items()):
        body, toc, census = assign_heading_ids(_verb_page_html(name, sp, one_liners.get(name, "")))
        pages.append(Page(src=None, rel=f"reference/cli/{name}.html", title=f"ff9mapkit {name}",
                          body=body, toc=toc, census=census, generated=True,
                          search_text=f"ff9mapkit {name} {one_liners.get(name, '')} "
                                      + re.sub(r"\s+", " ", _html.unescape(_TAG_RE.sub(" ", body)))[:4000]))
        rows.append(f'<tr><td><a href="{name}.html"><code>{name}</code></a></td>'
                    f"<td>{_html.escape(one_liners.get(name, ''))}</td></tr>")
    idx_html = (f"<h1>CLI reference</h1><p>All <strong>{len(rows)}</strong> <code>ff9mapkit</code> "
                f"subcommands, generated from the argument parser itself — this census cannot drift "
                f"from the code. Global flags (<code>--game</code>, <code>--mod-folder</code>) go "
                f"<em>before</em> the subcommand. The task-grouped tour lives in "
                f'<a href="../../SETUP.html#7-cli-command-reference">SETUP §7</a>.</p>'
                f'<table class="cli-index"><thead><tr><th>verb</th><th>what it does</th></tr></thead>'
                f'<tbody>{"".join(rows)}</tbody></table>')
    body, toc, census = assign_heading_ids(idx_html)
    pages.insert(0, Page(src=None, rel="reference/cli/index.html", title="CLI reference",
                         body=body, toc=toc, census=census, generated=True,
                         search_text="cli reference subcommands " + " ".join(sorted(sub.choices))))
    return pages


def _verb_page_html(name: str, sp: argparse.ArgumentParser, one_liner: str) -> str:
    usage = _html.escape(sp.format_usage().replace("usage: ", "").strip())
    desc = sp.description or one_liner
    out = [f"<h1><code>ff9mapkit {_html.escape(name)}</code></h1>"]
    if desc:
        out.append(f"<p>{_html.escape(desc)}</p>")
    out.append(f'<pre class="usage"><code>{usage}</code></pre>')
    rows = []
    for act in sp._actions:
        if isinstance(act, argparse._HelpAction):
            continue
        if act.option_strings:
            label = ", ".join(act.option_strings)
            if act.nargs != 0 and not isinstance(act, (argparse._StoreTrueAction,
                                                       argparse._StoreFalseAction,
                                                       argparse._CountAction)):
                label += f" {act.metavar or act.dest.upper()}"
        else:
            label = act.metavar or act.dest
        bits = []
        hlp = (act.help or "").replace("%(default)s", str(act.default))
        if hlp:
            bits.append(_html.escape(hlp))
        if act.choices:
            bits.append("one of: " + ", ".join(f"<code>{_html.escape(str(c))}</code>"
                                               for c in act.choices))
        if act.default not in (None, argparse.SUPPRESS, False) and act.option_strings:
            bits.append(f"default: <code>{_html.escape(str(act.default))}</code>")
        rows.append(f"<tr><td><code>{_html.escape(label)}</code></td><td>{' — '.join(bits)}</td></tr>")
    if rows:
        out.append('<h2>Arguments</h2><table class="args"><tbody>' + "".join(rows) + "</tbody></table>")
    out.append('<p class="stamp">Generated from <code>cli.build_parser()</code> — not hand-written.</p>')
    return "".join(out)


# ------------------------------------------------------------------------------------- navigation

def load_nav(pages: dict[str, Page]) -> list[dict]:
    cfg = tomllib.loads((HERE / "nav.toml").read_text(encoding="utf-8"))
    used: set[str] = set()
    sections = []
    errors = []
    for sec in cfg["section"]:
        entries = []
        for pat in sec.get("pages", []):
            if "*" in pat:
                pat_html = re.sub(r"\.md$", ".html", pat)
                hits = sorted(r for r in pages
                              if re.fullmatch(re.escape(pat_html).replace(r"\*", "[^/]*"), r)
                              and r not in used and r not in entries)
                if not hits:
                    errors.append(f"nav.toml: glob {pat!r} matched nothing")
                entries += hits
            else:
                rel = re.sub(r"\.md$", ".html", pat)
                if rel not in pages:
                    errors.append(f"nav.toml: no such page {pat!r}")
                    continue
                entries.append(rel)
        used.update(entries)
        sections.append({"title": sec["title"], "pages": entries})
    if errors:
        raise SystemExit("nav errors:\n  " + "\n  ".join(errors))
    # THE AUTO-BUCKET: an unlisted page joins "More" instead of vanishing -- curation orders, it
    # never gates existence (a gating list rots; the corpus grows most weeks).
    stray = sorted(r for r in pages if r not in used and r != "index.html"
                   and not r.startswith("reference/cli/"))
    if stray:
        sections.append({"title": "More", "pages": stray})
    return sections


def nav_html(sections: list[dict], pages: dict[str, Page], current: str) -> str:
    out = [f'<a class="brand" href="{_relpath("index.html", current)}">{SITE_TITLE}</a>']
    for sec in sections:
        rows = []
        open_ = any(r == current for r in sec["pages"])
        for r in sec["pages"]:
            cls = ' class="here"' if r == current else ""
            rows.append(f'<li{cls}><a href="{_relpath(r, current)}">'
                        f'{_html.escape(pages[r].title)}</a></li>')
        # A verb page keeps the Reference section open + its index row lit.
        if any(r == "reference/cli/index.html" for r in sec["pages"]) \
                and current.startswith("reference/cli/"):
            open_ = True
        out.append(f'<details{" open" if open_ else ""}><summary>{_html.escape(sec["title"])}'
                   f"</summary><ul>{''.join(rows)}</ul></details>")
    return "\n".join(out)


# --------------------------------------------------------------------------------------- template

PAGE_TMPL = """<!DOCTYPE html>
<html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} · {site}</title>
<link rel="stylesheet" href="{root}static/site.css">
<link rel="stylesheet" href="{root}static/pyg.css">
<script>const t=localStorage.getItem('dwix-theme');if(t)document.documentElement.dataset.theme=t;</script>
</head><body>
<nav class="side">{nav}</nav>
<div class="main">
<header class="top">
  <button class="navbtn" aria-label="Menu">☰</button>
  <input class="search" type="search" placeholder="Search the manual…" aria-label="Search the manual">
  <button class="theme" aria-label="Toggle theme">◐</button>
</header>
<div class="results" hidden></div>
<article class="page">
{toc}
{body}
<footer>ff9mapkit {version} · built from the repo's own docs — <a href="{root}index.html">Manual home</a></footer>
</article>
</div>
<script type="module" src="{root}static/site.mjs"></script>
</body></html>
"""


def page_toc_html(page: Page) -> str:
    items = [t for t in page.toc if t["level"] in (2, 3)]
    if len(items) < 3:
        return ""
    rows = "".join(f'<li class="l{t["level"]}"><a href="#{t["id"]}">{_html.escape(t["text"])}</a></li>'
                   for t in items)
    return f'<details class="pagetoc"><summary>On this page</summary><ul>{rows}</ul></details>'


# ------------------------------------------------------------------------------------------ build

def build(out_dir: Path) -> dict[str, Page]:
    version = kit_version()
    shots_dir = HERE / "assets" / "shots"

    pages: dict[str, Page] = {}
    for src in collect_sources():
        p = page_from_source(src)
        pages[p.rel] = p
    for p in build_cli_pages():
        pages[p.rel] = p

    rw = LinkRewriter(pages, shots_dir)
    rendered: dict[str, str] = {}
    shot_refs: dict[str, list[str]] = {}
    for rel, page in pages.items():
        html = rw.rewrite(page)
        html, used = upgrade_shot_figures(html, rel, shots_dir, rw.errors, rw.assets)
        rendered[rel] = html
        if used:
            shot_refs[rel] = used
    if rw.errors:
        raise SystemExit("link errors (" + str(len(rw.errors)) + "):\n  " + "\n  ".join(rw.errors))

    nav = load_nav(pages)
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)

    for rel, page in pages.items():
        root = "../" * rel.count("/")
        doc = PAGE_TMPL.format(title=_html.escape(page.title), site=SITE_TITLE, root=root,
                               nav=nav_html(nav, pages, rel), toc=page_toc_html(page),
                               body=rendered[rel], version=version)
        dst = out_dir / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(doc, encoding="utf-8")

    for rel, src in rw.assets.items():
        dst = out_dir / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)

    static = out_dir / "static"
    static.mkdir(exist_ok=True)
    for f in (HERE / "static").glob("*"):
        shutil.copy2(f, static / f.name)
    _write_pygments_css(static / "pyg.css")

    index = [{"u": rel, "t": p.title, "h": [t["text"] for t in p.toc], "b": p.search_text}
             for rel, p in sorted(pages.items())]
    (static / "search.json").write_text(json.dumps(index), encoding="utf-8")
    print(f"built {len(pages)} pages, {len(rw.assets)} assets, "
          f"{len(shot_refs)} page(s) with shot figures -> {out_dir}")
    return pages


def _write_pygments_css(dst: Path) -> None:
    from pygments.formatters import HtmlFormatter
    light = HtmlFormatter(style="default").get_style_defs(
        'html:not([data-theme="dark"]) .codehilite')
    dark = HtmlFormatter(style="native").get_style_defs('html[data-theme="dark"] .codehilite')
    auto_dark = HtmlFormatter(style="native").get_style_defs(
        'html:not([data-theme="light"]) .codehilite')
    dst.write_text(light + "\n@media (prefers-color-scheme: dark){\n" + auto_dark + "\n}\n" + dark,
                   encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default=str(HERE / "_site"))
    args = ap.parse_args()
    build(Path(args.out))


if __name__ == "__main__":
    main()
