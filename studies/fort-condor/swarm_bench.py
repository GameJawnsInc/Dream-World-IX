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
import json
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
# donor (2nd round): field 559, Lindblum B.D. Square (lb_plz) — pitch 68.8 deg, nearly
# top-down, THE Hunt's Zaghnol arena. Round 1's 576 was pitch -4.9 (ground-parallel:
# the swarm was unobservable — the lint's out-of-range pitch warning was the tell).

OP_SET_OBJECT_FLAGS = 0x93
OP_WALK = 0x23
OP_CHANGE_TIMER = 0x69
OP_SHOW_TIMER = 0x8D
OP_RUN_TIMER = 0x7D
JMP, JMP_IFNOT, JMP_IF = 0x01, 0x02, 0x03

# ---- rung 2: the two-lane skirmish (unit-vs-unit auto-battle) ----
SKIRMISH_FLAG = 8804                        # GLOB Bit: lever row 5 arms the skirmish
BREACH_FLAG = 8805                          # GLOB Bit: breach announced (once-guard)
ATTACKER_MODEL_ID, DEFENDER_MODEL_ID, HERALD_MODEL_ID = 247, 217, 218
ATTACKER_MODEL, DEFENDER_MODEL, HERALD_MODEL = \
    "GEO_MON_F0_FFG", "GEO_NPC_F0_CSO", "GEO_NPC_F2_CSO"
# GLOB BYTES (bits 8816+ region; distinct from the 8800-8805 bits in byte 1100):
HP_BYTES = [1102, 1103, 1104, 1105]         # attackerA, defenderA, attackerB, defenderB
TIMER_BYTES = [1106, 1107, 1108, 1109]      # per-unit swing timers
HP_PRESET = [3, 5, 5, 3]                    # lane A: defender wins; lane B: attacker breaches
CONTACT_R = 150                             # fight range (the Hunt's battle radius was 300)
ACQUIRE_R = 1500                            # defender aggro radius
SWING_FRAMES = 30                           # ~1 damage/second
SKIRMISH_JSON = BENCH / "skirmish.json"


def asm(blocks) -> bytes:
    """Two-pass label assembler for jump-bearing bodies. Items: raw bytes, ("label", name),
    or (JMP|JMP_IF|JMP_IFNOT, "target"). Offsets are from the 3-byte jump's END (engine
    truth: EBin.jumpToCommand: 0x01/0x03 signed, 0x02 unsigned forward-only)."""
    pos, labels = 0, {}
    for it in blocks:
        if isinstance(it, tuple) and it[0] == "label":
            labels[it[1]] = pos
        elif isinstance(it, tuple):
            pos += 3
        else:
            pos += len(it)
    out, pos = bytearray(), 0
    for it in blocks:
        if isinstance(it, tuple) and it[0] == "label":
            continue
        if isinstance(it, tuple):
            op, target = it
            off = labels[target] - (pos + 3)
            if op == JMP_IFNOT:
                if off < 0:
                    raise ValueError(f"JMP_IFNOT is forward-only (to {target})")
                out += bytes([op]) + struct.pack("<H", off)
            else:
                out += bytes([op]) + struct.pack("<h", off)
            pos += 3
        else:
            out += it
            pos += len(it)
    return bytes(out)


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


def set_byte_stmt(idx: int, value: int) -> bytes:
    return expr_stmt(f"Global.Byte[{idx}] const({value}) B_LET B_EXPR_END")


