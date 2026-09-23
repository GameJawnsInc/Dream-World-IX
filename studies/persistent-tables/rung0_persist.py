"""RUNG 0 of board entry #1 -- does a gScriptVector cell survive save -> quit -> relaunch -> load?

Three harness LAUNCHES, one phase each (a hard quit between them is the point), chained by a small
state file. The phase comes from the environment:

    RUNG0_PHASE=write py tools/play.py studies/persistent-tables/rung0_persist.py --label rung0-write
    RUNG0_PHASE=read  py tools/play.py studies/persistent-tables/rung0_persist.py --label rung0-read
    RUNG0_PHASE=lost  py tools/play.py studies/persistent-tables/rung0_persist.py --label rung0-lost

Benches (studies/persistent-tables/bench/): 30860 VECWRITE seeds tid 4242 (ten cells) + tid 8400000 at
Main_Init and bumps cell 3 by 7 on public flag 14867; 30861 VECREAD declares NO table, so nothing in
it can re-seed what it reads, and shows the cells on a HUD strip.

WRITE  New Game -> 30861 (NEGATIVE CONTROL: everything absent) -> 30860 (seed, then bump: cell 3 =
       4011, a value only PLAY creates) -> poke a NONCE byte -> 30861 (the field-entry autosave
       captures it all; the HUD shows it in-session). Then decode the sandbox autosave OFFLINE: the
       vectors must be in the Memoria extra file. Quit to desktop.
READ   Fresh process -> title Continue (the autosave) -> 30861. The nonce proves THIS run's save
       loaded (not a stale sandbox file, not the player's own autosave through a redirect race);
       the HUD must show the bumped cells. Then 30860: its entry autosave (taken BEFORE its
       Main_Init) must still hold 4011 -- the loaded vector was in memory -- and its Main_Init
       must re-seed cell 3 to 4004 (the kit's re-seed law, the thing a persistent class skips).
LOST   The extra file set aside -> Continue loads the main block alone: the nonce is back (the main
       block carries gEventGlobal) but every vector is EMPTY and the game plays on. That is the
       container verdict, measured rather than read: vectors ride ONLY the extra file.

The player's own save is never touched: the s83 agent sandboxes saves into x64/ff9harness/save/
while armed, and Session.start() refuses to run if it did not.
"""
from __future__ import annotations

import hashlib
import json
import os
import random
import re
import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "ff9mapkit"))
from ff9mapkit import save as _save  # noqa: E402

WRITER, READER = 30860, 30861
BUMP_FLAG = 14867                       # vecwrite's public flag `bump` (printed by its build)
NONCE_BYTE = 1990                       # gEventGlobal byte = bits 15920-15927 (modal-result home, unreserved)
NONCE_BITS = tuple(range(NONCE_BYTE * 8, NONCE_BYTE * 8 + 8))
T, T_HIGH, T_CONTROL = 4242, 8400000, 4243
SEED = [1001, 2002, 3003, 4004, 5005, 6006, 7007, 8008, 9009, 10010]
BUMPED = SEED[:3] + [4011] + SEED[4:]
HIGH = [424242, 17]
STATE_FILE = REPO / ".harness-runs" / "rung0-persist-state.json"
PHASE = os.environ.get("RUNG0_PHASE", "").strip().lower()

# the HUD rows on each bench: label -> the open-pass width SENTINEL of its slot (10**digits - 1,
# from each toml's `digits`). A row still showing its sentinel has not had its live pass yet.
READ_ROWS = {"SIZE 4242": 99, "CELL 3": 99999, "SUM 0-9": 99999, "OTHER 9 OK": 9,
             "HIGH 0": 99999, "HIGH SIZE": 9, "CONTROL SIZE": 9}
WRITE_ROWS = {"SIZE 4242": 99, "CELL 0": 99999, "CELL 3": 99999, "CELL 9": 99999, "HIGH 0": 99999}


def _sha(p: Path) -> str | None:
    try:
        return hashlib.sha256(p.read_bytes()).hexdigest()
    except OSError:
        return None


def _sandbox(g) -> Path:
    return g.channel.dir / "save"


def _hud(g, rows, *, want_header: str, timeout: float = 20.0, until=None) -> dict | None:
    """Parse the HUD strip's rendered values out of the published dialogue texts.

    The strip opens with 5-glyph width SENTINELS (99999) and the live pass overwrites them, so a
    parse that still sees a sentinel waits for the next sample rather than reporting it."""
    found: dict = {}

    def parse(st):
        for text in st.texts:
            if want_header not in text:
                continue
            vals = {}
            for label in rows:
                m = re.search(re.escape(label) + r"\s+(-?\d+)", text)
                if m:
                    vals[label] = int(m.group(1))
            if len(vals) == len(rows) and all(vals[k] != rows[k] for k in rows)                     and (until is None or until(vals)):
                found.clear()
                found.update(vals)
                return True
        return False

    try:
        g.wait_for(parse, timeout=timeout, what=f"the {want_header} HUD strip to render live values")
    except Exception as err:                 # noqa: BLE001 - reported as a check, never raised
        print(f"[rung0] HUD not readable from texts: {err}")
        print(f"[rung0] texts now: {g.state.texts!r}")
        return None
    return found


