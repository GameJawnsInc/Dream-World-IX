"""THE SINE KIT, RUNG 1 -- the bench builder (field 30946 SINE1, and 30947 SINE1C, the CAL arm).

Rung 1 ships `[[prop]] motion`: bench/sine1.field.toml authors eight props ONLY with the kit (seven movers + a static
control), and the build seats + arms the daemon (content/motion.py). This script deploys that toml twice and then
seats ONE study-side OBSERVER into every language's live .eb -- no kit code path, no Global lane in the kit:

  30946 SINE1   exactly the kit build + the observer
  30947 SINE1C  the same, except the daemon's InitCode is moved to Main_Init offset 0 -- BEFORE the movers'
                InitObjects (the activate_block shape THE ORDER LAW refuses): the calibration mutant, the "check that
                can fail" -- its FIRST band must read the SPAWN pose, where 30946's reads pose(0)

THE OBSERVER (why not a kit debug switch: it tests the exact bytes that ship, adds no kit code, and the daemon's clocks
are private, so the observer re-derives the tick black-box instead of trusting a self-reported clock). A type-0 code
entry, loc 2 (its own tick counter K = Instance.Int16[0]); its InitCode sits IMMEDIATELY AFTER the daemon's in
Main_Init, so it is created in the same pass, after the daemon and after every mover -- objects first run the frame
after creation, in creation order, so each frame the observer reads what the daemon JUST wrote:
  prelude  K = 0;  V += 1 (a Global visit counter: Main_Init re-ran);  the FIRST band -- A.z, A.f, B.b, B.z, C.z, F.f,
           G.z, read ONCE right after the daemon's tick 0 (each differs between pose(0) and the spawn pose)
  loop     M_K = K;  the Global Int16 mirrors of A f0-f3, B f0-f3, C f0 f2 f3, D f0 f2 f3, E f3, F f3, G f0 f2 f3,
           H f0-f3;  K += 1;  Wait(1);  JMP loop
So a sample carrying M_K = K must equal motion.pose(K) for every mover -- the kit's predictor is the oracle. Reads
only: obj(uid).f[3] is read only on these actor props (a kit prop IS an actor from its InitObject on).
(D f3 and G f3 -- the two movers WITHOUT a turn -- are mirrored so C2 can prove the daemon never turns them.)

The mirrors sit in Global bytes 1400-1463 (the safe band, >= byte 1089 = flag 8712; this bench has no [behavior] and
no [[flag]], so nothing else allocates there; harness saves are sandboxed). ONE owner of the layout: this module.

Usage (repo root):  py studies/sine-kit/sine1_bench.py probe | deploy
30946 / 30947 are NEW ids -> the FIRST deploy needs a relaunch (a harness launch is one).
Revert: py tools/scroll_out/revert_deploy_30946.py  and  py tools/scroll_out/revert_deploy_30947.py
"""
from __future__ import annotations

import argparse
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "ff9mapkit"))

from ff9mapkit import eblint, prop_archetypes                         # noqa: E402
from ff9mapkit.config import LANGS, ModLayout, find_game_path          # noqa: E402
from ff9mapkit.content import motion as M                              # noqa: E402
from ff9mapkit.content import object as _object                        # noqa: E402
from ff9mapkit.eb import EbScript, disasm as D, edit as eb_edit, exprasm, opcodes  # noqa: E402
from ff9mapkit.eb.labelasm import JMP, asm, label                      # noqa: E402
from ff9mapkit.fsutil import atomic_write_bytes                        # noqa: E402

FIELD_ID, FIELD_NAME = 30946, "SINE1"
CAL_ID, CAL_NAME = 30947, "SINE1C"
ARMS = {FIELD_ID: (FIELD_NAME, False), CAL_ID: (CAL_NAME, True)}        # id -> (scene name, is the CAL arm)
MOD_FOLDER = "FF9CustomMap"
BENCH_TOML = HERE / "bench" / "sine1.field.toml"
LABELS = "ABCDEFGH"                                                    # the toml's [[prop]]s, in order
ARCHETYPES = ("balloon", "cask", "letter", "chest", "sword", "fish", "hand_bell", "scroll")
STATIC = "H"                                                            # the control: no motion

