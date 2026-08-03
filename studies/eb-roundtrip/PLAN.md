# Byte-exact `.eb` round-trip — scoping (Rung 0 research)

> **STATUS:** Rungs 1-3 ★ DONE. Rung 1 census → [`FINDINGS.md`](FINDINGS.md) (corpus is
> **818 EVTs × 7 langs = 5726**; envelope fully derivable; lang-identical bytecode FALSIFIED —
> source is per (EVT, lang)). Rungs 2+3: `eb/ebsrc.py` (`write_source`/`assemble_source`,
> grammar v1 frozen in its module docstring, writer SELF-VERIFIES) + CLI `eb-src`/`eb-asm` +
> the standing gate `eb-src --verify-all` — **5726/5726 byte-exact on the full corpus**, plus
> an install-gated test sweep (`tests/test_ebsrc.py`, loud-count so a partial corpus can't
> pass green). ★ ADVERSARIALLY REVIEWED (72-agent workflow, 22 findings confirmed incl. 3
> HIGH — all fixed): grammar gained `off=` overrides + `raw=` entries + `.gap` records so
> **KIT-built/edited fields round-trip too (133/133 deployed custom .eb)**, the cmdasm
> expression-on-flagless-opcode silent-corruption hole is a hard error, the gate refuses a
> partial corpus, and every failure path is a clean EbSrcError/exit-2. Next = Rung 4
> (comment enrichment from logic_map) and Rung 5 (docs); Rung 6 edit-through-source and
> Rung 7 world EVT_ binaries remain stretch.

**Goal:** decompile any of FF9's 818 real field event binaries (`.eb`, × 7 languages) to a
*readable, re-compilable source file* that round-trips **byte-exact**, proven by a standing
gate that sweeps every binary. This turns every stock field into diffable, greppable,
editable source.

**Explicit non-goal (deferred):** the semantic lift into `field.toml` vocabulary
(`[[npc]]`/`[[gateway]]`/`[behavior]`). This arc stops at the *syntactic* source form.
The lift is a separate future arc that will sit ON this one.

---

## 1. Prior-art inventory — what already exists (verified in code, 2026-08-03)

The substrate is much further along than "start from disasm." Per-function round-trip is
**built and once-proven on all fields**; the gaps are file-level assembly, a source format,
CLI, and a standing gate.

| Piece | Where | Status |
|---|---|---|
| Whole-file byte-exact parse | `eb/model.py` `EbScript` | `from_bytes(x).to_bytes() == x` — parse view only; never re-serializes from structure |
| Instruction decoder + tables | `eb/disasm.py`, `_optables.py` (regenerated from Memoria source — provenance-clean) | mature; `decode_switch` 100% boundary-aligned on all 5563 switches game-wide |
| Expression pretty/assemble | `disasm.pretty_expr` / `eb/exprasm.py` | round-trip proven; auto short/long GLOB tokens; `0xD3` flex-varfunc carved out in all four walkers |
| **Function-level source round-trip** | `eb/cmdasm.py` `disassemble_block`/`disassemble_items` → `assemble_block` | labeled `L<n>` jump/switch targets, relocation under length change; **once-proven byte-exact on 29382/29382 functions, 3155/3155 switch functions across 676 fields** (review-time sweep, 2026-06-15, commit `8f4d8f4`) |
| Structural linter | `eblint.py` | 676 fields / 29382 funcs lint at 0 errors → every shipped function decodes to boundary (no data-in-code surprises at function level) |
| Authored-body jump encoder | `eb/labelasm.py` | island relaxation for >±32K jumps (authoring aid; not needed for faithful round-trip) |
| Read-side semantics | `logic_map.py` (`node_summary`/`node_report`/`kind_label`), `eventscan.py` | rich *comment fodder*: role/tag labels, flag band names, warp destination names, switch selector decode |
| CLI | `ff9mapkit disasm` (cli.py:6480) | pretty print only — output is NOT re-assemblable source; no assemble verb at all |
| Standing tests | `tests/test_cmdasm.py` | round-trip on ONE donor (battle scene `EF_R007`), install-gated skip; the 676-field sweep is not a committed test |