def unit_loop_body(*, role: str, enemy_uid: int, my_hp: int, enemy_hp: int,
                   my_timer: int, home: tuple[int, int], herald_txid: int = 0) -> bytes:
    """The rung-2 unit state machine (attacker marches on `home`=goal / defender holds
    `home`=post). SAFETY SHAPE (the player-ref eval law generalized to DEAD UIDS): every
    B_PTR(enemy)/obj(enemy) evaluation sits STRUCTURALLY behind the enemy-HP>0 gate as a
    separate statement + jump — never ANDAND'd (RPN has no short-circuit; both operands
    would evaluate and a terminated uid casts/derefs to a crash). A dead unit's HP hits 0
    one tick before its self-TerminateEntry, so a live peer's HP gate always wins the race."""
    hx, hz = home
    setup = (opcodes.encode(OP_SET_OBJECT_FLAGS, 7)
             + opcodes.set_walk_speed(55 if role == "defender" else 40)
             + opcodes.set_pathing(1)
             + opcodes.set_walk_turn_speed(16))
    chase_enemy = (opcodes.init_walk()
                   + opcodes.encode(OP_WALK,
                                    exprasm.assemble(f"obj(uid={enemy_uid}).f[0] B_EXPR_END"),
                                    exprasm.assemble(f"obj(uid={enemy_uid}).f[2] B_EXPR_END"),
                                    arg_flags=0b11))
    walk_home = opcodes.init_walk() + opcodes.encode(OP_WALK, hx, hz)
    fight = [
        opcodes.turn_toward_object(enemy_uid, 32),
        expr_stmt(f"Global.Byte[{my_timer}] Global.Byte[{my_timer}] const(1) B_PLUS "
                  f"B_LET B_EXPR_END"),
        expr_stmt(f"Global.Byte[{my_timer}] const({SWING_FRAMES}) B_LT B_EXPR_END"),
        (JMP_IF, "wait"),
        set_byte_stmt(my_timer, 0),
        expr_stmt(f"Global.Byte[{enemy_hp}] Global.Byte[{enemy_hp}] const(1) B_MINUS "
                  f"B_LET B_EXPR_END"),
        (JMP, "wait"),
    ]
    blocks = [
        ("label", "top"),
        setup,
        expr_stmt(f"Global.Bit[{SKIRMISH_FLAG}] B_EXPR_END"),
        (JMP_IFNOT, "wait"),
        expr_stmt(f"Global.Byte[{my_hp}] const(0) B_GT B_EXPR_END"),
        (JMP_IFNOT, "death"),
        expr_stmt(f"Global.Byte[{enemy_hp}] const(0) B_GT B_EXPR_END"),
        (JMP_IFNOT, "free"),                               # enemy dead -> free movement
        expr_stmt(f"B_PTR({enemy_uid}) B_DISTANCEA const({CONTACT_R}) B_LT B_EXPR_END"),
        (JMP_IFNOT, "approach"),
        *fight,
        ("label", "approach"),                             # enemy ALIVE, out of contact
    ]
    if role == "defender":
        blocks += [
            expr_stmt(f"B_PTR({enemy_uid}) B_DISTANCEA const({ACQUIRE_R}) B_LT B_EXPR_END"),
            (JMP_IFNOT, "home"),
            chase_enemy,
            (JMP, "wait"),
            ("label", "free"),
            ("label", "home"),
            walk_home,
            (JMP, "wait"),
        ]
    else:                                                  # attacker: march on the goal
        gx0, gx1, gz0, gz1 = hx - CONTACT_R, hx + CONTACT_R, hz - CONTACT_R, hz + CONTACT_R
        blocks += [
            ("label", "free"),
            expr_stmt(f"obj(uid=255).f[0] const({gx0}) B_GT obj(uid=255).f[0] const({gx1}) "
                      f"B_LT B_ANDAND obj(uid=255).f[2] const({gz0}) B_GT B_ANDAND "
                      f"obj(uid=255).f[2] const({gz1}) B_LT B_ANDAND B_EXPR_END"),
            (JMP_IFNOT, "march"),
            expr_stmt(f"Global.Bit[{BREACH_FLAG}] B_EXPR_END"),      # at the goal: breach once
            (JMP_IF, "wait"),
            expr_stmt(f"Global.Bit[{BREACH_FLAG}] const(1) B_LET B_EXPR_END"),
            opcodes.window_async(0, 128, herald_txid),
            (JMP, "wait"),
            ("label", "march"),
            walk_home,
            (JMP, "wait"),
        ]
    blocks += [
        ("label", "death"),
        opcodes.terminate_entry(255),
        ("label", "wait"),
        opcodes.wait(1),
        (JMP, "top"),
        opcodes.RETURN,
    ]
    return asm(blocks)