# ------------------------------------------------------------------- the mirror layout (Global Int16 byte offsets)
V_OFF = 1400                                                           # the visit counter (the observer's prelude)
FIRST = (("A", 2), ("A", 3), ("B", 1), ("B", 2), ("C", 2), ("F", 3), ("G", 2))   # (prop, f index), read once
FIRST_OFF = {k: 1402 + 2 * i for i, k in enumerate(FIRST)}               # 1402..1414
MK_OFF = 1416                                                          # M_K: the tick the mirrors belong to
MIRRORS = (("A", 0), ("A", 1), ("A", 2), ("A", 3), ("B", 0), ("B", 1), ("B", 2), ("B", 3),
           ("C", 0), ("C", 2), ("C", 3), ("D", 0), ("D", 2), ("D", 3), ("E", 3), ("F", 3),
           ("G", 0), ("G", 2), ("G", 3), ("H", 0), ("H", 1), ("H", 2), ("H", 3))
MIRROR_OFF = {k: 1418 + 2 * i for i, k in enumerate(MIRRORS)}            # 1418..1462
LAYOUT_END = 1418 + 2 * len(MIRRORS)                                   # 1464 (exclusive)
FIRST_OFFS = [V_OFF] + [FIRST_OFF[k] for k in FIRST]                   # the brief watch after each entry
ROLLING_OFFS = [V_OFF, MK_OFF] + [MIRROR_OFF[k] for k in MIRRORS]       # the watch every window reads
SENTINEL = 0x7A7A                   # poked into the FIRST band before each entry: no pose and no spawn produces it
K_REF = "Instance.Int16[0]"         # the observer's own tick counter (loc 2)
OBSERVER_LOC = 2
# the ops that may lie between the daemon's InitCode and the observer's on Main_Init (none of them yields a frame:
# JMP / JMP_IFNOT / JMP_IF / SET / InitCode / InitRegion / InitObject / SetTriangleFlagMask / SetControlDirection)
NO_YIELD_OPS = frozenset({0x01, 0x02, 0x03, 0x05, 0x07, 0x08, 0x09, 0x27, 0x67})
_OP_INITCODE, _OP_INITOBJ, _OP_SETMODEL = 0x07, 0x09, 0x2F


# ------------------------------------------------------------------- the bench's specs (the toml is the one truth)
def _load_props() -> list:
    import tomllib
    raw = tomllib.loads(BENCH_TOML.read_text(encoding="utf-8"))
    props = raw.get("prop") or []
    names = tuple(p.get("prop") for p in props)
    if names != ARCHETYPES:
        raise SystemExit(f"{BENCH_TOML.name}: expected the props {ARCHETYPES} in order, found {names}")
    return props


PROPS = dict(zip(LABELS, _load_props()))
SPECS = {lab: M.parse(p, i) for i, (lab, p) in enumerate(PROPS.items())}          # None for the static control
MOVERS = [lab for lab in LABELS if SPECS[lab] is not None]                         # A..G
MODELS = {lab: prop_archetypes.resolve(p["prop"])[0] for lab, p in PROPS.items()}
# what CreateObject + the Init's TurnInstant leave before any 0xAD / 0x87: (x, b, z, facing byte) -- a flat floor
SPAWN = {lab: (int(p["pos"][0]), 0, int(p["pos"][1]), int(p.get("face") or 0) & 0xFF) for lab, p in PROPS.items()}


def component(pose: M.Pose, fi: int):
    """``obj(uid).f[fi]`` of a pose: f0 x, f1 the 0xAD height operand b, f2 z, f3 the facing byte."""
    return (pose.x, pose.b, pose.z, pose.face)[fi]


