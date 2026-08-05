#!/usr/bin/env python
"""Splice the world-9013 jump into PATHDGATE's DEPLOYED event scripts (Path D, rung 6).

WHY THIS EXISTS
---------------
No declarative `field.toml` surface can express "warp to world 9013":

* `[[gateway]] to = <id>` compiles to `Field()` (opcode 0x2B) -- a FIELD warp.
* `[[gateway]] to = "worldmap"` compiles to the VERBATIM shared exit cascade
  (`content/worldexit.py`), which routes only the thirteen stock `wldMapNo`s
  (9000-9012) through `(ScenarioCounter band) x (region key D8:2)`. 9013 is a
  Dream-World-IX custom world id (s73's 9013-9099 band); no cascade arm emits it.

So the field ships gateway-less and this script appends ONE tread region carrying the
single-target form `WorldMap(9013)` (opcode 0xB6 -- `encode(0xB6, 9013)`; see
`eb/opcodes.py:514`) after the deterministic-arrival preset. It is post-deploy surgery on
the deployed `.eb.bytes`, run once per deploy of the field, for all seven locales.

⚠ Run it AFTER `deploy_field.py`. A re-deploy overwrites the `.eb` files and drops the
region -- re-run this script every time (it is idempotent, so re-running when nothing was
overwritten is a no-op).

THE BODY (exactly what gets appended as the region's Range/tag-2 trigger)
------------------------------------------------------------------------
    region.MOVEMENT_GATE                       ifnot (IsMovementEnabled) { return }
    worldexit.exit_fade()                      DisableMove; FadeFilter(6,24,white); Wait(25)
    worldexit.arrive_writes(x, z, face=f)      preset BOTH world player-objects' persisted
                                               position records (on-foot C8:0x40/D8:0x43/
                                               C8:0x45/D4:0x48 and vehicle C8:0x53/...)
    region.set_field_entrance(35)              D8:2 = POSITION_PRESET_KEY (NONZERO)
    opcodes.world_map(9013)                    WorldMap(9013)  <- the transition
    opcodes.terminate_entry(255)               KILL(This) -- the unreachable safety tail

The `D8:2 = 35` write is the load-bearing half of the arrival: WORLD13's entry-14 tag-0
reads `Global.Int16[2]`; **zero** makes it stamp stock WORLD11's default point over our
coordinates, **nonzero** makes it leave the record alone and `MoveInstantXZY` straight to
it. 35 is chosen (not any nonzero) because it is the one real disc-1 key whose cascade
arms are bare `WorldMap`s that do NOT re-zero D8:2 -- see `content/worldexit.py:66-76`.

MOVEMENT_GATE is correct here and MUST stay: this is a REGION (tread) context, not a talk
or menu context. In a talk handler the gate takes its early return and softlocks the
player (`worldexit.py:244-254`).

VERIFY-BEFORE-WRITE
-------------------
Nothing is written until the patched bytes pass, in memory:
  1. `EbScript.from_bytes` parses the whole container and every entry lies inside the file;
  2. every function of every non-empty entry decodes cleanly and its last instruction ends
     EXACTLY on the function boundary (an overrun is how a bad splice hides --
     `disasm.iter_code` stops at `end` and would otherwise swallow it);
  3. exactly one `WorldMap` op exists in the file, and its operand is the target world;
  4. the new entry carries a tag-0 `SetRegion` with our polygon and a tag-2 body byte-equal
     to the body above;
  5. Main_Init carries the arming `InitRegion(slot, 0)`;
  6. the check is BASELINE-RELATIVE: the same decode is run on the ORIGINAL bytes first and
     the patched file must introduce no problem the original did not already have;
  7. THE NON-DESTRUCTIVE INVARIANT -- every pre-existing function decodes to a BYTE-FOR-BYTE
     identical instruction stream afterwards, the only licensed differences being the two new
     functions of the region entry and Main_Init gaining exactly one `InitRegion(slot, 0)`.
     (4) and (5) prove what was ADDED; only (7) proves nothing else MOVED, and moving is the
     real hazard here -- when a field's content has already eaten both `Wait(2)` fillers the
     activation takes the INSERT path and re-points every following entry offset and func
     `fpos`, a fix-up that has silently mis-armed a region before (`eb/edit.py:576-581`).

SCOPE, stated honestly: this verifies that THIS SPLICE is well-formed and non-destructive.
It cannot certify bytes it did not write -- a `.eb` that was already corrupt goes in corrupt
and comes out corrupt, and almost any byte stream decodes as *something*. Run
`ff9mapkit lint-eb` on the deployed file for that (README step 3); the expected output is
exactly one pre-existing `entry0/tag1: empty function body`, and nothing else.

  ⚠ (6) is not slack, it is the only honest form of the check. The kit's blank-field
  template -- the start of EVERY synthesized field, all seven locales -- declares entry 0's
  slot size 65 bytes SHORT of where its own tag-1 func table entry points (blank: entry 0
  = [208..572], tag-1 `fpos` -> 637, and 637 really does hold that function's one-byte
  `RETURN`). `EbScript` bounds a last function by the entry's declared end, so that one
  function models as a NEGATIVE-length range and can never "decode to its boundary". It is
  reported as a DEGENERATE range, not a failure, and the degenerate set must come out of the
  splice unchanged. A blanket "every function decodes to its end" would refuse every field
  the kit has ever built -- a check that cannot pass is as useless as one that cannot fail.
  The kit's own source form names the same bytes: `eb-src` renders that tail as
  `.gap ... # gap: bytes covered by NO entry's declared span -- live code the engine reaches
  by func fpos, kept verbatim`. Independent corroboration that the splice is clean:
  `lint-eb` reports the IDENTICAL single `entry0/tag1: empty function body` error on the
  untouched blank template, on the unpatched build, and on the patched build (this splice
  adds zero findings), and the patched binary round-trips `eb-src` -> `eb-asm` BYTE-EXACT.

Idempotency: a file that already carries a `WorldMap` op is SKIPPED (reported, not
patched, exit 0), so re-running after a partial run or a no-op deploy is safe.

USAGE
-----
    py inject_worldjump.py --dry-run          # decode + verify, write nothing
    py inject_worldjump.py                    # patch the live FF9CustomMap deploy
    py inject_worldjump.py --mod-folder <dir> --backup-dir <dir> --print-disasm
"""

