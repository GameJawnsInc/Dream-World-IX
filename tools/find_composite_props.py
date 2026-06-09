#!/usr/bin/env python3
"""Find COMPOSITE props in shipping fields -- multi-part set pieces built from several objects placed
together (e.g. a save point = moogle + book + feather + letter at one spot). Grounded in real bytes; two
byte-level signals:

  1. CO-LOCATION  -- >=2 object entries whose Init spawns them at the SAME (x, z).
  2. ATTACHMENT   -- an object that calls AttachObject(0x4C) / AttachObjectOffset(0xD4) / PretendToBe
                     (0xB5): the engine's explicit "this object is bound to (follows) another" mechanism.

Reports the recurring co-located model-token SETS across all fields (the composite "templates") with
example fields, plus every attachment call -- so we can pick which to support as `prop = "save_point"`
composites. Read-only research; safe to re-run.

Usage: py tools/find_composite_props.py [--min N]    # min co-located cluster size (default 2)
"""
import os
import sys
from collections import Counter, defaultdict

KIT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "ff9mapkit"))
sys.path.insert(0, KIT)
from ff9mapkit import catalog as C
from ff9mapkit import extract
from ff9mapkit._fieldtable import FBG_TO_EVT
from ff9mapkit.eb import EbScript
from ff9mapkit.eb.disasm import iter_code

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import model_field_usage as MFU          # for field id -> location name

SET_MODEL, CREATE_OBJECT = 0x2F, 0x1D
ATTACH_OPS = {0x4C: "AttachObject", 0xD4: "AttachObjectOffset", 0xB5: "PretendToBe"}


def entry_info(raw, entry):
    """(model_id, (x, z), attaches) for an object entry, or None. Position from a literal CreateObject,
    else the SetVar D9(0)/D9(4) consts it reads; attaches = it calls an Attach/PretendToBe opcode."""
    f0 = entry.func_by_tag(0)
    if not f0:
        return None
    model = pos = None
    attach = False
    for ins in iter_code(raw, f0.abs_start, f0.abs_end):
        if ins.op == SET_MODEL:
            model = int.from_bytes(raw[ins.off + 2:ins.off + 4], "little")
        elif ins.op == CREATE_OBJECT and pos is None and raw[ins.off + 1] == 0:   # literal args
            pos = (int.from_bytes(raw[ins.off + 2:ins.off + 4], "little", signed=True),
                   int.from_bytes(raw[ins.off + 4:ins.off + 6], "little", signed=True))
        elif ins.op in ATTACH_OPS:
            attach = True
    if pos is None:                       # CreateObject read its args from vars -> the D9 consts
        body = raw[f0.abs_start:f0.abs_end]

        def fc(v):
            i = body.find(bytes([0x05, 0xD9, v, 0x7D]))
            return int.from_bytes(body[i + 4:i + 6], "little", signed=True) if i >= 0 else None
        x, z = fc(0), fc(4)
        if x is not None and z is not None:
            pos = (x, z)
    if model is None or pos is None:
        return None
    return model, pos, attach


def tok(model_id):
    m = C.model(model_id)
    return m.token if m else str(model_id)


def grp(model_id):
    m = C.model(model_id)
    return m.group if m else "?"


def main():
    min_n = 2
    if "--min" in sys.argv:
        min_n = int(sys.argv[sys.argv.index("--min") + 1])
    pure = "--pure" in sys.argv          # only sets where EVERY part is an ACC prop (no characters)
    names = MFU.field_names()
    field2evt = {rec[0]: rec[1] for rec in FBG_TO_EVT.values()}
    evt2field = {rec[1].upper(): rec[0] for rec in FBG_TO_EVT.values()}
    UnityPy = extract._unitypy()
    sa = extract._streaming_assets()
    bundle = extract._events_bundle()
    env = UnityPy.load(str(sa / bundle))

    sets = Counter()                      # frozenset(tokens) -> #fields it appears in
    examples = defaultdict(list)
    attaches = Counter()                  # (attacher_token,) -> count of fields with an attach call
    pair = Counter()                      # co-occurrence of ACC-token pairs (the "core parts")
    nfields = 0
    for k, obj in env.container.items():
        kl = k.lower()
        if "eventbinary/field/us/evt_" not in kl or not kl.endswith(".eb.bytes"):
            continue
        fid = evt2field.get(os.path.basename(k)[:-len(".eb.bytes")].upper())
        if fid is None:
            continue
        try:
            raw = extract._raw_bytes(obj.read())
            eb = EbScript.from_bytes(raw)
        except Exception:
            continue
        nfields += 1
        bypos = defaultdict(list)
        for e in eb.entries:
            if e.empty:
                continue
            info = entry_info(raw, e)
            if not info:
                continue
            model, pos, att = info
            bypos[pos].append(model)
            if att:
                attaches[tok(model)] += 1
        for pos, models in bypos.items():
            if len(models) < min_n:
                continue
            groups = [grp(m) for m in models]
            if pure:
                if not all(g == "ACC" for g in groups):     # every part an ACC prop
                    continue
            elif "ACC" not in groups:                       # at least one ACC prop
                continue
            toks = frozenset(tok(m) for m in models)
            if len(toks) < 2:
                continue
            sets[toks] += 1
            if len(examples[toks]) < 4:
                examples[toks].append(fid)
            accs = sorted(tok(m) for m in models if grp(m) == "ACC")
            for a in range(len(accs)):
                for b in range(a + 1, len(accs)):
                    pair[(accs[a], accs[b])] += 1

    print(f"scanned {nfields} fields\n")
    print(f"=== recurring co-located object SETS containing an ACC prop ({len(sets)} distinct) ===")
    for s, n in sets.most_common(30):
        ex = ", ".join(f"{f}={names.get(f, f)}" for f in examples[s])
        print(f"  x{n:<3} {{{', '.join(sorted(s))}}}")
        print(f"        e.g. {ex}")
    print(f"\n=== top ACC-prop pairs that co-locate (the composite 'cores') ===")
    for (a, b), n in pair.most_common(20):
        print(f"  x{n:<3} {a} + {b}")
    print(f"\n=== objects that use Attach/PretendToBe (explicit composition), by model ===")
    for t, n in attaches.most_common(25):
        print(f"  x{n:<3} {t}")


if __name__ == "__main__":
    main()