def expected(lab: str, fi: int, k: int) -> int:
    """What ``obj(uid).f[fi]`` holds on the observer's tick ``k`` -- the kit's predictor, never re-derived here."""
    spec, sp = SPECS[lab], SPAWN[lab]
    if spec is None:
        return sp[fi]
    p = M.pose(spec, k)
    if fi == 3:
        return sp[3] if p.face is None else p.face
    return component(p, fi) if spec.moves else sp[fi]


FIRST_POSE0 = {k: expected(k[0], k[1], 0) for k in FIRST}                  # C4 / C8: the daemon's tick 0 landed
FIRST_SPAWN = {k: SPAWN[k[0]][k[1]] for k in FIRST}                        # CAL: CreateObject overwrote it
_bad = [k for k in FIRST if FIRST_POSE0[k] == FIRST_SPAWN[k] or SENTINEL in (FIRST_POSE0[k], FIRST_SPAWN[k])]
if _bad:
    raise SystemExit(f"the FIRST band must discriminate pose(0) / spawn / sentinel, but {_bad} do not")


# ------------------------------------------------------------------- reading a harness sample
def bits(offsets) -> list:
    return [off * 8 + i for off in offsets for i in range(16)]


def i16(st, off: int) -> int | None:
    """A watched Global Int16, or None when any of its bits is not in this sample (never read an unwatched bit as 0)."""
    v = 0
    for i in range(16):
        b = st.flag(off * 8 + i)
        if b is None:
            return None
        v |= int(bool(b)) << i
    return v - 0x10000 if v & 0x8000 else v


def s16(v: int) -> int:
    v &= 0xFFFF
    return v - 0x10000 if v & 0x8000 else v


def read_first(st) -> dict | None:
    """{"V": .., (prop, f): ..} from a sample taken under the FIRST watch, or None."""
    out = {"V": i16(st, V_OFF)}
    out.update({k: i16(st, FIRST_OFF[k]) for k in FIRST})
    return None if any(v is None for v in out.values()) else out


def read_rolling(st) -> dict | None:
    """{"V": .., "K": .., (prop, f): ..} from a sample taken under the rolling watch, or None."""
    out = {"V": i16(st, V_OFF), "K": i16(st, MK_OFF)}
    out.update({k: i16(st, MIRROR_OFF[k]) for k in MIRRORS})
    return None if any(v is None for v in out.values()) else out


def sample_errors(sample: dict, labs=None) -> dict:
    """{(prop, f): (got, want)} for every mirror (of ``labs``, default all) that differs from the predictor."""
    k = sample["K"]
    return {key: (sample[key], expected(key[0], key[1], k)) for key in MIRRORS
            if (labs is None or key[0] in labs) and sample[key] != expected(key[0], key[1], k)}


# ------------------------------------------------------------------- the observer
def _stmt(text: str) -> bytes:
    return opcodes.encode(0x05, exprasm.assemble(text + " B_EXPR_END"), arg_flags=0b1)


def _g(off: int) -> str:
    return f"Global.Int16[{off}]"


def observer_body(uids: dict) -> bytes:
    B: list = [_stmt(f"{K_REF} const(0) B_LET"),
               _stmt(f"{_g(V_OFF)} {_g(V_OFF)} const(1) B_PLUS B_LET")]
    B += [_stmt(f"{_g(FIRST_OFF[(lab, fi)])} obj(uid={uids[lab]}).f[{fi}] B_LET") for lab, fi in FIRST]
    B += [label("top"), _stmt(f"{_g(MK_OFF)} {K_REF} B_LET")]
    B += [_stmt(f"{_g(MIRROR_OFF[(lab, fi)])} obj(uid={uids[lab]}).f[{fi}] B_LET") for lab, fi in MIRRORS]
    B += [_stmt(f"{K_REF} {K_REF} const(1) B_PLUS B_LET"), opcodes.wait(1), (JMP, "top"), opcodes.RETURN]
    return asm(B)


