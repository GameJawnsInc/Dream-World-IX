"""An offline stepper for the PHOTO0 daemon's own bytes -- catches RPN / branch / clamp bugs before a game launch.

It runs the ASSEMBLED body (not a Python re-statement of it): 0x05 statements through a small RPN evaluator,
0x01/0x02 jumps with the engine's offset rules, Wait(1) as the tick boundary, and a MODEL of the camera for the ops the
daemon emits (0xEA, 0xA9, 0x6F, 0x70, 0x71, 0x2D/0x2E). The camera model is the research reading of FieldMap.cs
(HOLD after a move, X clamped at issue to the widescreen window, Y never, dropped when inactive) -- so a pass here says
the DAEMON does what it was written to do against that reading; it says nothing about the engine. The in-game run does.

    py studies/photo-mode/daemon_sim.py        (the self-test; exits non-zero on the first failure)
"""
from __future__ import annotations

import re
import struct
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import photo0_bench as P  # noqa: E402
from ff9mapkit.eb import disasm as D  # noqa: E402

_TOK = re.compile(r"^(Global)\.(Int16|Byte|Bit)\[(\d+)\]$")


class Sim:
    def __init__(self, stage: int, *, spawn=(384, 286), boxw=(199, 569)):
        self.body = P.daemon_body(stage)
        self.mem = bytearray(2048)
        self.pc = 0
        self.keys = 0                     # held logical input bits
        self.prev_keys = 0
        self.keyon = 0                    # this tick's rising edges (ETb.ProcessKeyEvents, once per tick)
        self.uc = 0
        self.bound = False
        self.vrp = list(spawn)            # the engine's view centre (curVRP + co + half), MoveCamera space
        self.follow = list(spawn)         # where follow would put it
        self.state = 0                    # 0 follow, 4 hold, 2 moving, 3 releasing
        self.active = True
        self.move = None                  # (start, end, frames, frame)
        self.boxw = boxw
        self.ssys = [0, 0]
        self.effects = []                 # (tick, name, args)
        self.tick = 0
        self.player_screen = (960, 540)
        self.objflags = {250: 15, 2: 7, 3: 7, 4: 7}  # the show bit is bit 0
        self.meshflags = {2: 0, 3: 0, 4: 0, 250: 0}
        self.pflags = {}
        self.grade = (0, 0, 0)
        self.funcs = {}                   # (uid, tag) -> the flags a seated hide/show function writes

    # -- memory
    def i16(self, off):
        return struct.unpack_from("<h", self.mem, off)[0]

    def poke16(self, off, v):
        struct.pack_into("<h", self.mem, off, v)

    def _load(self, src, typ, idx):
        if typ == "Int16":
            return struct.unpack_from("<h", self.mem, idx)[0]
        if typ == "Byte":
            return self.mem[idx]
        return (self.mem[idx >> 3] >> (idx & 7)) & 1

    def _store(self, ref, v):
        _src, typ, idx = ref
        if typ == "Int16":
            struct.pack_into("<H", self.mem, idx, v & 0xFFFF)
        elif typ == "Byte":
            self.mem[idx] = v & 0xFF
        else:
            if v:
                self.mem[idx >> 3] |= 1 << (idx & 7)
            else:
                self.mem[idx >> 3] &= ~(1 << (idx & 7)) & 0xFF

    # -- RPN
    def _sysvar(self, i):
        return {1: 0, 2: self.uc, 12: self.ssys[0], 13: self.ssys[1]}[i]

    def eval_expr(self, off) -> tuple:
        text, end = D.pretty_expr(self.body, off)
        toks = text.strip("{}").split()
        st = []                                           # (value, ref)
        val = lambda i: st[i][0]                          # noqa: E731
        for t in toks:
            if t == "B_EXPR_END":
                break
            m = _TOK.match(t)
            if m:
                ref = (m.group(1), m.group(2), int(m.group(3)))
                st.append((self._load(*ref), ref))
                continue
            m = re.match(r"^const4?\((-?\d+)\)$", t)
            if m:
                v = int(m.group(1))
                if t.startswith("const(") and v > 0x7FFF:
                    v -= 0x10000                          # B_CONST is a signed Int16
                st.append((v, None))
                continue
            m = re.match(r"^obj\(uid=(\d+)\)\.f\[4\]$", t)
            if m:
                st.append((self.objflags[int(m.group(1))], None))
                continue
            m = re.match(r"^B_SYSVAR\[(\d+)\]$", t)
            if m:
                st.append((self._sysvar(int(m.group(1))), None))
                continue
            if t == "B_KEY":
                v, _ = st.pop()
                st.append((1 if (self.keys & v) else 0, None))
                continue
            if t == "B_KEYON":
                v, _ = st.pop()
                st.append((1 if (self.keyon & v) else 0, None))
                continue
            b, _rb = st.pop()
            a, ra = st.pop()
            if t == "B_LET":
                self._store(ra, b)
                st.append((b, None))
                continue
            f = {"B_PLUS": lambda: a + b, "B_MINUS": lambda: a - b, "B_MULT": lambda: a * b,
                 "B_DIV": lambda: int(a / b), "B_LT": lambda: int(a < b), "B_GT": lambda: int(a > b),
                 "B_LE": lambda: int(a <= b), "B_GE": lambda: int(a >= b), "B_EQ": lambda: int(a == b),
                 "B_NE": lambda: int(a != b), "B_ANDAND": lambda: int(bool(a) and bool(b)),
                 "B_OROR": lambda: int(bool(a) or bool(b)), "B_AND": lambda: a & b, "B_OR": lambda: a | b}[t]
            st.append((f(), None))
        return (st[-1][0] if st else 0), end

    # -- the camera model (one LateUpdate)
    def _late(self):
        if self.state == 2 and self.move:
            s, e, n, k = self.move
            k += 1
            self.vrp = [int(s[i] + (e[i] - s[i]) * k / n) for i in (0, 1)]
            self.move = (s, e, n, k)
            if k >= n:
                self.state = 4
        elif self.state == 3 and self.move:
            s, e, n, k = self.move
            k += 1
            self.fvrp = [s[i] + (e[i] - s[i]) * k / n for i in (0, 1)]
            self.vrp = [int(v) for v in self.fvrp]
            self.move = (s, e, n, k)
            if k >= n:
                self.state = 0
        elif self.state == 0 and self.active:
            self.vrp = list(self.follow)
            self.fvrp = None

    def _op(self, i):
        b = self.body
        if i.op == 0xEA:
            self.ssys = list(self.vrp)
        elif i.op == 0xA9:
            self.ssys = list(self.player_screen)
        elif i.op in (0x6F, 0x70):
            flags, off, vals = b[i.off + 1], i.off + 2, []
            sizes = (2, 2, 1, 1) if i.op == 0x6F else (1, 1)
            for k, sz in enumerate(sizes):
                if flags & (1 << k):
                    v, off = self.eval_expr(off)
                else:
                    v = struct.unpack_from("<h" if sz == 2 else "<B", b, off)[0]
                    off += sz
                vals.append(v)
            self.effects.append((self.tick, "0x%02X" % i.op, vals))
            if not self.active:
                return
            if i.op == 0x6F:
                x = min(max(vals[0], self.boxw[0]), self.boxw[1])
                self.move, self.state = (list(self.vrp), [x, vals[1]], vals[2], 0), 2
            else:
                start = list(getattr(self, "fvrp", None) or self.vrp) if self.state == 3 else list(self.vrp)
                self.move, self.state = (start, list(self.follow), vals[0], 0), 3
        elif i.op == 0x71:
            self.active = bool(b[i.off + 2])
            self.effects.append((self.tick, "0x71", [b[i.off + 2]]))
        elif i.op == 0x2D:
            self.uc = 0
            self.effects.append((self.tick, "0x2D", []))
        elif i.op == 0x14:                               # RunScriptSync(level, uid, tag): the seated flag function
            _lv, uid, tag = b[i.off + 2], b[i.off + 3], b[i.off + 4]
            f = self.objflags[uid]
            self.objflags[uid] = (f & ~1) | {40: 0, 41: 1}[tag]
            self.effects.append((self.tick, "0x14", [uid, tag]))
        elif i.op in (0xD5, 0xD6):
            for u in self.objflags:
                if i.op == 0xD5:
                    self.pflags[u] = self.objflags[u]
                    self.objflags[u] &= ~1
                else:
                    self.objflags[u] = (self.objflags[u] & ~1) | (self.pflags.get(u, 0) & 1)
            self.effects.append((self.tick, "0x%02X" % i.op, []))
        elif i.op in (0x39, 0x3A):
            uid, mesh = b[i.off + 2], b[i.off + 3]
            bit = 1 << mesh
            self.meshflags[uid] = self.meshflags[uid] | bit if i.op == 0x3A else self.meshflags[uid] & ~bit
        elif i.op == 0xEC:
            self.grade = tuple(b[i.off + 5:i.off + 8])
            self.effects.append((self.tick, "0xEC", list(b[i.off + 2:i.off + 8])))
        elif i.op == 0x2E:
            self.uc = 1
            self.effects.append((self.tick, "0x2E", []))

    def run_tick(self, limit: int = 20000):
        """Execute until the next Wait (the tick's end), then one LateUpdate."""
        b = self.body
        self.keyon, self.prev_keys = self.keys & ~self.prev_keys, self.keys
        for _ in range(limit):
            i = next(D.iter_code(b, self.pc, len(b)))
            if i.op == 0x05:
                self.cond, _e = self.eval_expr(i.off + 1)
                self.pc = i.end
            elif i.op == 0x01:
                self.pc = i.end + struct.unpack_from("<h", b, i.off + 1)[0]
            elif i.op == 0x02:
                self.pc = i.end + (struct.unpack_from("<H", b, i.off + 1)[0] if not self.cond else 0)
            elif i.op == 0x22:
                self.pc = i.end
                self._late()
                self.tick += 1
                return
            elif i.op == 0x04:
                raise AssertionError("the daemon RETURNED")
            else:
                self._op(i)
                self.pc = i.end
        raise AssertionError("no Wait within the step limit (a loop without a yield)")

    def g(self, name):
        return self.i16(P.G16.get(name) or P.S16[name])

    def cmd(self, c, ax=0, ay=0, ad=0, at=0):
        self.poke16(P.AX, ax)
        self.poke16(P.AY, ay)
        self.mem[P.AD], self.mem[P.AT] = ad, at
        self.mem[P.CMD] = c


