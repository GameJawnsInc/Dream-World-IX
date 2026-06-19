# Releasing Dream World IX

Maintainer runbook for cutting a public release of **Dream World IX** (the `ff9mapkit` toolkit).
Nothing here is automated — each step is deliberate. Current target: **`1.0.0b1`** (first public beta).

> **HEAD is already provenance-clean** — only the kit's own hut demo quad is tracked. The work below
> is about git **history** (which still holds Square-Enix-derived blobs) and the mechanics of going public.

---

## 0. Two hard gates (both must clear before *any* public push)

1. **Dali faithful-opening playtest is clean in-game.** Includes resolving (or documenting) the disc-1
   ATE SELECT-menu duplication. This is a human gate — it cannot be verified from code.
2. **The git-history SE-byte scrub has run** (§1) and the verify-grep (§2) returns only hut blobs.

Until both are done: no push, no remote, no public flip.

---

## 1. One-time history scrub (`git filter-repo`)

The repo keeps its full commit history (messages/dates/graph preserved); the scrub only excises the
contents of Square-Enix-derived blobs. `git filter-repo` **rewrites every branch**, so do this with the
feature branches quiesced (merged or accepted as rewritten — it's all local).

Install once: `pip install git-filter-repo`.

```bash
# from the repo root, all branches quiesced
git bundle create ../dwix-pre-scrub.bundle --all     # SAFETY NET (restore: git clone ../dwix-pre-scrub.bundle restored)

git filter-repo --force --invert-paths \
  --path backups \
  --path mod \
  --path reference/bgx-samples \
  --path reference/test2 \
  --path-glob 'reference/field-*.txt' \
  --path tools/room02_out \
  --path tools/room03_out \
  --path ff9mapkit/ff9mapkit/data/blank_field \
  --path-regex '.*evt_alex1_at_street_a\.eb\.bytes$' \
  --path ff9mapkit/tests/fixtures/alex100-us.eb.bytes \
  --path-glob 'ff9mapkit/tests/fixtures/clean-*.eb.bytes' \
  --path ff9mapkit/tests/fixtures/editor_multifloor.bgi.bytes \
  --path ff9mapkit/tests/fixtures/grgr.bgx
```

**Wholesale-removed** (purely SE-derived or regenerable scratch): `backups/`, `mod/`,
`reference/bgx-samples/`, `reference/test2/` (817 decompiled real-field scripts), `reference/field-*.txt`
(decompiled fields, e.g. the Alexandria weapon shop), `tools/room02_out/`, `tools/room03_out/`,
`ff9mapkit/ff9mapkit/data/blank_field/` (the real-field-derived blank template — regenerated from the
user's install by `extract-templates`).

**Surgically-removed from otherwise-kept dirs** (these dirs also hold the kit's own hut demo, which
**stays**): the real Alexandria street fork `evt_alex1_at_street_a.eb.bytes` inside `release/`, and the
real-field test fixtures `alex100-us.eb.bytes` / `clean-*.eb.bytes` / `editor_multifloor.bgi.bytes` /
`grgr.bgx` inside `ff9mapkit/tests/fixtures/`.

**Kept (kit-authored, safe to ship):** the hut quad — `release/FF9CustomMap/**/{EVT_HUT_EXT,EVT_HUT_INT}`,
`FBG_N11_HUT_*`, the custom `1073.mes`, `ff9mapkit/tests/fixtures/hut_*`, `tools/hut_out/**HUT**`.

> `filter-repo` removes the `origin` remote by default (a safety feature) — you re-add it in §3.

---

## 2. Verify the scrub (must pass before going further)

```bash
# game-byte blobs ever added — expect ONLY hut quad + the custom 1073.mes:
git log --all --diff-filter=A --name-only --pretty=format: \
  -- '*.eb.bytes' '*.bgx' '*.bgi.bytes' '*.mes' '*.bgs' | sort -u

# the wholesale-removed trees — expect NOTHING:
git log --all --oneline -- backups mod reference/test2 reference/bgx-samples \
  tools/room02_out tools/room03_out ff9mapkit/ff9mapkit/data/blank_field
```

If anything SE-derived still appears, add it to the `filter-repo` path set and re-run from the bundle.
Treat this as **verify-and-iterate**, not one-shot-trust. (Claude can run this verify pass and report.)

---

## 3. Publish sequence (only after §0–§2 are green)

1. On GitHub, rename the repo `FFIX` → `Dream-World-IX`.
2. Re-point the remote (filter-repo dropped it):
   `git remote add origin https://github.com/GameJawnsInc/Dream-World-IX.git`
   (the `pyproject.toml` / `CHANGELOG.md` slug already matches this URL).
3. Push the scrubbed history: `git push --force --all` then `git push --force --tags`.
4. Tag the beta: `git tag -a v1.0.0b1 -m "Dream World IX 1.0.0b1 — first public beta"` then push the tag.
5. Flip the repository to **public**.
6. (Optional) Build + publish to PyPI: `python -m build && twine upload dist/*` (version `1.0.0b1`).

---

## Notes

- **Version form.** `pyproject.toml` carries the PEP 440 string `1.0.0b1`; the CHANGELOG header, git tag,
  and URLs all use the same. Bump it there + add a dated CHANGELOG section for each subsequent release.
- **Engine honesty.** The shipped fork-fidelity engine is the bundled `s23` / `s24` / `s29` patch set
  (see `ff9mapkit/docs/ENGINE.md`). Disc-1 gates are in-game proven; the newest late-disc (s29) softlock
  gates are still being playtested — keep that caveat accurate as zones are verified.
- **Scratch hygiene.** `tworoom/treno_plat/` (SE-derived fork scratch) is gitignored; never `git add -A`
  it in before the scrub.
