"""RUNG 1 of the persistent-tables arc -- the KIT FEATURE (`persist = true`) in the running game.

Rung 0 proved the engine keeps vectors across save -> quit -> relaunch -> load, and that the kit's
re-seed law erased them the moment the declaring field was entered. This proves the feature closes
that: a persistent table loaded back INTO ITS OWN DECLARING FIELD survives that field's Main_Init,
while an ordinary twin table in the same field re-seeds (proof Main_Init really ran).

Four launches, chained by the rung-0 nonce/state machinery:

    RUNG1_PHASE=write   py tools/play.py studies/persistent-tables/rung1_persist.py --label rung1-write
    RUNG1_PHASE=read    py tools/play.py studies/persistent-tables/rung1_persist.py --label rung1-read
    (deploy pwrite_v2 to 30862)
    RUNG1_PHASE=reshape py tools/play.py studies/persistent-tables/rung1_persist.py --label rung1-reshape
    RUNG1_PHASE=lost    py tools/play.py studies/persistent-tables/rung1_persist.py --label rung1-lost

Benches (bench/): pwrite.field.toml / pwrite_v2.field.toml at 30862 (memo persist id 6004242 +
ordinary twin eph id 4300 + levers), pread.field.toml at 30863 (declares no table).

WRITE    negative control -> seed -> bump (4011, eph 5012) -> THE FENCE (k parked at n, a
         counter-indexed write must not append an 11th cell) -> nonce -> reader -> RE-ENTER the
         writer: memo keeps 4011 while eph re-seeds to 5005 -> the sandbox extra decodes -> quit.
READ     fresh process, Continue lands IN THE WRITER: memo 4011 survives its own Main_Init, eph
         reads 5005 though the save held 5012 -> bump to 4018 -> round trip -> quit in the writer.
RESHAPE  v2 (11 cells) deployed over 30862 -> Continue: the length change re-seeds memo (4004,
         cell 10 = 11011, the v2 check word) -> bump -> reader sees V2 -> quit in the writer.
LOST     the extra file set aside -> Continue: the main block restores the nonce, memo degrades to
         its SEED (4004 though the save's extra held 4011), the game plays on.
"""
from __future__ import annotations

import json
import os
import random
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import rung0_persist as R0  # noqa: E402  (the calibrated rung-0 helpers: _hud, nonce, Continue)

REPO = R0.REPO
from ff9mapkit import save as _save  # noqa: E402
from ff9mapkit.content import behavior as B  # noqa: E402

WRITER, READER = 30862, 30863
BUMP, ARM_K, BUMP_K = 14867, 14868, 14869          # the benches' public flags (printed by the build)
T, G, EPH = 6004242, 7004242, 4300
SEED10 = [1001, 2002, 3003, 4004, 5005, 6006, 7007, 8008, 9009, 10010]
BUMPED = SEED10[:3] + [4011] + SEED10[4:]
W_V1, W_V2 = B.persist_check_word("memo", 10), B.persist_check_word("memo", 11)
STATE_FILE = REPO / ".harness-runs" / "rung1-persist-state.json"
PHASE = os.environ.get("RUNG1_PHASE", "").strip().lower()

# label -> the open-pass width sentinel of its slot (10**digits - 1), from each bench's `digits`
WRITE_ROWS = {"T SIZE": 99, "CELL 3": 99999, "CELL 9": 99999, "CELL 10": 99999,
              "CHECK OK": 9, "G SIZE": 9, "EPH 0": 99999, "KCOUNT": 99}
READ_ROWS = {"T SIZE": 99, "CELL 3": 99999, "G SIZE": 9, "CHECK V1": 9, "CHECK V2": 9, "EPH 0": 99999}


def _preflight(g) -> None:
    """Calibrate the instrument: the literals baked into the benches must be the formula's."""
    g.check((W_V1, W_V2) == (27929820, 27601081), "the check words are the pinned contract values",
            f"{W_V1}, {W_V2}")
    bench = HERE / "bench"
    g.check(str(W_V1) in (bench / "pwrite.field.toml").read_text(encoding="utf-8")
            and str(W_V2) in (bench / "pwrite_v2.field.toml").read_text(encoding="utf-8"),
            "each writer's CHECK OK literal is its own table's check word")


def _w(g, header, **kw):
    return R0._hud(g, WRITE_ROWS, want_header=header, **kw)


def _r(g, **kw):
    return R0._hud(g, READ_ROWS, want_header="P READ 30863", **kw)


def _raise(g, flag):
    g.watch(flag)
    g.flag(flag, True)


def _load_state() -> dict:
    return json.loads(STATE_FILE.read_text(encoding="utf-8"))


def _save_state(g, **extra) -> None:
    extra_file = R0._sandbox(g) / "SavedData_ww_Memoria_Autosave.dat"
    main = R0._sandbox(g) / "SavedData_ww.dat"
    st = {**(json.loads(STATE_FILE.read_text(encoding="utf-8")) if STATE_FILE.exists() else {}),
          **extra, "extra_sha": R0._sha(extra_file), "main_sha": R0._sha(main)}
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(st, indent=2), encoding="utf-8")


