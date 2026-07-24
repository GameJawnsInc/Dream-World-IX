"""Rung 1 — THE SWARM BENCH (fort-condor study).

A native fork of Lindblum's Festival square (576) carrying 40 Mu chasers whose Loop bodies
run the Festival-of-the-Hunt chase idiom byte-for-byte (SetPathing + per-frame
Walk(obj(250).x, obj(250).z) — decoded from field 552 entry 16 func 15). A tier lever at
the spawn arms 10/20/30/40 movers via GLOB flags 8800-8803; Main_Init clears the flags on
every (re)load — so ~ -> Reload field is the bench reset — and starts the GENERIC countdown
timer HUD (ChangeTimerTime/ShowTimer/RunTimer, the Hunt's exact start sequence) to prove
the rung-0 claim that the match clock is not id-hardcoded.

Every chaser's arm condition also evaluates a B_PTR(250) B_DISTANCEA poll each frame
(OR-1'd so it can't affect behavior): the DistanceWithEntry cost rides every tier
constantly, isolating MOVER cost (varies by tier) from POLL cost (constant 40).

Usage (from the repo root):
    py studies/fort-condor/swarm_bench.py gen      # write C:/gd/_swarm_bench/SWARM.field.toml
    py studies/fort-condor/swarm_bench.py deploy   # deploy_field --id 30400 + patch the .eb(s)

First deploy of id 30400 needs a game RELAUNCH (DictionaryPatch registration); after that,
toml/patch edits hot-reload via ~ -> Reload field. Revert: py tools/scroll_out/revert_deploy_30400.py
"""
from __future__ import annotations

import argparse
import re
import struct
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
KIT = REPO / "ff9mapkit"
sys.path.insert(0, str(KIT))

from ff9mapkit.eb import edit as eb_edit                # noqa: E402
from ff9mapkit.eb import exprasm, opcodes               # noqa: E402
from ff9mapkit.eb.model import EbScript                 # noqa: E402
from ff9mapkit import eblint                            # noqa: E402
from ff9mapkit.scene.bgi import BgiWalkmesh, _pt_in_tri_xz  # noqa: E402