def _read_nonce(g) -> int:
    g.watch(*NONCE_BITS)
    g.wait_frames(8)
    st = g.state
    return sum((1 << i) for i, b in enumerate(NONCE_BITS) if st.flag(b))


def _load_state() -> dict:
    return json.loads(STATE_FILE.read_text(encoding="utf-8"))


def _continue_from_title(g) -> None:
    """Title -> Continue. Continue takes the cursor by default when an autosave exists
    (TitleUI.CheckAutoSaveSlot), and it is the only route to the autosave (SaveLoadUI never lists it)."""
    g.wait_for(lambda s: s.ui_state == "Title", timeout=120, what="the title screen")
    g._sleep_alive(12.0)                     # Memoria is still loading on a cold title
    menu = g.state.raw.get("menu")
    print(f"[rung0] title menu before Continue: {menu}")
    g.shot("title")
    g.press("confirm")
    g.wait_for(lambda s: s.ui_state == "FieldHUD" and s.field_id > 0, timeout=90,
               what="Continue to load the autosave into a field")
    g._booted_once = True


# ------------------------------------------------------------------------------------------ phases
def phase_write(g) -> None:
    sandbox = _sandbox(g)
    # A stale sandbox autosave (an earlier run's) must not be loadable later: park it in the run dir.
    parked = g.run_dir / "sandbox-before"
    for p in sorted(sandbox.glob("SavedData_ww*.dat")):
        parked.mkdir(parents=True, exist_ok=True)
        shutil.move(str(p), str(parked / p.name))
        print(f"[rung0] parked stale sandbox file {p.name}")

    g.note("rung0 WRITE")
    g.newgame()

    # 1. NEGATIVE CONTROL -- nothing written yet, so the reader must show every vector absent.
    g.warp(READER)
    neg = _hud(g, READ_ROWS, want_header="VEC READ 30861")
    g.shot("1-reader-before-write")
    g.check(neg is not None, "the reader's HUD strip is readable from the published texts", str(neg))
    if neg:
        g.check(neg["SIZE 4242"] == 0 and neg["SUM 0-9"] == 0 and neg["HIGH SIZE"] == 0
                and neg["CONTROL SIZE"] == 0,
                "NEGATIVE CONTROL: on a new game every probe vector reads absent", str(neg))

    # 2. the writer seeds, and a bump makes a value only play can create
    g.warp(WRITER)
    seeded = _hud(g, WRITE_ROWS, want_header="VEC WRITE 30860")
    g.shot("2-writer-seeded")
    g.check(seeded == {"SIZE 4242": 10, "CELL 0": 1001, "CELL 3": 4004, "CELL 9": 10010,
                       "HIGH 0": 424242}, "the writer's Main_Init seeded both tables", str(seeded))
    g.watch(BUMP_FLAG)
    g.flag(BUMP_FLAG, True)
    # wait on the OUTCOME (the cell moved), never on "the flag was seen" -- the branch can consume
    # the flag inside one frame, so a flag-edge wait can pass before anything happened
    bumped = _hud(g, WRITE_ROWS, want_header="VEC WRITE 30860",
                  until=lambda v: v["CELL 3"] != 4004)
    g.wait_frames(45)                         # then give a repeating write time to show itself
    settled = _hud(g, WRITE_ROWS, want_header="VEC WRITE 30860")
    g.shot("3-writer-bumped")
    g.check(bumped is not None and bumped.get("CELL 3") == 4011,
            "one bump moved cell 3 from 4004 to 4011", str(bumped))
    g.check(settled is not None and settled.get("CELL 3") == 4011 and g.state.flag(BUMP_FLAG) is False,
            "...exactly once: the branch consumed its flag and the cell stayed put", str(settled))

    # 3. the nonce, then the reader: its field-entry autosave captures vectors + nonce
    nonce = random.randint(1, 255)
    g.poke(NONCE_BYTE, nonce)
    g.check(_read_nonce(g) == nonce, f"the nonce byte {NONCE_BYTE} holds {nonce}")
    g.warp(READER)
    live = _hud(g, READ_ROWS, want_header="VEC READ 30861")
    g.shot("4-reader-after-write")
    g.check(live == {"SIZE 4242": 10, "CELL 3": 4011, "SUM 0-9": 55062, "OTHER 9 OK": 1,
                     "HIGH 0": 424242, "HIGH SIZE": 2, "CONTROL SIZE": 0},
            "IN-SESSION: the reader sees the written vectors across a field change", str(live))

    # 4. OFFLINE: which container carries them
    g.wait_frames(30)
    extra = sandbox / "SavedData_ww_Memoria_Autosave.dat"
    main = sandbox / "SavedData_ww.dat"
    vecs = _save.read_extra_vectors(extra)
    print(f"[rung0] sandbox extra-save vectors: {vecs}")
    g.check(vecs is not None and vecs.get(T) == BUMPED and vecs.get(T_HIGH) == HIGH,
            "the autosave's Memoria EXTRA file holds tid 4242 (bumped) and tid 8400000",
            str(vecs))
    geg = _save.read_extra_gEventGlobal(extra)
    g.check(geg is not None and geg[NONCE_BYTE] == nonce, "the extra file's gEventGlobal holds the nonce",
            f"byte {NONCE_BYTE} = {geg[NONCE_BYTE] if geg else None}")
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps({
        "nonce": nonce, "extra_sha": _sha(extra), "main_sha": _sha(main),
        "write_run": str(g.run_dir),
    }, indent=2), encoding="utf-8")
    print(f"[rung0] state -> {STATE_FILE}")
    g.quit()                                  # quit to desktop -- the next phase is a fresh process


