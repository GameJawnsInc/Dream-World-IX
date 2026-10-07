"""ADVERSARIAL VERIFY (GA4): does the instruction walk in eb_consumers.py miss any sysvar-192/207 read, and is the
WORLD08 switch really the ONLY writer of the beach-visit bits GLOB 856..876?

  1. RAW upper bound: count every byte pair 0x7A 0xC0 (B_SYSVAR 192) and 0x7A 0xCF (B_SYSVAR 207) in every stock
     dispatcher in EVERY language. Then count, through the kit disassembler, how many of those byte pairs sit inside
     a decoded expression. raw >= decoded always; raw - decoded must be explained (non-code bytes).
  2. Swallowed exceptions: eb_consumers.scan() does `except Exception: continue` on instr_expr_tokens. Count them.
  3. Beach bits: every expression in every stock dispatcher (us) that mentions Global.Bit[856..876], with its
     dispatcher/entry/tag and whether it is a write (B_LET) -- and every C# setVarManually on 856+i.

Rerun: py studies/terrain-malleability/gap_area_layer/verify_eb_area.py
"""
import re
import sys
from collections import Counter
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, r"C:\gd\Dream-World-IX\ff9mapkit")
from ff9mapkit.world import entrance as EN          # noqa: E402
from ff9mapkit.eb.model import EbScript             # noqa: E402
from ff9mapkit.eb import disasm as D                # noqa: E402

B_SYSVAR = 0x7A
alld = EN.load_all_dispatchers()
langs = Counter()
raw_tot = Counter()
dec_tot = Counter()
exc_tot = 0
beach_rows = []
for name in sorted(alld):
    for lang, data in sorted(alld[name].items()):
        langs[lang] += 1
        raw = Counter()
        for v in (192, 207):
            raw[v] = len(re.findall(re.escape(bytes([B_SYSVAR, v])), data))
        s = EbScript(data)
        dec = Counter()
        for e in s.entries:
            for f in e.funcs:
                for i in D.iter_code(s.data, f.abs_start, f.abs_end):
                    try:
                        toks = D.instr_expr_tokens(s.data, i)
                    except Exception:               # noqa: BLE001
                        exc_tot += 1
                        continue
                    for t in toks:
                        if not t:
                            continue
                        for (o, v) in t:
                            if o == B_SYSVAR and v in (192, 207):
                                dec[v] += 1
                    if lang == "us" and i.op == 0x05:
                        txt, _ = D.pretty_expr(s.data, i.off + 1)
                        for b in re.findall(r"Global\.Bit\[(\d+)\]", txt):
                            if 856 <= int(b) <= 876:
                                beach_rows.append((name, e.index, f.tag, i.off, int(b), "B_LET" in txt, txt[:90]))
        for v in (192, 207):
            raw_tot[(lang, v)] += raw[v]
            dec_tot[(lang, v)] += dec[v]
        if raw != dec:
            print(f"  {name} {lang}: raw {dict(raw)} decoded {dict(dec)}")
print("languages:", dict(langs))
for k in sorted(raw_tot):
    print(f"  lang={k[0]} sysvar {k[1]}: raw byte pairs {raw_tot[k]}, decoded reads {dec_tot[k]}")
print("instr_expr_tokens exceptions swallowed:", exc_tot)
print("\nGLOB 856..876 references (us):")
by_disp = Counter((r[0], r[5]) for r in beach_rows)
for k, v in sorted(by_disp.items()):
    print(f"  {k[0]} {'WRITE' if k[1] else 'read '}: {v}")
for r in beach_rows:
    if r[0] != "evt_world_world08":
        print("   non-WORLD08:", r)
# C# writers of the beach bits
cs = Path(r"C:\gd\FFIX\Memoria\Assembly-CSharp")
for p in cs.rglob("*.cs"):
    if "\\obj\\" in str(p):
        continue
    t = p.read_text(encoding="utf-8", errors="replace")
    for ln, line in enumerate(t.splitlines(), 1):
        if "856" in line and ("setVarManually" in line or "getVarOperation" in line):
            print(f"  C# {p.relative_to(cs)}:{ln}: {line.strip()[:140]}")
