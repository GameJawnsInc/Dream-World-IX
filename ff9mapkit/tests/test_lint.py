"""The unified offline lint pass (`ff9mapkit lint` / build.lint_all).

`lint_all` folds every offline validator into one structured report -- schema (validate), story/flag
logic (lint_logic), reserved flag-band use (lint_flag_bands), walkmesh geometry + content placement
(verify_walkmesh), and camera pitch. These tests pin the new flag-band check and prove the geometry /
placement / camera sections now surface through `lint` (they used to be reachable only via `walkmesh
verify` or a full build), without false-positives on the kit's established 8000+ flag band.
"""

from __future__ import annotations

import pytest

from ff9mapkit.build import FieldProject, LintReport, lint_all, lint_flag_bands, shared_text_block_hint_for


def test_shared_text_block_hint_flags_dialogue_edit_on_default_block():
    """The text-shadow pre-flight: a dialogue rewrite on the shared default block 1073 is shadow-prone."""
    txt = [{"kind": "text", "entry": 0, "tag": 1, "txid": 34, "old": "Sure is dark...", "text": "Sure is spooky..."}]
    assert shared_text_block_hint_for(txt, 1073)                     # text edit on the shared default -> hint
    assert "text-block shadow" in shared_text_block_hint_for(txt, 1073)
    assert shared_text_block_hint_for(txt, 7001) is None             # a unique block -> no shadow risk -> clear
    assert shared_text_block_hint_for(txt, None)                     # missing block defaults to 1073 -> hint
    assert shared_text_block_hint_for([{"kind": "field", "to": 5}], 1073) is None   # non-text edit -> clear
    assert shared_text_block_hint_for([], 1073) is None              # no edits -> clear
    assert shared_text_block_hint_for(None, 1073) is None            # robust to None

# A minimal, fully-offline custom scene (quad walkmesh + pitch camera -> resolves with no art/install).
# Spawn centred, NPC well inside the floor -> no placement noise. Flag 200 is unmapped free space.
CLEAN = """
[field]
id = 4003
name = "LINTROOM"
area = 11
text_block = 1073

[camera]
pitch = 45

[walkmesh]
quad = [[-1200, -100], [1200, -100], [1200, -1400], [-1200, -1400]]

[player]
spawn = [0, -700]

[[event]]
zone = [[300, -600], [700, -600], [700, -1000], [300, -1000]]
set_flag = [{set_flag}, 1]
message = "*click*"

[[npc]]
name = "Guard"
preset = "vivi"
pos = [-400, -700]
dialogue = "Hi."
requires_flag = {requires_flag}
"""


def _load(tmp_path, *, set_flag=200, requires_flag=200, body=None):
    p = tmp_path / "lint.field.toml"
    p.write_text(body if body is not None else
                 CLEAN.format(set_flag=set_flag, requires_flag=requires_flag), encoding="utf-8")
    return FieldProject.load(p)


# ---------------------------------------------------------------- lint_flag_bands (the new check)

def test_flag_bands_clean_on_kit_working_band(tmp_path):
    """The kit's established 8000+ band (and the unmapped 200 used by the docs example) is free space --
    NOT reserved -- so an explicit write/read there draws no flag warning."""
    assert lint_flag_bands(_load(tmp_path, set_flag=8001, requires_flag=8000)) == []
    assert lint_flag_bands(_load(tmp_path, set_flag=200, requires_flag=200)) == []


def test_flag_bands_warns_chest_write(tmp_path):
    """A raw write into the treasure-chest 'opened' bitfield (8376-8511) -- the exact collision the
    [[flag]] validator guards, here reached via a literal set_flag -- is flagged and named."""
    w = lint_flag_bands(_load(tmp_path, set_flag=8400, requires_flag=200))
    assert len(w) == 1
    assert "chest_opened" in w[0] and "8400" in w[0]


def test_flag_bands_advises_chest_read(tmp_path):
    """Gating on a chest bit (no static per-chest identity) is an advisory, not a hard write warning."""
    w = lint_flag_bands(_load(tmp_path, set_flag=200, requires_flag=8400))
    assert len(w) == 1
    assert "8400" in w[0] and "advisory" in w[0]


def test_flag_bands_warns_handshake_and_scratch(tmp_path):
    """The byte-23 menu handshake (bit 184) and the choice-mask scratch (16320) are reserved too."""
    assert lint_flag_bands(_load(tmp_path, set_flag=184, requires_flag=200))      # field_menu_guard
    assert lint_flag_bands(_load(tmp_path, set_flag=16320, requires_flag=200))     # choice_scratch


