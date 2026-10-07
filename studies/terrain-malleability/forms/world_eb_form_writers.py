"""forms lane -- can a world .eb drive the form switch?  Census of the 13 shipping world dispatchers (EVT_WORLD_*,
'us' copies, read-only from p0data via ff9mapkit.world.entrance.load_all_dispatchers):

  (a) every RunWorldCode (0xC4, WPRM) function code used, flagging 501/502 -- the only engine path from an .eb to
      w_worldChangeBlockSet / ResetBlockForms (ff9.cs:4162-4190);
  (b) every gEventGlobal variable token, decoded with the kit's own decode_var, looking for the bits the two
      flag-gated places read (byte 101: 0x40 ChocoboParadise, 0x80 MognetCentral -> Global.Bit[814] / [815], or a
      byte/word view of byte 101) -- i.e. whether the WORLD script itself touches the form-driving bits.
CALIBRATION (both must pass or the census is void):
  * (a) finds exactly 18 immediate RunWorldCode(26, imm) -- the Ragtime-Mouse writes the encounter study counted
    (memory project-ff9-overworld-worlds.md);
  * (b) finds Global.Bit[1608] -- the case-205 consumer gate that same memory quotes (`!GLOB.Bit[1608]`).
Rerun:  py world_eb_form_writers.py
"""
import sys, re, collections
sys.path.insert(0, r"C:\gd\Dream-World-IX\ff9mapkit")
from ff9mapkit.world import entrance as E
from ff9mapkit.eb.model import EbScript
from ff9mapkit.eb.disasm import instr_expr_tokens
from ff9mapkit.eb._exprtable import decode_var

TARGET = re.compile(r"^Global\.(Bit\[(814|815)\]|\w*Byte\[101\]|\w*Int16\[100\])$")

alld = E.load_all_dispatchers()
codes = collections.Counter()
by_disp = {}
glob_hits = []
gvars = collections.Counter()
n26 = 0
for name in sorted(alld):
    data = alld[name].get("us")
    if not data:
        continue
    s = EbScript(data)
    used = collections.Counter()
    for e in s.entries:
        for f in e.funcs:
            for i in s.instrs(f):
                if i.op == 0xC4:
                    c = i.imm(0)
                    used[c if c is not None else "expr"] += 1
                    if c == 26 and not i.arg_is_expr[1]:
                        n26 += 1
                for toks in instr_expr_tokens(data, i):
                    for o, v in (toks or []):
                        if 0xC0 <= o and o != 0xD3 and isinstance(v, int):
                            var = decode_var(o, v)
                            if var.startswith("Global."):
                                gvars[var] += 1
                                if TARGET.match(var):
                                    glob_hits.append((name, e.index, f.tag, var, str(i)[:120]))
    by_disp[name] = dict(used)
    codes.update(used)
print("dispatchers scanned:", len(by_disp))
print("RunWorldCode codes across all dispatchers:", dict(sorted(codes.items(), key=lambda kv: str(kv[0]))))
print("calibration (a): immediate RunWorldCode(26, imm) writes =", n26, "(expected 18)")
assert n26 == 18, n26
print("calibration (b): Global.Bit[1608] refs =", gvars.get("Global.Bit[1608]", 0), "(expected > 0)")
assert gvars.get("Global.Bit[1608]", 0) > 0
users = {n: {k: v for k, v in u.items() if k in (501, 502)} for n, u in by_disp.items() if 501 in u or 502 in u}
print("RunWorldCode 501/502 users:", users or "NONE")
print(f"world-.eb refs to the form-driving gEventGlobal bits (Bit 814/815, byte 101): {len(glob_hits)}")
for h in glob_hits[:20]:
    print("   ", h)
print("distinct Global vars referenced:", len(gvars))
