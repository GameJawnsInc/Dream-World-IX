"""SELFDRESS (field 30606) -- the s140 bench field's BUILDER: the kit builds selfdress.field.toml, this seats the rest.

Why a seat step: the toml expresses the player, the twin, the late entry and the cup with the kit's own blocks (the twin's
gated activation is what puts its InitObject AHEAD of the player's -- R3-FIELD-MODEL-AUDIT.md 4.1, refuted s138-F14), but
no field.toml block can express the conductors the s140 legs need: RunAnimationEx on uid 250, a GetEntryAnimFrame frame
wait, a function inside the PLAYER's entry whose loop bound is B_FRAME (GetAnimDuration evaluates on gCur, the RUNNING
object -- EventEngine.DoCalcOperationExt.cs:24-26 -- so field 2705's loop exercises s140's hook only from the player's
own entry), a ladder jump in the player's own entry (SetJumpAnimation / RunJumpAnimation / RunLandAnimation act on the
running object too), or an entry InitObject'd at run time. A prebuilt .eb cannot be committed either: every kit build embeds the
install-derived blank field (docs/PROVENANCE.md; test_provenance_tripwire.py). So, as the photo-mode and sine-kit rung-0
benches do, this script seats them with the kit's own primitives after the kit build -- eb.edit.add_function (T3 and J into the
player entry, LATE_CC into the late entry), content.object.seat_entry (the caller code entry) and eb.edit.activate_block
(its InitCode, after the player's InitObject) -- into EVERY language's .eb, structurally located in each, and rewrites the
field's EventAnimation clip list from the seated script (ff9mapkit.eventanim: the clip list a model is (re)created with,
which s140's AttachDress reads as the SOURCE list). No kit code changes. The contract (sids, bits, operands, preflight) is
studies/test-harness/scenarios/_selfdress_field.py, which also holds the T3 and caller BODIES the seat writes (t3_body /
caller_body), so its preflight compares the deployed bytes to the very builders the seat used.

Verbs (repo root):
    py -X utf8 studies/battle-coop/bench/selfdress_bench.py build [--out DIR]
        OFFLINE: the kit build exactly as deploy_field.py does it (id 30606, name TEST30606, mod FF9CustomMap-msgs) into
        DIR (default a temp dir), the seat, the preflight on every language, and the disassembly proof (proof.txt).
        Reads the install read-only for the stock op forms; writes nothing outside DIR.
    py -X utf8 studies/battle-coop/bench/selfdress_bench.py deploy
        LIVE: runs `py tools/deploy_field.py studies/battle-coop/bench/selfdress.field.toml --id 30606 --mod-folder
        FF9CustomMap-msgs`, then seats the live EVT_TEST30606 .eb (every language) + its EventAnimation list under the
        folder lock and re-runs the preflight on each. 30606 is a NEW id: the first deploy needs a game relaunch.
        Revert: py tools/scroll_out/revert_deploy_30606.py (it deletes the seated files as well).
"""
from __future__ import annotations

import argparse
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO / "studies" / "test-harness" / "scenarios"))
import _selfdress_field as F                                         # noqa: E402 - the contract, beside the bench

F._kit()                                                              # pins THIS checkout's ff9mapkit (asserted)
from ff9mapkit import eblint, eventanim                               # noqa: E402
from ff9mapkit.config import LANGS, ModLayout                         # noqa: E402
from ff9mapkit.content import object as _object                      # noqa: E402
from ff9mapkit.eb import EbScript, disasm as D, edit as eb_edit, opcodes as O   # noqa: E402

DEPLOY_FIELD = REPO / "tools" / "deploy_field.py"


# ================================================================================================ the bytes
# T3's function and the caller's loop live in the CONTRACT (_selfdress_field.t3_body / caller_body): the preflight
# compares the deployed bytes to those very builders, byte for byte, so the seat and the check can never disagree.
t3_body = F.t3_body
caller_body = F.caller_body