from __future__ import annotations

import argparse
import datetime as _dt
import os
import shutil
import sys
from pathlib import Path

# --------------------------------------------------------------------------------------
# the site spec (studies/path-d-new-world/rung6/site.json -- the site-selection pass)
# --------------------------------------------------------------------------------------
WORLD_ID = 9013                 # Path D, registered as `WorldScene 9013 WORLD13` in FF9CustomMap-world

#: the landing point on the V-shore bench island, blocks (5..7, 7..8) -- cell (13,14),
#: block (6,7). 1u-sampled clean grass: y 3.200, topograph 0 (GRASS), walkable, 0.0000u
#: relief over a 5x5u box, 13u radial clearance to the nearest non-walkable/water, ONE
#: walkable sheet on the vertical line (no stack).
LANDING_X = 425.0
LANDING_Z = -479.0
#: facing byte 224 = south-east under the kit compass (0=S, 64=W, 128=N, 192=E;
#: `(dx,dz) = (-sin(f/256*2pi), -cos(f/256*2pi))` -> (+0.707,-0.707)) -- straight down the
#: EAST walking corridor toward the exit cell. Plain 0 (south) would aim the player at the
#: island's central massif 9u ahead.
LANDING_FACE = 224
#: the y the position record is seeded with. It is a SEED ONLY -- the world actor
#: re-grounds on its next movement tick -- so it is deliberately left at `arrive_writes`'
#: own default 4.0, i.e. 0.8u ABOVE the measured 3.200 lawn, so the ground query drops onto
#: the terrain instead of starting inside it.
LANDING_Y_SEED = 4.0