BENCH = Path("C:/gd/_swarm_bench")
BASE_TOML = BENCH / "LDBM_NATIVE.field.toml"
SWARM_TOML = BENCH / "SWARM.field.toml"
FIELD_ID = 30400
FIELD_NAME = "SWARM"
MOD_FOLDER = "FF9CustomMap"
GAME = Path(r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX")

N_CHASERS = 40
BAND = 10                                   # chasers per tier
TIER_FLAGS = [8800, 8801, 8802, 8803]       # GLOB Bit: arm 10 / 20 / 30 / 40
CHASER_MODEL = "GEO_MON_F0_MUU"             # Mu (248) — the chase-loop donor's own model
CHASER_MODEL_ID = 248
TIMER_SECONDS = 600
SPAWN = (2833, -791)                        # the import's player spawn
LEVER_CENTER = (2833, -430)                 # just north of spawn

OP_SET_OBJECT_FLAGS = 0x93
OP_WALK = 0x23
OP_CHANGE_TIMER = 0x69
OP_SHOW_TIMER = 0x8D
OP_RUN_TIMER = 0x7D
JMP, JMP_IFNOT = 0x01, 0x02


# --------------------------------------------------------------- expression builders
def expr_stmt(text: str) -> bytes:
    """An opcode-0x05 expression statement from pretty_expr text (assembler self-verifies)."""
    return bytes([0x05]) + exprasm.assemble(text)


def clear_flag_stmt(idx: int) -> bytes:
    # stock assign shape: { target value B_LET } (e.g. field 552 @19158)
    return expr_stmt(f"Global.Bit[{idx}] const(0) B_LET B_EXPR_END")


def arm_condition(band: int) -> bytes:
    """(tier flag OR any higher tier). Flags only — NO player-referencing terms.

    THE PLAYER-REF EVAL LAW (minted by this bench's first playtest, 2026-07-24): a
    B_PTR/B_DISTANCEA expression hard-casts the resolved objects to Actor
    (EBin.cs:1161-1173) and GetObjUID(250) resolves the CONTROLLED alias — evaluating it
    before a controlled Actor exists throws InvalidCastException INSIDE the 0x05
    evaluation, nothing is pushed, and the following 0x02 pops an empty CalcStack =
    permanent per-frame desync (8287 CalcStack.pop errors, stuck black screen). Stock
    corollary: the Hunt's DistanceWithEntry poller (552 entry 17) only STARTS after the
    player is staged. So: player-referencing expressions only ever run behind a
    player-alive gate — here, the armed branch (arming requires the lever = a player)."""
    toks = []
    for i, f in enumerate(TIER_FLAGS[band:]):
        toks.append(f"Global.Bit[{f}]")
        if i:
            toks.append("B_OROR")
    toks.append("B_EXPR_END")
    return bytes([0x05]) + exprasm.assemble(" ".join(toks))


def poll_condition() -> bytes:
    """The DistanceWithEntry cost probe — ARMED-ONLY (see the law above). OR-1'd truthy
    so it cannot affect behavior; its value is consumed by a 0x02 that falls through
    either way. Poll cost therefore scales WITH the armed tier (the honest composite —
    a real unit polls only while it exists and acts)."""
    return bytes([0x05]) + exprasm.assemble(
        "B_PTR(250) B_DISTANCEA const(32000) B_LT const(1) B_OR B_EXPR_END")


# --------------------------------------------------------------- bytecode blocks
def chase_loop_body(band: int) -> bytes:
    """The per-chaser Loop (tag 1) body — the Mu chase loop generalized:

        top:  SetObjectFlags(7); SetWalkSpeed(50); SetPathing(1); SetWalkTurnSpeed(16)
              if (armed) {                       # flags only — player-safe
                  (distance-poll, consumed)      # armed-only: player exists
                  InitWalk(); Walk(player.x, player.z)
              }
        wait: Wait(1); JMP top
    """
    px = exprasm.assemble("obj(uid=250).f[0] B_EXPR_END")
    pz = exprasm.assemble("obj(uid=250).f[2] B_EXPR_END")
    setup = (opcodes.encode(OP_SET_OBJECT_FLAGS, 7)
             + opcodes.set_walk_speed(50)
             + opcodes.set_pathing(1)
             + opcodes.set_walk_turn_speed(16))
    cond = arm_condition(band)
    chase = opcodes.init_walk() + opcodes.encode(OP_WALK, px, pz, arg_flags=0b11)
    poll = poll_condition()
    # the poll's value is consumed by a fall-through-either-way 0x02 (offset 0 = its own
    # end); OR-1 makes it always-true so the chase always runs when armed
    poll_sink = bytes([JMP_IFNOT]) + struct.pack("<H", 0)
    armed_block = poll + poll_sink + chase
    gate = bytes([JMP_IFNOT]) + struct.pack("<H", len(armed_block))   # skip when unarmed
    wait = opcodes.wait(1)
    upto = setup + cond + gate + armed_block + wait
    jback = bytes([JMP]) + struct.pack("<h", -(len(upto) + 3))        # offset from instr END
    return upto + jback + opcodes.RETURN


def main_init_prepend() -> bytes:
    """Bench reset + the generic-timer probe (the Hunt's exact start triplet)."""
    out = b"".join(clear_flag_stmt(f) for f in TIER_FLAGS)
    out += opcodes.encode(OP_CHANGE_TIMER, TIMER_SECONDS)
    out += opcodes.encode(OP_SHOW_TIMER, 1)
    out += opcodes.encode(OP_RUN_TIMER, 1)
    return out


# --------------------------------------------------------------- walkmesh grid
def grid_positions() -> list[tuple[int, int]]:
    mesh = BgiWalkmesh.from_bytes((BENCH / "walkmesh.bgi").read_bytes())
    wv = mesh.world_verts()
    tris = [tuple(wv[i] for i in t.vtx) for t in mesh.tris]

    def on_mesh(x: float, z: float) -> bool:
        return any(_pt_in_tri_xz(x, z, a, b, c) for a, b, c in tris)

    pts = []
    for z in range(-2400, 1401, 350):
        for x in range(-600, 5601, 350):
            if (x - SPAWN[0]) ** 2 + (z - SPAWN[1]) ** 2 < 500 ** 2:
                continue                                   # keep the spawn/lever area clear
            if on_mesh(x, z):
                pts.append((x, z))
    if len(pts) < N_CHASERS:
        raise SystemExit(f"only {len(pts)} on-mesh grid points — widen the lattice")
    step = len(pts) / N_CHASERS
    return [pts[int(i * step)] for i in range(N_CHASERS)]


# --------------------------------------------------------------- gen
def gen() -> None:
    text = BASE_TOML.read_text(encoding="utf-8")
    # own-id text block: custom prompt text must NOT squat the donor's real block 276
    text = re.sub(r"(?m)^text_block = \d+", f"text_block = {FIELD_ID}", text)
    text = re.sub(r"(?m)^id = \d+", f"id = {FIELD_ID}", text)
    text = re.sub(r'(?m)^name = "[^"]+"', f'name = "{FIELD_NAME}"', text)

    parts = [text, "\n# ---- SWARM BENCH (generated by studies/fort-condor/swarm_bench.py) ----\n"]
    for i, (x, z) in enumerate(grid_positions()):
        parts.append(f'\n[[npc]]\nname = "chaser{i:02d}"\nmodel = "{CHASER_MODEL}"\n'
                     f'pos = [{x}, {z}]\n')

    cx, cz = LEVER_CENTER
    h = 220
    rows = "".join(
        f'\n[[choice.options]]\ntext = "{(b + 1) * BAND} movers"\n'
        f'reply = "{(b + 1) * BAND} released! (~ Reload to reset)"\nset_flag = [{f}, 1]\n'
        for b, f in enumerate(TIER_FLAGS))
    parts.append(
        f'\n[[choice]]\nzone = [[{cx - h},{cz + h}],[{cx + h},{cz + h}],'
        f'[{cx + h},{cz - h}],[{cx - h},{cz - h}]]\n'
        f'prompt = "Swarm bench: release how many movers?"\ninstant = true\n'
        f'{rows}\n[[choice.options]]\ntext = "None for now."\n')

    SWARM_TOML.write_text("".join(parts), encoding="utf-8")
    print(f"wrote {SWARM_TOML}  ({N_CHASERS} chasers + tier lever)")


# --------------------------------------------------------------- patch
def patch_eb(data: bytes) -> bytes:
    eb = EbScript.from_bytes(data)
    sig = bytes([0x2F, 0x00]) + struct.pack("<H", CHASER_MODEL_ID)[:2] + b"\x00"
    # SetModel(248, animset): 2F 00 F8 00 <animset> — match on the first 4 bytes
    sig = sig[:4]
    standby = bytes([0x22, 0x00, 0x01, 0x01, 0xFA, 0xFF])   # content.npc.NPC_STANDBY_LOOP
    chaser_entries = []
    for idx in range(eb.entry_count):
        e = eb.entry(idx)
        f0, f1 = e.func_by_tag(0), e.func_by_tag(1)
        if f0 is None or f1 is None:
            continue
        # a chaser = our model AND the kit NPC standby loop (carried donor 248-model
        # objects keep their real donor loops and must stay verbatim)
        if sig in bytes(data[f0.abs_start:f0.abs_end]) \
                and bytes(data[f1.abs_start:f1.abs_end]) == standby:
            chaser_entries.append(idx)
    if len(chaser_entries) != N_CHASERS:
        raise SystemExit(f"expected {N_CHASERS} chaser entries (SetModel {CHASER_MODEL_ID}), "
                         f"found {len(chaser_entries)}: {chaser_entries}")
    baseline = {str(p) for p in eblint.lint_eb(bytes(data))}
    out = bytes(data)
    for i, idx in enumerate(chaser_entries):
        out = eb_edit.replace_function_body(out, idx, 1, chase_loop_body(i // BAND))
    out = eb_edit.insert_in_function(out, 0, 0, 0, main_init_prepend())
    fresh = [p for p in eblint.lint_eb(out)
             if getattr(p, "severity", "error") == "error" and str(p) not in baseline]
    if fresh:
        raise SystemExit("NEW lint errors after patch:\n" + "\n".join(map(str, fresh)))
    return out


def deploy() -> None:
    if not SWARM_TOML.exists():
        gen()
    r = subprocess.run([sys.executable, str(REPO / "tools" / "deploy_field.py"),
                        str(SWARM_TOML), "--id", str(FIELD_ID), "--name", FIELD_NAME,
                        "--text-block", str(FIELD_ID), "--mod-folder", MOD_FOLDER])
    if r.returncode != 0:
        raise SystemExit("deploy_field failed")

    ebs = sorted((GAME / MOD_FOLDER).rglob(f"*{FIELD_NAME}*.eb*"))
    ebs = [p for p in ebs if p.suffix in (".eb", ".bytes")]
    if not ebs:
        raise SystemExit(f"no deployed .eb found under {GAME / MOD_FOLDER} for {FIELD_NAME}")
    for p in ebs:
        patched = patch_eb(p.read_bytes())
        p.write_bytes(patched)
        print(f"patched {p}  ({len(patched)} bytes)")
    print(f"\nPLAYTEST: relaunch (first deploy of {FIELD_ID}) -> ~ -> Warp -> {FIELD_ID}"
          f"\n  - countdown clock visible (the generic-timer probe)"
          f"\n  - stand at spawn, press Confirm -> pick 10/20/30/40 movers"
          f"\n  - judge frame feel per tier; ~ -> Reload field = reset"
          f"\n  - revert: py tools/scroll_out/revert_deploy_{FIELD_ID}.py")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["gen", "deploy"])
    args = ap.parse_args()
    (gen if args.cmd == "gen" else deploy)()


if __name__ == "__main__":
    main()