def j_body() -> bytes:
    """J_TAG: field 404's ladder mount without its arc (test2_107.txt:1191-1199 -- Zidane_13's SetJumpAnimation(10687, 2,
    6) / RunJumpAnimation / WaitAnimation, then RunLandAnimation / WaitAnimation; no SetupJump / Jump: the player stays
    where he stands), with the phase bits J_LAND (right before the landing) and J_END around the landing."""
    return b"".join(raw for _op, raw in F._expected_j())


def late_cc_body() -> bytes:
    """LATE_CC_TAG: DefinePlayerCharacter in a function nothing calls (EntryDefinesPlayer true, control never moves)."""
    return O.DEFINE_PLAYER_CHARACTER + O.RETURN


def caller_entry() -> bytes:
    """A seated code entry: type 0, ONE tag-0 function at fpos 4 (the sine-kit / photo daemon shape)."""
    return bytes([F.CODE_ENTRY_TYPE, 0x01]) + struct.pack("<HH", 0, 4) + caller_body()


# ================================================================================================ the seat
def kit_layout_problems(eb: bytes) -> list:
    """The kit build's layout the seat relies on, checked structurally ([] = as expected): the entries at the contract's
    sids, the guarded activations of the twin (JMP_IF over GlobBit TWIN_GATE) and the late entry (JMP_IFNOT over GlobBit
    LATE_GATE), the player's, the cup's, and a free caller slot."""
    s = EbScript.from_bytes(eb)
    bad = []
    f = F.facts(eb)
    ents = f["entries"]
    for name, sid, model in (("player", F.PLAYER_SID, F.ZIDANE_MODEL), ("twin", F.TWIN_SID, F.ZIDANE_MODEL),
                             ("late", F.LATE_SID, F.ZIDANE_MODEL), ("cup", F.CUP_SID, F.CUP_MODEL)):
        got = (ents.get(sid) or {}).get("init_model")
        if not got or got[0] != model:
            bad.append(f"{name}: entry {sid}'s Init sets {got} (want model {model})")
    if (ents.get(F.PLAYER_SID) or {}).get("define_tags") != [0]:
        bad.append(f"player: DefinePlayerCharacter in tags {(ents.get(F.PLAYER_SID) or {}).get('define_tags')}")
    for sid in (F.TWIN_SID, F.LATE_SID):
        if (ents.get(sid) or {}).get("define_tags"):
            bad.append(f"entry {sid} already holds DefinePlayerCharacter")
    if F.CALLER_SID < s.entry_count and not s.entry(F.CALLER_SID).empty:
        bad.append(f"slot {F.CALLER_SID} is taken (want it free for the caller)")
    main = s.entry(0).func_by_tag(0)
    code = list(D.iter_code(eb, main.abs_start, main.abs_end))
    guards = {F.TWIN_SID: (F.TWIN_GATE, F.OP_JMP_IF), F.LATE_SID: (F.LATE_GATE, F.OP_JMP_IFNOT)}
    for sid, (gate, jop) in guards.items():
        at = [k for k, i in enumerate(code) if i.op == F.OP_INIT_OBJECT and i.imm(0) == sid]
        ok = (len(at) == 1 and at[0] >= 2 and code[at[0] - 2].op == F.OP_EXPR
              and eb[code[at[0] - 2].off:code[at[0] - 2].end] == F.glob_test(gate) and code[at[0] - 1].op == jop)
        if not ok:
            bad.append(f"Main_Init: InitObject({sid}) is not the kit's guarded call over GlobBit[{gate}]")
    return bad


def player_ids(eb: bytes) -> tuple:
    """The player Init's own (stand, walk, run) immediates -- restored after T3. The contract's reader
    (_selfdress_field.player_ids), the same one the preflight rebuilds t3_body from."""
    got = F.player_ids(eb)
    if got is None:
        raise SystemExit("the player Init's stand/walk/run setters are not all immediates")
    return got