def _same_sandbox(g, st0) -> None:
    sb = R0._sandbox(g)
    g.check(R0._sha(sb / "SavedData_ww_Memoria_Autosave.dat") == st0["extra_sha"]
            and R0._sha(sb / "SavedData_ww.dat") == st0["main_sha"],
            "the sandbox save on disk is exactly the one the previous launch left")


# ------------------------------------------------------------------------------------------ phases
def phase_write(g) -> None:
    _preflight(g)
    sandbox = R0._sandbox(g)
    parked = g.run_dir / "sandbox-before"
    for p in sorted(sandbox.glob("SavedData_ww*.dat")):
        parked.mkdir(parents=True, exist_ok=True)
        shutil.move(str(p), str(parked / p.name))
    g.note("rung1 WRITE")
    g.newgame()

    g.warp(READER)
    neg = _r(g)
    g.shot("1-reader-new-game")
    g.check(neg == {"T SIZE": 0, "CELL 3": 0, "G SIZE": 0, "CHECK V1": 0, "CHECK V2": 0, "EPH 0": 0},
            "NEGATIVE CONTROL: on a new game neither memo, its guard nor eph exists", str(neg))

    g.warp(WRITER)
    seeded = _w(g, "P WRITE v1 30862")
    g.shot("2-writer-first-entry")
    g.check(seeded == {"T SIZE": 10, "CELL 3": 4004, "CELL 9": 10010, "CELL 10": 0, "CHECK OK": 1,
                       "G SIZE": 1, "EPH 0": 5005, "KCOUNT": 0},
            "first entry: the guard found nothing, seeded memo and wrote its check word; "
            "one past the end reads 0", str(seeded))

    _raise(g, BUMP)
    bumped = _w(g, "P WRITE v1 30862", until=lambda v: v["CELL 3"] != 4004)
    g.wait_frames(45)
    settled = _w(g, "P WRITE v1 30862")
    g.shot("3-writer-bumped")
    g.check(bumped is not None and bumped["CELL 3"] == 4011 and bumped["EPH 0"] == 5012,
            "the bump moved memo[3] to 4011 and eph[0] to 5012", str(bumped))
    g.check(settled is not None and settled["CELL 3"] == 4011 and g.state.flag(BUMP) is False,
            "...exactly once", str(settled))

    # THE FENCE: park k at exactly memo's length, then a counter-indexed write
    _raise(g, ARM_K)
    armed = _w(g, "P WRITE v1 30862", until=lambda v: v["KCOUNT"] == 10)
    g.check(armed is not None and armed["KCOUNT"] == 10, "k parked at 10 == memo's length", str(armed))
    _raise(g, BUMP_K)
    g.wait_for(lambda s: s.flag(BUMP_K) is False, timeout=15, what="bump_k to be consumed")
    g.wait_frames(45)
    fenced = _w(g, "P WRITE v1 30862")
    g.shot("4-writer-fence")
    g.check(fenced is not None and fenced["T SIZE"] == 10 and fenced["CELL 10"] == 0
            and fenced["CELL 3"] == 4011,
            "THE APPEND FENCE: memo[k] at k == n wrote nothing -- still 10 cells, cell 10 reads 0",
            str(fenced))

    nonce = random.randint(1, 255)
    g.poke(R0.NONCE_BYTE, nonce)
    g.check(R0._read_nonce(g) == nonce, f"nonce {nonce} poked")
    g.warp(READER)
    rd = _r(g)
    g.shot("5-reader-after-write")
    g.check(rd == {"T SIZE": 10, "CELL 3": 4011, "G SIZE": 1, "CHECK V1": 1, "CHECK V2": 0,
                   "EPH 0": 5012}, "the reader sees memo (and its v1 guard) and eph as play left them",
            str(rd))

    g.warp(WRITER)
    back = _w(g, "P WRITE v1 30862")
    g.shot("6-writer-reentered")
    g.check(back is not None and back["CELL 3"] == 4011 and back["CHECK OK"] == 1,
            "RE-ENTRY: the writer's own Main_Init KEPT memo (4011) -- rung 0 saw it wiped here",
            str(back))
    g.check(back is not None and back["EPH 0"] == 5005,
            "...while the SAME Main_Init re-seeded the ordinary twin (5012 -> 5005)", str(back))

    extra = sandbox / "SavedData_ww_Memoria_Autosave.dat"
    vecs = _save.read_extra_vectors(extra)
    g.check(vecs is not None and vecs.get(T) == BUMPED and vecs.get(G) == [W_V1]
            and vecs.get(EPH) == [5012],
            "the entry autosave (taken before Main_Init) holds memo, its guard word and eph=5012",
            str(vecs))
    geg = _save.read_extra_gEventGlobal(extra)
    g.check(geg is not None and geg[R0.NONCE_BYTE] == nonce, "...and the nonce")
    STATE_FILE.unlink(missing_ok=True)
    _save_state(g, nonce=nonce, write_run=str(g.run_dir))
    g.quit()


