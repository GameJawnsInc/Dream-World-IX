"""PREP for the in-game check of the ENTRANCE GUARD's premise (terrain study defect 6), 2026-10-08. NO DEPLOY: the
reshape dry-runs read stock through an EMPTY scratch mod folder.

THE QUESTION. `mesh.entrance_guard` refuses raising ground more than 1.17u within 8u of an entrance tile or a stock
door arrival. Its premise: the world sets the player down at the HEIGHT stored in the position record
(WORLD09 e13 tag0 `MoveInstantXZY(Int24[64], Int16[67], Int24[69])`), and the foot walk ray, starting 2.34375u above
the player, then misses ground raised past that: frozen (the Dali freeze, commit 3e388d0d, 2026-07-01). Against it:
  * the engine re-grounds every world actor FROM THE SKY on each world load: `w_frameMainRoutine`
    (ff9.cs:3700-3705) runs `LoadBlocks(false)` (every block, synchronously IsReady, WMWorld.cs:1228-1232) and then
    `w_movementChrInitSlice` (ff9.cs:4596: CastRayFromSky + UseInfiniteRaycast, `w_movementSetheight`);
  * every stock exit that writes the record writes y too, as -ground*256 (Dali stores -6803 = its ground 26.578);
    field 6603's kit exit stores +1024 (world -4.0) over ground 3.2, and every harness arrival there published
    y 3.199 BEFORE any input (veh sessions 2, d9 loops).
H-SKY: the player lands ON the new ground (published y = new ground at the first settled read, no input) and walks.
H-RECORD: the player lands at the stored height (the stock ground) and, under ground raised past the ray start, cannot
move in any direction.

This screens the 43 stock door arrivals (`gap_inplace_stitch_composition/out/door_arrivals.json`) for a test site:
  * no live override within one block (the lab must be the only edit there);
  * the kit's own reshape at r16 centred on the arrival passes every gate with --allow-entrances for each phase amount
    (+4: past the 2.34375 ray start by 1.66u; +1: under the guard's 1.17; -3: lowering);
  * the stored y equals the stock ground (the H-RECORD premise holds there);
  * open walkable ground around it (topographs in placement.WALK_OK on rings r 4/8/12).
Writes out/guard_prep.json.
Run:  py studies/terrain-malleability/ingame/guard_prep.py
"""
from __future__ import annotations

import json
import math
import struct
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
TM = HERE.parent
sys.path.insert(0, str(TM / "gap_area_layer"))
sys.path.insert(0, str(TM / "gap_inplace_stitch_composition"))
sys.path.insert(0, str(HERE))
import arealib as A                                  # noqa: E402
import disc4_prep as P                               # noqa: E402
import door_arrivals as DA                           # noqa: E402
from ff9mapkit import _fieldtable as FT              # noqa: E402
from ff9mapkit import extract as FX                  # noqa: E402
from ff9mapkit.world import terrain as TER           # noqa: E402
from ff9mapkit.world.placement import WALK_OK        # noqa: E402

P.DISC = 1
AMOUNTS = (4.0, 1.0, -3.0)
RADIUS = 16.0


def event_fields() -> dict:
    """event-script name (lower, no extension) -> [field id, ...]"""
    out = {}
    for t in (v for v in vars(FT).values() if isinstance(v, dict)):
        for k, v in t.items():
            if isinstance(v, (list, tuple)) and len(v) >= 2 and isinstance(v[1], str) and isinstance(v[0], int):
                out.setdefault(v[1].lower(), set()).add(int(v[0]))
            elif isinstance(v, (list, tuple)) and len(v) >= 2 and isinstance(v[0], str) and isinstance(v[1], int):
                out.setdefault(str(k).lower(), set())
    return {k: sorted(s) for k, s in out.items() if s}


