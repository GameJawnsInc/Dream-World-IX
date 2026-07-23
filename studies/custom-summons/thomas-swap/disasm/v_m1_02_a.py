"""V-M1-02 step A: independently locate the five Hi_Register*EffModel real bodies and
dump them, so the [DATA+0x10]=0 claim can be checked against a FRESH disassembly."""
import refkit

pe = refkit.load()
fns = refkit.functions(pe)
base = refkit.image_base(pe)

NAMES = [
    "Hi_RegisterSolidEffModel", "Hi_RegisterGouEffModel", "Hi_RegisterTexEffModel",
    "Hi_RegisterTexListModel", "Hi_RegisterTexPtrModel",
]
for n in NAMES:
    info = refkit.locate_function(pe, n, fns)
    print("=" * 78)
    print(n, "string@", hex(info["string_rva"] or 0), "funcs:",
          [(hex(a), hex(b)) for a, b in (info.get("all_funcs") or [])])