def observer_entry(uids: dict) -> bytes:
    """A seated code entry: type 0, ONE tag-0 function at fpos 4 (the daemon's own shape), loc 2."""
    return bytes([0x00, 0x01]) + struct.pack("<HH", 0, 4) + observer_body(uids)


# ------------------------------------------------------------------- finding things in a built / deployed .eb
def prop_uids(eb: bytes) -> dict:
    """{label: uid} -- the ONE entry whose Init sets each prop's model (every bench model is unique; a kit prop's uid
    IS its entry slot)."""
    s = EbScript.from_bytes(eb)
    found: dict = {}
    for e in s.entries:
        if e.size <= 0 or not e.funcs:
            continue
        f0 = e.func_by_tag(0)
        if f0 is None:
            continue
        for i in D.iter_code(eb, f0.abs_start, f0.abs_end):
            if i.op == _OP_SETMODEL:
                found.setdefault(struct.unpack_from("<H", eb, i.off + 2)[0], []).append(e.index)
    out = {}
    for lab, mid in MODELS.items():
        hits = found.get(mid, [])
        if len(hits) != 1:
            raise SystemExit(f"prop {lab} ({PROPS[lab]['prop']}, model {mid}): expected ONE entry setting it, "
                             f"found {hits}")
        out[lab] = hits[0]
    return out


def movers(uids: dict) -> list:
    """[(spec, uid)] in TOML order -- exactly what the build hands motion.entry_bytes."""
    return [(SPECS[lab], uids[lab]) for lab in MOVERS]


def daemon_slot(eb: bytes, uids: dict) -> int:
    """The ONE entry equal to motion.entry_bytes(the bench's movers) -- the tested daemon IS the kit's emission."""
    want, loc = M.entry_bytes(movers(uids))
    s = EbScript.from_bytes(eb)
    hits = [e.index for e in s.entries if e.size > 0 and eb[e.abs_start:e.abs_end] == want and e.loc == loc]
    if len(hits) != 1:
        raise SystemExit(f"expected ONE entry == motion.entry_bytes(movers) (loc {loc}), found {hits}")
    return hits[0]


def observer_slot(eb: bytes, uids: dict) -> int | None:
    want = observer_entry(uids)
    s = EbScript.from_bytes(eb)
    hits = [e.index for e in s.entries if e.size > 0 and eb[e.abs_start:e.abs_end] == want]
    if len(hits) > 1:
        raise SystemExit(f"more than one observer entry: {hits}")
    return hits[0] if hits else None


def is_patched(eb: bytes) -> bool:
    try:
        return observer_slot(eb, prop_uids(eb)) is not None
    except SystemExit:
        return False


def _main_calls(eb: bytes, op: int, slot: int) -> list:
    """Every instruction in Main_Init with opcode ``op`` naming ``slot``."""
    main = EbScript.from_bytes(eb).entry(0).func_by_tag(0)
    return [i for i in D.iter_code(eb, main.abs_start, main.abs_end) if i.op == op and eb[i.off + 1] == slot]


def between_problems(eb: bytes, dslot: int, oslot: int) -> list:
    """The critic's calibration guard: the daemon and the observer must be CREATED IN THE SAME Main_Init pass, the
    daemon first -- so the observer's K equals the daemon's tick n on both arms, and CAL fails only for THE ORDER LAW.
    Every op between the two InitCodes must be a known non-yielding op, and every jump there must land inside."""
    d, o = _main_calls(eb, _OP_INITCODE, dslot), _main_calls(eb, _OP_INITCODE, oslot)
    if len(d) != 1 or len(o) != 1:
        return [f"expected one InitCode each for the daemon ({dslot}) and the observer ({oslot}) in Main_Init, "
                f"found {len(d)} / {len(o)}"]
    d, o = d[0], o[0]
    if d.off >= o.off:
        return [f"the observer's InitCode (+{o.off}) is not after the daemon's (+{d.off})"]
    out = []
    for i in D.iter_code(eb, d.end, o.off):
        if i.op not in NO_YIELD_OPS:
            out.append(f"op 0x{i.op:02X} at {i.off} between the daemon's and the observer's InitCode may yield")
        elif i.op in (0x01, 0x02, 0x03):
            t = D.jump_target(i)
            if t is None or not d.end <= t <= o.off:
                out.append(f"the jump at {i.off} leaves the daemon->observer span (target {t})")
    return out


