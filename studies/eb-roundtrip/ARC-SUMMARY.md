# eb-roundtrip arc — what we built, what it proved, and why it was worth the tokens

> Written at arc wrap-up. Status ledger: [`PLAN.md`](PLAN.md) · census: [`FINDINGS.md`](FINDINGS.md)
> · in-game checks: [`PLAYTEST.md`](PLAYTEST.md).

## The deliverable in one sentence

Every event script in FF9 — **9,753 binaries**: 818 fields, 562 battle scenes, and the world
dispatchers, in all 7 languages — plus every `.eb` this toolkit has ever built or edited, now
decompiles to readable, annotated, *re-compilable* source that reassembles **byte-exact**, with
a standing gate that proves it corpus-wide on every run, and an edit path where changing one
operand in the text changes exactly the bytes you meant (4 of 9,268 in the playtest field).

## What shipped (user-facing)

- **`ff9mapkit eb-src <field|path>`** — decompile any event binary to `.ebs` source. Annotated
  by default from the kit's own offline semantic layers: entry roles (`# gateway, armed x3`),
  routine kinds (`# Talk handler — says 8 lines · 2 warps`), warp destinations by name, battle
  scene names, item names, dialogue previews from the field's `.mes`, story-flag band phrases.
  `--plain` for bare grammar. Self-verifying: it will not emit source that does not reproduce
  its input.
- **`ff9mapkit eb-asm <src> [-o out] [--verify-against ref]`** — compile source back.
- **`ff9mapkit eb-asm --against <donor.eb>`** — edit-through-source: splice ONLY the functions
  whose source changed into the donor's own bytes; everything untouched stays verbatim, with
  three self-verifies (envelope identity, lint-no-worse, and splice≡full-reassembly).
- **`ff9mapkit eb-src --verify-all`** — the standing gate: every event binary in the install,
  reported per group, refusing partial corpora.

## The numbers that make it trustworthy

| Claim | Proof |
|---|---|
| **The edit path works in the running game** | ★ owner-playtested: a 4-byte source edit to a deployed Ice Cavern fork gave the edited reward in-game; everything else played stock |
| Stock corpus round-trips | 9,753/9,753 byte-exact (field 5726 + battle 3934 + world 93), the standing gate |
| The kit's own output round-trips | every deployed custom `.eb` swept to date — 133 at hardening, 480 distinct blobs (78 exotic layouts) at Rung 6 — via `off=`/`raw=`/`.gap` escapes |
| Edits are surgical | Ice Cavern chest: 1 operand edited in text → 1 function spliced → 1–4 bytes changed of 9,268; entry table bit-identical |
| The tooling is honest | the writer self-verifies at birth and NAMES every `raw=` fallback on its line; the gate bounds the corpus-wide `raw=` count against the stock baseline (73), so an encoder regression cannot hide behind a green byte-exact count; the splice path surfaces the full assembler's refusal of pin-breaking edits instead of minting bytes; a partial corpus is refused |
| Tests | 95 arc tests in `test_ebsrc.py` (plus sibling `logic_map`/`cmdasm` additions), incl. install-gated corpus sweeps with loud counts; the nightly gate owns the full suite |

## What the arc taught us (new knowledge, now recorded)

1. **Event bytecode is NOT language-identical** — a repo-wide assumption since Session 9,
   falsified by the Rung-1 census: only 238/818 fields match across languages; 94 differ in
   length (window operands, text-pacing waits, voice ids). Source is per (field, language).
2. **The kit's blank-template lineage hides live code outside every entry's declared span**
   (the `.gap` discovery) — the engine reaches Main_Loop by fpos and never consults entry size.
3. **argFlag noise bits exist** in exactly 2 jp-only world binaries corpus-wide — decoders
   ignore them, encoders zero them; the entry-level encode-verify fallback now contains them.
4. **14 shipping fields repeat a func tag inside one entry** — tag-addressed splicing would
   silently hit the wrong namesake; the splice addresses by index with the tag as an assertion.
5. **The engine has three entry-activation opcodes, not one** — the "not spawned" mislabel
   (77% wrong corpus-wide) found by the Rung-4 review, fixed here and in logic_map/GUI.

## Why it was worth the tokens

- **It is the substrate for the north star.** The narrative-state census (the declared weak
  axis) can now run over grep-able text with flags, scenario switches, and warps named — not
  ad-hoc byte scanners. Fork edits become reviewable one-line source diffs.
- **It is a permanent regression harness for the whole `.eb` stack.** Any future change to the
  opcode tables, expression walkers, or edit primitives that would corrupt a byte now trips a
  9,753-file byte-exact gate. This class of silent corruption has cost real playtests before.
- **The adversarial process caught what single-lane work ships.** Two review workflows (72 +
  25 agents) confirmed 28 findings, 4 HIGH, 0 refuted-later — including a silent bytecode
  corrupter in the assembler, a gate that passed green on an empty corpus, a tool that refused
  the kit's own files, and a comment layer that confidently inverted the truth. Every one was
  fixed and regression-tested the same day it was found. The reviews cost roughly a third of
  the arc's tokens and produced the majority of its correctness.
- **It ships user-facing value beyond this project:** the community tooling we know of
  (memory `reference-ff9-modding-community`) offers no `.eb` assembler — Hades Workshop is
  abandoned and corrupts entry-adds, and Memoria itself only interprets. As far as our survey
  reaches, `eb-src`/`eb-asm` is the first working source-level round trip for FF9 event scripts.

## What we deliberately did NOT do

The semantic lift (real fields → `field.toml` vocabulary) stays a future arc, now standing on
proven ground: verbatim islands can carry whatever the vocabulary can't express, with the gate
guaranteeing the islands byte-exact. Rung 5's docsite page also remains open.
