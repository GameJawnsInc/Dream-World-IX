"""The Workspace Chocobo Hot & Cold form (a [chocobo] block authored on a verbatim forest fork).

Two proofs, both driving the real shell:
  * NEGATIVE (install-independent) -- a non-chocobo verbatim fork's Script subtree carries NO 'chocobo_root'
    node, so the form is hidden everywhere except an actual forest (the "reduce clutter" gate).
  * POSITIVE (install-gated) -- a real 2950 fork surfaces the node; mounting the panel + committing a slot
    edit writes a [chocobo] block (dirty), and Reset clears it. Skips without the game install (needs the
    real forest .eb) or without PySide6.
"""
from __future__ import annotations

import os
import struct
import tempfile
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication          # noqa: E402

from ff9mapkit import campaign as C                 # noqa: E402
from ff9mapkit.editor.theme import pick_palette     # noqa: E402
from ff9mapkit.workspace import shell               # noqa: E402


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def _min_eb(body: bytes) -> bytes:
    """A valid 1-entry / 1-func (tag 0) .eb wrapping ``body`` -- a field with no chocobo pool."""
    head = bytearray(0x80)
    head[0:2] = b"EV"
    head[3] = 1
    funcbody = bytes([0, 1]) + struct.pack("<HH", 0, 4) + body
    slot = struct.pack("<HHBBH", 8, len(funcbody), 0, 0, 0)
    return bytes(head) + slot + funcbody


def _verbatim_fork(win, eb_bytes, name="FORK", fid=30100):
    """Build a one-member verbatim-fork campaign around ``eb_bytes`` and open it; return the member tree item
    with its Script (logic_root) group lazily loaded. Mirrors the shell smoke's ALEXFORK setup."""
    d = Path(tempfile.mkdtemp())
    mem = [C.Member(100, fid, name, "borrow", 11, "", f"{name}/{name}.field.toml", False)]
    plan = C.CampaignPlan(name="CH", mod_folder="M", id_base=fid, flag_base=C.FIRST_SAFE_FLAG,
                          flags_per_field=64, entry_name=name, entry_entrance=0, members=mem, edges=[], seams=[])
    (d / "campaign.toml").write_text(C.render_campaign_toml(plan), encoding="utf-8")
    (d / name).mkdir(parents=True, exist_ok=True)
    (d / name / f"{name}.field.toml").write_text(
        f'[field]\nid = {fid}\nname = "{name}"\narea = 11\n\n'
        f'[verbatim_eb]\nbin = "{name}.verbatim_eb.bin"\n', encoding="utf-8")
    (d / name / f"{name}.verbatim_eb.bin").write_bytes(eb_bytes)
    assert win.open_campaign(d / "campaign.toml")
    item = win.tree.topLevelItem(0).child(0)
    win.tree.expandItem(item)                                    # lazy _load_objects -> badge + Script group
    sgrp = next(item.child(i) for i in range(item.childCount())
                if win._payload(item.child(i))[0] == "logic_root")
    win.tree.expandItem(sgrp)                                    # lazy _load_logic_map (+ the scan gate)
    return item, sgrp


def _chocobo_node(win, sgrp):
    for i in range(sgrp.childCount()):
        if win._payload(sgrp.child(i))[0] == "chocobo_root":
            return sgrp.child(i)
    return None


def test_gate_hides_the_form_on_a_non_chocobo_fork(app):
    """A verbatim fork with no dig-prize pool shows NO Chocobo node in its Script subtree."""
    win = shell.Workspace(pick_palette("dark"))
    _item, sgrp = _verbatim_fork(win, _min_eb(bytes([0x04])), name="PLAIN")
    assert _chocobo_node(win, sgrp) is None, "the Chocobo form must be hidden on a non-forest field"


def test_chocobo_form_on_a_real_forest(app):
    """A real 2950 fork: the node appears, the panel mounts, a slot edit writes a [chocobo] block + dirties
    the member, and Reset restores the clean baseline."""
    try:
        from ff9mapkit.extract import EventBundle
        eb = EventBundle().eb_for_id(2950)
    except Exception:                                           # noqa: BLE001
        pytest.skip("no game install (need the real 2950 .eb)")
    from ff9mapkit.content import chocobo as CH

    win = shell.Workspace(pick_palette("dark"))
    _item, sgrp = _verbatim_fork(win, eb, name="CHFOREST")
    node = _chocobo_node(win, sgrp)
    assert node is not None, "the Chocobo Hot & Cold node appears on a forest fork"

    win.tree.setCurrentItem(node)                               # the real click path: inspector + panel mount
    assert "prize" in win.insp_body.text().lower() or "timer" in win.insp_body.text().lower(), \
        "the inspector describes the chocobo node"
    assert win.doc_host_lay.count() > 0, "the Chocobo panel mounted"

    # author slot 0 -> Elixir + timer 120 through the same commit path the buttons use
    cfg = CH.set_prize(win._doc("CHFOREST").data.get("chocobo"), 0, {"item": "Elixir"})
    cfg = CH.set_timer(cfg, 120)
    win._commit_chocobo("CHFOREST", cfg)
    block = win._doc("CHFOREST").data.get("chocobo")
    assert block and CH.prize_entry(block, 0) == {"slot": 0, "item": "Elixir"}, block
    assert (block.get("tuning") or {}).get("timer") == 120
    assert "CHFOREST" in win._unsaved(), "authoring dirtied the member"

    # a redundant value-override that resolves to vanilla still commits cleanly (it emits zero edits) --
    # the interactive dialog path (_edit_chocobo_slot) is what collapses it back to 'no override'.
    van = CH.scan(eb).slots[0].value
    win._commit_chocobo("CHFOREST", CH.set_prize(block, 0, {"value": van}))
    assert CH.prize_entry(win._doc("CHFOREST").data.get("chocobo"), 0) == {"slot": 0, "value": van}

    # Reset -> back to the (empty) saved baseline, member clean
    win._reset_chocobo("CHFOREST")
    assert not win._doc("CHFOREST").data.get("chocobo"), "Reset dropped the [chocobo] block"
    assert "CHFOREST" not in win._unsaved(), "Reset cleared the dirty mark"


def test_bad_edit_is_refused_not_written(app):
    """A [chocobo] cfg that can't resolve (an unknown item) is refused by the commit dry-run -- nothing is
    written into the doc."""
    try:
        from ff9mapkit.extract import EventBundle
        eb = EventBundle().eb_for_id(2950)
    except Exception:                                           # noqa: BLE001
        pytest.skip("no game install (need the real 2950 .eb)")

    win = shell.Workspace(pick_palette("dark"))
    _verbatim_fork(win, eb, name="CHBAD")
    win._open_editor("CHBAD", "chocobo_root", "chocobo")
    win._commit_chocobo("CHBAD", {"prize": [{"slot": 0, "item": "NotARealItem"}]})
    assert not win._doc("CHBAD").data.get("chocobo"), "a bad edit must not be written"
    assert "CHBAD" not in win._unsaved(), "a refused edit must not dirty the member"