# ---------------------------------------------------------------- lint_logic: model-bucket encounter scene
def test_lint_warns_on_model_bucket_encounter_scene(tmp_path):
    from ff9mapkit.build import lint_logic
    body = '[field]\nid = 4003\nname = "T"\narea = 11\n\n[encounter]\nscene = {scene}\n'
    assert any("MODEL-BUCKET" in w for w in lint_logic(_load(tmp_path, body=body.format(scene=472))))   # BSC_B3_*
    assert not any("MODEL-BUCKET" in w for w in lint_logic(_load(tmp_path, body=body.format(scene=67))))  # real EF


# ---------------------------------------------------------------- lint_logic: story-branch doors (#2)

def test_lint_warns_on_ungated_co_zone_gateways(tmp_path):
    # #2 (FORK_FIDELITY.md): a collapsed story-branch door = 2+ gateways at one zone. Ungated, they ALL arm
    # in a fork -> the player hits the wrong branch. lint_logic warns until each is gated by requires_flag.
    from ff9mapkit.build import lint_logic
    Z = "[[300, -600], [700, -600], [700, -1000], [300, -1000], [300, -1000]]"
    base = ('[field]\nid = 4003\nname = "LR"\narea = 11\ntext_block = 1073\n\n'
            '[camera]\npitch = 45\n\n'
            '[walkmesh]\nquad = [[-1200, -100], [1200, -100], [1200, -1400], [-1200, -1400]]\n\n'
            '[player]\nspawn = [0, -700]\n\n')

    def _warns(body):
        return [x for x in lint_logic(_load(tmp_path, body=body)) if "share one zone" in x]

    # two exits sharing one zone, both ungated -> warns and names both destinations
    w = _warns(base + f'[[gateway]]\nto = 4100\nzone = {Z}\n\n[[gateway]]\nto = 4200\nzone = {Z}\n')
    assert len(w) == 1 and "4100" in w[0] and "4200" in w[0]
    # each branch gated (one when SET, one when CLEAR) -> no warning (the fix the author is meant to apply)
    assert _warns(base + f'[[gateway]]\nto = 4100\nzone = {Z}\nrequires_flag = 8001\n\n'
                         f'[[gateway]]\nto = 4200\nzone = {Z}\nrequires_flag_clear = 8001\n') == []
    # a single door at the zone -> nothing to disambiguate
    assert _warns(base + f'[[gateway]]\nto = 4100\nzone = {Z}\n') == []


# ------------------------------------------------- lint_logic: synth content dropped on a verbatim fork

def test_lint_warns_synth_content_dropped_on_verbatim_fork(tmp_path):
    # a verbatim fork ([verbatim_eb]) runs the donor's real .eb -> build_script (which injects [cutscene]/
    # [[gateway]]/...) is bypassed, so that authored synth content is silently dropped. Warn before the user
    # wonders why their added door / cutscene never appears.
    from ff9mapkit.build import lint_logic
    body = ('[field]\nid = 4003\nname = "VTEST"\narea = 11\n\n'
            '[verbatim_eb]\nbin = "donor.bin"\n\n'
            '[encounter]\nscene = 67\n\n'
            '[[gateway]]\nname = "door"\n')
    w = lint_logic(_load(tmp_path, body=body))
    assert any("verbatim fork" in s and "[[gateway]]" in s for s in w), w         # synth content dropped
    assert any("does NOT add random battles" in s for s in w), w                  # encounter: BGM only here


def test_lint_does_not_warn_npc_dropped_on_verbatim_fork(tmp_path):
    # [[npc]] is NOW supported on a verbatim fork (seated below the party band by _inject_verbatim_npcs), so
    # it must NOT be reported as dropped -- the regression guard for removing it from _VERBATIM_IGNORED_BLOCKS.
    from ff9mapkit.build import lint_logic
    body = ('[field]\nid = 4003\nname = "VTEST"\narea = 11\n\n'
            '[verbatim_eb]\nbin = "donor.bin"\n\n'
            '[[npc]]\nname = "Guy"\npos = [0, 0]\n')
    w = lint_logic(_load(tmp_path, body=body))
    assert not any("[[npc]]" in s and "ignored" in s for s in w), w


def test_lint_no_verbatim_warning_on_a_synthesized_field(tmp_path):
    # the SAME blocks on a synthesized field (no [verbatim_eb]) ARE injected -> no verbatim warning
    from ff9mapkit.build import lint_logic
    body = ('[field]\nid = 4003\nname = "STEST"\narea = 11\n\n'
            '[encounter]\nscene = 67\n\n'
            '[[npc]]\nname = "Guy"\n')
    assert not any("verbatim fork" in s for s in lint_logic(_load(tmp_path, body=body)))


# ---------------------------------------------------------------- lint_all (the unified pass)

def test_lint_all_clean_field_is_ok(tmp_path):
    rep = lint_all(_load(tmp_path))
    assert isinstance(rep, LintReport)
    assert rep.errors == [] and rep.flags == []
    assert rep.source == "custom scene"
    assert rep.ok