def phase_read(g) -> None:
    st0 = _load_state()
    sandbox = _sandbox(g)
    extra = sandbox / "SavedData_ww_Memoria_Autosave.dat"
    g.check(_sha(extra) == st0["extra_sha"] and _sha(sandbox / "SavedData_ww.dat") == st0["main_sha"],
            "the sandbox save on disk is exactly the one the WRITE launch produced")
    g.note("rung0 READ")
    _continue_from_title(g)
    g.wait_playable(timeout=60)
    g.check(g.state.field_id == READER, "Continue landed in the reader (the last autosave's field)",
            f"field {g.state.field_id}")
    nonce = _read_nonce(g)
    g.check(nonce == st0["nonce"], "the NONCE came back: this launch loaded the WRITE launch's save",
            f"read {nonce}, wrote {st0['nonce']}")
    got = _hud(g, READ_ROWS, want_header="VEC READ 30861")
    g.shot("5-reader-after-relaunch")
    g.check(got == {"SIZE 4242": 10, "CELL 3": 4011, "SUM 0-9": 55062, "OTHER 9 OK": 1,
                    "HIGH 0": 424242, "HIGH SIZE": 2, "CONTROL SIZE": 0},
            "RUNG 0: the vectors survived save -> quit -> relaunch -> load, bumped cell included",
            str(got))

    # the loaded vector is in MEMORY: the writer's entry autosave runs BEFORE its Main_Init re-seed
    g.warp(WRITER)
    vecs = _save.read_extra_vectors(extra)
    g.check(vecs is not None and vecs.get(T) == BUMPED,
            "the post-load autosave (taken before Main_Init) still holds cell 3 = 4011", str(vecs))
    reseeded = _hud(g, WRITE_ROWS, want_header="VEC WRITE 30860")
    g.shot("6-writer-reseeded-after-load")
    g.check(reseeded is not None and reseeded.get("CELL 3") == 4004,
            "the kit's re-seed law: the writer's Main_Init put cell 3 back to 4004", str(reseeded))
    # end in the READER, so the LOST launch's Continue lands where nothing can re-seed tid 4242
    g.warp(READER)
    g.wait_frames(30)
    g.check(g.state.field_id == READER, "READ ends in the reader (its entry autosave is LOST's save)")
    g.quit()


def phase_lost(g) -> None:
    st0 = _load_state()
    sandbox = _sandbox(g)
    extra = sandbox / "SavedData_ww_Memoria_Autosave.dat"
    parked = g.run_dir / "extra-parked"
    parked.mkdir(parents=True, exist_ok=True)
    moved = extra.exists()
    if moved:
        shutil.move(str(extra), str(parked / extra.name))
    g.check(moved, "the Memoria extra file was set aside before launch")
    try:
        g.note("rung0 LOST")
        _continue_from_title(g)
        g.wait_playable(timeout=60)
        nonce = _read_nonce(g)
        # READ ended in the reader, so its entry autosave is what Continue loads -- no warp
        # needed, and none is taken (a warp to the writer would re-seed tid 4242 and mask the loss)
        g.check(g.state.field_id == READER, "Continue landed in the reader", f"field {g.state.field_id}")
        g.check(nonce == st0["nonce"], "the main block alone restored gEventGlobal (the nonce)",
                f"read {nonce}, wrote {st0['nonce']}")
        got = _hud(g, READ_ROWS, want_header="VEC READ 30861")
        g.shot("7-reader-extra-lost")
        g.check(got is not None and got["SIZE 4242"] == 0 and got["HIGH SIZE"] == 0
                and got["SUM 0-9"] == 0,
                "CONTAINER VERDICT: with the extra file gone every vector loads EMPTY", str(got))
        g.check(g.state.control, "and the game still plays (degrades, does not break)")
        g.quit()
    finally:
        # Continue's field entry autosaves, so a NEW extra file (empty vectors) normally exists by
        # now and is left alone -- the sandbox is scratch. The pre-launch one stays in the run dir.
        restored = moved and not extra.exists()
        if restored:
            shutil.copy2(str(parked / extra.name), str(extra))
        print(f"[rung0] the pre-launch extra file is kept in {parked}"
              + (" and was restored" if restored else "; the sandbox now holds the post-load autosave"))


def run(g) -> None:
    if PHASE == "write":
        phase_write(g)
    elif PHASE == "read":
        phase_read(g)
    elif PHASE == "lost":
        phase_lost(g)
    else:
        raise SystemExit("set RUNG0_PHASE to write | read | lost")
