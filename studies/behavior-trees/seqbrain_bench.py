"""THE SEQBRAIN BENCH — the per-unit-brain probes' in-game crossing (30422).

The two side probes the study carried for months ((a) shared-script caller
context, (b) self-REQ) are now ANSWERED AT THE SOURCE — Memoria's EBin.cs:164
sets ``gCur = FindObjByUID(seq.uid - 64)`` (the CALLER) for every tick of a
STARTSEQ coroutine, DoEventCode binds actor/po from gCur, GetObjUID(255)
resolves to gCur, and Request() is a plain ``level < p.level`` gate over a
stack-push — and CALIBRATED against stock (309 of 817 field exports use
RunSharedScript; the shared bodies run bare actor ops on the caller).

What stock does NOT prove — and this bench does — are the four COMPOSITES the
per-unit-brain architecture needs:

  P1  a PERSISTENT-LOOP Seq (stock coroutines are finite cutscene beats):
      both knights bow whenever the player comes near, forever.
  P2  REQ(4, 255, tag) from a Seq as the NATIVE RUN-GATE (requestAcceptable
      ``4 < level`` replaces the whole sel/run byte protocol): the mu patrols
      on a steady rhythm; the brain REQs every 30f into a ~100f body, and the
      overlapping REQs must be silently DROPPED, not queued.
  P3  TWO Seq instances of ONE entry with PRIVATE Instance vars (EBin binds
      ``_instance`` to gExec = the Seq, so per-unit latches need ZERO
      blackboard bytes): each knight's FIRST greeting is a KNEEL, every later
      one a talk gesture — and each knight keeps his OWN count.
  P4  THE ORPHAN-BRAIN LAW's mitigation: a unit's die body must StopSharedScript
      (0x45) BEFORE TerminateEntry(255) — DisposeObj does NOT cascade to the
      Seq, and an orphaned brain NREs the engine on its next tick (DoEventCode
      line 28 derefs gCur unconditionally). Talk to the mu: it leaps, its brain
      is stopped, it vanishes — and the field must SURVIVE 30+ seconds after.
  P5  TRUE SELF-REQ: mu's tag-8 body (KNOWN to run at level 4) self-REQs its
      own tag-10 at level 3 (3 < 4 guaranteed acceptable) — every patrol cycle
      must END WITH A HOP (the ip-redirect call fires, tag-8 resumes after).

THE 64-STRIDE LAW (design constraint, engine-read): a brain Seq's uid is the
unit's uid + 64 (a Byte), and STARTSEQ DISPOSES whatever object already sits
there — so no live object may occupy [unit_uid+64] and unit uids stay < 192.
Kit fields assign uid == entry slot (InitObject(slot, 0) -> uid = sid), so a
<= ~20-entry bench is automatically clean.

Bench-grade shortcut, NOT production: the brains open with Wait(90) instead of
the compiler's staged player-mirror latch, so the B_PTR(250) distance read can
not run before DefinePlayerCharacter. A production brain keeps the mirror.

Usage (repo root):   py studies/behavior-trees/seqbrain_bench.py gen | probe | deploy
30422 is a NEW id -> the FIRST deploy needs a game RELAUNCH (registration),
then ~ -> Reload field re-reads everything (patch included: deploy re-patches).
Revert: py tools/scroll_out/revert_deploy_30422.py
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "ff9mapkit"))

from ff9mapkit import catalog, eblint                                # noqa: E402
from ff9mapkit.config import LANGS, ModLayout, find_game_path        # noqa: E402
from ff9mapkit.content import object as _object                      # noqa: E402
from ff9mapkit.content.behavior import _stmt                         # noqa: E402
from ff9mapkit.content.npc import NPC_STANDBY_LOOP                   # noqa: E402
from ff9mapkit.eb import edit as eb_edit, opcodes                    # noqa: E402
from ff9mapkit.eb.labelasm import JMP, JMP_IFNOT, asm, label         # noqa: E402
from ff9mapkit.eb.model import EbScript                              # noqa: E402
from ff9mapkit.fsutil import atomic_write_bytes                      # noqa: E402

BENCH = Path("C:/gd/_seqbrain_bench")
BASE_TOML = BENCH / "LDBM_NATIVE.field.toml"
BENCH_TOML = BENCH / "SEQBRAIN.field.toml"
FIELD_ID = 30422
FIELD_NAME = "SEQBRAIN"
MOD_FOLDER = "FF9CustomMap"
DONOR = "fbg_n11_ldbm_map158_lb_plz_0"           # 559, the proven yaw-0 bench plaza

KNIGHT_MODEL = "GEO_NPC_F0_CSO"
MU_MODEL = "GEO_MON_F0_MUU"

# own-form gestures (catalog.own_form_gestures -- THE CROSS-FORM CLIP TRAP guard)
KN_KNEEL = 12497        # hiza_1  -- P3's first-greeting special
KN_TALK = 5973          # talk_1_1 -- every later greeting
MU_TURN_L = 6682
MU_TURN_R = 6686
MU_JUMP = 202           # the P5 hop AND the P4 farewell leap

DIE_FLAG = 77           # Map.Byte[77] -- talk-to-mu sets it; transient, never saved.
                        # ⚠ THE MAPVAR-80 LAW: the engine's Map var space is Byte[80]
                        # (EventContext.cs: `mapvar = new Byte[80]`) with NO bounds guard --
                        # round 1 used index 241 and every read threw IndexOutOfRange,
                        # aborting the brain's frame mid-statement (the die lane never fired
                        # and Memoria.log filled with IOOR + CalcStack.pop pairs).
NEAR = 600              # the knights' greeting radius
DISPATCH = 4            # the production dispatch level (requestAcceptable: 4 < 7 idle)
STOP_SHARED_SCRIPT = 0x45


# ------------------------------------------------------------------- brain bodies
def brain_a() -> bytes:
    """The knights' shared brain: greet on approach; FIRST greeting kneels.

    Runs as a Seq -- every bare actor op below drives THE CALLER (gCur), and
    Instance.Byte[0] is THIS SEQ's private latch (one per knight, zero
    blackboard bytes)."""
    return asm([
        opcodes.wait(90),                                   # bench-grade player settle
        label("top"),
        _stmt(f"B_PTR(250) B_DISTANCEA const({NEAR}) B_LT"),
        (JMP_IFNOT, "far"),
        _stmt("Instance.Byte[0] const(0) B_EQ"),
        (JMP_IFNOT, "again"),
        _stmt("Instance.Byte[0] const(1) B_LET"),           # the PRIVATE latch
        opcodes.encode(0x40, KN_KNEEL),                     # RunAnimation on the CALLER
        opcodes.wait(70),
        (JMP, "top"),
        label("again"),
        opcodes.encode(0x40, KN_TALK),
        opcodes.wait(70),
        (JMP, "top"),
        label("far"),
        opcodes.wait(8),
        (JMP, "top"),
        opcodes.RETURN,                                     # unreachable (a brain never returns)
    ])


def brain_b() -> bytes:
    """The mu's brain: the native run-gate dispatcher + the die watch.

    REQ(4, 255, 8) targets gCur = THE CALLING MU (GetObjUID(255)); while tag-8
    runs at level 4, further REQs fail ``4 < 4`` and are silently dropped --
    the whole sel/run byte protocol, engine-native."""
    return asm([
        opcodes.wait(90),
        label("top"),
        _stmt(f"Map.Byte[{DIE_FLAG}] const(1) B_EQ"),
        (JMP_IFNOT, "patrol"),
        opcodes.run_script_async(DISPATCH, 255, 9),         # fire MY unit's die body
        label("halt"),
        opcodes.wait(30),
        (JMP, "halt"),                                      # idle until tag-9's 0x45 disposes me
        label("patrol"),
        opcodes.run_script_async(DISPATCH, 255, 8),         # dropped while tag-8 is busy
        opcodes.wait(30),
        (JMP, "top"),
        opcodes.RETURN,
    ])


def mu_tag8() -> bytes:
    """The patrol body (runs ON the mu at level 4, ~100f -- 3x the REQ cadence),
    ending in P5: a TRUE self-REQ at level 3 (3 < 4 -- guaranteed acceptable)."""
    return asm([
        opcodes.encode(0x40, MU_TURN_L), opcodes.wait(45),
        opcodes.encode(0x40, MU_TURN_R), opcodes.wait(45),
        opcodes.run_script_async(3, 255, 10),               # SELF-REQ -> tag-10 hop, then resume
        opcodes.RETURN,
    ])


def mu_tag9() -> bytes:
    """The die body -- THE ORPHAN-BRAIN LAW's canonical ordering: leap for the
    camera, STOP MY SHARED SCRIPT (0x45 keys off gExec = this mu), THEN dispose
    myself. Swap the last two ops and the engine NREs within a tick."""
    return asm([
        opcodes.encode(0x40, MU_JUMP), opcodes.wait(30),
        opcodes.encode(STOP_SHARED_SCRIPT),
        opcodes.terminate_entry(255),
        opcodes.RETURN,
    ])


def mu_tag10() -> bytes:
    """The P5 hop -- with the announce blip, so a hop is UNMISTAKABLE from the
    silent die leap (round 1 read the per-cycle hops as talk responses)."""
    return asm([opcodes.encode(0xC8, 53248, 683, 0, 128, 125),
                opcodes.encode(0x40, MU_JUMP), opcodes.RETURN])


def seq_entry(body: bytes) -> bytes:
    """A one-function code entry (type 0, tag 0 at fpos 4) -- the STARTSEQ target
    shape. Seated DORMANT (no InitObject): it exists only as code for Seqs."""
    import struct
    return bytes([0x00, 0x01]) + struct.pack("<HH", 0, 4) + body


# ------------------------------------------------------------------- the .eb patch
def patch_eb(eb0: bytes) -> bytes:
    """Seat the two brains, add the mu's tag-8/9/10, splice the STARTSEQs."""
    s = EbScript.from_bytes(eb0)
    npcs = [e.index for e in s.entries
            if e.size > 0 and [f.tag for f in e.funcs] == [0, 1, 3]
            and eb0[e.funcs[1].abs_start:e.funcs[1].abs_end].endswith(NPC_STANDBY_LOOP)]
    if len(npcs) != 3:
        raise SystemExit(f"expected exactly 3 kit NPCs (kn0, kn1, mu), found entries {npcs}")
    kn0, kn1, mu = npcs                                     # toml order == seat order

    baseline = {str(p) for p in eblint.lint_eb(eb0)}
    out = bytes(eb0)
    # the brains: seated dormant; loc=8 allocates each SEQ 8 private var bytes (varn --
    # the entry-table byte our model calls `loc` IS the engine ObjTable's `varn`)
    out, slot_a = _object.seat_entry(out, seq_entry(brain_a()), loc=8)
    out, slot_b = _object.seat_entry(out, seq_entry(brain_b()), loc=8)
    # the mu's bodies
    out = eb_edit.add_function(out, mu, 8, mu_tag8())
    out = eb_edit.add_function(out, mu, 9, mu_tag9())
    out = eb_edit.add_function(out, mu, 10, mu_tag10())
    # STARTSEQ splices -- at the head of each unit's tag-1 (the unit's OWN context;
    # a Main_Init STARTSEQ would bind the brain to the field object instead)
    for unit, brain in ((kn0, slot_a), (kn1, slot_a), (mu, slot_b)):
        out = eb_edit.insert_in_function(out, unit, 1, 0, opcodes.run_shared_script(brain))
    # talk-to-mu arms the die flag (dialogue window follows, untouched)
    out = eb_edit.insert_in_function(out, mu, 3, 0,
                                     _stmt(f"Map.Byte[{DIE_FLAG}] const(1) B_LET"))
    fresh = [p for p in eblint.lint_eb(out)
             if getattr(p, "severity", "error") == "error" and str(p) not in baseline]
    if fresh:
        raise SystemExit("patch produced NEW lint errors:\n  "
                         + "\n  ".join(map(str, fresh)))
    print(f"  patched: brains at slots {slot_a}/{slot_b}, units kn0={kn0} kn1={kn1} mu={mu}, "
          f"+{len(out) - len(eb0)}B")
    return out