**Conclusion:** this arc is not "build a decompiler." It is: (a) define a whole-file source
format, (b) build the file-level assembler around the proven function-level core,
(c) promote the one-off 676 sweep into a standing gate, (d) ship the CLI.

---

## 2. Gap analysis — what a whole-file round-trip needs that doesn't exist

1. **A source grammar for the file envelope.** `cmdasm` covers a function *body*. A field
   file also has: the 44-byte header (opaque, preserved verbatim today), the 84-byte PSX
   name string (per-language, FF9 text encoding), the entry table (off/sz/loc/flags/pad —
   including EMPTY slots and their parked off values), each entry's type byte + func table
   (tag/fpos). All of it must be representable in source and re-emitted byte-exact.
2. **A file-level assembler.** Parse the source → `assemble_block` each function → rebuild
   func tables (fpos), entry bodies, entry table, header. The fpos/entry-table fixup math
   already exists in `eb/edit.py` (insert_in_function / replace_function_body) but as
   *edit* primitives over existing bytes, not as a from-source serializer.
3. **A byte-conservation story for anything the grammar can't claim.** Unknowns to census
   in Rung 1 (see §4): inter-entry gap bytes, entry-table ordering vs. physical order,
   EOF slack, empty-slot off conventions, per-language differences (bytecode regions are
   known lang-identical; the PSX name may not be). Whatever falls outside the grammar gets
   an explicit escape hatch (`raw` directives) so round-trip never depends on luck.
4. **Determinism + canonicalization.** The emitted source must be deterministic (stable
   int formatting, stable expr rendering) so `decompile → assemble → decompile` is a
   fixpoint and diffs are meaningful.
5. **A standing gate that cannot silently pass.** The 676-sweep must become a committed
   test/CLI (`eb-src --verify-all`). Per `feedback-a-check-that-cannot-fail` and the
   worktree skip trap (project-ff9-test-suite-perf): the gate must FAIL LOUDLY or report
   "N/676 verified", never quietly skip to green in a fresh worktree.
6. **CLI + docs.** `ff9mapkit eb-src <field>` (decompile, with `--comments` enrichment)
   and `ff9mapkit eb-asm <src> -o out.eb` (+ `--verify` self-check), a docsite page.

---

## 3. Source-format sketch (strawman, to be settled in Rung 2)

One file per field, extension `.ebs`. Design principles: byte-exactness is carried by the
*directives*; all human-facing enrichment is in *comments* (stripped by the assembler, so
they can never break the round-trip).

```
.eb field 351 "FBG_N08_DLII..."          # comment: Dali Inn (from _fieldtable)
.header raw <hex...>                     # 44B opaque header, verbatim
.name lang=us raw <hex...>               # 84B PSX name; decoded text in a comment

.entry 0 type=0 loc=.. flags=..          # role: main            (comment via logic_map)
  .func tag=0                            # Main_Init
    SET({Global.Bit[8712] = 1})          # flag 8712 -- kit safe band
    Field(1055)                          # -> Dali Inn (comment)
    L12:
    JMP(L12)
  .func tag=1                            # Main_Loop
    ...
.entry 1 EMPTY off=512                   # parked-off convention preserved
```

Open grammar questions (settled by the Rung-1 census, decided in Rung 2):
- entry/table metadata as explicit fields vs. raw where opaque (`loc`/`flags`/`pad`);
- whether fpos values are ever non-canonical (func table not tightly packed) → if yes,
  they need explicit representation; if no, they're derived;
- numeric literal style (decimal with hex comments vs. hex) — pick once, canonically;
- how the 7-language set is expressed: one `.ebs` + per-lang `.name` lines (bytecode is
  lang-identical — assert it at decompile time and refuse otherwise).

