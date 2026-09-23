"""A plain BG-borrow fork's donor row, in-game: does field 2507's delayed walkmesh hotfix fire on it, and does the
kit-built player stay on the walkmesh?

`ff9mapkit import 2507` (BG-borrow) now writes `[field] source_field = 2507`, so deploy emits the ForkDonorPatch row
`<fork> 2507` and the engine's EffectiveFieldId gates fire for the borrow (s29 routes FieldMap.DelayedActiveTri
through it). It used to write nothing, so a standalone borrow never got the row. The pass runs 0.5 s after load: it
detaches every actor whose `isPlayer` is false (the two carried chests, and a kit-built player) and deactivates the
landing tris 174/175/177/178. The build guards the player (content.walkmesh_hotfix.reattach_player) wherever the
pass can run -- a `borrow_bg` of 2507's scene included -- so both slots below carry the guard.

A/B, one launch, two slots built from ONE `import 2507`, identical except the key:

    30993  source_field = 2507  -> ForkDonorPatch `30993 2507` -> the engine's gate fires
    30994  no source_field      -> no row                      -> the gate stays false (the old import output)

Both drop the donor's [encounter] and carry the same instrument as editable_2507_ingame.py: a [[behavior.hud]]
reading B_BGIID/B_BGIFLOOR for the player (B_PTR(250)) and the two chests (entries 7/8), plus the keeper NPC the
unit gate needs. Both write the same 739.mes (the HUD at txids 500/501), so the live text is the same for both.

    py tools/deploy_field.py <A>/IPSN_FORK.field.toml --id 30993
    py tools/deploy_field.py <B>/IPSN_FORK.field.toml --id 30994
    py tools/play.py studies/fork-walkmesh-hotfix/borrow_2507_ingame.py --label borrow-2507-donor-row

PRE  ForkDonorPatch maps 30993 -> 2507 and not 30994; both deployed .eb carry the chests at entries 7/8
B    30994 (no row): the chests stay attached on the landing (floor 4) -- the hotfix did not run
A    30993 (row):    the chests read -1 (DelayedActiveTri fired), the player is on a triangle
W    from entrance 128, 12 run frames right toward the platform's east edge: both slots stop on the walkway, as the
     real field does (a detached player moves the full 360u into the void)
M    the in-field menu on each slot, shot for the s33 LOCATION label (the donor's name with the row, blank without)
X    exceptions, tallied by name
"""
from __future__ import annotations

import re
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "ff9mapkit"))
from ff9mapkit import extract  # noqa: E402
from ff9mapkit.config import ModLayout, find_game_path  # noqa: E402
from ff9mapkit.eb import EbScript  # noqa: E402
from ff9mapkit.scene import bgi  # noqa: E402
from ff9mapkit.scene.bgi import _pt_in_tri_xz  # noqa: E402

WITH_ROW, NO_ROW, REAL = 30993, 30994, 2507
DONOR = 2507
LANDING = (174, 175, 176, 177, 178)     # floor 4
CHESTS = (7, 8)                         # entry == uid; tags [0, 23, 24, 25, 26] (the carried props)
ENTRANCE = 128                          # the donor's arrival at (2019, -1077): the upper walkway
START = (2019, -1077)
FRAMES = 12
UPPER_Y = 2540                          # the walkmesh's -2540, sign-flipped in the published state
SENTINEL = 65535                        # a 5-digit HUD slot's open-pass placeholder (a u16)
DETACHED = (-1, 65535)                  # -1 as the Int32 expression renders it, or truncated to u16
LIVE = ModLayout(find_game_path() / "FF9CustomMap")
ROWS = ("P", "CA", "CB", "FA")


def _donor_mesh() -> bgi.BgiWalkmesh:
    """A borrow ships no walkmesh -- the engine loads the donor's -- so read the donor's own from the install."""
    with tempfile.TemporaryDirectory(prefix="ff9mk-2507-") as td:
        extract.extract_field(str(DONOR), td)
        return bgi.BgiWalkmesh.from_bytes((Path(td) / "walkmesh.bgi").read_bytes())


def _on_upper(wm, x, z) -> bool:
    wv = wm.world_verts()
    tf = wm._tri_floor()
    for t, tri in enumerate(wm.tris):
        vs = [wv[i] for i in tri.vtx]
        if tf[t] != 2 and abs(sum(v[1] for v in vs) / 3 + UPPER_Y) < 300 and _pt_in_tri_xz(x, z, *vs):
            return True
    return False


def _eb(fid) -> EbScript:
    p = LIVE.root / "StreamingAssets" / "assets" / "resources" / "commonasset" / "eventengine" / "eventbinary" \
        / "field" / "us" / f"EVT_TEST{fid}.eb.bytes"
    return EbScript.from_bytes(p.read_bytes())


def _preflight(g, wm) -> None:
    rows = {}
    fdp = LIVE.root / "ForkDonorPatch.txt"
    for ln in (fdp.read_text(encoding="utf-8-sig").splitlines() if fdp.exists() else []):
        parts = ln.split()
        if len(parts) == 2 and parts[0].isdigit():
            rows[int(parts[0])] = int(parts[1])
    g.check(rows.get(WITH_ROW) == DONOR and NO_ROW not in rows,
            f"PRE: ForkDonorPatch maps {WITH_ROW} -> {DONOR} and has no row for {NO_ROW}",
            f"rows {({k: v for k, v in rows.items() if k in (WITH_ROW, NO_ROW)})}")
    for fid in (WITH_ROW, NO_ROW):
        eb = _eb(fid)
        props = tuple(i for i, e in enumerate(eb.entries)
                      if not e.empty and [f.tag for f in e.funcs] == [0, 23, 24, 25, 26])
        g.check(props == CHESTS, f"PRE: {fid}'s deployed .eb carries the chests at entries {CHESTS}", str(props))
    g.check(_on_upper(wm, *START) and not _on_upper(wm, START[0] + 300, START[1]),
            "PRE: the arrival is on the upper walkway and 300u east of it is off every walkway tri")


