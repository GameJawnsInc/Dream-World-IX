"""V-M1-14 step G: exhaustive refutation hunt.
(1) EVERY read of `dword ptr [reg + 8]` inside every function that receives a ModelData* --
    is any of them used as a table INDEX (shl/scaled-index/lea base+idx*n) rather than decoded?
(2) census of the PSX-decode pattern `shr X,0x18 ; cmp X,0x80` -- what does each one decode?
(3) 0x4eb0 (per-mesh helper) -- does it read DATA+8?
"""
import refkit, re
pe = refkit.load(); fns = refkit.functions(pe); base = refkit.image_base(pe)

# --- (2) decoder-site census: find `shr rX, 0x18` followed within 3 ins by `cmp rX, 0x80`
ins_all = list(refkit.iter_instructions(pe, fns))
by_rva = {i.address - base: i for i in ins_all}
seq = [(i.address - base, i.mnemonic, i.op_str) for i in ins_all]
print("total instructions:", len(seq))
sites = []
for k in range(len(seq) - 2):
    r, m, o = seq[k]
    if m == "shr" and o.endswith(", 0x18"):
        r2, m2, o2 = seq[k+1]
        if m2 == "cmp" and o2.endswith(", 0x80"):
            sites.append(r)
print("\n--- PSX address-DECODE sites (shr,0x18 ; cmp,0x80) ---")
for r in sites:
    # look back up to 6 instructions for the load that produced the value
    k = next(j for j, s in enumerate(seq) if s[0] == r)
    ctx = [seq[j] for j in range(max(0, k-5), k)]
    src = " | ".join(f"{m} {o}" for _, m, o in ctx)
    fo = refkit.func_of(fns, r)
    print(f"  {hex(r)}  chunk={fo and hex(fo[0])}   <= {src}")
print("count:", len(sites))