def patch_eb(eb0: bytes) -> bytes:
    """Seat T3 and J (player), LATE_CC (late entry) and the caller (+ its InitCode after the player's InitObject). Refuses a
    layout it does not recognise, and any NEW eblint error."""
    bad = kit_layout_problems(eb0)
    if bad:
        raise SystemExit("the kit build is not the layout the seat expects:\n  " + "\n  ".join(bad))
    baseline = {str(p) for p in eblint.lint_eb(eb0)}
    out = eb_edit.add_function(eb0, F.PLAYER_SID, F.T3_TAG, t3_body(*player_ids(eb0)))
    out = eb_edit.add_function(out, F.PLAYER_SID, F.J_TAG, j_body())
    out = eb_edit.add_function(out, F.LATE_SID, F.LATE_CC_TAG, late_cc_body())
    out, slot = _object.seat_entry(out, caller_entry(), slot=F.CALLER_SID, loc=F.CALLER_LOC)
    if slot != F.CALLER_SID:
        raise SystemExit(f"the caller landed in slot {slot}, not {F.CALLER_SID}")
    out = eb_edit.activate_block(out, O.init_code(F.CALLER_SID, 0), after_player=True)
    fresh = [p for p in eblint.lint_eb(out) if getattr(p, "severity", "error") == "error" and str(p) not in baseline]
    if fresh:
        raise SystemExit("the seat produced NEW lint errors:\n  " + "\n  ".join(map(str, fresh)))
    why = F.preflight(out)
    if why:
        raise SystemExit(f"the seated .eb fails its own preflight: {why}")
    return out


def patch_mod(root: Path, name: str, *, write) -> dict:
    """Seat every language's ``EVT_<name>.eb.bytes`` under the mod root and rewrite its EventAnimation list from the
    seated scripts. ``write(path, data)`` does the writing (atomic). Only files the kit build/deploy already wrote are
    touched, so deploy_field's revert (which deletes both) still owns everything. Returns {lang: seated bytes}."""
    lay = ModLayout(root)
    done = {}
    for lang in LANGS:
        p = lay.eb_path(lang, f"EVT_{name}.eb.bytes")
        if not p.is_file():
            continue
        eb0 = p.read_bytes()
        if F.preflight(eb0) is None:
            raise SystemExit(f"{p} is ALREADY seated (re-run the kit build/deploy first)")
        done[lang] = patch_eb(eb0)
    if not done:
        raise SystemExit(f"no EVT_{name}.eb.bytes under {root}")
    ea = lay.eventanimation_path(f"EVT_{name}")
    text = eventanim.event_animation_text(list(done.values()))
    if not ea.is_file() or text is None:
        raise SystemExit(f"{ea}: the kit build wrote no EventAnimation list to rewrite (or the seat lists none)")
    for lang, data in done.items():
        write(lay.eb_path(lang, f"EVT_{name}.eb.bytes"), data)
    write(ea, text.encode("utf-8"))
    return done


# ================================================================================================ the proof
def _dis(eb: bytes, f, *, rel=True) -> list:
    return [f"    {i.off - f.abs_start if rel else i.off:5d}  {eb[i.off:i.end].hex(' '):44s} {D.pretty_expr(eb, i.off + 1)[0] if i.op == F.OP_EXPR else i}"
            for i in D.iter_code(eb, f.abs_start, f.abs_end)]