# --------------------------------------------------------------------------------------
# the field side
# --------------------------------------------------------------------------------------
FIELD_NAME = "PATHDGATE"        # -> EVT_PATHDGATE.eb.bytes
FIELD_ID = 30950
LANGS = ("us", "uk", "jp", "fr", "gr", "it", "es")

#: The tread zone, in the field's world frame. KEEP IN SYNC with the header comment of
#: `pathdgate.field.toml` (the toml cannot own it -- there is no gateway block).
#:
#: Edge order is the gateway edge-order law (`content/gateway.py:11-12`): **q0 -> q1 is the
#: edge the player walks OUT across**, so the far/front edge (z = -1900, toward the camera)
#: comes first. FRONT = toward the camera = NEGATIVE z.
#:
#: The walkmesh front edge is z = -1931 and the controller radius is 80u, so the player's
#: centre can never get past z = -1851: the strip covers every reachable point at the room's
#: front and cannot be skirted along z. It CAN be walked around at |x| > 600 -- deliberate,
#: so the pad is a door the player chooses, not an invisible wall.
ZONE_CORNERS = [(-600, -1900), (600, -1900), (600, -1500), (-600, -1500)]

DEFAULT_MOD_FOLDER = Path(r"C:\Program Files (x86)\Steam\steamapps\common"
                          r"\FINAL FANTASY IX\FF9CustomMap")
#: Backups go to the MAIN repo, never a `__file__`-rooted dir under this worktree --
#: a worktree is deleted when its branch merges and would take the only copy of the
#: pre-patch install bytes with it ([[project-ff9-worktree-parked-backups]]).
DEFAULT_BACKUP_ROOT = Path(r"C:\gd\Dream-World-IX\backups\rung6-pathdgate")

EB_RELDIR = Path("StreamingAssets/assets/resources/commonasset/eventengine/eventbinary/field")


# --------------------------------------------------------------------------------------
# import bootstrap -- find the ff9mapkit package root without needing it installed
# --------------------------------------------------------------------------------------
def _bootstrap() -> None:
    env = os.environ.get("FF9MAPKIT_ROOT")
    cands = [Path(env)] if env else []
    here = Path(__file__).resolve()
    # .../<worktree>/studies/path-d-new-world/rung6/fieldside/inject_worldjump.py
    cands += [p / "ff9mapkit" for p in here.parents]
    for c in cands:
        if (c / "ff9mapkit" / "__init__.py").is_file():
            sys.path.insert(0, str(c))
            return
    raise SystemExit("cannot locate the ff9mapkit package root; set $FF9MAPKIT_ROOT")


_bootstrap()

from ff9mapkit.content import region as R                      # noqa: E402
from ff9mapkit.content import worldexit as WX                  # noqa: E402
from ff9mapkit.eb import EbScript, opcodes as O                # noqa: E402

WORLDMAP_OP = 0xB6                      # WMAPJUMP
INITREGION_OP = 0x08                    # InitRegion(slot, arg)
WAIT_OP = 0x22


# --------------------------------------------------------------------------------------
def range_body(world_id: int = WORLD_ID, x: float = LANDING_X, z: float = LANDING_Z,
               face: int = LANDING_FACE, y: float = LANDING_Y_SEED) -> bytes:
    """The tread trigger's Range (tag-2) body -- see the module docstring."""
    return (R.MOVEMENT_GATE
            + WX.exit_fade()
            + WX.arrive_writes(float(x), float(z), y=float(y), face=int(face))
            + R.set_field_entrance(WX.POSITION_PRESET_KEY)
            + O.world_map(int(world_id))
            + O.terminate_entry(255))


