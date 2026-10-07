"""CAPACITY lane, step 1 -- THE WORLDMAP ASSET UNIVERSE: what directories ("LODs"), parts, prefabs and
Unity version the overworld bundles actually hold, read from the user's own install (read-only).

Answers:
  * the bundle's Unity version (serialized-file unity_version) -> the 16-bit-index ceiling question;
  * every worldmap/disc{D}/<dir>/ mesh directory that exists (is "0_2" a far LOD or Form 2?),
    with per-dir block + part counts;
  * whether the stock index buffers are 16-bit (m_IndexFormat / m_Use16BitIndices) and single-submesh;
  * the PREFAB children names (the s34 override key is `transform.name`), esp. for form-2 components.

Writes out/universe.json (derived names/counts only -- no asset bytes).
Run:  py studies/terrain-malleability/capacity/universe.py
"""
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, r"C:\gd\Dream-World-IX\ff9mapkit")
from ff9mapkit.world import extract as X  # noqa: E402

OUT = Path(__file__).resolve().parent / "out"
OUT.mkdir(exist_ok=True)

PAT = re.compile(r"worldmap/disc(\d+)/([^/]+)/r(\d+)/block\[(\d+)\]\[(\d+)\] ([a-z0-9_]+)(?:\.asset)?$")


def main():
    res = {}
    for disc in (1, 4):
        env = X._worldmap_env(disc)
        # unity version(s) of the serialized files in this env
        versions = Counter()
        for f in getattr(env, "files", {}).values():
            for sf in _walk_files(f):
                v = getattr(sf, "unity_version", None)
                if v:
                    versions[str(v)] += 1
        dirs = defaultdict(lambda: defaultdict(set))
        other_worldmap = Counter()
        for k in env.container:
            kl = (k or "").lower()
            if "worldmap" not in kl:
                continue
            m = PAT.search(kl)
            if m and int(m.group(1)) == disc:
                dirs[m.group(2)][m.group(6)].add((int(m.group(4)), int(m.group(5))))
            else:
                # bucket the rest of the worldmap tree by its first 3 path components
                parts = kl.split("/")
                try:
                    i = parts.index("worldmap")
                    other_worldmap["/".join(parts[i:i + 3])] += 1
                except ValueError:
                    other_worldmap[kl[:60]] += 1
        # index formats + submesh counts over every block mesh in this env
        idx = X._mesh_index(env)
        fmt = Counter()
        subm = Counter()
        n = 0
        for c, o in idx.items():
            m = PAT.search(c)
            if not m or int(m.group(1)) != disc:
                continue
            md = o.read()
            use32 = getattr(md, "m_IndexFormat", None) == 1 or getattr(md, "m_Use16BitIndices", 1) in (0, False)
            fmt["u32" if use32 else "u16"] += 1
            subm[len(md.m_SubMeshes)] += 1
            n += 1
        res[f"disc{disc}"] = {
            "unity_versions": dict(versions),
            "mesh_dirs": {d: {p: len(bs) for p, bs in sorted(parts.items())} for d, parts in sorted(dirs.items())},
            "dir_block_union": {d: len(set().union(*parts.values())) for d, parts in dirs.items()},
            "0_2_blocks": {p: sorted(bs) for p, bs in sorted(dirs.get("0_2", {}).items())},
            "index_format": dict(fmt),
            "submesh_count_hist": dict(subm),
            "block_meshes_scanned": n,
            "other_worldmap_top": dict(other_worldmap.most_common(25)),
        }
    (OUT / "universe.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    for d, r in res.items():
        print(f"== {d}: unity={r['unity_versions']} index_format={r['index_format']} "
              f"submeshes={r['submesh_count_hist']} scanned={r['block_meshes_scanned']}")
        for dd, parts in r["mesh_dirs"].items():
            print(f"   dir {dd}: blocks={r['dir_block_union'][dd]} parts={parts}")
        print(f"   0_2 blocks: {r['0_2_blocks']}")
        print(f"   other worldmap: {r['other_worldmap_top']}")


def _walk_files(f):
    """Yield SerializedFile objects under a UnityPy file node (bundle -> files)."""
    if hasattr(f, "unity_version") and hasattr(f, "objects"):
        yield f
    for sub in getattr(f, "files", {}).values() if isinstance(getattr(f, "files", None), dict) else []:
        yield from _walk_files(sub)


if __name__ == "__main__":
    main()
