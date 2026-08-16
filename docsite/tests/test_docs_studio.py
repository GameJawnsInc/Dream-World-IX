"""Docs Studio core gates -- the Qt-free half (studio_core.py) proven headlessly.

The nav model must round-trip the REAL nav.toml (header comment preserved, sections equal),
the reorder ops must do what the buttons claim, resolution must mirror build.load_nav's
semantics (globs, first-use-wins, the More bucket), page creation must refuse bad names and
overwrites, and the problem parser must read the build's own error format.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

import studio_core as core  # noqa: E402

try:
    import tomllib
except ImportError:  # pragma: no cover
    import tomli as tomllib


# ------------------------------------------------------------------------------- nav round-trip

def test_nav_roundtrip_preserves_data_and_header():
    nav = core.load_nav()
    text = core.dumps_nav(nav)
    cfg = tomllib.loads(text)
    assert [s["title"] for s in cfg["section"]] == [s.title for s in nav.sections]
    assert [s.get("pages", []) for s in cfg["section"]] == [s.entries for s in nav.sections]
    # the curation comment survives serialization verbatim
    assert text.startswith(nav.header)
    assert nav.header.lstrip().startswith("#")


def test_nav_roundtrip_is_stable():
    nav = core.load_nav()
    once = core.dumps_nav(nav)
    tmp = core.Nav(header=nav.header, sections=nav.sections)
    assert core.dumps_nav(tmp) == once


# ---------------------------------------------------------------------------------- reorder ops

def _nav():
    return core.Nav(header="# h", sections=[
        core.NavSection("A", ["a.md", "b.md", "c.md"]),
        core.NavSection("B", ["x.md"]),
    ])


def test_move_entry_clamps_at_both_ends():
    nav = _nav()
    assert core.move_entry(nav, 0, 0, -1) == 0            # clamped, no change
    assert nav.sections[0].entries == ["a.md", "b.md", "c.md"]
    assert core.move_entry(nav, 0, 2, +1) == 2            # clamped at the tail
    assert core.move_entry(nav, 0, 0, +1) == 1
    assert nav.sections[0].entries == ["b.md", "a.md", "c.md"]


def test_transfer_add_remove():
    nav = _nav()
    core.transfer_entry(nav, 0, 1, 1)
    assert nav.sections[0].entries == ["a.md", "c.md"]
    assert nav.sections[1].entries == ["x.md", "b.md"]
    core.add_entry(nav, 0, "n.md", at=0)
    assert nav.sections[0].entries[0] == "n.md"
    assert core.remove_entry(nav, 0, 0) == "n.md"
    assert core.remove_page_everywhere(nav, "b.md") == 1
    assert nav.sections[1].entries == ["x.md"]
    assert core.rename_page_entries(nav, "x.md", "y.md") == 1
    assert nav.sections[1].entries == ["y.md"]


# ----------------------------------------------------------------------------------- resolution

def _fake_pages():
    def p(repo_rel, out_rel, title):
        return core.DocPage(src=Path("C:/fake") / repo_rel, repo_rel=repo_rel,
                            out_rel=out_rel, title=title)
    return [
        p("README.md", "README.html", "Readme"),
        p("docsite/pages/what-can-i-do.md", "what-can-i-do.html", "What can I do"),
        p("ff9mapkit/docs/tutorials/s1.md", "ff9mapkit/docs/tutorials/s1.html", "S1"),
        p("ff9mapkit/docs/tutorials/s2.md", "ff9mapkit/docs/tutorials/s2.html", "S2"),
        p("ff9mapkit/docs/STRAY.md", "ff9mapkit/docs/STRAY.html", "Stray"),
    ]


def test_resolve_literal_glob_generated_missing_and_more():
    nav = core.Nav(header="", sections=[
        core.NavSection("Start", ["README.md", "what-can-i-do.md", "reference/cli/index.html",
                                  "gone.md"]),
        core.NavSection("Tutorials", ["ff9mapkit/docs/tutorials/s2.md",
                                      "ff9mapkit/docs/tutorials/*.md"]),
    ])
    sections, more = core.resolve_nav(nav, _fake_pages())
    kinds = [r.kind for r in sections[0].rows]
    assert kinds == ["literal", "literal", "generated", "missing"]
    # the docsite/pages page resolves through its site-root rel
    assert sections[0].rows[1].page.repo_rel == "docsite/pages/what-can-i-do.md"
    # s2 is pinned literal; the glob picks up only the remainder (first use wins)
    tut = sections[1].rows
    assert [(r.kind, r.page.title) for r in tut] == [("literal", "S2"), ("auto", "S1")]
    # the un-navved page lands in More, never vanishes
    assert [p.title for p in more] == ["Stray"]


def test_nav_entry_for_site_pages_is_root_relative():
    pages = _fake_pages()
    assert core.nav_entry_for(pages[1]) == "what-can-i-do.md"
    assert core.nav_entry_for(pages[0]) == "README.md"
    assert core.nav_entry_for(pages[2]) == "ff9mapkit/docs/tutorials/s1.md"


def test_resolve_real_corpus_has_no_missing_rows():
    """The shipping nav against the shipping corpus: every literal entry resolves."""
    sections, _more = core.resolve_nav(core.load_nav(), core.corpus())
    bad = [r.entry for s in sections for r in s.rows if r.kind == "missing"]
    assert bad == []


# --------------------------------------------------------------------------------- page create

def test_create_page_blank_and_refusals(tmp_path):
    dst = core.create_page(tmp_path, "my-page.md", "My Page", "blank")
    assert dst.read_text(encoding="utf-8").startswith("# My Page\n")
    with pytest.raises(FileExistsError):
        core.create_page(tmp_path, "my-page.md", "My Page", "blank")
    for bad in ("no-suffix", "../escape.md", "sp ace.md", ".hidden.md"):
        with pytest.raises(ValueError):
            core.create_page(tmp_path, bad, "t", "blank")


def test_create_page_tutorial_template_retitles(tmp_path):
    dst = core.create_page(tmp_path, "t.md", "08 -- Fork a room", "tutorial")
    text = dst.read_text(encoding="utf-8")
    assert text.startswith("# 08 -- Fork a room\n")
    assert "[tutorial]" in text                      # the frontmatter fence survives
    assert "[[tutorial.ui]]" in text


def test_slug_filename():
    assert core.slug_filename("Fork a Field!") == "fork-a-field.md"
    assert core.slug_filename("  ") == "untitled.md"


# ------------------------------------------------------------------------------ problem parsing

BUILD_ERR = """\
some chatter
build errors (3):
  ff9mapkit/docs/FORMAT.html: broken link ../nope.md
  what-can-i-do.html: anchor #gone not found in README.html
  ui-inventory.json missing -- run: py docsite/uiharvest.py
built 0 pages
"""

NAV_ERR = """\
nav errors:
  nav.toml: no such page 'ghost.md'
"""


def test_parse_problems_build_block():
    probs = core.parse_problems(BUILD_ERR)
    assert [(p.rel, p.message) for p in probs] == [
        ("ff9mapkit/docs/FORMAT.html", "broken link ../nope.md"),
        ("what-can-i-do.html", "anchor #gone not found in README.html"),
        (None, "ui-inventory.json missing -- run: py docsite/uiharvest.py"),
    ]
    assert core.parse_problems("all green, no errors here") == []


def test_problem_source_maps_back_to_sources():
    pages = _fake_pages()
    probs = core.parse_problems(NAV_ERR)
    assert probs[0].rel == "nav.toml"
    assert core.problem_source(probs[0], pages).name == "nav.toml"
    p = core.parse_problems(BUILD_ERR)[1]
    assert core.problem_source(p, pages).as_posix().endswith("docsite/pages/what-can-i-do.md")