def zone_points(corners=ZONE_CORNERS) -> list:
    """5-point IsInQuad-safe polygon (convex quad + doubled last vertex): the engine fans
    consecutive vertex triplets, and the kit's own build takes this path for every authored
    4-corner zone (`build.py:6276-6277` -> `gateway.quad_zone`)."""
    from ff9mapkit.content.gateway import quad_zone
    return quad_zone([tuple(c) for c in corners])


# --------------------------------------------------------------------------------------
# decode helpers
# --------------------------------------------------------------------------------------
def _iter_funcs(eb: EbScript):
    for e in eb.entries:
        if e.empty:
            continue
        for f in e.funcs:
            yield e, f


def decode_report(data: bytes) -> tuple[list, list, list]:
    """Decode every function.

    Returns ``(problems, degenerate, worldmaps)``:
      * ``problems``  -- hard failures (a function that raises, overruns, or stops short of
                         its boundary), each a human string;
      * ``degenerate`` -- ``(entry_index, func_tag)`` for a function the CONTAINER cannot
                         bound (``abs_end <= abs_start``): the blank template's entry-0
                         tag-1 quirk documented in the module docstring. Never decoded,
                         never a failure -- but the set must be identical before and after;
      * ``worldmaps`` -- ``(entry_index, func_tag, operand_or_None)`` per ``WorldMap`` op.
    """
    problems: list = []
    degenerate: list = []
    worldmaps: list = []
    try:
        eb = EbScript.from_bytes(data)
    except Exception as exc:                                    # noqa: BLE001
        return [f"container will not parse: {exc!r}"], [], []
    for e in eb.entries:
        if e.empty:
            continue
        if not (0 < e.abs_start <= e.abs_end <= len(data)):
            problems.append(f"entry {e.index}: extent [{e.abs_start}..{e.abs_end}] "
                            f"is outside the {len(data)}-byte file")
    for e, f in _iter_funcs(eb):
        if f.abs_end <= f.abs_start:
            degenerate.append((e.index, f.tag))
            continue
        if f.abs_end > len(data):
            problems.append(f"entry {e.index} tag {f.tag}: ends at {f.abs_end}, past EOF {len(data)}")
            continue
        last_end = f.abs_start
        try:
            for ins in eb.instrs(f):
                last_end = ins.end
                if ins.op == WORLDMAP_OP:
                    worldmaps.append((e.index, f.tag, ins.imm(0)))
        except Exception as exc:                                # noqa: BLE001
            problems.append(f"entry {e.index} tag {f.tag}: decode raised {exc!r}")
            continue
        if last_end != f.abs_end:
            problems.append(f"entry {e.index} tag {f.tag}: decode ended at {last_end}, "
                            f"function boundary is {f.abs_end} "
                            f"({'OVERRUN' if last_end > f.abs_end else 'short'})")
    return problems, degenerate, worldmaps


def instr_signature(data: bytes) -> dict:
    """``{(entry_index, func_tag): [(op, args...), ...]}`` for every container-bounded
    function -- a decode-level fingerprint that ignores byte OFFSETS. Two files with the
    same signature run the same code even though the splice moved every entry."""
    sig: dict = {}
    eb = EbScript.from_bytes(data)
    for e, f in _iter_funcs(eb):
        if f.abs_end <= f.abs_start:
            continue                                            # degenerate: handled separately
        sig[(e.index, f.tag)] = [(i.op, tuple(str(a) for a in i.args)) for i in eb.instrs(f)]
    return sig