# ------------------------------------------------------------------- verbs
def read_spawn(text: str) -> tuple[int, int]:
    m = re.search(r"(?m)^spawn = \[(-?\d+), (-?\d+)\]", text)
    if not m:
        raise SystemExit("no [player] spawn in the base toml")
    return int(m.group(1)), int(m.group(2))


def gen() -> None:
    if not BASE_TOML.exists():
        print(f"importing donor {DONOR} ...")
        r = subprocess.run([sys.executable, "-m", "ff9mapkit", "import", DONOR,
                            "--native", "--out", str(BENCH)], cwd=REPO / "ff9mapkit")
        if r.returncode != 0:
            raise SystemExit("donor import failed")
    text = BASE_TOML.read_text(encoding="utf-8")
    text = re.sub(r"(?m)^text_block = \d+", f"text_block = {FIELD_ID}", text)
    text = re.sub(r"(?m)^id = \d+", f"id = {FIELD_ID}", text)
    text = re.sub(r'(?m)^name = "[^"]+"', f'name = "{FIELD_NAME}"', text)
    text = re.sub(r"(?ms)^\[\[gateway\]\].*?(?=^\[|\Z)", "", text)    # a closed room
    if "entry_settle" not in text:                                    # the owner directive
        text = re.sub(r"(?m)^\[camera\]$", '[camera]\nentry_settle = "auto"', text)
    blocks = re.split(r"(?m)(?=^\[)", text)                           # no donor bystanders
    text = "".join(b for b in blocks
                   if not (b.startswith("[[object]]") and 'kind = "npc"' in b))
    sx, sz = read_spawn(text)
    toml = text + f"""
# ---- THE SEQBRAIN BENCH (generated by studies/behavior-trees/seqbrain_bench.py) ----
# The three units are PLAIN kit NPCs here; the brains are spliced post-build (patch_eb).

[[npc]]
name = "kn0"
model = "{KNIGHT_MODEL}"
pos = [{sx + 260}, {sz - 160}]
face = 160
dialogue = "My first greeting is a KNEEL -- after that, only words. My brother keeps his OWN count; go test him."

[[npc]]
name = "kn1"
model = "{KNIGHT_MODEL}"
pos = [{sx - 280}, {sz - 160}]
face = 96
dialogue = "One kneel each, sir. HIS kneel spends nothing of mine."

[[npc]]
name = "mu"
model = "{MU_MODEL}"
pos = [{sx}, {sz + 420}]
face = 128
dialogue = "KWEEEH! (Farewell -- one leap and gone. Now count thirty seconds: if the field still lives, the orphan law held.)"
"""
    BENCH_TOML.write_text(toml, encoding="utf-8")
    print(f"wrote {BENCH_TOML}  (spawn {sx},{sz})")