def _parse(text: str) -> dict:
    out = {}
    for label in ROWS:
        m = re.search(r"(?<![A-Z])" + label + r"\s+(-?\d+)", text)
        if m:
            out[label] = int(m.group(1))
    return out


def _read_hud(g, fid) -> dict | None:
    """The strip's four values once its live pass has landed: the player row stops showing the open-pass
    sentinel. Every slot is written in the same pass, so the other three are live too."""
    seen: dict = {}

    def ready(st):
        for text in st.texts:
            vals = _parse(text)
            if len(vals) == len(ROWS) and vals["P"] != SENTINEL:
                seen.clear()
                seen.update(vals)
                return True
        return False

    try:
        g.wait_for(ready, timeout=20, what=f"{fid}'s HUD strip to render live values")
    except Exception as err:                     # noqa: BLE001 - reported as a check, never raised
        print(f"[borrow-2507] {fid}: HUD not readable: {err}; texts {g.state.texts!r}")
        return None
    return seen


def _probe(g, wm, fid, *, hud=True) -> dict:
    g.warp(fid, entrance=ENTRANCE)
    s0 = g.settle()
    g.check(s0.player_y is not None and abs(s0.player_y - UPPER_Y) < 120,
            f"{fid}: arrives at entrance {ENTRANCE} on the upper walkway",
            f"at ({s0.player_x}, {s0.player_y}, {s0.player_z})")
    g.wait_frames(90)                            # 3 s: well past the 0.5 s coroutine and the HUD warmup
    out: dict = {"hud": _read_hud(g, fid) if hud else None}
    if hud:
        g.shot(f"{fid}-hud")
    s0 = g.settle()
    g.walk("right", FRAMES)
    s1 = g.settle()
    g.shot(f"{fid}-after-right")
    out.update({"start": (s0.player_x, s0.player_z), "end": (s1.player_x, s1.player_z), "y": s1.player_y,
                "moved": round(((s1.player_x - s0.player_x) ** 2 + (s1.player_z - s0.player_z) ** 2) ** 0.5),
                "on_walkway": _on_upper(wm, s1.player_x, s1.player_z), "field": s1.field_id})
    if hud:
        out["hud_after"] = _read_hud(g, fid)
    print(f"[borrow-2507] {fid}: {out}")
    return out


def _menu_shot(g, fid) -> None:
    g.press("menu")                              # the s33 location label: the donor's name with the row
    g.wait_frames(45)
    g.shot(f"{fid}-menu")
    g.close_ui()


def run(g) -> None:
    wm = _donor_mesh()
    _preflight(g, wm)
    g.note("plain BG-borrow fork of 2507: the donor row decides whether DelayedActiveTri fires")
    g.newgame()
    mark = g.log_mark()
    res = {}
    for fid in (NO_ROW, WITH_ROW, REAL):
        try:
            res[fid] = _probe(g, wm, fid, hud=fid != REAL)
        except Exception as err:                 # noqa: BLE001 - one slot failing must not hide the others
            print(f"[borrow-2507] {fid}: probe failed: {err}")
            res[fid] = None
        if fid != REAL and res[fid] is not None:
            _menu_shot(g, fid)

    b, a = (res[NO_ROW] or {}).get("hud"), (res[WITH_ROW] or {}).get("hud")
    g.check(b is not None and b["CA"] in LANDING and b["CB"] in LANDING and b["FA"] == 4
            and b["P"] not in DETACHED,
            f"B {NO_ROW} (no row): both chests stay attached to the landing (floor 4) -- the hotfix did not run",
            str(b))
    g.check(a is not None and a["CA"] in DETACHED and a["CB"] in DETACHED and a["FA"] in DETACHED
            and a["P"] not in DETACHED,
            f"A {WITH_ROW} (row -> {DONOR}): both chests detached (-1), the player on a triangle -- "
            f"DelayedActiveTri fired", str(a))
    aa = (res[WITH_ROW] or {}).get("hud_after")
    g.check(aa is not None and aa["CA"] in DETACHED and aa["CB"] in DETACHED and aa["P"] not in DETACHED,
            f"A {WITH_ROW} after the walk: the chests still detached, the player still on a triangle", str(aa))
    # Attached vs detached, not an exact stop point: a bound player slides along the platform edge and comes to
    # rest at (2157, -870) or (2142, -907) from run to run, while a detached one covers the full 360u.
    for fid in (NO_ROW, WITH_ROW, REAL):
        r = res[fid]
        g.check(r is not None and r["on_walkway"] and r["moved"] < 300,
                f"W {fid}: stops at the platform edge, on the walkway (a detached player moves 360u)", str(r))

    tally: dict = {}
    for e in g.exceptions_since(mark):
        tally[str(e)] = tally.get(str(e), 0) + 1
    print(f"[borrow-2507] exceptions: {tally or 'none'}")
    g.check(True, "X: exceptions tallied", str(tally or "none"))