# ------------------------------------------------------------------- the patch (deterministic: P1 re-applies it)
def patch_eb(eb0: bytes, *, cal: bool) -> tuple:
    """Seat + arm the observer right after the daemon's InitCode; on the CAL arm, then MOVE the daemon's InitCode to
    Main_Init offset 0 -- the old one neutralised by a non-yielding JMP +0 (skip_range: a 0x00 NOP would yield a frame
    and desynchronise K from the daemon's tick). Returns (bytes, info)."""
    uids = prop_uids(eb0)
    if observer_slot(eb0, uids) is not None:
        raise SystemExit("this .eb already carries the observer -- patch a fresh deploy")
    dslot = daemon_slot(eb0, uids)
    baseline = {str(p) for p in eblint.lint_eb(eb0)}
    out, oslot = _object.seat_entry(eb0, observer_entry(uids), loc=OBSERVER_LOC)
    main = EbScript.from_bytes(out).entry(0).func_by_tag(0)
    ic = _main_calls(out, _OP_INITCODE, dslot)
    if len(ic) != 1:
        raise SystemExit(f"expected ONE InitCode({dslot}) in Main_Init, found {len(ic)}")
    out = eb_edit.insert_in_function(out, 0, 0, ic[0].end - main.abs_start, opcodes.init_code(oslot, 0))
    if cal:
        ic = _main_calls(out, _OP_INITCODE, dslot)
        out = eb_edit.skip_range(out, ic[0].off, 3)
        out = eb_edit.insert_in_function(out, 0, 0, 0, opcodes.init_code(dslot, 0))
    fresh = [p for p in eblint.lint_eb(out)
             if getattr(p, "severity", "error") == "error" and str(p) not in baseline]
    if fresh:
        raise SystemExit("patch produced NEW lint errors:\n  " + "\n  ".join(map(str, fresh)))
    slots = [uids[lab] for lab in MOVERS]
    order = M.arming_problems(out, dslot, slots)
    watcher = M.arming_problems(out, oslot, list(uids.values()))
    between = between_problems(out, dslot, oslot)
    if (bool(order) != cal) or watcher or between:
        raise SystemExit(f"the {'CAL' if cal else 'main'} arm is not the intended shape: ORDER {order} / observer "
                         f"{watcher} / daemon->observer {between}")
    return out, {"uids": uids, "daemon": dslot, "observer": oslot, "order": order}


def build_raw(fid: int, workdir: Path) -> dict:
    """{lang: the kit's .eb} for arm ``fid`` -- the SAME build deploy_field runs (id, name and text block forced)."""
    from ff9mapkit import build as B
    name, _cal = ARMS[fid]
    proj = B.FieldProject.load(BENCH_TOML)
    proj.raw.setdefault("field", {})["id"] = fid
    proj.raw["field"]["name"] = name
    proj.raw["field"]["text_block"] = fid
    info = B.build_mod([proj], workdir / "mod", mod_name=MOD_FOLDER)
    nm = info["dictionary"][0].split()[4]
    tl = ModLayout(workdir / "mod")
    return {L: tl.eb_path(L, f"EVT_{nm}.eb.bytes").read_bytes() for L in LANGS
            if tl.eb_path(L, f"EVT_{nm}.eb.bytes").exists()}


