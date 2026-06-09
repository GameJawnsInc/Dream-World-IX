#!/usr/bin/env python3
"""Map each field model id -> the FF9 fields (LOCATIONS) whose scripts place it, by disassembling every
field's event .eb from p0data for SetModel(model_id) ops. Gives the archetype gallery real CONTEXT:
"this NPC appears in Black Mage Village / Treno" is far easier to identify than a bare silhouette.

Builds a cache once (model id -> [field ids], from one events-bundle scan), then queries are instant.

Usage:
  py tools/model_field_usage.py BMG          # a token (GEO_NPC_F0_<TOK>) or model id -> its fields
  py tools/model_field_usage.py --build      # (re)build the index cache
"""
import json
import os
import sys
from pathlib import Path

KIT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "ff9mapkit"))
sys.path.insert(0, KIT)
from ff9mapkit import catalog as C
from ff9mapkit import extract
from ff9mapkit._fieldtable import FBG_TO_EVT
from ff9mapkit.eb import EbScript
from ff9mapkit.eb.disasm import iter_code

SET_MODEL = 0x2F
CACHE = Path(__file__).parent / "model_field_usage.json"
MANIFEST = Path(__file__).parent.parent / "reference" / "field-manifest.tsv"


def field_names() -> dict:
    """field_id -> human location name (e.g. 'Black Mage Vil./House'), from field-manifest.tsv."""
    names = {}
    if MANIFEST.exists():
        for line in MANIFEST.read_text(encoding="utf-8").splitlines():
            p = line.split("\t")
            if len(p) >= 3 and p[1].strip().isdigit():
                names[int(p[1])] = p[2].strip()
    return names


def models_in_eb(eb: bytes) -> set:
    """Every model id placed by SetModel(0x2F) anywhere in this field's script."""
    out = set()
    for e in EbScript.from_bytes(eb).entries:
        if e.empty:
            continue
        for f in e.funcs:
            for ins in iter_code(eb, f.abs_start, f.abs_end):
                if ins.op == SET_MODEL:
                    out.add(int.from_bytes(eb[ins.off + 2:ins.off + 4], "little"))
    return out


def build_index() -> dict:
    UnityPy = extract._unitypy()
    sa = extract._streaming_assets()
    bundle = extract._events_bundle()
    print(f"scanning field scripts in {bundle} ...", flush=True)
    env = UnityPy.load(str(sa / bundle))
    evt_to_field = {rec[1].upper(): rec[0] for rec in FBG_TO_EVT.values()}
    idx, n = {}, 0
    for k, obj in env.container.items():
        kl = k.lower()
        if "eventbinary/field/us/evt_" in kl and kl.endswith(".eb.bytes"):
            fid = evt_to_field.get(os.path.basename(k)[:-len(".eb.bytes")].upper())
            if fid is None:
                continue
            try:
                for mid in models_in_eb(extract._raw_bytes(obj.read())):
                    idx.setdefault(mid, set()).add(fid)
                n += 1
            except Exception:
                continue
    CACHE.write_text(json.dumps({str(m): sorted(f) for m, f in idx.items()}), encoding="utf-8")
    print(f"indexed {n} field scripts -> {len(idx)} models used; cache: {CACHE.name}")
    return {m: sorted(f) for m, f in idx.items()}


def load_index() -> dict:
    if not CACHE.exists():
        build_index()
    return {int(k): v for k, v in json.loads(CACHE.read_text(encoding="utf-8")).items()}


def usage(model_id: int, limit: int = 6):
    """[(field_id, name), ...] of fields that place this model (up to limit), + the total count."""
    idx, names = load_index(), field_names()
    fids = idx.get(int(model_id), [])
    return [(f, names.get(f, f"field {f}")) for f in fids[:limit]], len(fids)


if __name__ == "__main__":
    args = sys.argv[1:]
    if args and args[0] == "--build":
        build_index()
        sys.exit(0)
    if not args:
        print(__doc__)
        sys.exit(1)
    q = args[0]
    m = C.model(q) if q.isdigit() else (C.model(f"GEO_NPC_F0_{q.upper()}") or C.model(q))
    if not m:
        print(f"no model for {q!r}")
        sys.exit(1)
    rows, total = usage(m.id)
    print(f"{m.name} (id {m.id}) -> placed in {total} field(s):")
    for fid, nm in rows:
        print(f"  {fid:5}  {nm}")
