"""docs -> CLI drift, the one direction the docsite cannot cover by construction (scout F48).

The docsite generates one reference page per verb from ``cli.build_parser()`` itself and gates its index
row count against the parser's verb count, so IMPLEMENTED -> DOCUMENTED cannot drift. The hand-written
pages can: a verb renamed or removed leaves ``ff9mapkit old-verb`` in a tutorial. This walks every
hand-written page (the kit's docs/ tree, the docsite's own pages, the repo-root README / SETUP) for verbs
named AS COMMANDS -- inside a code span or on a fenced command line; prose like "ff9mapkit ships" is not
a command -- and asserts each exists. The vocabulary half: every root field.toml key the harvested schema
knows appears as ``[key]`` / ``[[key]]`` in some doc, with an explicit set of the keys that do not yet
(shrink it, never grow it -- a warning nobody reads is not a gate)."""

from __future__ import annotations

import re
from pathlib import Path

from ff9mapkit import _fieldschema, cli

REPO = Path(__file__).resolve().parents[2]
KIT = REPO / "ff9mapkit"

#: a doc may name a verb precisely to say it does NOT exist; each entry must be cited that way somewhere
_NAMED_AS_ABSENT = {"gui"}                     # KNOWN_ISSUES.md: "There is no `ff9mapkit gui` subcommand yet."
#: root keys the harvested vocabulary knows that no doc mentions yet -- shrink, never grow
_UNDOCUMENTED_ROOT_KEYS = {"folklore"}

_SPAN = re.compile(r"`[^`\n]*?\bff9mapkit ([a-z][a-z0-9-]+)[^`\n]*`")
_FENCE = re.compile(r"```.*?```", re.S)
_FENCE_CMD = re.compile(r"^\s*(?:\$ |> |py |python |python3 )?(?:-m )?ff9mapkit ([a-z][a-z0-9-]+)", re.M)


def hand_written_docs() -> list:
    pages = (list((KIT / "docs").rglob("*.md")) + list((REPO / "docsite").rglob("*.md"))
             + list(REPO.glob("*.md")))
    return sorted(p for p in set(pages) if p.is_file())


def verbs_named_as_commands(text: str) -> set:
    """Every ``<verb>`` a page names as a command: ``ff9mapkit <verb>`` inside a code span, or a fenced-block
    line invoking it (``ff9mapkit v``, ``py -m ff9mapkit v``, ``$ ff9mapkit v``)."""
    found = {m.group(1) for m in _SPAN.finditer(text)}
    for fence in _FENCE.findall(text):
        found.update(m.group(1) for m in _FENCE_CMD.finditer(fence))
    return found


def implemented_verbs() -> set:
    sub = next(a for a in cli.build_parser()._actions if a.__class__.__name__ == "_SubParsersAction")
    return set(sub.choices)


def _corpus() -> dict:
    return {p: p.read_text(encoding="utf-8", errors="replace") for p in hand_written_docs()}


def test_every_verb_the_docs_name_as_a_command_exists():
    verbs, corpus = implemented_verbs(), _corpus()
    assert len(verbs) >= 100 and len(corpus) >= 50               # the walk saw the real parser + corpus
    ghosts: dict = {}
    for page, text in corpus.items():
        for v in verbs_named_as_commands(text) - verbs - _NAMED_AS_ABSENT:
            ghosts.setdefault(v, []).append(str(page.relative_to(REPO)))
    assert ghosts == {}, ghosts
    for v in _NAMED_AS_ABSENT:                                    # the allowlist cannot rot into a real ghost
        assert v not in verbs, f"{v} exists now -- drop it from _NAMED_AS_ABSENT"
        assert any(f"no `ff9mapkit {v}`" in t for t in corpus.values()), f"no page says `ff9mapkit {v}` is absent"


def test_the_extractor_reads_commands_not_prose():
    """Calibration: today's corpus is clean, so show the instrument sees a ghost and ignores prose."""
    text = ("ff9mapkit ships a `ff9mapkit fork-report` verb and a `ff9mapkit no-such-verb` one.\n"
            "```\n$ ff9mapkit another-ghost 100\npy -m ff9mapkit build x.toml\n```\n"
            "and the prose 'ff9mapkit therefore' is not a command, nor is ff9mapkit contains\n")
    assert verbs_named_as_commands(text) == {"fork-report", "no-such-verb", "another-ghost", "build"}
    assert verbs_named_as_commands(text) - implemented_verbs() == {"no-such-verb", "another-ghost"}


def _undocumented(keys, corpus_text: str) -> set:
    return {k for k in keys if f"[{k}]" not in corpus_text and f"[[{k}]]" not in corpus_text}


def test_every_root_field_key_is_documented_somewhere():
    corpus_text = "\n".join(_corpus().values())
    root = {k for k in _fieldschema.VOCAB[""] if not k.startswith("_")}
    assert len(root) >= 50
    undocumented = _undocumented(root, corpus_text)
    assert undocumented == _UNDOCUMENTED_ROOT_KEYS, {
        "new undocumented keys": undocumented - _UNDOCUMENTED_ROOT_KEYS,
        "now documented -- shrink the set": _UNDOCUMENTED_ROOT_KEYS - undocumented}
    assert _undocumented({"zzz_no_such_block", "field"}, corpus_text) == {"zzz_no_such_block"}   # calibration
