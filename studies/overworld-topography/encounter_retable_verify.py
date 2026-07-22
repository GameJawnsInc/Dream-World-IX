"""Offline proof for the demo-island encounter re-table (roadmap SOON 6.0).

Phases (run from the ff9mapkit/ kit root so the local package shadows any install):

  py studies/overworld-topography/encounter_retable_verify.py pre     # backup + pre-deploy gates
  py -m ff9mapkit world-encounters --config .../encounter_retable_island.toml --disc 1 --mod-folder FF9CustomMap-world
  py studies/overworld-topography/encounter_retable_verify.py post    # byte-diff gate + decode-back + idempotency

`pre`  : round-trip identity of the pristine image, save the pristine bytes to backups/, apply the config
         IN MEMORY, validate every scene id in the whole 355-table against the battle-scene db (REFUSE on any
         invalid id -> black-screen risk), and print the exact expected byte diff.
`post` : re-read the DEPLOYED discmr.img override, byte-diff it against the pristine base (assert ONLY the two
         topo-0 zone-0 records' 16 scene bytes changed), decode-back + re-validate the new table, and prove
         idempotency (re-applying the config yields byte-identical output).
"""
import sys, pathlib

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "ff9mapkit"))

from ff9mapkit.world import worldpack as WP          # noqa: E402
from ff9mapkit._scenedb import SCENES                # noqa: E402

DISC = 1
MOD = "FF9CustomMap-world"
CFG = REPO / "studies" / "overworld-topography" / "encounter_retable_island.toml"
BACKUP = REPO / "backups" / "encounter-retable.20260721"
PRISTINE = BACKUP / "discmr.img.disc1.pristine"
VALID = set(SCENES.values())
EXPECT_MIX = [206, 165, 5, 230]
EXPECT_RECS = (0, 1)                                  # zone-0 topo-0 fog twins


def _load_cfg():
    import tomllib
    with open(CFG, "rb") as fh:
        return tomllib.load(fh)


def _all_ids_valid(d, label):
    bad = sorted({s for r in d.encounters for s in r.scene if s not in VALID and s != WP.SPECIAL_EMPTY})
    if bad:
        raise SystemExit(f"REFUSE: {label} has scene ids not in the battle-scene db: {bad} (black-screen risk)")
    print(f"  [{label}] all {len(d.encounters)*4} scene slots valid battle scenes (or the 0xFFFF empty sentinel)")


def pre():
    print("== PRE-DEPLOY GATES ==")
    base = WP.load_discmr(DISC)
    base_bytes = base.to_bytes()
    # 1. round-trip identity of the UNEDITED image (the codec must be byte-exact)
    raw = bytes(base._data)
    assert base_bytes == raw, "round-trip identity FAILED (Discmr(x).to_bytes() != x) -- codec not byte-exact"
    print(f"  round-trip identity OK ({len(raw)} B, Discmr(x).to_bytes() == x)")
    # 2. save the pristine base for the byte-diff gate + restore reference
    BACKUP.mkdir(parents=True, exist_ok=True)
    PRISTINE.write_bytes(raw)
    print(f"  saved pristine base -> {PRISTINE} ({len(raw)} B)")
    # 3. show the BEFORE state of the target records
    print("  target records BEFORE (zone 0, topo 0, both fog twins):")
    for i in EXPECT_RECS:
        r = base.encounters[i]
        print(f"    rec[{i}] topo={r.topograph} fog={r.fog} idx(pattern&3)={r.pattern & 3} scene={r.scene}")
    # 4. apply config in memory + validate the WHOLE table
    d = WP.load_discmr(DISC)
    summ = WP.apply_config(d, _load_cfg())
    print(f"  apply_config -> {summ['sets']}")
    matched = d.match(area=0, topograph=0)
    assert matched == list(EXPECT_RECS), f"matcher hit {matched}, expected {list(EXPECT_RECS)}"
    for i in EXPECT_RECS:
        assert d.encounters[i].scene == EXPECT_MIX, f"rec[{i}] scene not set to the mix"
        assert d.encounters[i].pattern == base.encounters[i].pattern, "pattern (topograph) must NOT change"
        assert d.encounters[i].pad == base.encounters[i].pad, "pad (fog) must NOT change"
    _all_ids_valid(d, "post-edit in-memory")
    # 5. exact expected byte diff
    new_bytes = d.to_bytes()
    diff = [k for k in range(len(raw)) if raw[k] != new_bytes[k]]
    runs = _runs(diff)
    print(f"  expected byte diff: {len(diff)} bytes in runs {runs}")
    ea = base.enc_abs
    want = [(ea + 0, ea + 8), (ea + 10, ea + 18)]     # rec0.scene, rec1.scene (8 B each)
    assert runs == want, f"diff runs {runs} != the two scene fields {want}"
    print("  PRE-DEPLOY GATES PASS -> safe to deploy via the kit CLI\n")


def _runs(idxs):
    out = []
    for k in idxs:
        if out and k == out[-1][1]:
            out[-1] = (out[-1][0], k + 1)
        else:
            out.append((k, k + 1))
    return out


def post():
    print("== POST-DEPLOY GATES ==")
    from ff9mapkit import config
    raw = PRISTINE.read_bytes()
    root = config.find_mod_root(config.find_game_path(None), MOD)
    base = WP.load_discmr(DISC)                        # for container path + enc_abs
    dest = pathlib.Path(root) / "StreamingAssets" / base.container
    assert dest.is_file(), f"deployed override not found at {dest} -- did the CLI deploy run?"
    dep = dest.read_bytes()
    print(f"  deployed override: {dest} ({len(dep)} B)")
    # 1. byte-diff gate vs pristine base
    assert len(dep) == len(raw), f"deployed size {len(dep)} != pristine {len(raw)}"
    diff = [k for k in range(len(raw)) if raw[k] != dep[k]]
    runs = _runs(diff)
    ea = base.enc_abs
    want = [(ea + 0, ea + 8), (ea + 10, ea + 18)]
    print(f"  byte diff vs pristine: {len(diff)} bytes in runs {runs}")
    assert runs == want, f"BLAST RADIUS FAIL: diff runs {runs} != the two scene fields {want}"
    print("  byte-diff gate PASS: only the two topo-0 zone-0 records' 16 scene bytes changed")
    # 2. decode-back the deployed file + re-validate
    d = WP.Discmr.from_bytes(dep, container=base.container, disc=DISC)
    print("  decode-back of the DEPLOYED file, target records AFTER:")
    for i in EXPECT_RECS:
        r = d.encounters[i]
        names = "/".join(next((n for n, x in SCENES.items() if x == s), f"?{s}") for s in r.scene)
        print(f"    rec[{i}] topo={r.topograph} fog={r.fog} idx={r.pattern & 3} scene={r.scene}  ({names})")
        assert r.scene == EXPECT_MIX
    _all_ids_valid(d, "deployed")
    # 3. idempotency: re-apply the config to the pristine base -> byte-identical to the deployed file
    d2 = WP.load_discmr(DISC)
    WP.apply_config(d2, _load_cfg())
    assert d2.to_bytes() == dep, "IDEMPOTENCY FAIL: re-running the config does not reproduce the deployed bytes"
    print("  idempotency PASS: re-applying the config reproduces the deployed file byte-for-byte")
    print("  POST-DEPLOY GATES PASS\n")


if __name__ == "__main__":
    {"pre": pre, "post": post}[sys.argv[1] if len(sys.argv) > 1 else "pre"]()