def test_lint_all_surfaces_geometry_placement(tmp_path):
    """An off-walkmesh NPC must now show up through `lint` (it used to need `walkmesh verify`)."""
    rep = lint_all(_load(tmp_path, body=CLEAN.format(set_flag=200, requires_flag=200)
                         .replace("pos = [-400, -700]", "pos = [9000, 9000]")))
    assert any("off the walkmesh" in w for w in rep.placement)
    assert not rep.ok


def test_lint_all_surfaces_flag_band(tmp_path):
    rep = lint_all(_load(tmp_path, set_flag=8400, requires_flag=200))
    assert any("chest_opened" in w for w in rep.flags)
    assert not rep.ok


def test_lint_all_surfaces_camera_pitch(tmp_path):
    """A pitch outside the supported (0, 50) range surfaces in the camera section (cam.pitch_warning)."""
    body = CLEAN.format(set_flag=200, requires_flag=200).replace("pitch = 45", "pitch = 72")
    rep = lint_all(_load(tmp_path, body=body))
    assert rep.camera and any("pitch" in w for w in rep.camera)


def test_lint_all_errors_dont_mask_logic(tmp_path):
    """A schema error (area < 10) is reported, and the pass still completes (no crash)."""
    body = CLEAN.format(set_flag=200, requires_flag=200).replace("area = 11", "area = 3")
    rep = lint_all(_load(tmp_path, body=body))
    assert any("area" in e for e in rep.errors)
    assert not rep.ok


# ---------------------------------------------------------------- review-driven hardening

def test_flag_bands_tolerates_bare_int_set_flag(tmp_path):
    """A malformed `set_flag = N` (a bare int, not the documented [idx, val] list) must NOT crash the
    lint -- the index is still extracted and band-checked."""
    body = CLEAN.format(set_flag=200, requires_flag=200).replace("set_flag = [200, 1]", "set_flag = 8400")
    w = lint_flag_bands(_load(tmp_path, body=body))
    assert len(w) == 1 and "chest_opened" in w[0]
    # an empty list is tolerated too (no index, no crash)
    body2 = CLEAN.format(set_flag=200, requires_flag=200).replace("set_flag = [200, 1]", "set_flag = []")
    assert lint_flag_bands(_load(tmp_path, body=body2)) == []


PROP = """
[field]
id = 4003
name = "PROPROOM"
area = 11
text_block = 1073

[camera]
pitch = 45

[walkmesh]
quad = [[-1000, -100], [1000, -100], [1000, -1000], [-1000, -1000]]

[player]
spawn = [0, -500]

[[prop]]
prop = "chest"
pos = [-300, -500]
requires_flag = 8400
"""


def test_flag_bands_scans_prop_gates(tmp_path):
    """Props gate exactly like NPCs (requires_flag) -- a chest-band prop gate is flagged (was a gap)."""
    p = tmp_path / "prop.field.toml"
    p.write_text(PROP, encoding="utf-8")
    w = lint_flag_bands(FieldProject.load(p))
    assert any("8400" in m and "advisory" in m for m in w)


def test_lint_all_missing_borrow_does_not_crash(tmp_path):
    """A field that borrows a camera .bgx absent on disk (a fork whose game-derived input isn't copied in
    yet) must yield a clean reported error, NOT a traceback -- the pitch loop used to re-raise the
    FileNotFoundError. Calling lint_all without an exception IS the assertion."""
    body = """
[field]
id = 4003
name = "BORROWROOM"
area = 21

[camera]
borrow = "nope.bgx"

[walkmesh]
quad = [[-500, -500], [500, -500], [500, 500], [-500, 500]]
"""
    rep = lint_all(_load(tmp_path, body=body))          # must not raise
    assert rep.errors and not rep.ok


def _placement_warnings(tmp_path, npc_xz):
    from ff9mapkit.build import verify_walkmesh
    body = CLEAN.format(set_flag=200, requires_flag=200).replace(
        "pos = [-400, -700]", f"pos = [{npc_xz[0]}, {npc_xz[1]}]")
    rep = verify_walkmesh(_load(tmp_path, body=body))
    return [w for w in rep["warnings"] if "off the walkmesh" in w]


def test_npc_just_off_back_edge_is_not_flagged(tmp_path):
    """A back-wall NPC just past the floor edge (within talk reach) is a NORMAL placement -- no warning.
    The walkmesh quad spans z in [-1400, -100]; an NPC at z=-50 sits ~50u beyond the edge, reachable."""
    assert _placement_warnings(tmp_path, (0, -50)) == []


def test_npc_grossly_off_is_flagged(tmp_path):
    """An NPC far outside the floor footprint is still flagged as a misplacement."""
    w = _placement_warnings(tmp_path, (9000, 9000))
    assert len(w) == 1 and "far off the walkmesh" in w[0]
