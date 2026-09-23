"""Census: seam re-keying across every shipping walkmesh. Usage: py studies/actor-shadow/census_seam_rekey.py

(a) the unedited editable re-export -> _donor_floor_map is None (identity premise; the path is byte-identical)
(b) multi-floor: the floor blocks written in REVERSED order -> with the re-keying, every seam the unedited
    round-trip links still links (same donor-numbered link set); without it (the pre-fix code), how many drop.
"""
import sys
import tempfile
from collections import Counter
from pathlib import Path

KIT = Path(__file__).resolve().parents[2] / "ff9mapkit"
sys.path.insert(0, str(KIT))
from ff9mapkit import build, extract  # noqa: E402
from ff9mapkit.scene import bgi  # noqa: E402


def reshape(obj_text, order):
    head, blocks, cur = [], {}, None
    for line in obj_text.splitlines():
        if line.startswith("o floor_"):
            cur = int(line[len("o floor_"):])
            blocks[cur] = [line]
        elif cur is None:
            head.append(line)
        else:
            blocks[cur].append(line)
    out = list(head)
    for d in order:
        out += blocks[d]
    return "\n".join(out) + "\n"


def links(wm, to_donor):
    return {frozenset({(to_donor[fa], a), (to_donor[fb], b)}) for (fa, a, fb, b) in wm.extract_seams()}


def rebuild(td, obj_text, use_map):
    obj = td / "walkmesh.obj"
    obj.write_text(obj_text, encoding="utf-8")
    v, f, fid = bgi.load_obj_floors(str(obj))
    mesh = bgi.build(v, f, floor_ids=fid)
    w = []
    build._apply_links(mesh, td / "walkmesh.links.toml", w, build._donor_floor_map(obj) if use_map else None)
    return mesh, w


def main():
    index = extract.build_field_index(verbose=False)
    sa = extract._streaming_assets()
    by_bundle = {}
    for folder, bn in index.items():
        by_bundle.setdefault(bn, []).append(folder)
    UnityPy = extract._unitypy()
    stats = Counter()
    bad_identity, bad_rekey, errs, old_drops = [], [], [], []
    for bi, (bn, folders) in enumerate(sorted(by_bundle.items())):
        env = UnityPy.load(str(sa / bn))
        keys = {}
        for k in env.container:
            kl = k.lower()
            if kl.endswith(".bgi.bytes") and "fieldmaps/" in kl:
                keys.setdefault(kl.split("fieldmaps/")[1].split("/")[0], []).append(k)
        print(f"  [{bi + 1}/{len(by_bundle)}] {bn}", flush=True)
        for folder in folders:
            for key in keys.get(folder, []):
                try:
                    wm = bgi.BgiWalkmesh.from_bytes(extract._raw_bytes(env.container[key].read()))
                    with tempfile.TemporaryDirectory() as t:
                        td = Path(t)
                        text = extract._world_walkmesh_obj_text(wm)
                        (td / "walkmesh.obj").write_text(text, encoding="utf-8")
                        stats["walkmeshes"] += 1
                        if build._donor_floor_map(td / "walkmesh.obj") is not None:
                            bad_identity.append(key)
                        floors = sorted({t.floor_ndx for t in wm.tris})
                        if len(floors) < 2:
                            continue
                        stats["multi"] += 1
                        extract._write_links_toml(wm, td / "walkmesh.links.toml")
                        base, _ = rebuild(td, text, True)
                        base_links = links(base, list(range(len(base.floors))))
                        stats["seams"] += len(base_links)
                        order = list(reversed(floors))
                        rtext = reshape(text, order)
                        new, w_new = rebuild(td, rtext, True)
                        old, w_old = rebuild(td, rtext, False)
                        if links(new, order) != base_links or any("seam" in x for x in w_new):
                            bad_rekey.append((key, len(base_links), len(links(new, order))))
                        dropped = len(base_links) - len({l for l in links(old, order) if l in base_links})
                        if dropped:
                            old_drops.append((folder, dropped, len(base_links)))
                            stats["old_dropped_seams"] += dropped
                except Exception as e:  # noqa: BLE001
                    errs.append((key, repr(e)))
    print(f"\n{stats['walkmeshes']} walkmeshes, {stats['multi']} multi-floor, {stats['seams']} seams (unedited links)")
    print(f"(a) unedited re-export NOT identity: {len(bad_identity)} {bad_identity[:10]}")
    print(f"(b) reversed reshape, re-keyed: link-set mismatches {len(bad_rekey)} {bad_rekey[:10]}")
    print(f"    reversed reshape, pre-fix: {len(old_drops)} walkmeshes drop {stats['old_dropped_seams']} seams"
          f" e.g. {old_drops[:6]}")
    print(f"errors {len(errs)} {errs[:5]}")


if __name__ == "__main__":
    main()