def main_init_prepend() -> bytes:
    """Bench reset (tier + skirmish flags, HP presets, swing timers — so ~ -> Reload field
    is the full reset) + the generic-timer probe (the Hunt's exact start triplet)."""
    out = b"".join(clear_flag_stmt(f) for f in TIER_FLAGS + [SKIRMISH_FLAG, BREACH_FLAG])
    out += b"".join(set_byte_stmt(b, v) for b, v in zip(HP_BYTES, HP_PRESET))
    out += b"".join(set_byte_stmt(b, 0) for b in TIMER_BYTES)
    out += opcodes.encode(OP_CHANGE_TIMER, TIMER_SECONDS)
    out += opcodes.encode(OP_SHOW_TIMER, 1)
    out += opcodes.encode(OP_RUN_TIMER, 1)
    return out


# --------------------------------------------------------------- walkmesh grid
def read_spawn() -> tuple[int, int]:
    m = re.search(r"(?m)^spawn = \[(-?\d+), (-?\d+)\]", BASE_TOML.read_text(encoding="utf-8"))
    if not m:
        raise SystemExit("no [player] spawn in the base toml")
    return int(m.group(1)), int(m.group(2))


def lattice_points(spawn: tuple[int, int]) -> list[tuple[int, int]]:
    """All on-mesh lattice points (spawn area kept clear), densified until >= N_CHASERS."""
    mesh = BgiWalkmesh.from_bytes((BENCH / "walkmesh.bgi").read_bytes())
    wv = mesh.world_verts()
    tris = [tuple(wv[i] for i in t.vtx) for t in mesh.tris]
    xs = [v[0] for v in wv]
    zs = [v[2] for v in wv]
    x0, x1 = int(min(xs)) + 300, int(max(xs)) - 300
    z0, z1 = int(min(zs)) + 300, int(max(zs)) - 300

    def on_mesh(x: float, z: float) -> bool:
        return any(_pt_in_tri_xz(x, z, a, b, c) for a, b, c in tris)

    step = max(350, min(x1 - x0, z1 - z0) // 9)
    pts: list[tuple[int, int]] = []
    while step >= 200 and len(pts) < N_CHASERS:            # much of a city bbox is buildings —
        pts = []                                           # densify until 40 points land on mesh
        for z in range(z0, z1 + 1, step):
            for x in range(x0, x1 + 1, step):
                if (x - spawn[0]) ** 2 + (z - spawn[1]) ** 2 < 500 ** 2:
                    continue                               # keep the spawn/lever area clear
                if on_mesh(x, z):
                    pts.append((x, z))
        if len(pts) < N_CHASERS:
            step = int(step * 0.7)
    if len(pts) < N_CHASERS:
        raise SystemExit(f"only {len(pts)} on-mesh grid points — widen the lattice")
    return pts


def nearest(pts, x, z):
    return min(pts, key=lambda p: (p[0] - x) ** 2 + (p[1] - z) ** 2)


def skirmish_layout(pts, spawn) -> dict:
    """Lane geometry from the on-mesh lattice: attackers at the far north (west + east),
    the goal near the player spawn, each defender posted ~55% along its lane."""
    goal = nearest(pts, spawn[0] + 400, spawn[1] + 600)
    zmax = max(p[1] for p in pts)
    north = [p for p in pts if p[1] >= zmax - 1000] or sorted(pts, key=lambda p: -p[1])[:2]
    atk = [min(north, key=lambda p: p[0]), max(north, key=lambda p: p[0])]
    posts = [nearest(pts, a[0] + 0.55 * (goal[0] - a[0]), a[1] + 0.55 * (goal[1] - a[1]))
             for a in atk]
    herald = nearest(pts, goal[0] + 350, goal[1])
    return {"attackers": atk, "defenders": posts, "goal": list(goal), "herald": list(herald)}


# --------------------------------------------------------------- gen
def gen() -> None:
    text = BASE_TOML.read_text(encoding="utf-8")
    # own-id text block: custom prompt text must NOT squat the donor's real block
    text = re.sub(r"(?m)^text_block = \d+", f"text_block = {FIELD_ID}", text)
    text = re.sub(r"(?m)^id = \d+", f"id = {FIELD_ID}", text)
    text = re.sub(r'(?m)^name = "[^"]+"', f'name = "{FIELD_NAME}"', text)
    # strip the imported gateways: the bench is a closed room (no wandering into real Lindblum)
    text = re.sub(r"(?ms)^\[\[gateway\]\].*?(?=^\[|\Z)", "", text)

    spawn = read_spawn()
    pts = lattice_points(spawn)
    parts = [text, "\n# ---- SWARM BENCH (generated by studies/fort-condor/swarm_bench.py) ----\n"]
    pick = len(pts) / N_CHASERS
    for i in range(N_CHASERS):
        x, z = pts[int(i * pick)]
        # explicit dialogue: a dialogue-less kit NPC's default talk shares txid 500 with the
        # [[choice]] prompt -> talking to any chaser rendered the menu rows with no dispatch
        # behind them (playtest-2 finding). An own line = an own txid = no collision.
        parts.append(f'\n[[npc]]\nname = "chaser{i:02d}"\nmodel = "{CHASER_MODEL}"\n'
                     f'pos = [{x}, {z}]\ndialogue = "Kweh!"\n')

    # ---- rung 2: the skirmish cast (2 lanes: attacker marches, defender intercepts) ----
    lay = skirmish_layout(pts, spawn)
    for i, (ax, az) in enumerate(lay["attackers"]):
        parts.append(f'\n[[npc]]\nname = "attacker{i}"\nmodel = "{ATTACKER_MODEL}"\n'
                     f'pos = [{ax}, {az}]\ndialogue = "Grrrr!"\n')
    for i, (dx, dz) in enumerate(lay["defenders"]):
        parts.append(f'\n[[npc]]\nname = "defender{i}"\nmodel = "{DEFENDER_MODEL}"\n'
                     f'pos = [{dx}, {dz}]\ndialogue = "For Lindblum! Hold the line!"\n')
    hx, hz = lay["herald"]
    parts.append(f'\n[[npc]]\nname = "herald"\nmodel = "{HERALD_MODEL}"\n'
                 f'pos = [{hx}, {hz}]\n'
                 f'dialogue = "The beasts broke through!  The gate is lost!"\n')
    SKIRMISH_JSON.write_text(json.dumps(lay), encoding="utf-8")

    cx, cz = spawn                         # the lever zone CONTAINS the spawn point
    h = 220
    rows = "".join(
        f'\n[[choice.options]]\ntext = "{(b + 1) * BAND} movers"\n'
        f'reply = "{(b + 1) * BAND} released! (~ Reload to reset)"\nset_flag = [{f}, 1]\n'
        for b, f in enumerate(TIER_FLAGS))
    rows += (f'\n[[choice.options]]\ntext = "Skirmish demo"\n'
             f'reply = "The beasts are loose!  Soldiers, hold the line!"\n'
             f'set_flag = [{SKIRMISH_FLAG}, 1]\n')
    parts.append(
        f'\n[[choice]]\nzone = [[{cx - h},{cz + h}],[{cx + h},{cz + h}],'
        f'[{cx + h},{cz - h}],[{cx - h},{cz - h}]]\n'
        f'prompt = "Swarm bench: release how many movers?"\ninstant = true\n'
        f'{rows}\n[[choice.options]]\ntext = "None for now."\n')

    SWARM_TOML.write_text("".join(parts), encoding="utf-8")
    print(f"wrote {SWARM_TOML}  ({N_CHASERS} chasers + 2-lane skirmish + lever)")
    print(f"  skirmish: attackers {lay['attackers']}  posts {lay['defenders']}"
          f"  goal {lay['goal']}  herald {lay['herald']}")


# --------------------------------------------------------------- patch
STANDBY = bytes([0x22, 0x00, 0x01, 0x01, 0xFA, 0xFF])       # content.npc.NPC_STANDBY_LOOP


def _model_sig(model_id: int) -> bytes:
    return bytes([0x2F, 0x00]) + struct.pack("<H", model_id)  # SetModel(id, ·) head


def _kit_npcs_by_model(data: bytes, eb: EbScript, model_id: int) -> list[int]:
    """Entry indices of KIT-built NPCs wearing model_id (standby loop = never a carried
    donor object), ascending = toml order."""
    sig, out = _model_sig(model_id), []
    for idx in range(eb.entry_count):
        e = eb.entry(idx)
        f0, f1 = e.func_by_tag(0), e.func_by_tag(1)
        if f0 is None or f1 is None:
            continue
        if sig in bytes(data[f0.abs_start:f0.abs_end]) \
                and bytes(data[f1.abs_start:f1.abs_end]) == STANDBY:
            out.append(idx)
    return out


def _talk_txid(data: bytes, eb: EbScript, idx: int) -> int:
    """The txid of a kit NPC's talk WindowSync (1F 00 <win> <flags> <txid u16>)."""
    f3 = eb.entry(idx).func_by_tag(3)
    body = bytes(data[f3.abs_start:f3.abs_end])
    at = body.index(bytes([0x1F, 0x00]))
    return struct.unpack_from("<H", body, at + 4)[0]


def patch_eb(data: bytes) -> bytes:
    eb = EbScript.from_bytes(data)
    chaser_entries = _kit_npcs_by_model(data, eb, CHASER_MODEL_ID)
    if len(chaser_entries) != N_CHASERS:
        raise SystemExit(f"expected {N_CHASERS} chaser entries (SetModel {CHASER_MODEL_ID}), "
                         f"found {len(chaser_entries)}: {chaser_entries}")
    attackers = _kit_npcs_by_model(data, eb, ATTACKER_MODEL_ID)
    defenders = _kit_npcs_by_model(data, eb, DEFENDER_MODEL_ID)
    heralds = _kit_npcs_by_model(data, eb, HERALD_MODEL_ID)
    if len(attackers) != 2 or len(defenders) != 2 or len(heralds) != 1:
        raise SystemExit(f"skirmish cast mismatch: attackers {attackers} defenders "
                         f"{defenders} heralds {heralds}")
    herald_txid = _talk_txid(data, eb, heralds[0])
    lay = json.loads(SKIRMISH_JSON.read_text(encoding="utf-8"))

    baseline = {str(p) for p in eblint.lint_eb(bytes(data))}
    out = bytes(data)
    for i, idx in enumerate(chaser_entries):
        out = eb_edit.replace_function_body(out, idx, 1, chase_loop_body(i // BAND))
    # rung 2: unit uid == entry index (the stock convention: SetObjectSize(16,...) inside
    # entry 16; Entry17's ObjectUID_24 = entry 24) — in-game verified by the units engaging.
    for lane in (0, 1):
        a_idx, d_idx = attackers[lane], defenders[lane]
        a_hp, d_hp = HP_BYTES[lane * 2], HP_BYTES[lane * 2 + 1]
        out = eb_edit.replace_function_body(out, a_idx, 1, unit_loop_body(
            role="attacker", enemy_uid=d_idx, my_hp=a_hp, enemy_hp=d_hp,
            my_timer=TIMER_BYTES[lane * 2], home=tuple(lay["goal"]),
            herald_txid=herald_txid))
        out = eb_edit.replace_function_body(out, d_idx, 1, unit_loop_body(
            role="defender", enemy_uid=a_idx, my_hp=d_hp, enemy_hp=a_hp,
            my_timer=TIMER_BYTES[lane * 2 + 1], home=tuple(lay["defenders"][lane])))
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
