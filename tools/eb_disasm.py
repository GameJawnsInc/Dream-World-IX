#!/usr/bin/env python3
# FF9 field event-script (.eb) disassembler.
# Parses Memoria's EventEngineUtils.cs opcode tables directly (no hand transcription),
# then walks the BinaryScript -> Entry -> Function -> Code structure.
# Usage: eb_disasm.py <file.eb.bytes> [entryIndex]
import re, sys, os

# Point FF9_MEMORIA_SRC at the root of your Memoria source clone (the dir holding Assembly-CSharp/).
_MEMORIA_SRC = os.environ.get("FF9_MEMORIA_SRC", "")
MEM = os.path.join(_MEMORIA_SRC, r"Assembly-CSharp\Global\Event\Engine\EventEngineUtils.cs")
DOC = os.path.join(_MEMORIA_SRC, r"Assembly-CSharp\Global\Event\Engine\EventEngine.DoEventCode.cs")

def load_tables():
    if not _MEMORIA_SRC:
        sys.exit("eb_disasm: set FF9_MEMORIA_SRC to your Memoria source clone root "
                 "(the dir holding Assembly-CSharp/) so the opcode tables can be parsed.")
    src = open(MEM, encoding='utf-8', errors='replace').read()
    # opArgCount : SByte[]
    m = re.search(r"opArgCount\s*=\s*new\s+SByte\[\]\s*\{(.*?)\}", src, re.S)
    opArgCount = [int(x) for x in re.findall(r"-?\d+", m.group(1))]
    # opArgSize : Byte[][]
    m = re.search(r"opArgSize\s*=\s*new\s+Byte\[\]\[\]\s*\{(.*?)\n\s*\};", src, re.S)
    body = m.group(1)
    py = body.replace("new Byte[]{", "[").replace("new Byte[] {", "[")
    py = py.replace("}", "]").replace("null", "None")
    opArgSize = eval("[" + py + "]")
    return opArgCount, opArgSize

def load_names():
    names = {}
    for line in open(DOC, encoding='utf-8', errors='replace'):
        m = re.search(r'case EBin\.event_code_binary\.(\w+):\s*//\s*(0x[0-9A-Fa-f]+),\s*"([^"]+)"', line)
        if m:
            names[int(m.group(2),16)] = m.group(3)
    return names

opArgCount, opArgSize = load_tables()
NAMES = load_names()

def argsize(op, i):
    if op == 0x29: return 4
    if op in (0x06,0x0B,0x0D): return 2
    a = opArgSize[op] if op < len(opArgSize) else None
    return a[i] if (a and i < len(a)) else 0

def read_expr(raw, pos):
    # returns (str, pos)
    ops = []
    while True:
        o = raw[pos]; pos += 1
        isconst = o in (0x7D,0x7E)
        isvar = o >= 0xC0 or o in (0x29,0x5F,0x78,0x79,0x7A)
        if not isconst and not isvar:
            ops.append(f"op{o:02X}")
            if o == 0x7F: break
            continue
        if o == 0x7E: a=[raw[pos],raw[pos+1],raw[pos+2],raw[pos+3]]; pos+=4
        elif o >= 0xE0 or o in (0x78,0x7D): a=[raw[pos],raw[pos+1]]; pos+=2
        else: a=[raw[pos]]; pos+=1
        ops.append(f"op{o:02X}({','.join(str(x) for x in a)})")
    return "{"+" ".join(ops)+"}", pos

def read_code(raw, pos):
    start = pos
    op = raw[pos]; pos += 1
    if op == 0xFF: op = 0x100 | raw[pos]; pos += 1
    ac = opArgCount[op] if op < len(opArgCount) else 0
    argFlag = 0
    if op >= 0x10 and ac != 0: argFlag = raw[pos]; pos += 1
    if op == 0x05: argFlag = 1
    if ac < 0:
        ac = raw[pos]; pos += 1
        if op == 0x0D: ac |= raw[pos] << 8; pos += 1
        if op == 0x06: ac = 1 + 2*ac
        elif op in (0x0B,0x0D): ac = 2 + ac
    args = []
    for i in range(ac):
        if argFlag & (1 << i):
            s, pos = read_expr(raw, pos); args.append(s)
        else:
            sz = argsize(op, i)
            v = 0
            for k in range(sz): v |= raw[pos+k] << (8*k)
            pos += sz
            args.append(str(v))
    nm = NAMES.get(op, f"op_{op:02X}")
    return f"  [{start}] {nm}({', '.join(args)})", pos

def disasm(path, only_entry=None):
    raw = open(path,'rb').read()
    print(f"=== {os.path.basename(path)}  size={len(raw)} ===")
    if raw[0:2] != b'EV':
        print("  not EV header"); return
    entryCount = raw[3]; base = 128
    tab = []
    p = base
    for i in range(entryCount):
        off = raw[p]|(raw[p+1]<<8); sz=raw[p+2]|(raw[p+3]<<8); loc=raw[p+4]; fl=raw[p+5]; p+=8
        tab.append((off,sz,loc,fl))
    for i,(off,sz,loc,fl) in enumerate(tab):
        if only_entry is not None and i != only_entry: continue
        ep = base+off; maxpos = base+off+sz
        print(f"\nENTRY {i}: off={off} sz={sz} loc={loc} fl={fl}  range[{ep}..{maxpos}]")
        if maxpos <= ep:
            print("  (empty)"); continue
        etype = raw[ep]; fc = raw[ep+1]; q = ep+2
        ftab = []
        for f in range(fc):
            tag = raw[q]|(raw[q+1]<<8); fpos=raw[q+2]|(raw[q+3]<<8); q+=4
            ftab.append((tag,fpos))
        fbase = ep+2  # funcBasePos = entryStart+2 (fpos is measured from BEFORE the func table)
        print(f"  type={etype} funcCount={fc} tags={[t for t,_ in ftab]}")
        for f,(tag,fpos) in enumerate(ftab):
            fstart = fbase+fpos
            fend = (fbase+ftab[f+1][1]) if f+1 < len(ftab) else maxpos
            print(f"  --- func{f} tag={tag} [{fstart}..{fend}]")
            cp = fstart; guard=0
            while cp < fend and guard < 400:
                line, cp = read_code(raw, cp); print(line); guard+=1

if __name__ == "__main__":
    path = sys.argv[1]
    ent = int(sys.argv[2]) if len(sys.argv) > 2 else None
    disasm(path, ent)
