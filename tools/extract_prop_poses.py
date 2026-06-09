#!/usr/bin/env python3
"""Extract each PROP model's canonical resting pose -- the SetStandAnimation id that shipping fields use
when they place it. A prop's true pose is often NOT a named model animation (the save-book's 1872 = 'b'+1),
so the model->anim name join can't supply it; the shipping bytes can. This is a DEV research tool: its
output (model -> pose id) gets baked into the prop archetypes (a curated constant, provenance-clean -- a
number, like the model ids already in archetypes.py), so the kit needs no runtime extraction.

Per field entry we read the LAST SetModel + the LAST SetStandAnimation in its Init (tag 0) -- the settled
object + pose -- and tally pose ids per model across all fields; the most common is the canonical pose.

Usage:
  py tools/extract_prop_poses.py                 # every ACC prop + the no-walk NPC props
  py tools/extract_prop_poses.py TBX MGR MGP TNT # specific tokens (any group's GEO_*_F0_<tok>)
"""
import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

KIT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "ff9mapkit"))
sys.path.insert(0, KIT)
from ff9mapkit import catalog as C
from ff9mapkit import extract
from ff9mapkit.eb import EbScript
from ff9mapkit.eb.disasm import iter_code

SET_MODEL, SET_STAND_ANIM = 0x2F, 0x33
CACHE = Path(__file__).parent / "prop_poses.json"     # model id -> canonical pose id (regenerable cache)


def build_cache():
    """(Re)build the model -> canonical pose cache from a full field scan. Returns {model_id: pose_id}."""
    canon = {str(mid): c.most_common(1)[0][0] for mid, c in scan_poses().items()}
    CACHE.write_text(json.dumps(canon), encoding="utf-8")
    print(f"cached {len(canon)} model poses -> {CACHE.name}", file=sys.stderr)
    return canon


def pose_of(model_id, default=None):
    """The canonical resting pose id for a model (builds the cache on first use)."""
    if not CACHE.exists():
        build_cache()
    return json.loads(CACHE.read_text(encoding="utf-8")).get(str(int(model_id)), default)


def scan_poses():
    """model_id -> Counter(pose_id): for every field entry, the (last SetModel, last SetStandAnimation)
    in its Init -- the object it places and the pose it settles to."""
    UnityPy = extract._unitypy()
    sa = extract._streaming_assets()
    bundle = extract._events_bundle()
    env = UnityPy.load(str(sa / bundle))
    poses = defaultdict(Counter)
    n = 0
    for k, obj in env.container.items():
        kl = k.lower()
        if "eventbinary/field/us/evt_" not in kl or not kl.endswith(".eb.bytes"):
            continue
        try:
            raw = extract._raw_bytes(obj.read())
            eb = EbScript.from_bytes(raw)
        except Exception:
            continue
        n += 1
        for e in eb.entries:
            if e.empty:
                continue
            f0 = e.func_by_tag(0)
            if not f0:
                continue
            model = stand = None
            for ins in iter_code(raw, f0.abs_start, f0.abs_end):
                if ins.op == SET_MODEL:
                    model = int.from_bytes(raw[ins.off + 2:ins.off + 4], "little")
                elif ins.op == SET_STAND_ANIM:
                    stand = int.from_bytes(raw[ins.off + 2:ins.off + 4], "little")
            if model is not None and stand is not None:
                poses[model][stand] += 1
    print(f"scanned {n} field scripts", file=sys.stderr)
    return poses


def main():
    if sys.argv[1:2] == ["--build"]:
        build_cache()
        return
    args = [a.upper() for a in sys.argv[1:]]
    poses = scan_poses()
    if args:
        models = [C.model(f"GEO_ACC_F0_{t}") or C.model(f"GEO_NPC_F0_{t}") or C.model(t) for t in args]
        models = [m for m in models if m]
    else:
        models = [m for m in C.models(group="ACC", field_only=True)]
        models += [m for m in C.models(group="NPC", field_only=True) if not C.npc_anims(m.id)]
    print(f"{'token':5} {'model':18} {'pose':>6}  named?  (consistency)")
    seen = set()
    for m in sorted(models, key=lambda m: m.token):
        if m.token in seen:
            continue
        seen.add(m.token)
        c = poses.get(m.id)
        if not c:
            print(f"{m.token:5} {m.name:18} {'--':>6}  (not placed with a pose)")
            continue
        pose, hits = c.most_common(1)[0]
        total = sum(c.values())
        rev = {v: k for k, v in C.animations_for_model(m.id).items()}
        named = rev.get(pose, "raw")
        print(f"{m.token:5} {m.name:18} {pose:>6}  {named:9} {hits}/{total}")


if __name__ == "__main__":
    main()