def derive(fid: int) -> dict:
    """{lang: the bytes the deploy must have left live} -- rebuilt from the toml and patched again (P1)."""
    with tempfile.TemporaryDirectory(prefix="sine1_") as td:
        raw = build_raw(fid, Path(td))
    return {L: patch_eb(b, cal=ARMS[fid][1])[0] for L, b in raw.items()}


def live_path(fid: int, lang: str, game: Path | None = None) -> Path:
    game = game or find_game_path()
    return ModLayout(game / MOD_FOLDER).eb_path(lang, f"EVT_{ARMS[fid][0]}.eb.bytes")


# ------------------------------------------------------------------- P3: the daemon run offline
def engine_mismatches(eb: bytes, n_ticks: int | None = None) -> tuple:
    """Run the DAEMON entry of ``eb`` in tests/_ebengine.MotionEngine for ``n_ticks`` (default two cycles of the
    slowest mover) and compare every captured 0xAD / 0x87 operand with motion.pose. Returns (ticks, mismatches)."""
    sys.path.insert(0, str(REPO / "ff9mapkit" / "tests"))
    from _ebengine import MotionEngine
    uids = prop_uids(eb)
    dslot = daemon_slot(eb, uids)
    e = EbScript.from_bytes(eb).entry(dslot)
    body = eb[e.abs_start:e.abs_end][6:]
    n = n_ticks or 2 * max(SPECS[lab].cycle for lab in MOVERS)
    got = MotionEngine(e.loc, strict_reduced=True).ticks(body, n)
    bad = []
    for t, ops in enumerate(got):
        want = []
        for lab in MOVERS:
            spec, p = SPECS[lab], M.pose(SPECS[lab], t)
            if spec.moves:
                want.append((M.MOVE_EX, uids[lab], (p.x, p.b, p.z)))
            if spec.turns:
                want.append((M.TURN_EX, uids[lab], (p.face,)))
        have = [(op, uid, (vals[0] & 0xFF,) if op == M.TURN_EX else vals) for op, uid, vals in ops]
        if have != want and len(bad) < 5:
            bad.append((t, have, want))
    return n, bad


# ------------------------------------------------------------------- verbs
def _main_listing(eb: bytes, slots: set) -> list:
    main = EbScript.from_bytes(eb).entry(0).func_by_tag(0)
    out = []
    for i in D.iter_code(eb, main.abs_start, main.abs_end):
        if i.op in (0x01, 0x22) or (i.op in (_OP_INITCODE, _OP_INITOBJ) and eb[i.off + 1] in slots):
            out.append(f"    +{i.off - main.abs_start:4d}  {eb[i.off:i.end].hex()}")
    return out