def preservation_failures(before: bytes, after: bytes, *, slot: int) -> list:
    """THE NON-DESTRUCTIVE INVARIANT.

    A splice that decodes cleanly can still be wrong: `activate` either overwrites a
    Main_Init `Wait(2)` filler (shift-free) or, when the field's content already ate both
    fillers, INSERTS the `InitRegion` and re-points every following entry offset and func
    `fpos`. That fix-up path has been wrong before -- it once left a 3rd+ region silently
    un-armed because a raw insert left other funcs' `fpos` stale (`eb/edit.py:576-581`).
    A structural decode cannot see that; only a before/after comparison can.

    So: every pre-existing function must decode to the IDENTICAL instruction stream
    afterwards, with exactly two licensed differences --
      * the two brand-new functions of the region entry in ``slot``, and
      * Main_Init (entry 0, tag 0) gaining exactly one ``InitRegion(slot, 0)``, either
        inserted (insert path) or replacing one ``Wait(2)`` filler (shift-free path).
    """
    fails: list = []
    b_sig, a_sig = instr_signature(before), instr_signature(after)

    added = set(a_sig) - set(b_sig)
    removed = set(b_sig) - set(a_sig)
    if removed:
        fails.append(f"the splice DROPPED pre-existing function(s) {sorted(removed)!r}")
    want_added = {(slot, 0), (slot, R.RANGE_TAG)}
    if added != want_added:
        fails.append(f"unexpected new function set {sorted(added)!r} (wanted {sorted(want_added)!r})")

    init_sig = (INITREGION_OP, (str(slot), "0"))
    wait2_sig = (WAIT_OP, ("2",))
    for key in sorted(set(b_sig) & set(a_sig)):
        b, a = b_sig[key], a_sig[key]
        if key != (0, 0):
            if a != b:
                fails.append(f"pre-existing entry {key[0]} tag {key[1]} CHANGED across the splice "
                             f"({len(b)} -> {len(a)} instructions)")
            continue
        # Main_Init: exactly one InitRegion(slot, 0) appears, and nothing else moves
        if a.count(init_sig) != 1 or b.count(init_sig) != 0:
            fails.append(f"Main_Init should gain exactly one InitRegion({slot}, 0); "
                         f"before={b.count(init_sig)} after={a.count(init_sig)}")
            continue
        a2 = [x for x in a if x != init_sig]
        if a2 == b:
            continue                                            # insert path
        drops = [b[:i] + b[i + 1:] for i, x in enumerate(b) if x == wait2_sig]
        if any(a2 == d for d in drops):
            continue                                            # shift-free Wait(2)-overwrite path
        fails.append("Main_Init changed beyond adding the InitRegion (and, on the shift-free "
                     "path, consuming one Wait(2) filler)")
    return fails


def disasm_text(data: bytes, only_entry: int | None = None) -> str:
    out: list[str] = []
    eb = EbScript.from_bytes(data)
    out.append(f"=== size={len(eb.data)} entries={eb.entry_count} ===")
    for e in eb.entries:
        if e.empty or (only_entry is not None and e.index != only_entry):
            continue
        out.append(f"ENTRY {e.index}: off={e.off} sz={e.size} type={e.type} "
                   f"funcs={[f.tag for f in e.funcs]}  [{e.abs_start}..{e.abs_end}]")
        for f in e.funcs:
            out.append(f"  --- func{f.index} tag={f.tag} [{f.abs_start}..{f.abs_end}]")
            for ins in eb.instrs(f):
                out.append(f"    {ins}")
    return "\n".join(out)


# --------------------------------------------------------------------------------------
def patch_bytes(data: bytes, *, world_id: int, x: float, z: float, face: int, y: float,
                corners) -> tuple[bytes, int, bytes]:
    """Append the world-jump region. Returns ``(new_bytes, slot, body)``.

    `inject_region` seats a type-1 entry (tag 0 = `SetRegion(zone)` + return, tag 2 = the
    trigger) into the first free slot and ARMS it from Main_Init -- overwriting a `Wait(2)`
    filler when one is free, else inserting the `InitRegion` through the fpos-fixing insert
    (`eb/edit.py:568-596`).
    """
    body = range_body(world_id, x, z, face, y)
    out, slot = R.inject_region(data, zone_points(corners), body)
    return out, slot, body


