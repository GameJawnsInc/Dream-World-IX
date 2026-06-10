# `research/` — FF9 story-flag (gEventGlobal) research

Artifacts from the `story_flags` branch: how to **view / understand / name / create / recreate** FF9's
save-persistent story flags. Start with **`STORY_FLAGS.md`**.

| File | What it is |
|---|---|
| **`STORY_FLAGS.md`** | **The research report.** The 2048-byte heap mapped; the five verbs (current state & gaps); the safe-band collision finding; prioritized toolkit work; a named-flag catalog. |
| `CENSUS_DIGEST.md` | Human-readable data appendix — scenario milestones, bit-flag region clusters, word-var map. Regenerate: `py make_digest.py`. |
| `flag_catalog.toml` | **Named-flag registry seed** (machine-readable) — engine-grounded named vars + reserved regions + scenario milestones + auto-derived empirical clusters + recommended safe bands. Regenerate: `py make_catalog.py`. **This seeded the kit's canonical registry, now `ff9mapkit/ff9mapkit/flags.py`** (recommendation 2 — `ff9mapkit flags` / `flags-inspect`). |
| `flag_census.py` | The scanner: reads every real field's `.eb` from p0data and decodes every save-persistent `gEventGlobal` variable, byte-exact against the engine's token layout. Run from kit root: `cd ff9mapkit && py ../research/flag_census.py`. |
| `flag_census.json` | Full census output (per-index aggregation, per-field summary, scenario map). **Gitignored — regenerable** (~1 MB). |
| `make_digest.py` / `make_catalog.py` | Regenerate the digest / catalog from the JSON. |

## The one-paragraph model

FF9 story state lives in one save-persistent blob: `EventState.gEventGlobal` (2048 bytes), the engine's
`VariableSource.Global` space. It holds **(1)** the **ScenarioCounter** (UInt16 @ bytes 0–1, the master
story-progress value, 1..12000), **(2)** ~1051 **bit-flags** (once-events, gates, chest-opened state) and
**(3)** word-counters. Field scripts touch it via the `0x05` expression opcode. The kit can already *encode*
and *scan* flags but has no **name registry**, **save-file viewer**, or **seed/recreate** tool — and its
campaign flag band (8300+) **collides** with real FF9's chest flags (bits 8376–8511); the first provably-safe
base is **bit 8512**. Full detail + citations in `STORY_FLAGS.md`.

## Reproduce from scratch

```
cd ff9mapkit && py ../research/flag_census.py   # scan all 676 fields -> research/flag_census.json
py research/make_digest.py                       # -> CENSUS_DIGEST.md
py research/make_catalog.py                      # -> flag_catalog.toml
```