def probe() -> None:
    """Offline: build nothing -- just assemble the brains/bodies and decode them back."""
    from ff9mapkit.eb import disasm
    for tag, body in (("brain_a", brain_a()), ("brain_b", brain_b()),
                      ("mu_tag8", mu_tag8()), ("mu_tag9", mu_tag9()), ("mu_tag10", mu_tag10())):
        ops = [i.op for i in disasm.iter_code(body, 0, len(body))]
        print(f"{tag}: {len(body)}B, {len(ops)} ops, "
              f"STARTSEQ={0x43 in ops} REQ={0x10 in ops} ENDSEQ={STOP_SHARED_SCRIPT in ops}")
    print("gestures:", {k: v for k, v in catalog.own_form_gestures(KNIGHT_MODEL).items()
                        if v in (KN_KNEEL, KN_TALK)},
          {k: v for k, v in catalog.own_form_gestures(MU_MODEL).items()
           if v in (MU_TURN_L, MU_TURN_R, MU_JUMP)})


def deploy() -> None:
    if not BENCH_TOML.exists():
        gen()
    r = subprocess.run([sys.executable, str(REPO / "tools" / "deploy_field.py"),
                        str(BENCH_TOML), "--id", str(FIELD_ID), "--name", FIELD_NAME,
                        "--text-block", str(FIELD_ID), "--mod-folder", MOD_FOLDER])
    if r.returncode != 0:
        raise SystemExit("deploy_field failed")
    # patch the LIVE .eb in place (all languages) -- ~ Reload re-reads it, so the
    # patched brains hot-iterate; a re-deploy re-runs this whole step
    live = ModLayout(find_game_path() / MOD_FOLDER)
    patched = 0
    for L in LANGS:
        p = live.eb_path(L, f"EVT_{FIELD_NAME}.eb.bytes")
        if p.exists():
            atomic_write_bytes(p, patch_eb(p.read_bytes()))
            patched += 1
    if not patched:
        raise SystemExit(f"no live EVT_{FIELD_NAME}.eb.bytes found to patch")
    print(f"""patched {patched} language .eb file(s)

PLAYTEST round 2 (already registered -> ~ -> Reload field is enough; P1-P3 passed
round 1 and should simply still hold):
  P5    each of the mu's turn-in-place cycles ends with a BLIP + HOP (~ every
        2s). The blip is new -- it separates the self-REQ hop from the die leap.
        (The model snapping back to straight after each turn is EXPECTED: the
        turn clips are layered one-shots; the actor's true facing never moves.)
  P4    TALK to the mu: dialogue, one SILENT leap, and it VANISHES for good.
        Then wait 30 seconds and keep walking around: the knights must still
        greet, no freeze, no crash (the die body stopped its brain BEFORE
        self-disposal). Round 1 never tested this -- the die flag sat out of
        range and the die lane never fired.
  Also: Memoria.log should stay CLEAN of the once-per-second
        IndexOutOfRange/CalcStack pairs this time.
  Revert: py tools/scroll_out/revert_deploy_{FIELD_ID}.py""")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("verb", choices=["gen", "probe", "deploy"])
    v = ap.parse_args().verb
    {"gen": gen, "probe": probe, "deploy": deploy}[v]()
