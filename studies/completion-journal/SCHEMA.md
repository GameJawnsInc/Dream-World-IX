# The full-fidelity catalog schema — FROZEN (v1)

> The data contract for the walkthrough-shaped journal the owner picked (PLAN.md
> §7.2 Q3). Two layers, one law: **every displayable fact is either derivable
> from a declared predicate, or explicitly labelled NOT TRACKED — never silently
> omitted, never invented.**

## The two layers

| layer | unit | count | where | authored by |
|---|---|---|---|---|
| counter catalog | an aggregate number (Chocographs 9/24) | 48 rows | `journal.py` `ROWS` (code, shipped) | machine, done |
| **entry catalog** | one obtainable/completable THING (the Elixir chest in Gizamaluke's Grotto) | ~600 machine-seeded + hand rows | `journal_catalog.toml` (data) | generator skeleton + human prose |

The counter catalog is T1b, unchanged. This document freezes the **entry
catalog**.

## The entry row

```toml
[[entry]]
id          = "treasure.b7687"          # keyed on the LATCH BIT for treasure (Q2: fields double-count, bits don't)
section     = "d1.gizamaluke"           # the walkthrough-spine key (below)
category    = "treasure"                # treasure|keyitem|card|chocograph|minigame|mognet|story|party|combat|meta
title       = "Elixir chest"            # display; budget-linted against the MEASURED pane (§7.2 Q6)
detail      = "Behind the bell altar."  # OUR prose, original wording; budget-linted
# --- exactly ONE predicate (lint-enforced, the neither/both rule from T1b) ---
latch       = 7687                      # a monotone GLOB once-bit
# window    = { on = 3593, off = 3599 } # a set-then-clear pair (the ~76-bit population)
# inventory = 263                       # B_HAVE_ITEM class -- the item IS the latch
# counter   = "party.key_items"         # delegate to a counter-catalog row id
# manual    = "no engine registry"      # NOT TRACKED -- rendered as such
# --- optional columns ---
item        = 236                       # id-keyed: display name resolves at RUNTIME from live tables (§7.4, Moguri)
missable    = { close_sc = 4080, confidence = "derived" }   # derived|owner|none
exclusive_group = ""                    # rows that cannot all complete in one run
run_mode    = ""                        # e.g. "excalibur2" -- totals computed per mode
provenance  = "census"                  # engine|census|owner|crosscheck
source      = "treasure_join v2 event f706/b7687"
verify      = "unverified"              # unverified|save-diffed|playtested
```

## The laws (each becomes a lint that MUST be provable-breakable)

1. **Exactly one predicate per row** — the T1b neither/both rule, extended to
   five predicate kinds.
2. **Atlas exhaustiveness, both directions** — every v2 reward event appears as
   exactly one row (or one shared row for F5 split-bit events, listing both
   bits); every `latch`/`window` bit in the catalog exists in the census. A
   catalog row citing a bit no script writes is a typo caught at lint, not in a
   playtest.
3. **The catch-up filter is a catalog gate too** — a `latch` bit that any
   Main_Init mass-sets under an SC guard (the 3818 class) is REFUSED as a
   predicate; it can only appear as `manual` with the reason.
4. **Missable verdicts gate on confidence** — the UI may say "PERMANENTLY
   MISSED" only for `confidence = "owner"` (playthrough-confirmed). A
   `derived` close_sc renders as "window likely closed". A wrong confident
   verdict is this feature's worst failure mode (§T4) and the schema makes the
   overconfident state unrepresentable.
5. **Runtime name resolution** — a row with `item` set derives its display
   name from the live item table, never from baked catalog text (§7.4: the
   owner's install stacks Moguri).
6. **Text budgets are measured, not inherited** — title/detail budgets come
   from the live pane measurement (§7.2 Q6, still owed); until measured, the
   lint pins the T1b word-wrap datum (the authored header wrapped at bench
   30801) as a ceiling.
7. **Totals are per run_mode** — a full bar must be reachable in every declared
   mode (§T4's "100% is ill-defined"; the ATE-80 pair, hunt winners,
   Excalibur II).
8. **Provenance: `crosscheck` rows never ship text** — guide-derived facts may
   only confirm a census/engine fact (the owner's ruling: reference, never
   reproduction; our missable SET comes from the census + the owner's
   playthrough, not any compilation's selection).

## The walkthrough spine (`[[section]]`)

Sections are OUR arrangement of the game's own order — disc + area, joined to
SC by the curated anchor table (`flags.py` STORY_REGIONS / the 52 anchors):

```toml
[[section]]
id     = "d1.gizamaluke"
disc   = 1
title  = "Gizamaluke's Grotto"
sc     = { enter = 3560, leave = 4080 }   # from the anchor table, NOT hand-invented
areas  = [24]                             # field-manifest area ids, for the room join
```

The spine is ~40-50 sections. Entry rows join to sections by hand during the
authoring pass (the machine seed guesses from the field→area map; a human
confirms — this is part of the prose pass, not extra work).

## What is deliberately NOT in the schema

- **No per-chest "chests N/446" total** — the catalog can COUNT ITS OWN latch
  rows and show "chests found: N of the M this journal tracks". The 446-class
  external denominators stay banned (journal.py's standing law).
- **No localized bodies** — one body, written to 7 language dirs (Q5 default).
- **No bestiary/synth/Nero/friendly-monster rows except as `manual`** — the
  unrepresentable list from §T4 renders as NOT TRACKED with reasons.

## Freeze discipline

Additive changes (new optional columns) are free. Changing a predicate kind's
semantics after rows are authored is a migration with a script, never a hand
edit — the catalog will be ~600+ rows and a silent semantic drift across them
is unreviewable.
