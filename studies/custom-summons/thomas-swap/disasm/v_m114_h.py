"""V-M1-14 step H: every read of [+8] inside the ModelData-consuming functions; is any an INDEX?"""
import refkit, re
pe = refkit.load(); fns = refkit.functions(pe); base = refkit.image_base(pe)

# function chunk sets for the model-family bodies (span the chunked ranges)
SPANS = {
  "model_prepare 0x7120":      (0x7120, 0x7240),
  "build_world_mat 0x7820":    (0x7820, 0x7a31),
  "worldmat cont 0x7a42":      (0x7a42, 0x7de7),
  "worldmat cont 0x7de7":      (0x7de7, 0x80c0),
  "pose_eval 0x186a0":         (0x186a0, 0x187f0),
  "mesh_helper 0x4eb0":        (0x4eb0, 0x4ff9),
  "DrawEffModel 0x16184":      (0x16184, 0x16547),
  "DrawSummonModel 0x17740":   (0x17740, 0x179f2),
  "DrawSliceEff 0x165ae":      (0x165ae, 0x167cd),
  "DrawEffByBone 0x16837":     (0x16837, 0x16c80),
  "DrawMorphEff 0x16d23":      (0x16d23, 0x16ed8),
  "DrawMorphByBone 0x171ef":   (0x171ef, 0x17355),
  "RegSummon work 0x1606c":    (0x1606c, 0x16184),
  "GetSummonBonePos 0x185b0":  (0x185b0, 0x18630),
  "GetSummonBoneMatrix 0x18630": (0x18630, 0x186a0),
}
pat8 = re.compile(r"\[(r[a-z0-9]+|e[a-z]+) \+ 8\]")
for label,(lo,hi) in SPANS.items():
    hits=[]
    for ins in refkit.disasm(pe, lo, hi):
        if pat8.search(ins.op_str):
            hits.append((ins.address-base, ins.mnemonic, ins.op_str))
    if hits:
        print(f"\n### {label}")
        for r,m,o in hits: print(f"  {hex(r)}: {m}\t{o}")

# scaled-index uses anywhere: is there a `[base + <reg-from-DATA+8> * n]` shape?
print("\n--- scaled-index instructions mentioning *8 or *4 near a DATA+8 load (Draw bodies) ---")
for label,(lo,hi) in [("DrawEff",(0x16184,0x16547)),("DrawSummon",(0x17740,0x179f2))]:
    seq=[(i.address-base,i.mnemonic,i.op_str) for i in refkit.disasm(pe,lo,hi)]
    for k,(r,m,o) in enumerate(seq):
        if re.search(r"dword ptr \[r[a-z0-9]+ \+ 8\]", o) and m=="mov":
            print(f"  {label} load @{hex(r)}: {m} {o}")
            for j in range(k+1, min(k+40,len(seq))):
                print(f"      {hex(seq[j][0])}: {seq[j][1]}\t{seq[j][2]}")
                if seq[j][1] in ("call",): break