def stock_forms(game: Path) -> dict:
    """The stock instructions each conductor copies, as the install's own bytes (READ-ONLY; the kit's events-bundle
    cache must already exist -- this never creates it): {label: (field, entry, tag, bytes) or None}."""
    from ff9mapkit import extract as X
    sa = Path(game) / "StreamingAssets" / ".ff9mapkit-events-bundle.txt"
    if not sa.is_file():
        return {"(skipped)": f"{sa} missing: the kit would WRITE it into the install -- run any ff9mapkit read by hand"}
    want = {   # label -> (field, entry, tag, predicate on (instr, bytes))
        "554 RunAnimationEx(12, 186)": (554, 0, 1, lambda b: b == O.run_animation_ex(12, F.ANIM_X)),
        "554 WaitAnimationEx(12)": (554, 0, 1, lambda b: b == O.wait_animation_ex(12)),
        "307 GetEntryAnimFrame(255) < 58": (307, None, None, lambda b: b == bytes.fromhex("05 78 ff 07 7d 3a 00 18 7f")),
        "307 RunAnimation(2572)": (307, None, None, lambda b: b == O.run_animation(F.ANIM_T1)),
        "2705 RunScript(2, 6, 25)": (2705, 0, None, lambda b: b == O.run_script(2, 6, 25)),
        "2705 SetWalkAnimation(8847)": (2705, 6, 23, lambda b: b == O.encode(F.OP_WALK_ANIM, F.ANIM_T3_WALK)),
        "2705 SetStandAnimation(7922)": (2705, 6, 23, lambda b: b == O.encode(F.OP_STAND, F.ANIM_T3_STAND)),
        "2705 SetWalkSpeed(7)": (2705, 6, 25, lambda b: b == O.set_walk_speed(F.T3_WALK_SPEED)),
        "2705 MakeAnimationLoop(40)": (2705, 6, 25, lambda b: b == O.encode(F.OP_ANIM_LOOP, F.T3_PRE_LOOP)),
        "2705 MakeAnimationLoop(1)": (2705, 6, 25, lambda b: b == O.encode(F.OP_ANIM_LOOP, 1)),
        "2705 the loop bound": (2705, 6, 25, lambda b: b == F.T3_BOUND_STMT),
        "404 SetJumpAnimation(10687, 2, 6)": (404, None, None,
                                              lambda b: b == O.set_jump_animation(F.ANIM_J, F.J_JUMP0, F.J_JUMP1)),
        "404 RunJumpAnimation": (404, None, None, lambda b: b == O.run_jump_animation()),
        "404 RunLandAnimation": (404, None, None, lambda b: b == O.run_land_animation()),
        "404 WaitAnimation": (404, None, None, lambda b: b == O.wait_animation()),
    }
    cache, out = {}, {}
    for lab, (fid, ent, tag, pred) in want.items():
        if fid not in cache:
            cache[fid] = X.extract_event_script(str(fid), game=game, lang="us")
        eb = cache[fid]
        out[lab] = None
        if not eb:
            continue
        s = EbScript.from_bytes(eb)
        for e in s.entries:
            if e.empty or (ent is not None and e.index != ent):
                continue
            for f in e.funcs:
                if tag is not None and f.tag != tag:
                    continue
                hit = next((eb[i.off:i.end] for i in D.iter_code(eb, f.abs_start, f.abs_end) if pred(eb[i.off:i.end])),
                           None)
                if hit is not None and out[lab] is None:
                    out[lab] = (fid, e.index, f.tag, hit)
    if cache.get(2705):                                   # the whole Zidane_25 loop, stock vs ours, op for op
        s = EbScript.from_bytes(cache[2705])
        f = s.entry(6).func_by_tag(25)
        out["2705 Zidane_25 body"] = [(i.op, cache[2705][i.off:i.end]) for i in D.iter_code(cache[2705], f.abs_start,
                                                                                               f.abs_end)]
    return out


def _loop_ops(body: list) -> list:
    """The while-loop core of a function's instruction list: from the JMP to the cond through the closing JMP_IF."""
    ops = [op for op, _b in body]
    end = next(k for k, (op, b) in enumerate(body) if b == F.T3_BOUND_STMT) + 1
    start = max(k for k in range(end) if ops[k] == F.OP_JMP)
    return body[start:end + 1]


