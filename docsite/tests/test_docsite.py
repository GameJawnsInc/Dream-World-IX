"""The Manual's gates, as tests. Run: py -m pytest docsite/tests -q  (from the repo root).

These are the rung-0/1 gates from studies/interactive-docs/PLAN.md: GitHub-parity slugs (the
double-hyphen trap), link/anchor validation with TEETH, the nav auto-bucket, the generated CLI
census, and search sampling. The full-corpus build runs ONCE per session (module fixture) --
the corpus is the fixture, so these tests cannot silently pass on an empty room.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

import build as B  # noqa: E402


# ------------------------------------------------------------------------------- slug parity

@pytest.mark.parametrize("text,slug", [
    ("Fork a field", "fork-a-field"),
    ("`[field]` (required)", "field-required"),
    # THE DOUBLE-HYPHEN TRAP: GitHub strips punctuation without collapsing the hyphens that
    # surrounding spaces become. "a / b" -> "a--b", never "a-b".
    ("deploy-campaign / deploy-journey", "deploy-campaign--deploy-journey"),
    ("7. CLI command reference", "7-cli-command-reference"),
    ("[[npc]] (optional, repeatable)", "npc-optional-repeatable"),
    ("Speaker names & the dialogue tail", "speaker-names--the-dialogue-tail"),
    ("UPPER_case_and-dashes", "upper_case_and-dashes"),
])
def test_github_slug_parity(text, slug):
    assert B.github_slug(text) == slug


def test_duplicate_headings_dedupe_like_github():
    html = "<h2>Same</h2><h2>Same</h2><h2>Same</h2>"
    out, toc, census = B.assign_heading_ids(html)
    assert [t["id"] for t in toc] == ["same", "same-1", "same-2"]
    assert 'id="same-1"' in out


def test_relpath():
    assert B._relpath("docs/FORMAT.html", "index.html") == "docs/FORMAT.html"
    assert B._relpath("index.html", "docs/tutorials/06.html") == "../../index.html"
    assert B._relpath("docs/a.html", "docs/b.html") == "a.html"


# --------------------------------------------------------------------------- the corpus build

@pytest.fixture(scope="module")
def site(tmp_path_factory):
    out = tmp_path_factory.mktemp("site")
    pages = B.build(out)
    return out, pages


def test_every_source_has_a_page(site):
    out, pages = site
    srcs = B.collect_sources()
    assert len(srcs) >= 45, "the docs corpus shrank drastically -- wrong repo root?"
    for src in srcs:
        rel = B.out_rel(src)
        assert rel in pages and (out / rel).is_file(), f"no page for {src}"


def test_cli_reference_census_matches_the_parser(site):
    out, pages = site
    verb_pages = [r for r in pages if r.startswith("reference/cli/") and r != "reference/cli/index.html"]
    # the truth is the parser, never prose
    sys.path.insert(0, str(B.REPO / "ff9mapkit"))
    import argparse

    from ff9mapkit import cli as _cli
    argv0, sys.argv = sys.argv, ["ff9mapkit"]
    try:
        parser = _cli.build_parser()
    finally:
        sys.argv = argv0
    sub = next(a for a in parser._actions if isinstance(a, argparse._SubParsersAction))
    assert len(verb_pages) == len(sub.choices)
    assert len(verb_pages) > 100, "the CLI census collapsed -- partial introspection?"
    idx = (out / "reference/cli/index.html").read_text(encoding="utf-8")
    assert f"<strong>{len(verb_pages)}</strong>" in idx


def test_search_index_finds_the_sampled_terms(site):
    out, _ = site
    index = json.loads((out / "static" / "search.json").read_text(encoding="utf-8"))
    body = {e["u"]: (e["t"] + " " + " ".join(e["h"]) + " " + e["b"]).lower() for e in index}
    assert any("walkmesh" in v for v in body.values())
    assert any("gateway" in v for v in body.values())
    hits = [u for u, v in body.items() if "walkmesh" in v]
    assert "ff9mapkit/docs/FORMAT.html" in hits


def test_nav_lists_every_page_or_buckets_it(site):
    _, pages = site
    sections = B.load_nav(pages)
    listed = {r for s in sections for r in s["pages"]}
    for rel in pages:
        if rel == "index.html" or rel.startswith("reference/cli/"):
            continue
        assert rel in listed, f"{rel} fell out of the nav (auto-bucket broke)"
    assert "reference/cli/index.html" in listed


def test_nav_missing_entry_fails(tmp_path, monkeypatch, site):
    _, pages = site
    bad = tmp_path / "nav.toml"
    bad.write_text('[[section]]\ntitle = "X"\npages = ["no/such/file.md"]\n', encoding="utf-8")
    monkeypatch.setattr(B, "HERE", tmp_path)
    with pytest.raises(SystemExit):
        B.load_nav(pages)


def test_broken_link_is_a_build_error(site):
    """The validator has teeth: a synthetic page with a dead href must produce an error."""
    _, pages = site
    fake = B.Page(src=B.REPO / "README.md", rel="README.html", title="x",
                  body='<a href="ff9mapkit/docs/NO_SUCH_FILE.md">x</a>', census={})
    rw = B.LinkRewriter(pages, B.HERE / "assets" / "shots")
    rw.rewrite(fake)
    assert any("broken link" in e for e in rw.errors)


# --------------------------------------------------------------- the "What can I do?" catalog

def test_wcid_cards_are_well_formed(site):
    """Every catalog card keeps the three-part contract (what you get / how to try it / where to
    go deeper) -- a half-authored card is a test failure, not a shipped stub."""
    import re as _re
    out, pages = site
    page = pages.get("what-can-i-do.html")
    assert page is not None, "docsite/pages/what-can-i-do.md vanished"
    cards = [t for t in page.toc if t["level"] == 2]
    assert len(cards) >= 20, f"the catalog shrank to {len(cards)} cards"
    sections = _re.split(r"^## ", page.raw, flags=_re.M)[1:]
    assert len(sections) == len(cards)
    for sec in sections:
        title = sec.splitlines()[0]
        for label in ("**You get:**", "**Try it:**", "**Go deeper:**"):
            assert label in sec, f"card {title!r} is missing its {label} line"


def test_wcid_shuffle_is_wired(site):
    """The shuffle enhancement's three legs -- page buttons, the site.mjs module, the card CSS --
    must all be present; losing any one leaves a dead button or an unstyled list."""
    out, pages = site
    html = (out / "what-can-i-do.html").read_text(encoding="utf-8")
    assert 'id="wcid-shuffle"' in html and 'id="wcid-all"' in html
    mjs = (out / "static" / "site.mjs").read_text(encoding="utf-8")
    for needle in ("wcid-shuffle", "wcid-all", "wcid-card", "wcid-solo", "wcid-pick"):
        assert needle in mjs, f"site.mjs lost the shuffle hook {needle!r}"
    css = (out / "static" / "site.css").read_text(encoding="utf-8")
    for needle in (".wcid-card", "article.wcid-solo .wcid-card.wcid-pick"):
        assert needle in css, f"site.css lost the card rule {needle!r}"
