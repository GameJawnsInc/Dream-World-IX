"""The plain-language concept-card registry (workspace.concepts) -- PySide6-FREE pure data + resolver,
the single source of truth condensed from docs/GLOSSARY.md."""

from __future__ import annotations

from ff9mapkit.workspace import concepts


def test_every_card_is_well_formed():
    cards = concepts.all_concepts()
    assert len(cards) >= 20, "the vocabulary should be broadly covered"
    seen = set()
    for c in cards:
        assert c.term and c.term.islower(), c.term
        assert c.term not in seen, f"duplicate term {c.term}"
        seen.add(c.term)
        assert c.title and c.plain, c.term
        # plain language: a full sentence, not a bare gloss
        assert c.plain.endswith((".", "!")) and len(c.plain) > 40, c.term


def test_resolve_matches_term_alias_and_substring():
    assert concepts.resolve("walkmesh").term == "walkmesh"          # exact term
    assert concepts.resolve("Walkmesh").term == "walkmesh"          # case-insensitive
    assert concepts.resolve("story flag").term == "story-flag"       # alias
    assert concepts.resolve("gEventGlobal").term == "story-flag"     # engine-term alias
    assert concepts.resolve(".mes").term == "mes"                    # dotted alias
    assert concepts.resolve("forking").term == "fork"               # alias
    assert concepts.resolve("zzzzzz nonsense") is None
    assert concepts.resolve("") is None


def test_the_headline_vocabulary_all_resolves():
    # the §3/§5 vocabulary a newcomer meets -- every one must answer to a card
    for term in ("field", "walkmesh", "gateway", "encounter", "campaign", "journey", "fork", "verbatim",
                 "native", "editable", "story flag", "scenario", "deploy", "F6", "Memoria", "mesID",
                 "FBG", "bg-borrow", "paint template"):
        assert concepts.resolve(term) is not None, f"no concept card for {term!r}"


def test_html_defers_the_engine_term_to_a_muted_aside():
    c = concepts.get("walkmesh")
    html = c.html("#888888")
    assert c.plain in html
    assert "Under the hood" in html and "#888888" in html         # the technical aside is muted, not primary
