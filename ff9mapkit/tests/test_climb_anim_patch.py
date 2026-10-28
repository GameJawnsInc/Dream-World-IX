"""[ff9mapkit netsync s157] THE CLIMB-ANIM ROUND's CAPTURE, read off the live patch stack (memoria-patches/, through
tests/_patchstack -- no clone, no install): studies/field-coop/GUEST-TRAVERSAL-TWO-PC.md Findings 1 + 2.

THE TAG LAW across the WHOLE s157 patch (test_coop_ghost_frame pins HarnessAgent.cs alone): one live s157 patch; every hunk of
every engine file carries `[ff9mapkit netsync s157]` on an added line and every added line is ASCII -- except the generated
guest-traversal table's section, which is the kit's render replaced WHOLE (one hunk; its header keeps s156's marker:
test_guest_traversal_table's whole-lineage pin owns that section). Twin, ghost-frame and lever pins live with their specs'
tests (test_harness_netsync, test_coop_ghost_frame, test_coop_peer, test_coop_climb_anim_bench).
"""
from __future__ import annotations

import re

import pytest

from ._patchstack import msr

TAG = b"[ff9mapkit netsync s157]"
TABLE = "NetSyncGuestLocalTable.cs"


def _s157() -> tuple:
    names = [n for n in msr.stack() if n.startswith("s157-") and n not in msr.DEAD]
    if not names:
        pytest.fail("s157 not captured: no live memoria-patches/s157-*.patch yet (capture it from the engine tree)")
    assert len(names) == 1, names
    return names[0], (msr.PATCHES / names[0]).read_bytes()


def _hunks(sec: bytes) -> list:
    """The section's hunks, each a list of its LF-split lines (the '@@' line first)."""
    lines = re.findall(rb"[^\n]*\n|[^\n]+$", sec)
    at = [k for k, ln in enumerate(lines) if ln.startswith(b"@@")]
    return [lines[s:(at[i + 1] if i + 1 < len(at) else len(lines))] for i, s in enumerate(at)]


def _untagged(blob: bytes) -> list:
    """(path, hunk head) of every engine hunk that breaks the tag law; the table's section must be ONE hunk."""
    bad = []
    for path, sec in msr.sections(blob):
        hunks = _hunks(sec)
        if not path or path.startswith("/") or ":" in path or not hunks:
            bad.append((path, b"unparseable section"))
            continue
        if path.endswith("/" + TABLE):
            if len(hunks) != 1:
                bad.append((path, b"%d hunks (the generated table is replaced WHOLE)" % len(hunks)))
            continue
        for h in hunks:
            added = [ln for ln in h[1:] if ln.startswith(b"+")]
            if not any(TAG in ln for ln in added) or not all(ln.isascii() for ln in added):
                bad.append((path, h[0].strip()))
    return bad


def test_every_s157_hunk_carries_the_tag_but_the_generated_tables():
    name, blob = _s157()
    assert _untagged(blob) == [], f"{name}: hunks without the s157 tag (or non-ASCII): {_untagged(blob)[:4]}"
    tables = [p for p, _ in msr.sections(blob) if p and p.endswith("/" + TABLE)]
    assert len(tables) == 1, "s157 carries the regenerated guest-traversal table (the kit's JSON), replaced whole"
    assert len(msr.sections(blob)) >= 2


def test_the_tag_law_can_fail():
    """Each break turns it red: a hunk with its tag stripped, a non-ASCII added line, the table split into two hunks."""
    _name, blob = _s157()
    h0 = blob.index(b"\n@@")
    h1 = min(i for i in (blob.find(b"\n@@", h0 + 1), blob.find(b"\ndiff --git", h0 + 1)) if i > 0)
    stripped = blob[:h0] + blob[h0:h1].replace(TAG, b"[ff9mapkit netsync s000]") + blob[h1:]   # the first hunk untagged
    assert _untagged(stripped) and len(_untagged(stripped)) == 1
    at = blob.index(b"\n+", blob.index(b"\n@@")) + 2
    assert _untagged(blob[:at] + "é".encode("utf-8") + blob[at:])
    t = blob.index(b"+++ b/Assembly-CSharp/Memoria/Netsync/" + TABLE.encode())
    mid = blob.index(b"\n+", blob.index(b"\n@@", t) + 200) + 1
    assert _untagged(blob[:mid] + b"@@ -1,1 +1,1 @@\n" + blob[mid:])