---

## 4. Rung ladder

- **Rung 1 — file-envelope census (research, offline). ★ DONE 2026-08-03** →
  [`FINDINGS.md`](FINDINGS.md) (probes checked in beside it). All grammar questions
  answered; §3's open questions are settled there.
- **Rung 2 — grammar freeze + writer.** Decide the `.ebs` grammar from the census; build
  the decompiler (`ebsrc.py`: `write_source(eb_bytes) -> str`), deterministic output.
- **Rung 3 — reader + file assembler + the identity proof.** `parse_source(str)` →
  full-file serializer. Gate A: `assemble(write_source(x)) == x` for the golden donors in
  the repo fixtures. Gate B: the full 676×(bytecode)+7-lang sweep as an install-gated
  test AND a CLI verify verb that prints `676/676 byte-exact`. This is the arc's keystone
  milestone.
- **Rung 4 — enrichment pass (comments only).** Wire `logic_map`/`eventscan`/catalog into
  comments: entry roles, tag kind labels, flag band names + read/write phrasing, Field()
  destination names, txid → `.mes` line previews, switch selector decode (ScenarioCounter
  etc.), resolved RunScript targets. Round-trip stays strict (comments stripped).
- **Rung 5 — CLI + docs + fixpoint.** `eb-src` / `eb-asm` verbs, `decompile(assemble(s))`
  fixpoint test, docsite page. Ship in a kit release.
- **Rung 6 (stretch) — edit-through-source.** `eb-asm --against <donor>` mode that
  reassembles only *changed* functions via `replace_function_body` (untouched bytes stay
  verbatim — belt-and-braces for hand edits). This is the bridge the future semantic-lift
  arc will stand on, and it makes `.ebs` diffs a practical review artifact for
  `[[logic_edit]]`-class changes.
- **Rung 7 (stretch) — the non-field EVT_ binaries.** 818 FBG ids − 676 field maps ≈ 142
  world/special event binaries (world dispatchers 9000-9012 among them). Same format;
  census first (their entry shapes may differ). Battle `.eb` stays in the battle lane
  (already has its own proven asm path).

## 5. Risks / open questions

- **The 676 sweep was one-off.** cmdasm has since gained users (logic_add/edit, ferry
  lane, aiauthor) but the full-field sweep hasn't re-run; Rung 3's gate re-proves it and
  keeps it proven. Any regression found is a bug to fix, not a blocker.
- **Pretty-form ambiguity.** `assemble_instruction` inverts the *decoded* operand form; if
  any field instruction has two byte encodings decoding to the same pretty form (e.g. a
  redundant argFlag bit), byte-exactness breaks. The one-off sweep says no such case
  exists in shipping data; the standing gate makes that an invariant, and any exception
  gets a `raw` escape hatch.
- **Provenance.** A decompiled `.ebs` is derived from SE bytecode → NEVER committed to the
  repo (same rule as templates). The corpus regenerates locally from the user's install;
  repo fixtures stay the existing kit-authored synthetic `.eb`s + the already-committed
  test bytes. The gate runs install-gated, like the byte-level suite.
- **Perf.** 676 × decompile+assemble+diff should land well under a minute (pure Python
  over ~1-5KB files); if not, it's still fine as an opt-in `--verify-all` + CI-on-main.

## 6. Why this arc pays rent

- Every stock field becomes searchable/diffable SOURCE → the narrative-state census
  (scenario dispatch, flag constellations) runs over text instead of ad-hoc byte scans.
- Verbatim-fork edits (`[[logic_edit]]`/`[[logic_add]]`) become reviewable as source
  diffs (Rung 6).
- A permanent regression harness for the whole disasm/asm stack: any future opcode-table
  or expr-walker change that would corrupt an edit now trips 676 byte-exact diffs.