def stored_heights() -> dict:
    """(x, z) -> {event: stored world y} from every stock record write (door_arrivals' own regex)."""
    env = FX._load_env(FX._streaming_assets(A.GAME) / FX._events_bundle(A.GAME))
    out = {}
    for k, obj in env.container.items():
        kl = k.lower()
        if "eventbinary/field/us/" not in kl or not kl.endswith(".eb.bytes"):
            continue
        data = FX._raw_bytes(obj.read())
        evt = kl.rsplit("/", 1)[1][:-len(".eb.bytes")]
        ws = DA.writes(data)
        for ox, vx in [(o, v) for o, var, v in ws if var == (0xC8, 0x40)]:
            vy = next((v for o, var, v in ws if var == (0xD8, 0x43) and o > ox), None)
            vz = next((v for o, var, v in ws if var == (0xC8, 0x45) and o > ox), None)
            if vz is None:
                continue
            key = (round(vx / 256.0, 3), round(vz / 256.0, 3))
            out.setdefault(key, {})[evt] = None if vy is None else round(-vy / 256.0, 3)
    return out


def openness(x, z) -> dict:
    rings = {}
    for r in (4, 8, 12):
        ok = 0
        for k in range(12):
            a = 2 * math.pi * k / 12
            g = P.ground(x + r * math.cos(a), z + r * math.sin(a))
            ok += int(g["topo"] is not None and g["topo"] in WALK_OK and not g["event"])
        rings[r] = ok
    return rings


def main():
    import ff9mapkit
    assert "Dream-World-IX" in ff9mapkit.__file__, ff9mapkit.__file__
    arr = json.loads((TM / "gap_inplace_stitch_composition/out/door_arrivals.json").read_text(encoding="utf-8"))
    ef = event_fields()
    ys = stored_heights()
    live = A.live_cells()
    rows = []
    with tempfile.TemporaryDirectory() as empty:
        for a in arr["arrivals"]:
            x, z = a["x"], a["z"]
            bx, by = a["block"]
            near_live = sorted({f"{ns}:{cx},{cy}" for (ns, cx, cy) in live
                                if ns in (1, 4) and abs(cx - bx) <= 1 and abs(cy - by) <= 1})
            g = P.ground(x, z)
            stored = ys.get((round(x, 3), round(z, 3)), {})
            dry = {}
            for amt in AMOUNTS:
                try:
                    s = TER.reshape(empty, radius=RADIUS, at=(x, z), amount=amt, dry_run=True, allow_entrances=True,
                                    game=A.GAME)
                    dry[f"{amt:+g}"] = {"ok": True, "blocks": [b["block"] for b in s["blocks"]],
                                        "pinned": s.get("pinned"), "torn": s["stitch"]["torn"],
                                        "entrance_hits": len(s.get("entrances") or [])}
                except Exception as e:                                          # noqa: BLE001
                    dry[f"{amt:+g}"] = {"ok": False, "why": f"{type(e).__name__}: {str(e)[:200]}"}
            fields = sorted({fid for ev in stored for fid in ef.get(ev.replace("evt_", "evt_"), [])}
                            | {fid for ev in a["events"] for fid in ef.get(ev, [])})
            row = {"x": x, "z": z, "block": [bx, by], "events": a["events"], "fields": fields,
                   "stored_y": stored, "ground": g, "near_live": near_live,
                   "nearest_entrance_tile": a["nearest_entrance_tile"], "open": openness(x, z), "dry": dry}
            row["eligible"] = (not near_live and all(d["ok"] for d in dry.values())
                               and g["topo"] in WALK_OK
                               and all(v is not None and abs(v - g["y"]) <= 0.1 for v in stored.values())
                               and sum(row["open"].values()) >= 30)
            rows.append(row)
            print(f"({x:8.2f},{z:9.2f}) {str(fields):18s} ground {g['y']} topo {g['topo']} stored "
                  f"{sorted(set(stored.values()))} live {near_live[:3]} open {row['open']} "
                  + " ".join(f"{k}:{'ok' if d['ok'] else 'NO'}" for k, d in dry.items())
                  + ("  <-- ELIGIBLE" if row["eligible"] else ""), flush=True)
    out = HERE / "out"
    out.mkdir(exist_ok=True)
    (out / "guard_prep.json").write_text(json.dumps({"radius": RADIUS, "amounts": AMOUNTS, "rows": rows},
                                                    indent=1, default=str), encoding="utf-8")
    print("eligible:", sum(r["eligible"] for r in rows), "->", out / "guard_prep.json")


if __name__ == "__main__":
    main()