def verify(new: bytes, *, old: bytes, slot: int, body: bytes, world_id: int, corners,
           baseline_degenerate: list) -> list:
    """Every check named in the module docstring. Returns a list of failure strings."""
    fails: list = []
    problems, degenerate, worldmaps = decode_report(new)
    fails += problems
    fails += preservation_failures(old, new, slot=slot)

    if sorted(degenerate) != sorted(baseline_degenerate):
        fails.append(f"the container-unbounded (degenerate) function set CHANGED across the "
                     f"splice: before {sorted(baseline_degenerate)!r}, after {sorted(degenerate)!r}")

    hits = [w for w in worldmaps if w[2] == world_id]
    if len(worldmaps) != 1 or len(hits) != 1:
        fails.append(f"expected exactly one WorldMap({world_id}); found {worldmaps!r}")

    try:
        eb = EbScript.from_bytes(new)
    except Exception as exc:                                    # noqa: BLE001
        fails.append(f"re-parse failed: {exc!r}")
        return fails

    if slot >= eb.entry_count or eb.entry(slot).empty:
        fails.append(f"slot {slot} is not a live entry after the splice")
        return fails
    ent = eb.entry(slot)
    if ent.type != R.REGION_ENTRY_TYPE:
        fails.append(f"slot {slot} entry type is {ent.type}, expected {R.REGION_ENTRY_TYPE} (region)")

    init = ent.func_by_tag(0)
    rng = ent.func_by_tag(R.RANGE_TAG)
    if init is None or rng is None:
        fails.append(f"slot {slot} is missing tag 0 and/or tag {R.RANGE_TAG}")
        return fails

    want_region = R.set_region(zone_points(corners))
    if new[init.abs_start:init.abs_start + len(want_region)] != want_region:
        fails.append(f"slot {slot} tag 0 does not open with the expected SetRegion polygon")
    got_body = new[rng.abs_start:rng.abs_end]
    if got_body != body:
        fails.append(f"slot {slot} tag {R.RANGE_TAG} body differs from the authored body "
                     f"({len(got_body)} B vs {len(body)} B)")

    # the arming call must be reachable from Main_Init (entry 0, tag 0)
    main = eb.entry(0).func_by_tag(0)
    if main is None:
        fails.append("entry 0 has no Main_Init")
    else:
        armed = any(i.op == INITREGION_OP and i.imm(0) == slot for i in eb.instrs(main))
        if not armed:
            fails.append(f"Main_Init carries no InitRegion({slot}, 0) -- the region would never arm")
    return fails


