"""VERIFIER (forms lane, F3/F4/F17) -- is `WorldMap(<same id>)` from a WORLD .eb a real scene reload in stock?

The lane's F4 cites "WMAPJUMP 0xB6 (DoEventCode.cs:2458) -> mode 3 -> Replace("WorldMap") (WMScriptDirector.cs:225-228)"
as the clean mid-visit refresh. This reads the Memoria SOURCE (read-only) and checks each link of that chain:
  L1  WMAPJUMP's handler returns 5 (the world-jump result code).
  L2  the FIELD tick consumes 5 (HonoluluFieldMain: `case 5:` -> nextMode = 3) -- the calibration that 5 IS the
      world-jump code and that this grep can see a consumer when one exists.
  L3  the WORLD tick (WMScriptDirector.HonoUpdate20FPS) switches on w_frameMainRoutine() -- which cases exist?
  L4  every writer of the FF9Sys.attr 0x1000 bit that arms the WMScriptDirector shutdown/Replace branch.
  L5  every writer of FF9World.map.nextMode = 3 outside HonoAwake's default (WMScriptDirector.cs:56).
If L3 lacks `case 5` and no L4 writer is reachable from a script opcode, a world-originated WorldMap() is INERT in
stock (it only stores FF9World.map.nextMapNo) and the mode==3 Replace branch is reached only by the custom
debug menu (Ff9mkDebugMenu.ArmWorldReload).
Rerun:  py verify_world_reload_chain.py
"""
import re
from pathlib import Path

SRC = Path(r"C:\gd\FFIX\Memoria\Assembly-CSharp")


def read(rel):
    return (SRC / rel).read_text(encoding="utf-8-sig", errors="replace")


doe = read("Global/Event/Engine/EventEngine.DoEventCode.cs")
m = re.search(r"case EBin\.event_code_binary\.WMAPJUMP:.*?return (\d+);", doe, re.S)
print("L1 WMAPJUMP handler returns:", m.group(1))
assert m.group(1) == "5"

fld = read("Global/Honolulu/HonoluluFieldMain.cs")
m2 = re.search(r"case 5:\s*\n\s*this\.FF9FieldMap\.nextMode = 3;", fld)
print("L2 calibration -- field tick consumes 5 -> nextMode=3:", bool(m2))
assert m2

wsd = read("Global/WM/WMScriptDirector.cs")
sw = re.search(r"switch \(ff9\.w_frameMainRoutine\(\)\)\s*\{(.*?)\n            \}", wsd, re.S)
cases = re.findall(r"case (\d+):", sw.group(1))
print("L3 world tick handles w_frameMainRoutine results:", cases)

writers = []
for p in SRC.rglob("*.cs"):
    t = p.read_text(encoding="utf-8-sig", errors="replace")
    for i, line in enumerate(t.splitlines(), 1):
        if re.search(r"attr \|= (0x1000u?|4096u?|4096U)\b", line, re.I):
            writers.append(("attr|=0x1000", str(p.relative_to(SRC)), i, line.strip()[:110]))
        if re.search(r"FF9World\.map\.nextMode = 3|FF9WorldMap\.nextMode = 3", line):
            writers.append(("nextMode=3", str(p.relative_to(SRC)), i, line.strip()[:110]))
print("L4/L5 writers:")
for w in writers:
    print("   ", w)
verdict = "5" not in cases
print("\nVERDICT: world-originated WorldMap() is", "INERT in stock (no case 5 on the world tick)" if verdict
      else "HANDLED (case 5 present)")