def probe() -> None:
    """Offline: the bench's specs and the layout, then both arms built + patched in a tempdir, the laws' verdicts on
    them, and the daemon run in the MotionEngine; the live deploy compared when present."""
    from ff9mapkit import build as B
    proj = B.FieldProject.load(BENCH_TOML)
    print(f"{BENCH_TOML.name}: validate {B.validate(proj)} | motion.problems "
          f"{M.problems(proj.raw, donor=B.donor_field_id(proj.raw))} | lint notes {M.lint_notes(proj.raw)}")
    for lab in LABELS:
        s = SPECS[lab]
        print(f"  {lab} {PROPS[lab]['prop']:9s} model {MODELS[lab]:3d} spawn {SPAWN[lab]}  "
              + (M.describe(s) if s else "STATIC control"))
    print(f"mirror layout: V {V_OFF}; FIRST {FIRST_OFF}; M_K {MK_OFF}; mirrors {MIRROR_OFF}; end {LAYOUT_END}")
    print(f"FIRST  pose(0) {FIRST_POSE0}\n       spawn   {FIRST_SPAWN}\n       sentinel {SENTINEL}")
    for k in (0, 1, 2, 3, 127, 128, 1025):
        print(f"  K={k:5d} " + " ".join(f"{lab}{fi}={expected(lab, fi, k)}" for lab, fi in MIRRORS))
    game = None
    try:
        game = find_game_path()
    except Exception as e:                               # noqa: BLE001 -- the probe is offline first
        print(f"(no game install: {e})")
    for fid, (name, cal) in ARMS.items():
        with tempfile.TemporaryDirectory(prefix="sine1_") as td:
            raw = build_raw(fid, Path(td))
        lang = "us" if "us" in raw else sorted(raw)[0]
        out, info = patch_eb(raw[lang], cal=cal)
        print(f"\n{fid} {name} ({'CAL' if cal else 'main'} arm): {len(raw)} language(s); uids {info['uids']}; "
              f"daemon slot {info['daemon']}; observer slot {info['observer']}")
        print(f"  ORDER LAW on the daemon: {info['order'] or 'clean'}")
        print(f"  daemon -> observer span: {between_problems(out, info['daemon'], info['observer']) or 'no yield'}")
        slots = set(info["uids"].values()) | {info["daemon"], info["observer"]}
        print("  Main_Init's InitObject / InitCode / JMP / Wait:")
        print("\n".join(_main_listing(out, slots)))
        n, bad = engine_mismatches(raw[lang])
        print(f"  P3 (built): MotionEngine {n} ticks vs motion.pose -- {'EXACT' if not bad else bad}")
        if game is not None:
            for L in sorted(raw):
                p = live_path(fid, L, game)
                if p.exists():
                    same = p.read_bytes() == patch_eb(raw[L], cal=cal)[0]
                    print(f"  live {L}: {'== derived' if same else 'DIFFERS from derived'} ({p.name})")
    ob = observer_body({lab: 2 + i for i, lab in enumerate(LABELS)})
    print(f"\nobserver: {len(ob)} B")
    for i in D.iter_code(ob, 0, len(ob)):
        if i.op == 0x05:
            print("   SET", D.pretty_expr(ob, i.off + 1)[0][:120])
        else:
            print(f"   op 0x{i.op:02X} {ob[i.off:i.end].hex()}")


def deploy() -> None:
    game = find_game_path()
    for fid, (name, cal) in ARMS.items():
        r = subprocess.run([sys.executable, str(REPO / "tools" / "deploy_field.py"), str(BENCH_TOML),
                            "--id", str(fid), "--name", name, "--text-block", str(fid), "--mod-folder", MOD_FOLDER])
        if r.returncode != 0:
            raise SystemExit(f"deploy_field failed for {fid}")
        n, info = 0, None
        for lang in LANGS:
            p = live_path(fid, lang, game)
            if p.exists():
                out, info = patch_eb(p.read_bytes(), cal=cal)
                atomic_write_bytes(p, out)
                n += 1
        if not n:
            raise SystemExit(f"no live EVT_{name}.eb.bytes found to patch")
        print(f"{fid} {name}: patched {n} language .eb file(s) -- uids {info['uids']}, daemon slot {info['daemon']}, "
              f"observer slot {info['observer']}{', daemon armed FIRST (CAL)' if cal else ''}")
        derived = derive(fid)                               # the scenario's P1, run now rather than after a launch
        off = [L for L, b in derived.items() if live_path(fid, L, game).read_bytes() != b]
        if off or not derived:
            raise SystemExit(f"{fid}: the live .eb DIFFERS from a fresh build + patch in {off or 'every language'} "
                             f"-- the scenario's P1 would fail; do not launch")
        print(f"  derive-forward: the live bytes == a fresh build + patch in all {len(derived)} language(s)")
    print("  Revert: " + "  ".join(f"py tools/scroll_out/revert_deploy_{fid}.py" for fid in ARMS))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("verb", choices=["probe", "deploy"])
    {"probe": probe, "deploy": deploy}[ap.parse_args().verb]()