def proof(eb: bytes, game: Path | None) -> list:
    """The disassembly proof of the seated .eb (MAIN_INIT_ORDER, the sids, every conductor's bytes, the T3 function in
    the player entry, the late entry's 0x2C outside its Init), with the stock forms beside them when the install reads."""
    s = EbScript.from_bytes(eb)
    f = F.facts(eb)
    L = ["== (1) MAIN_INIT_ORDER", "  " + F.main_init_order(eb, f)[1]]
    L += [f"  Main_Init activations (op, Main_Init offset, sid, uid): {f['main_init']}"]
    L += ["== (5) sids / uids (uid = sid: every activation passes 0)"]
    for name, sid in F.SIDS.items():
        e = s.entry(sid)
        L.append(f"  {name:6s} sid {sid}  type {e.type}  loc {e.loc}  funcs {[g.tag for g in e.funcs]}  "
                 f"Init model {f['entries'].get(sid, {}).get('init_model')}  0x2C in tags "
                 f"{f['entries'].get(sid, {}).get('define_tags')}")
    L += ["== (3) T3: function %d of the PLAYER entry %d (B_FRAME evaluates on gCur = this entry)" % (F.T3_TAG, F.PLAYER_SID)]
    L += _dis(eb, s.entry(F.PLAYER_SID).func_by_tag(F.T3_TAG))
    L += ["== (3b) J: function %d of the PLAYER entry %d (field 404's ladder jump, no arc)" % (F.J_TAG, F.PLAYER_SID)]
    L += _dis(eb, s.entry(F.PLAYER_SID).func_by_tag(F.J_TAG))
    L += ["== (4) the late entry %d: Init (tag 0) has no 0x2C; function %d holds it and nothing calls it" % (F.LATE_SID, F.LATE_CC_TAG)]
    L += _dis(eb, s.entry(F.LATE_SID).func_by_tag(F.LATE_CC_TAG))
    callers = [(e.index, g.tag) for e in s.entries if not e.empty for g in e.funcs
               for i in D.iter_code(eb, g.abs_start, g.abs_end) if i.op in (0x10, 0x12, 0x14) and i.imm(2) == F.LATE_CC_TAG
               and i.imm(1) in (F.LATE_SID, F.SELF_UID)]
    L.append(f"  RunScript* sites naming tag {F.LATE_CC_TAG} on the late entry: {callers or 'none'}")
    L += ["== (2) the caller (code entry %d), every conductor" % F.CALLER_SID]
    L += _dis(eb, s.entry(F.CALLER_SID).func_by_tag(0))
    if game is not None:
        try:
            st = stock_forms(game)
        except Exception as err:                         # noqa: BLE001 - the proof survives a missing install
            st = {"(error)": f"{type(err).__name__}: {err}"}
        L += ["== stock forms the conductors copy (install, us, read-only)"]
        body = st.pop("2705 Zidane_25 body", None)
        for lab, v in st.items():
            L.append(f"  {lab:34s} " + (f"field {v[0]} entry {v[1]} tag {v[2]}: {v[3].hex(' ')}" if isinstance(v, tuple)
                                         else str(v)))
        if body:
            ours = [(i.op, eb[i.off:i.end]) for i in D.iter_code(eb, *(lambda g: (g.abs_start, g.abs_end))(
                s.entry(F.PLAYER_SID).func_by_tag(F.T3_TAG)))]
            a, b = _loop_ops(body), _loop_ops(ours)
            same_ops = [op for op, _ in a] == [op for op, _ in b]
            same_bytes = [x for op, x in a if op not in (F.OP_JMP, F.OP_JMP_IF, F.OP_WALK)] == \
                         [x for op, x in b if op not in (F.OP_JMP, F.OP_JMP_IF, F.OP_WALK)]
            L.append(f"  2705 Zidane_25 while-loop vs T3's: op sequence identical {same_ops}; every byte identical "
                     f"but the Walk targets and the jump offsets {same_bytes}")
            L.append("    stock: " + " | ".join(x.hex(' ') for _o, x in a))
            L.append("    ours : " + " | ".join(x.hex(' ') for _o, x in b))
    return L