def phase_read(g) -> None:
    st0 = _load_state()
    _preflight(g)
    _same_sandbox(g, st0)
    g.note("rung1 READ")
    R0._continue_from_title(g)
    g.wait_playable(timeout=60)
    g.check(g.state.field_id == WRITER, "Continue landed IN THE WRITER", f"field {g.state.field_id}")
    g.check(R0._read_nonce(g) == st0["nonce"], "the nonce came back: the write launch's save loaded")
    got = _w(g, "P WRITE v1 30862")
    g.shot("7-writer-after-relaunch")
    g.check(got is not None and got["T SIZE"] == 10 and got["CELL 3"] == 4011
            and got["CHECK OK"] == 1 and got["CELL 10"] == 0,
            "RUNG 1: a save loaded INTO the declaring field -- memo survived that field's Main_Init",
            str(got))
    g.check(got is not None and got["EPH 0"] == 5005,
            "...and Main_Init DID run: the ordinary twin re-seeded (the save held 5012)", str(got))
    g.check(g.state.control, "the player has control")

    _raise(g, BUMP)
    b2 = _w(g, "P WRITE v1 30862", until=lambda v: v["CELL 3"] != 4011)
    g.check(b2 is not None and b2["CELL 3"] == 4018, "a post-load bump builds on the loaded value",
            str(b2))
    g.warp(READER)
    g.warp(WRITER)
    again = _w(g, "P WRITE v1 30862")
    g.shot("8-writer-round-trip")
    g.check(again is not None and again["CELL 3"] == 4018, "a round trip keeps 4018", str(again))
    _save_state(g, read_run=str(g.run_dir))
    g.quit()


def phase_reshape(g) -> None:
    st0 = _load_state()
    _preflight(g)
    _same_sandbox(g, st0)
    g.note("rung1 RESHAPE (v2 deployed: 11 cells)")
    R0._continue_from_title(g)
    g.wait_playable(timeout=60)
    g.check(g.state.field_id == WRITER, "Continue landed in the writer", f"field {g.state.field_id}")
    v2 = _w(g, "P WRITE v2 30862")
    g.shot("9-writer-v2-reshaped")
    g.check(v2 == {"T SIZE": 11, "CELL 3": 4004, "CELL 9": 10010, "CELL 10": 11011, "CHECK OK": 1,
                   "G SIZE": 1, "EPH 0": 5005, "KCOUNT": 0},
            "RESHAPE: a length change is a new identity -- memo re-seeded to the v2 shape (4018 is "
            "gone by design) under the v2 check word", str(v2))
    _raise(g, BUMP)
    b = _w(g, "P WRITE v2 30862", until=lambda v: v["CELL 3"] != 4004)
    g.check(b is not None and b["CELL 3"] == 4011, "the v2 table takes writes", str(b))
    g.warp(READER)
    rd = _r(g)
    g.check(rd is not None and rd["T SIZE"] == 11 and rd["CHECK V1"] == 0 and rd["CHECK V2"] == 1,
            "the reader sees the v2 guard word and 11 cells", str(rd))
    vecs = _save.read_extra_vectors(R0._sandbox(g) / "SavedData_ww_Memoria_Autosave.dat")
    g.check(vecs is not None and len(vecs.get(T, [])) == 11 and vecs.get(G) == [W_V2],
            "the autosave carries the reshaped table and its v2 word", str(vecs))
    g.warp(WRITER)
    _save_state(g, reshape_run=str(g.run_dir))
    g.quit()


def phase_lost(g) -> None:
    st0 = _load_state()
    _preflight(g)
    _same_sandbox(g, st0)
    sandbox = R0._sandbox(g)
    extra = sandbox / "SavedData_ww_Memoria_Autosave.dat"
    vecs_before = _save.read_extra_vectors(extra)
    g.check(vecs_before is not None and vecs_before.get(T, [0] * 4)[3] == 4011,
            "the extra file being set aside holds memo[3] = 4011", str(vecs_before))
    parked = g.run_dir / "extra-parked"
    parked.mkdir(parents=True, exist_ok=True)
    shutil.move(str(extra), str(parked / extra.name))
    g.note("rung1 LOST")
    R0._continue_from_title(g)
    g.wait_playable(timeout=60)
    g.check(g.state.field_id == WRITER, "Continue landed in the writer", f"field {g.state.field_id}")
    g.check(R0._read_nonce(g) == st0["nonce"], "the main block alone restored gEventGlobal (the nonce)")
    got = _w(g, "P WRITE v2 30862")
    g.shot("10-writer-extra-lost")
    g.check(got is not None and got["T SIZE"] == 11 and got["CELL 3"] == 4004 and got["CHECK OK"] == 1,
            "DEGRADE: with the extra file gone memo re-seeds to its SEED (4004, not the 4011 the lost "
            "file held) -- enrichment, never a gate", str(got))
    g.check(g.state.control, "and the game plays on")
    g.quit()


def run(g) -> None:
    {"write": phase_write, "read": phase_read, "reshape": phase_reshape,
     "lost": phase_lost}.get(PHASE, lambda _g: (_ for _ in ()).throw(
         SystemExit("set RUNG1_PHASE to write | read | reshape | lost")))(g)
