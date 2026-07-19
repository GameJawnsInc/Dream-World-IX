"""Shared .eb loader for the moogle-reveal decode round.

Every agent MUST use this so all decodes read identical bytes. Resolves a numeric
field id -> its EVT name -> the compiled .eb out of the install bundle, bypassing
the FBG reverse map (which collapses shared-background fields like 904/1904).

Run from the KIT ROOT (ff9mapkit/), so the local package shadows any editable install:

    cd ff9mapkit
    py ../studies/moogle-savepoints/ebload.py 300              # entry/tag map
    py ../studies/moogle-savepoints/ebload.py 407 --disasm 5:1 # disassemble entry 5 tag 1
    py ../studies/moogle-savepoints/ebload.py 407 --raw 5:1    # raw hex of that function
    py ../studies/moogle-savepoints/ebload.py --census out.json # rescan every field

From Python (both sys.path inserts are required):

    import sys; sys.path.insert(0, '.'); sys.path.insert(0, '../studies/moogle-savepoints')
    import ebload
    eb = ebload.load(407)                    # EbScript
    ebload.find_moogles(eb)                  # [(entry_index, model_id)]
    for ins in ebload.func_code(eb, 5, 1): print(ins)   # absolute offsets
"""
import sys
from pathlib import Path

# Running this file from elsewhere puts the SCRIPT's dir on sys.path, not the cwd --
# so the kit root has to be added explicitly for the local package to shadow.
sys.path.insert(0, str(Path.cwd()))

from ff9mapkit import extract
from ff9mapkit.eb import disasm
from ff9mapkit.eb.model import EbScript


def evt_name(field_id: int) -> str:
    evt = extract.ID_TO_EVT.get(int(field_id))
    if not evt:
        raise SystemExit(f"field {field_id}: no EVT mapping")
    return evt


def load_bytes(field_id: int, lang: str = "us") -> bytes:
    """The raw .eb bytes for a numeric field id, resolved by EVT name directly."""
    evt = evt_name(field_id)
    bundle = extract._events_bundle(None)
    if not bundle:
        raise SystemExit("no events bundle found in the install")
    env = extract._load_env(extract._streaming_assets(None) / bundle)
    # The container keys are ".eb.bytes", not ".eb" -- substring match, same as extract's own.
    want = f"eventbinary/field/{lang}/{evt}.eb".lower()
    for key, obj in env.container.items():
        kl = key.lower()
        if want in kl and kl.endswith(".eb.bytes"):
            return extract._raw_bytes(obj.read())
    raise SystemExit(f"field {field_id} ({evt}): .eb not present in bundle")


def load(field_id: int, lang: str = "us") -> EbScript:
    """The parsed EbScript for a numeric field id."""
    return EbScript(load_bytes(field_id, lang))


def func_code(eb: EbScript, entry_index: int, tag: int):
    """Yield the disassembled Instrs of one entry/tag, with ABSOLUTE offsets
    (so a printed offset matches the byte positions quoted in the memory notes)."""
    fn = eb.entries[entry_index].func_by_tag(tag)
    if fn is None:
        raise SystemExit(f"entry {entry_index} has no tag {tag}")
    return disasm.iter_code(eb.data, fn.abs_start, fn.abs_end)


# The save-moogle models: 220 = GEO_NPC_F0_MOG, 129 = GEO_NPC_F1_MOG. An entry is a moogle
# iff its Init (tag 0) calls SetModel with one of these -- the same key eventscan uses.
MOOGLE_MODELS = (220, 129)


def find_moogles(eb: EbScript) -> list:
    """[(entry_index, model_id)] for every moogle object in this script."""
    out = []
    for i, entry in enumerate(eb.entries):
        if entry.empty:
            continue
        f0 = entry.func_by_tag(0)
        if not f0:
            continue
        for ins in disasm.iter_code(eb.data, f0.abs_start, f0.abs_end):
            if ins.name == "SetModel":
                m = ins.imm(0)
                if m in MOOGLE_MODELS:
                    out.append((i, m))
                    break
    return out


def census(lang: str = "us") -> list:
    """Scan EVERY mapped field for save moogles. Returns
    [{field, evt, entries:[{entry, model, tags:{tag: length}}]}] -- only fields with >=1 moogle."""
    rows = []
    for fid in sorted(extract.ID_TO_EVT):
        try:
            eb = load(fid, lang)
        except SystemExit:
            continue
        except Exception:
            continue
        found = find_moogles(eb)
        if not found:
            continue
        entries = []
        for ei, model in found:
            tags = {f.tag: f.length for f in eb.entries[ei].funcs}
            entries.append({"entry": ei, "model": model, "tags": tags})
        rows.append({"field": fid, "evt": extract.ID_TO_EVT[fid], "entries": entries})
    return rows


def _main(argv):
    if not argv:
        raise SystemExit(__doc__)
    if argv[0] == "--census":
        import json
        rows = census()
        out = Path(argv[1]) if len(argv) > 1 else None
        text = json.dumps(rows, indent=1)
        if out:
            out.write_text(text, encoding="utf-8")
            print(f"{len(rows)} moogle fields -> {out}")
        else:
            print(text)
        return
    fid = int(argv[0])
    eb = load(fid)
    rest = argv[1:]
    if rest and rest[0] in ("--disasm", "--raw"):
        ei, tag = (int(x) for x in rest[1].split(":"))
        if rest[0] == "--raw":
            fn = eb.entries[ei].func_by_tag(tag)
            print(eb.data[fn.abs_start:fn.abs_end].hex(" "))
        else:
            for ins in func_code(eb, ei, tag):
                print(ins)
        return
    print(f"field {fid} = {evt_name(fid)}  ({len(eb.entries)} entries)")
    for i, entry in enumerate(eb.entries):
        if entry.empty:
            continue
        tags = ", ".join(f"{f.tag}({f.length}b)" for f in entry.funcs)
        print(f"  entry {i:3d}: {tags}")


if __name__ == "__main__":
    _main(sys.argv[1:])