def _expect(ok, what, detail=""):
    print(("  ok   " if ok else "  FAIL ") + what + (f"  [{detail}]" if detail else ""))
    if not ok:
        raise SystemExit(1)


def _boot(stage):
    s = Sim(stage)
    for _ in range(3):
        s.run_tick()
    _expect(s.g("gate") == 3 and s.g("t") == 0, "the latch holds until the player is bound")
    s.uc, s.mem[P.PBOUND >> 3] = 1, s.mem[P.PBOUND >> 3] | (1 << (P.PBOUND & 7))
    for _ in range(P.SETTLE + 3):
        s.run_tick()
    return s


def selftest():
    print("stage 1")
    s = _boot(1)
    _expect((s.g("vx"), s.g("vy")) == (384, 286) and s.g("t") >= 1, "VX/VY mirror the view", (s.g("vx"), s.g("vy")))
    s.keys = P.KEYMASK["right"] | P.KEYMASK["cancel"] | P.KEYMASK["r1"]
    s.run_tick()
    _expect(s.g("keys") == 2 + 32 + 64, "KEYS: right + cancel (const4) + R1 (const4)", s.g("keys"))
    _expect(s.g("fpb") > 0 and s.g("fuc") > 0, "first-true ticks recorded", (s.g("fpb"), s.g("fuc")))
    _expect(not [e for e in s.effects if e[1] in ("0x6F", "0x70", "0x71")], "stage 1 issues no camera op")

    print("stage 2")
    s = _boot(2)
    s.cmd(7)
    s.run_tick()
    _expect(s.uc == 0 and s.g("ack") == 1 and s.g("last") == 7 and s.mem[P.CMD] == 0, "LOCK acks, CMD cleared")
    s.cmd(1, 300, 200)
    s.run_tick()
    _expect((s.g("tx"), s.g("ty")) == (300, 200) and s.g("nmc") == 1, "MOVE1 commands (300,200)")
    s.run_tick()
    _expect((s.g("vx"), s.g("vy")) == (300, 200) and (s.g("txp"), s.g("issp")) == (300, 1),
            "the next tick's mirrors read the move back, with the target + issued flag in force", (s.g("vx"), s.g("vy")))
    s.run_tick()
    _expect(s.g("issp") == 0, "ISSP is per tick")
    s.cmd(3, 40, -24)
    s.run_tick()
    s.run_tick()
    _expect((s.g("vx"), s.g("vy")) == (340, 176), "REL moves relative to the mirrored view", (s.g("vx"), s.g("vy")))
    s.cmd(1, 100, 176)
    s.run_tick(), s.run_tick()
    _expect(s.g("vx") == 199 and s.g("tx") == 100, "model: X clamps at issue", (s.g("vx"), s.g("tx")))
    s.cmd(2, 250, 150, ad=0)
    s.run_tick()
    _expect(s.g("last") == -2 and not [e for e in s.effects if e[0] == s.tick - 1 and e[1] == "0x6F"],
            "MOVEN with a zero duration is REFUSED, never issued", s.g("last"))
    s.cmd(2, 250, 150, ad=30)
    s.run_tick()
    _expect(s.effects[-1][1:] == ("0x6F", [250, 150, 30, 0]), "MOVEN issues (250,150) over 30", s.effects[-1])
    s.cmd(4, ad=0)
    s.run_tick()
    _expect(s.g("last") == -4, "RELEASE with a zero duration is refused")
    s.cmd(4, ad=20, at=8)
    s.run_tick()
    _expect(s.effects[-1][1:] == ("0x70", [20, 8]) and s.g("rt") == 1, "RELEASE(20, 8), RT armed", s.effects[-1])
    for _ in range(5):
        s.run_tick()
    _expect(s.g("rt") == 6, "RT counts ticks since the release", s.g("rt"))
    s.cmd(5)
    s.run_tick()
    s.cmd(1, 300, 200)
    s.run_tick(), s.run_tick()
    _expect(s.effects[-1][1:] == ("0x6F", [300, 200, 1, 0]) and not s.active, "SVC_OFF then a move: issued")
    s.cmd(99)
    s.run_tick()
    _expect(s.g("last") == -99 and s.g("ack") >= 9, "an unknown command is acked as refused", s.g("last"))

    print("stage 3")
    s = _boot(3)
    s.cmd(7)
    s.run_tick()
    s.mem[P.MODE] = 1
    for _ in range(5):
        s.run_tick()
    _expect(s.g("nmc") == 0 and s.g("vx") == 384, "MODE 1 idle issues nothing")
    s.cmd(1, 300, 200)
    s.run_tick()
    s.run_tick()
    _expect((s.g("txp"), s.g("typ"), s.g("issp"), s.g("vx")) == (300, 200, 1, 300),
            "a dispatcher move in MODE 1 with nothing held keeps its target (the idle pan pass writes no TX)",
            (s.g("txp"), s.g("typ"), s.g("issp"), s.g("vx")))
    s.cmd(1, 384, 286)
    s.run_tick(), s.run_tick()
    s.keys = P.KEYMASK["right"]
    for _ in range(10):
        s.run_tick()
    _expect(s.g("vx") == 384 + 4 * (s.g("nr") - 1) and s.g("nr") == 10, "relative pan: VX = VX0 + 4 per held tick "
            "(one tick behind the poll)", (s.g("vx"), s.g("nr")))
    for _ in range(100):
        s.run_tick()
    _expect(s.g("vx") == 569 and s.g("tx") == 573, "X edge: VX 569 while TX 573", (s.g("vx"), s.g("tx")))
    s.keys = P.KEYMASK["left"]
    s.run_tick(), s.run_tick()
    _expect(s.g("vx") == 565, "no wind-up in the relative form", s.g("vx"))
    s.keys = P.KEYMASK["down"]
    for _ in range(40):
        s.run_tick()
    _expect(s.g("vy") == 336 and s.g("ty") == 336, "Y edge: the SCRIPT clamps at 336", (s.g("vy"), s.g("ty")))
    s.keys = P.KEYMASK["up"]
    for _ in range(80):
        s.run_tick()
    _expect(s.g("vy") == 112, "Y edge: 112", s.g("vy"))
    s.keys = 0
    s.mem[P.MODE] = 3
    s.keys = P.KEYMASK["right"]
    for _ in range(150):
        s.run_tick()
    _expect(s.g("tx") == 608 and s.g("vx") == 569, "absolute: TX runs to the script clamp 608", (s.g("tx"), s.g("vx")))
    s.keys = P.KEYMASK["left"]
    vxs = []
    for _ in range(12):
        s.run_tick()
        vxs.append(s.g("vx"))
    # the mirror lags the command by a tick: sample 0 is the pre-left view; commands 1..9 (TX 604..572) are clamped
    # to 569 at issue, command 10 (TX 568) is the first to move it
    _expect(vxs[:10] == [569] * 10 and vxs[10] == 568, "absolute: 9 commands of wind-up, then 568", vxs)
    s.mem[P.MODE] = 0
    s.keys = P.KEYMASK["right"]
    n = s.g("nmc")
    for _ in range(5):
        s.run_tick()
    _expect(s.g("nmc") == n, "MODE 0: the d-pad pans nothing")
    print("stage 4")
    s = Sim(4)
    for _ in range(3):
        s.run_tick()
    s.uc, s.mem[P.PBOUND >> 3] = 1, s.mem[P.PBOUND >> 3] | (1 << (P.PBOUND & 7))
    for _ in range(3):
        s.run_tick()
    _expect(s.g("t") == 0, "stage 4's latch also waits for the props' ready bits")
    for b in (P.READY_L, P.READY_C, P.READY_R):
        s.mem[b >> 3] |= 1 << (b & 7)
    for _ in range(P.SETTLE + 3):
        s.run_tick()
    _expect(s.g("t") >= 1 and s.g("flags") == 15, "FLAGS: all four show bits", s.g("flags"))
    steps = [("FLAG_HIDE_C", 13), ("FLAG_SHOW_C", 15), ("MESH_HIDE_L", 15), ("MESH_SHOW_L", 15),
             ("FLAG_HIDE_P", 14), ("FLAG_SHOW_P", 15), ("HIDEALL", 0), ("SHOWALL", 15)]
    for name, want in steps:
        s.cmd(P.CMDS[name])
        s.run_tick()
        s.run_tick()
        _expect(s.g("flags") == want and s.g("last") == P.CMDS[name], f"{name}: FLAGS {want}", s.g("flags"))
        if name == "MESH_HIDE_L":
            _expect(s.meshflags[2] == 0xFFFF, "MESH_HIDE_L hides meshes 0-15 of uid 2 (the flags untouched)")
        if name == "MESH_SHOW_L":
            _expect(s.meshflags[2] == 0, "MESH_SHOW_L shows them all again")
    s.cmd(P.CMDS["GRADE"])
    s.run_tick()
    _expect(s.grade == (0, 64, 128) and s.effects[-1][2][0] == 2, "GRADE: SUB (mode 2) 0,64,128", s.effects[-1])
    s.cmd(P.CMDS["GRADE_CLEAR"])
    s.run_tick()
    _expect(s.grade == (0, 0, 0), "GRADE_CLEAR", s.grade)
    print("stage 5")
    s = Sim(5)
    s.uc, s.mem[P.PBOUND >> 3] = 1, s.mem[P.PBOUND >> 3] | (1 << (P.PBOUND & 7))
    for b in (P.READY_L, P.READY_C, P.READY_R):
        s.mem[b >> 3] |= 1 << (b & 7)
    for _ in range(P.SETTLE + 3):
        s.run_tick()

    def press(name, ticks=1):
        s.keys = P.KEYMASK[name]
        for _ in range(ticks):
            s.run_tick()
        s.keys = 0
        s.run_tick()
        s.run_tick()

    for n in ("r1", "l1", "cancel"):
        press(n)
    _expect(s.g("modal") == 0 and s.objflags == {250: 15, 2: 7, 3: 7, 4: 7} and s.meshflags[2] == 0
            and s.grade == (0, 0, 0) and s.uc == 1, "closed: R1 / L1 / Cancel edges do nothing")
    v0 = (s.g("vx"), s.g("vy"))
    press("select", ticks=2)
    _expect(s.g("modal") == 1 and s.uc == 0 and s.mem[P.MODE] == 1 and (s.g("vx"), s.g("vy")) == v0
            and any(e[1] == "0x6F" and e[2][:2] == list(v0) for e in s.effects),
            "OPEN: a Select edge (held 2 ticks = ONE edge) locks, takes the view it is on, MODE 1",
            (s.g("modal"), s.uc, s.mem[P.MODE]))
    press("r1")
    _expect(s.meshflags[2] == 0xFFFF and s.g("modal") == 1 + 4, "R1 #1: L by mesh", s.g("modal"))
    press("r1")
    _expect(s.objflags[3] & 1 == 0 and s.g("modal") == 1 + 8, "R1 #2: C by flags", s.g("modal"))
    press("r1")
    _expect(s.objflags[250] & 1 == 0 and s.g("modal") == 1 + 12, "R1 #3: the player by flags", s.g("modal"))
    n14 = sum(e[1] == "0x14" for e in s.effects)
    press("r1")
    _expect(s.g("modal") == 1 + 12 and sum(e[1] == "0x14" for e in s.effects) == n14, "R1 #4: nothing")
    press("l1")
    _expect(s.grade == (0, 64, 128) and s.g("modal") == 1 + 2 + 12, "L1: grade on", s.g("modal"))
    press("l1")
    _expect(s.grade == (0, 0, 0) and s.g("modal") == 1 + 12, "L1: grade off")
    press("l1")
    _expect(s.grade == (0, 64, 128), "L1: grade on again")
    vx = s.g("vx")
    s.keys = P.KEYMASK["right"]
    for _ in range(5):
        s.run_tick()
    s.keys = 0
    s.run_tick(), s.run_tick()
    _expect(s.g("vx") == vx + 20, "the d-pad pans while open", (vx, s.g("vx")))
    press("cancel")
    _expect(s.meshflags[2] == 0 and s.objflags[3] & 1 and s.objflags[250] & 1 and s.grade == (0, 0, 0)
            and s.uc == 1 and s.g("modal") == 0 and s.mem[P.MODE] == 0
            and any(e[1] == "0x70" and e[2] == [16, 8] for e in s.effects),
            "CANCEL: everything shown, grade cleared, ReleaseCamera(16, 8), unlocked, closed")
    want = 1 * 1 + 16 * 2 + 256 * 5 + 4096 * 4
    _expect(s.g("edges") == want, "EDGES counts every edge, open or closed", (s.g("edges"), want))
    print("stage 6")
    import math

    def boot6():
        s6 = Sim(6)
        s6.uc, s6.mem[P.PBOUND >> 3] = 1, s6.mem[P.PBOUND >> 3] | (1 << (P.PBOUND & 7))
        for b in (P.READY_L, P.READY_C, P.READY_R):
            s6.mem[b >> 3] |= 1 << (b & 7)
        for _ in range(P.SETTLE + 3):
            s6.run_tick()
        return s6

    def tap(s6, name):
        s6.keys = P.KEYMASK[name]
        s6.run_tick()
        s6.keys = 0

    def exit_run(exitmode, walk):
        s6 = boot6()
        s6.mem[P.EXITMODE] = exitmode
        tap(s6, "select")
        s6.run_tick()
        s6.keys = P.KEYMASK["right"]
        for _ in range(11):
            s6.run_tick()
        s6.keys = 0
        s6.run_tick(), s6.run_tick()
        start = s6.g("vx")
        tap(s6, "cancel")                                # the Cancel tick's own LateUpdate is glide step 1
        xs = [s6.vrp[0]]
        for k in range(29):
            if walk:
                s6.follow = [s6.follow[0] - 10, s6.follow[1]]   # the player walks left ~10 canvas px a tick
            s6.run_tick()
            xs.append(s6.vrp[0])
        return s6, start, xs

    s6, start, xs = exit_run(0, walk=False)
    ease = [start + (384 - start) * (1 - math.cos(math.pi * k / 16)) / 2 for k in range(1, 17)]
    dev = max(abs(a - b) for a, b in zip(xs[:16], ease))
    _expect(dev <= 1.5 and xs[16:] == [384] * 14 and s6.g("modal") == 0,
            "TRACKING EXIT, still player: traces the approved cosine ease and lands", (round(dev, 2), xs[:17]))
    s6, start, xs = exit_run(0, walk=True)
    steps = [abs(b - a) for a, b in zip([start] + xs[:-1], xs)]
    _expect(xs[-1] == s6.follow[0] and max(steps) <= 40, "TRACKING EXIT, walking player: lands on him, no snap",
            (max(steps), xs[15:18], s6.follow[0]))
    s6o, starto, xso = exit_run(1, walk=True)
    stepso = [abs(b - a) for a, b in zip([starto] + xso[:-1], xso)]
    _expect(max(stepso) >= 100, "EXITMODE 1 (the stage-5 single release), walking: the model shows the snap",
            max(stepso))
    s6 = boot6()
    tap(s6, "select")
    s6.run_tick()
    tap(s6, "cancel")
    s6.run_tick(), s6.run_tick()
    tap(s6, "select")
    n70 = sum(e[1] == "0x70" for e in s6.effects)
    for _ in range(20):
        s6.run_tick()
    _expect(s6.g("modal") & 1 and not s6.g("modal") & 16 and sum(e[1] == "0x70" for e in s6.effects) == n70,
            "re-opening mid-glide stops the tracking: no release is issued into the held camera", s6.g("modal"))
    print("daemon_sim: all green")


if __name__ == "__main__":
    selftest()
