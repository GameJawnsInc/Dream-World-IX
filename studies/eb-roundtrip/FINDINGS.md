# Rung 1 — file-envelope census FINDINGS (2026-08-03)

Probes: `envelope_census.py`, `lang_diff_probe.py`, `lang_divergence_probe.py`,
`empty_slot_probe.py` (+ two scratchpad one-offs). All read-only over the install's
events bundle. Every claim below is measured over the full corpus unless noted.

## The corpus is 818 × 7 = 5726, not 676

`eventbinary/field/<lang>/*.eb.bytes` holds **818 EVT names** in **7 languages**
(es fr gr it jp uk us). The "676" in the plan was the FBG-*folder* count — fields
sharing a background folder (same room, different story beat) each have their OWN
event binary. The round-trip gate must sweep 818 × 7.

## The envelope is maximally clean (all 818, us representative)

- **No gaps, no slack, no reordering, no overlap:** entry bodies start immediately
  after the entry table and are contiguous in table order; EOF slack is 0 in all 818.
- **Func tables are 100% canonical:** `fpos[0] == funcCount*4`, strictly ascending,
  functions contiguous → every fpos is DERIVABLE; the grammar never stores one.
- **`raw[2]` (the "unknown" header u8) is 2 in all 818.**
- entryCount ranges 10..49 (mode 14–19).

## Empty-slot `off` is fully derivable — rule PROVEN 38325/38325 (all langs)

> An empty slot's `off` equals the `off` of the **next non-empty entry**; a
> **trailing** empty (no non-empty after it) parks at the off of the **last
> non-empty entry**. (Interior case ≡ "previous entry's end" since bodies are
> contiguous. This also explains the blank-field lore of empties "parked at 512" —
> that is the trailing rule pointing at the last entry's start.)

0 violations across all 38,325 empty slots in all 5,726 binaries. The grammar
derives empty offs; `loc/flags/pad` of an empty slot are always (0,0,0).

## The "header" is actually the NAME — one 124-byte block at [0x04..0x80)

The bytes the model calls an opaque 44-byte header [0x04..0x2C) are the HEAD of the
field-name string (full-width SJIS-style text, e.g. "Ｃｌｅｙｒａ／…"); [0x2C..0x80)
is its continuation. Treat [0x04..0x80) as ONE per-language name block.

- It differs per language in ALL 818 fields.
- It is NOT text+zero-padding: **jp** blocks routinely carry a SECOND (Japanese)
  name string after the first NUL **plus a ~20-byte binary blob** (constant-prefix
  `a6f1b2baf5cdefa6fa034c…`, per-field suffix — likely PSX-era metadata).
- → grammar: the name block is **opaque per-lang raw hex, preserved verbatim**;
  decoded text is a comment only.

## ⚠ The lang-identical-bytecode assumption is FALSE corpus-wide

With the name block masked, only **238/818** EVTs are byte-identical across all 7
languages. **486** diverge with EQUAL length; **94** diverge in LENGTH (61 jp-only,
16 all six non-us, 13 all-but-jp — i.e. us+jp agree, the European langs differ).
Divergence count by lang: jp 538 · fr 343 · it 327 · gr 326 · es 313 · uk 100.

What diverges (equal-length diff-site op histogram): `WindowSync` 236, `SET`(0x05
expr consts) 216, `WindowAsync` 188, `WindowSyncEx` 142, `Wait` 52, `WindowAsyncEx`
21, `SetTilePositionEx` 12, `RunSoundCode2/3` 17, `FadeFilter` 8 — i.e. dialogue
window txids/geometry, text-pacing waits, and per-language VOICE sound ids.

Consequences:
1. The `.ebs` grammar is **per (EVT, language)** — 5726 source files, not 818.
   (A base+overlay form that shares the 238 identical + factors small deltas is a
   possible LATER optimization, not Rung 2.)
2. The kit's standing "bytecode regions are identical across langs" shorthand
   (extract.py `EVT_LANG` comment, the injector lore) is true for only 29% of
   fields. Existing tools stay safe where they assert expected bytes per-file
   (the injectors do) or ship whole per-lang files (verbatim forks do), but any
   OFFSET computed on `us` must never be applied to another lang's file blind —
   94 fields don't even share lengths.

## Grammar decisions locked by this census

| Element | Decision |
|---|---|
| magic 'EV', raw[2]=2, entryCount | implicit / derived from source structure |
| name block [0x04..0x80) | opaque raw hex per lang, verbatim; decoded text as comment |
| entry table | only per-entry `type loc flags` stored (pad always 0 for real entries); offs/sizes derived |
| empty slots | fully derived (rule above); grammar records only WHICH slots are empty (and slot count) |
| func tables | derived (tags in source; fpos computed) |
| function bodies | cmdasm labeled source (existing, proven) |
| escape hatch | none needed by the data — but keep a `raw`-entry directive for defense |
| file granularity | one source per (EVT, lang) |

## Open items carried to Rung 2/3

- The census structural walk used the `us` file as representative; the Rung-3 gate
  must verify the envelope invariants (contiguity, derivability) on ALL langs while
  it round-trips them — cheap to fold in. (The empty-slot rule is already proven
  on all langs.)
- 3 non-jp files showed nonzero name tails in the us-representative pass — moot
  under raw-hex preservation, but eyeball them once in Rung 2 for curiosity.
- Decide numeric literal canon (decimal + hex comments) when freezing the grammar.
