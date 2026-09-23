"""``tools/memoria_stack_replay.py`` -- its DEAD skip set must match the README's dead rows.

The replay is the audit the "audit the stack before any rebuild" law runs. Until 2026-09-23 its
DEAD set covered only s12/s18/s21/s59, while ``memoria-patches/README.md`` had since RETIRED s35 and
REMOVED s63/s67 (reverse-applied out of the live tree). The replay kept applying them, so every
full-file audit printed ``DIFF BGSCENE_DEF.cs`` and ``DIFF ff9.cs`` against a CORRECT clone -- false
alarms loud enough to train the reader to ignore the audit. These tests pin (a) that DEAD equals the
set of patches the README marks dead, both directions, (b) that every DEAD name is a real file (a typo
would skip nothing), and (c) that every patch the replay does NOT skip parses into sections it can
apply -- an unparseable live patch (s63's absolute ``C:/`` headers) would be skipped just as silently --
and (d) that diag's EOL match forgives ONLY an all-LF live copy (BGSCENE_DEF.cs, all-LF and otherwise
content-identical, was the one false DIFF left once s35 stopped replaying), never mixed endings or content.

Offline: reads only the repo's own memoria-patches/, never the Memoria clone.
"""

import importlib.util
import pathlib
import re

REPO = pathlib.Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("memoria_stack_replay", REPO / "tools" / "memoria_stack_replay.py")
msr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(msr)

README = REPO / "memoria-patches" / "README.md"

# A status row whose verdict cell OPENS with a dead word: | `s35-....patch` | **RETIRED 2026-07-29 ...
_DEAD_ROW = re.compile(r"(?m)^\| `(s\d+[^`]*\.patch)`[^|]*\|\s*\*\*(?:RETIRED|REMOVED|WITHDRAWN)\b")
_ROW = re.compile(r"(?m)^\| `(s\d+[^`]*\.patch)`")


def readme_dead(text):
    """Every patch the README records as dead: a RETIRED/REMOVED/WITHDRAWN verdict anywhere, plus
    every row of the "Superseded / historical ... do NOT apply" table (s12/s18/s21)."""
    dead = set(_DEAD_ROW.findall(text))
    m = re.search(r"(?ms)^## Superseded / historical.*?(?=^## )", text)
    assert m, "README lost its 'Superseded / historical' section -- re-point this parser"
    dead |= set(_ROW.findall(m.group(0)))
    return dead


def test_parser_sees_every_known_dead_row():
    # Calibrate the parser before trusting it: these seven are dead by the README's own words.
    assert readme_dead(README.read_text(encoding="utf-8")) >= {
        "s12-engine-edits.patch", "s18-field-reload-hotkey.patch", "s21-dev-hotkeys-f6-f10.patch",
        "s35-overlay-texture-cache.patch", "s59-debug-warp-settle.patch",
        "s63-world-scene-probe.patch", "s67-rig-probe.patch"}


def test_parser_ignores_live_rows_that_merely_mention_removal():
    text = ("| `s71-x.patch` | **THE SPIKE -- THROWAWAY** (remove or re-gate once it has answered) |\n"
            "| `s35-y.patch` | **RETIRED 2026-07-29** -- reverted |\n"
            "## Superseded / historical -- do NOT apply\n| File | By |\n|---|---|\n"
            "| `s12-z.patch` | early scratch |\n## Next\n| `s99-w.patch` | live |\n")
    assert readme_dead(text) == {"s35-y.patch", "s12-z.patch"}


def test_dead_set_equals_the_readme_dead_rows():
    dead = readme_dead(README.read_text(encoding="utf-8"))
    missing = sorted(dead - msr.DEAD)
    extra = sorted(msr.DEAD - dead)
    assert not missing, f"README marks these dead but the replay still APPLIES them: {missing}"
    assert not extra, f"the replay skips these but the README does not mark them dead: {extra}"


def test_every_dead_name_is_a_real_patch():
    on_disk = {p.name for p in msr.PATCHES.glob("s*.patch")}
    assert msr.DEAD <= on_disk, f"DEAD names no file (a typo skips nothing): {sorted(msr.DEAD - on_disk)}"


def test_eol_match_forgives_only_an_all_lf_live_copy():
    tree = b"a\r\nb\r\n"
    assert msr.eol_match(tree, b"a\nb\n") == (b"a\nb\n", True)            # BGSCENE_DEF.cs: all-LF live
    assert msr.eol_match(tree, tree) == (tree, False)                     # the CRLF convention: untouched
    assert msr.eol_match(tree, b"a\r\nb\n")[0] != b"a\r\nb\n"             # mixed live: still a DIFF
    assert msr.eol_match(b"a\r\nb\n", b"a\nb\n") == (b"a\r\nb\n", False)  # mixed tree: not normalised
    assert msr.eol_match(tree, b"a\nc\n")[0] != b"a\nc\n"                 # real content change: still a DIFF


def test_every_replayed_patch_parses_into_applicable_sections():
    bad = {}
    for name in msr.stack():
        if name in msr.DEAD:
            continue
        paths = [p for p, _ in msr.sections((msr.PATCHES / name).read_bytes())]
        if not paths or any(not p or p.startswith("/") or ":" in p for p in paths):
            bad[name] = paths
    assert not bad, f"live patches the replay would silently skip (no repo-relative +++ header): {bad}"
