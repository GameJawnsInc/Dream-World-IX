# Releasing Dream World IX

Maintainer runbook for cutting a public release of **Dream World IX** (the `ff9mapkit` toolkit).
Nothing here is automated — each step is deliberate. Current target: **`1.0.0b2`**. The first-publish
steps (create the public repo, push `master`, flip to public — steps 1–2, 5–6 below) are **one-time and
already done** for `1.0.0b1`; a subsequent release is just tag + engine bundle + (optional) PyPI.

> **HEAD is already provenance-clean** — only the kit's own hut demo quad is tracked. The work below
> is about git **history** (which still holds Square-Enix-derived blobs) and the mechanics of going public.

---

## 0. Two hard gates (both must clear before *any* public push)

1. **Dali faithful-opening playtest is clean in-game.** Includes resolving (or documenting) the disc-1
   ATE SELECT-menu duplication. This is a human gate — it cannot be verified from code.
2. **The git-history SE-byte scrub has run** (§1) and the verify-grep (§2) returns only hut blobs.

Until both are done: no push, no remote, no public flip.

---

## 1. Archive the original, then clone it for the scrub (Pattern 3)

The current `FFIX` repo stays **private and untouched** as the full-history archive (it holds the
SE-derived bytes). The scrub runs on a throwaway **clone**, which becomes the public repo — so the
destructive rewrite never touches your only copy.

`git filter-repo` preserves the commit history (messages, authors, dates, branch graph) and only
**rewrites the commit SHAs** to drop the excised blob contents — your build log stays intact.

Install once: `pip install git-filter-repo`.

```bash
# (recommended) an extra off-machine snapshot of the original -- keep PRIVATE:
git bundle create ../dwix-archive.bundle --all       # restore: git clone ../dwix-archive.bundle

# make an independent clone of master OUTSIDE the original repo, and scrub THAT:
cd ..
git clone --no-local -b master FFIX-editor_gui Dream-World-IX
cd Dream-World-IX
git remote remove origin                             # detach from the private archive

# scrub the clone:
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

## 3. Publish sequence (only after §0–§2 are green) — run from inside the scrubbed `Dream-World-IX/` clone

1. On GitHub, create a **new, empty, private** repo `GameJawnsInc/Dream-World-IX` (private for now;
   you flip it public in step 6). Leave the original `FFIX` repo **private** as the permanent archive.
2. Point the clone at it and push master (the pyproject/CHANGELOG slug already matches this URL):
   ```bash
   git remote add origin https://github.com/GameJawnsInc/Dream-World-IX.git
   git push -u origin master
   ```
   (Only `master` goes public — a clean public repo. The archive keeps every branch.)
3. Tag the beta and push it:
   ```bash
   git tag -a v1.0.0b2 -m "Dream World IX 1.0.0b2 — verbatim-fork spatial authoring + engine s23–s33"
   git push origin v1.0.0b2
   ```
4. **Build + attach the custom-engine bundle.** Forked fields need it, and
   [`ENGINE.md`](ff9mapkit/docs/ENGINE.md) tells users to download it from Releases — so the asset MUST
   exist when the repo goes public, or every fork's install path dead-ends.
   - Build the fork-fidelity engine: apply `memoria-patches/` `s23` + `s24` + `s29` + `s30` + `s31` +
     `s32` + `s33` (plus `s22` for the F6 dev menu) to a Memoria source clone and compile `Assembly-CSharp`
     (see ENGINE.md "Build from source"; the per-file map is `memoria-patches/README.md`).
   - Assemble `dwix-custom-memoria-1.0.0b2.zip` = the three managed DLLs (`Assembly-CSharp.dll` + the
     matched `Memoria.Prime.dll` / `UnityEngine.UI.dll`) + an `INSTALL.txt` + MIT/Albeoris attribution.
     (A pre-built bundle exists at `dwix-custom-memoria-1.0.0b2.zip` outside the repo — rebuild only if
     the patch set or the Memoria base changed. The b1 bundle was s23/s24/s29; b2 adds s30–s33.)
   - **Verify the zip ships zero game bytes**, then create the GitHub Release for `v1.0.0b2` and upload it
     as a Release asset. Keep the asset filename in lockstep with ENGINE.md's download instruction.
5. Sanity-check the GitHub repo (README renders, no stray branches, no game bytes in the tree).
6. Flip the repository to **public**.
7. (Optional) Publish to PyPI: run `python -m twine check dist/*` first (the metadata + README-render
   gate), then `python -m build && twine upload dist/*` (version `1.0.0b2`).

---

## Notes

- **Version form.** `pyproject.toml` carries the PEP 440 string `1.0.0b1`; the CHANGELOG header, git tag,
  and URLs all use the same. Bump it there + add a dated CHANGELOG section for each subsequent release.
- **Engine honesty.** The shipped fork-fidelity engine is the bundled `s23`–`s33` patch set
  (see `ff9mapkit/docs/ENGINE.md`). Disc-1 gates plus the s30/s31 walk+occlusion and s33 menu-LOCATION
  fixes are in-game proven; the late-disc s29 softlock gates, s32, and the s33 sibling sweeps ship
  unverified (identity-safe for real fields) — keep that caveat accurate as zones are verified.
- **Scratch hygiene.** `tworoom/treno_plat/` (SE-derived fork scratch) is gitignored; never `git add -A`
  it in before the scrub.