# ================================================================================================ the verbs
def kit_build(out: Path) -> dict:
    """The kit build exactly as deploy_field.py makes it: the toml with its id/name forced to the 30606 sandbox
    identity, built by build_mod into ``out`` for the FF9CustomMap-msgs folder."""
    from ff9mapkit import build as B
    proj = B.FieldProject.load(F.TOML)
    proj.raw.setdefault("field", {})["id"] = F.FIELD_ID
    proj.raw["field"]["name"] = F.FIELD_NAME
    return B.build_mod([proj], out, mod_name=F.MOD_FOLDER)


def _write_plain(p: Path, data: bytes) -> None:
    p.write_bytes(data)


def cmd_build(out: Path | None) -> int:
    probs = F.toml_flag_problems()
    if probs:
        raise SystemExit("the toml's [[flag]] table disagrees with _selfdress_field.TOML_FLAGS:\n  " + "\n  ".join(probs))
    out = Path(out) if out else Path(tempfile.mkdtemp(prefix="selfdress-"))
    mod = out / "mod"
    info = kit_build(mod)
    for w in info.get("warnings", []):
        print(f"kit warning: {w}")
    print(f"kit build: {info['dictionary'][0]}  ->  {mod}")
    seated = patch_mod(mod, F.FIELD_NAME, write=_write_plain)
    for lang, data in seated.items():
        why = F.preflight(data)
        print(f"  {lang}: {len(data)} B seated, preflight {'OK' if why is None else 'FAIL: ' + why}")
        if why:
            return 1
    us = seated.get("us") or next(iter(seated.values()))
    same = sorted(k for k, v in seated.items() if v == us)
    print(f"  languages byte-identical to us: {same}")
    try:
        from ff9mapkit.config import find_game_path
        game = find_game_path()
    except Exception:                                    # noqa: BLE001 - offline without an install is fine
        game = None
    lines = proof(us, game)
    ea = ModLayout(mod).eventanimation_path(f"EVT_{F.FIELD_NAME}").read_text(encoding="utf-8")
    lines += ["== EventAnimation (rewritten from the seated script)", *("  " + x for x in ea.splitlines())]
    (out / "proof.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    print(f"\nwrote {out / 'proof.txt'}")
    return 0


def cmd_deploy() -> int:
    from ff9mapkit.config import find_game_path
    from ff9mapkit.fsutil import atomic_write_bytes, locked_mod_folder
    probs = F.toml_flag_problems()
    if probs:
        raise SystemExit("the toml's [[flag]] table disagrees with the contract:\n  " + "\n  ".join(probs))
    r = subprocess.run([sys.executable, str(DEPLOY_FIELD), str(F.TOML), "--id", str(F.FIELD_ID),
                        "--mod-folder", F.MOD_FOLDER], cwd=REPO)
    if r.returncode != 0:
        raise SystemExit("deploy_field.py failed -- nothing seated")
    root = find_game_path() / F.MOD_FOLDER
    with locked_mod_folder(root):
        seated = patch_mod(root, F.FIELD_NAME, write=atomic_write_bytes)
    lay = ModLayout(root)
    for lang in seated:
        why = F.preflight(lay.eb_path(lang, f"EVT_{F.FIELD_NAME}.eb.bytes").read_bytes())
        print(f"  {lang}: live preflight {'OK' if why is None else 'FAIL: ' + why}")
        if why:
            return 1
    print(f"seated {len(seated)} language(s) of EVT_{F.FIELD_NAME} in {root}\n"
          f"  a NEW id: relaunch the game once to register it.  Revert: py tools/scroll_out/revert_deploy_{F.FIELD_ID}.py")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("verb", choices=["build", "deploy"])
    ap.add_argument("--out", default=None, help="build: the scratch dir (default: a new temp dir)")
    a = ap.parse_args()
    sys.exit(cmd_build(a.out) if a.verb == "build" else cmd_deploy())