# --------------------------------------------------------------------------------------
def eb_path(mod_folder: Path, lang: str, field_name: str) -> Path:
    return mod_folder / EB_RELDIR / lang / f"EVT_{field_name}.eb.bytes"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--mod-folder", type=Path, default=DEFAULT_MOD_FOLDER,
                    help=f"deployed mod root (default: {DEFAULT_MOD_FOLDER})")
    ap.add_argument("--field-name", default=FIELD_NAME, help="field base name (EVT_<name>.eb.bytes)")
    ap.add_argument("--langs", default=",".join(LANGS), help="comma-separated locales")
    ap.add_argument("--world-id", type=int, default=WORLD_ID)
    ap.add_argument("--landing", nargs=2, type=float, metavar=("X", "Z"),
                    default=[LANDING_X, LANDING_Z])
    ap.add_argument("--face", type=int, default=LANDING_FACE)
    ap.add_argument("--y-seed", type=float, default=LANDING_Y_SEED)
    ap.add_argument("--dry-run", action="store_true",
                    help="decode, patch in memory, verify -- write NOTHING (no backups either)")
    ap.add_argument("--backup-dir", type=Path, default=None,
                    help=f"where to copy the pre-patch bytes (default: "
                         f"{DEFAULT_BACKUP_ROOT}\\<UTC timestamp>)")
    ap.add_argument("--print-disasm", action="store_true",
                    help="print the injected entry's disassembly for each locale")
    ap.add_argument("--print-disasm-once", action="store_true",
                    help="print the injected entry's disassembly for the FIRST locale only")
    args = ap.parse_args(argv)

    langs = [s.strip() for s in args.langs.split(",") if s.strip()]
    x, z = args.landing
    stamp = _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_root = args.backup_dir or (DEFAULT_BACKUP_ROOT / stamp)

    print(f"inject_worldjump: field EVT_{args.field_name}  ->  WorldMap({args.world_id})")
    print(f"  mod folder : {args.mod_folder}")
    print(f"  landing    : x={x} z={z} face={args.face} (y seed {args.y_seed})")
    print(f"  zone       : {ZONE_CORNERS}  (q0->q1 = the walk-out edge)")
    print(f"  mode       : {'DRY RUN (no writes)' if args.dry_run else 'WRITE'}")
    if not args.dry_run:
        print(f"  backups    : {backup_root}")
    print()

    missing, skipped, patched, failed = [], [], [], []
    printed_once = False
    printed_baseline = False

    for lang in langs:
        p = eb_path(args.mod_folder, lang, args.field_name)
        if not p.is_file():
            print(f"[{lang}] MISSING  {p}")
            missing.append(lang)
            continue
        data = p.read_bytes()

        pre_problems, pre_degenerate, pre_worldmaps = decode_report(data)
        if pre_problems:
            print(f"[{lang}] REFUSED  the file does not decode cleanly BEFORE patching:")
            for m in pre_problems:
                print(f"           - {m}")
            failed.append(lang)
            continue
        if pre_degenerate and not printed_baseline:
            print(f"           (baseline note: {len(pre_degenerate)} container-unbounded func(s) "
                  f"{pre_degenerate!r} -- the blank template's entry-0 quirk, see the docstring; "
                  f"required to be unchanged by the splice)")
            printed_baseline = True
        if pre_worldmaps:
            where = ", ".join(f"WorldMap({w[2]}) at entry {w[0]} tag {w[1]}" for w in pre_worldmaps)
            print(f"[{lang}] SKIP     already carries {where} -- idempotent no-op")
            skipped.append(lang)
            continue

        try:
            new, slot, body = patch_bytes(data, world_id=args.world_id, x=x, z=z,
                                          face=args.face, y=args.y_seed, corners=ZONE_CORNERS)
        except Exception as exc:                                # noqa: BLE001
            print(f"[{lang}] FAILED   splice raised {exc!r}")
            failed.append(lang)
            continue

        fails = verify(new, old=data, slot=slot, body=body, world_id=args.world_id,
                       corners=ZONE_CORNERS, baseline_degenerate=pre_degenerate)
        if fails:
            print(f"[{lang}] FAILED   verification ({len(fails)}):")
            for m in fails:
                print(f"           - {m}")
            failed.append(lang)
            continue

        print(f"[{lang}] OK       slot {slot}, {len(data)} -> {len(new)} B "
              f"(+{len(new) - len(data)}), Range body {len(body)} B, all funcs decode clean")

        if args.print_disasm or (args.print_disasm_once and not printed_once):
            print(disasm_text(new, only_entry=slot))
            printed_once = True

        if args.dry_run:
            patched.append(lang)
            continue

        bdir = backup_root / lang
        bdir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, bdir / p.name)
        p.write_bytes(new)
        # read back what actually landed on disk -- a write that half-lands is exactly the
        # class this whole script exists to refuse ([[feedback-verify-the-cache-write-lands]])
        back = p.read_bytes()
        if back != new:
            print(f"[{lang}] FAILED   post-write read-back differs from the verified bytes")
            failed.append(lang)
            continue
        patched.append(lang)

    print()
    print(f"summary: {len(patched)} {'verified' if args.dry_run else 'patched'}, "
          f"{len(skipped)} skipped, {len(missing)} missing, {len(failed)} failed")
    if failed or missing:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
