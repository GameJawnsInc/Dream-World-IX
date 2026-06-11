# Faithful Text/Dialogue Carry — Implementation

> The last gap the object + player grafts left. The object carry (`docs/OBJECT_CARRY.md`) and the player-function
> graft (`docs/PLAYER_GRAFT.md`) carry a real field's NPCs/props + their interactions byte-for-byte — but a window
> those grafted bytes open (`WindowSync`/`WindowAsync[Ex]`) names a donor `.mes` TXID a fork doesn't ship → an
> **empty window**. Text carry ships the donor's referenced field text VERBATIM (per language) and remaps each
> grafted window's TXID to it, so the forked interactions show the REAL words. It is the FAITHFUL path; the
> existing `import --dialogue` (editable `[[npc]]` stubs you re-author) is the re-author path. Every number below
> is from a 676-field census against the real bytes; every primitive is verified against the real code.

---

## 1. SUMMARY

A window opcode carries its text id as an immediate operand (`WindowSync`/`WindowAsync` 0x1F/0x20 at operand 2,
the `...Ex` variants 0x95/0x96 at operand 3 — `dialogue.WINDOW_OPS`). The id is a **2-byte immediate**, and FF9
**never computes a window txid** (census: 0/24166 expression txids game-wide), so every one is a static, in-place
remap. Carry:

1. **Collects** the donor txids the grafts will actually SHOW — the windows in each carried object's *carried*
   funcs (its `carry_tags`) + the windows in each grafted *text* player func (`content/textcarry.collect_carry`).
2. **Reads** each referenced txid's text in EVERY shipped language (`dialogue._load_field_text` keyed on the
   field's `eventIDToMESID` text-zone, the same block selection `read_field_dialogue` proved), VERBATIM.
3. **Assigns** each donor txid a fresh band id (`CARRY_BASE_TXID + i`, base **1000**), writes a gitignored
   `<name>.carrytext.json` sidecar (SE-derived strings), and emits one `[carry_text] bin = "…"` line.
4. At **build**: after both grafts, remaps every grafted window's TXID donor→carried — a same-length 2-byte patch
   reusing `content/object._arg_byte_offset(ins, operand)` — and ships the carried text per language, APPENDED
   after the fork's authored `.mes` block (its own `[TXID=>=1000]` re-index keeps it disjoint).

It composes with the object + player grafts (a carried NPC's tag-3 window AND a grafted text player func both get
their real text from one subsystem) and is OPT-IN (`import --carry-text`, which implies `--graft-player-funcs`).
It never touches the authored-dialogue path: single-field authored builds stay byte-identical (the hut golden).

---

## 2. THE BAND — why ≥ 1000, not ≥ 600

A fork ships its OWN `.mes` at its OWN `text_block` (default **1073**); `build.collect_text` writes a fresh block
from `content.text.DEFAULT_BASE_TXID` (**500**) upward by line count. So the only collision surface for carried
txids is (a) the base game's real txids (if a borrowed block were ever read by donor id — it is not, but margin is
cheap) and (b) the fork's own authored 500+ band.

**Census (all 674 windowed fields):** the **max real txid in use is 863** (field 1607, Madain Sari); **32 fields**
use a txid ≥ 600 but **0 fields** use a txid ≥ 1000. So `>= 600` is NOT clear — `>= 1000` is the first
unconditionally-safe floor, and 1000–65535 is still a 2-byte immediate (preserving the same-length patch) with
effectively unbounded headroom (distinct txids per carried interaction is small — mean ~3). `CARRY_BASE_TXID =
1000`. (Reject ≥ 600: it would only work if the fork's authored allocation never reaches 600, i.e. < 100 authored
lines — fragile; a chatty fork or a campaign member breaks it.)

---

## 3. PER-LANGUAGE — carry verbatim, never us-fallback

`.mes` text is per-language (`config.LANGS` = us/uk/fr/gr/it/es/jp). Carry reads each language's block
independently and ships it VERBATIM. The decisive edge case (verified): **field 357 txid 470 is EMPTY (`''`) in
us/uk but populated in fr/gr/it/jp** (`fr = "Kab, chef du village : …"`). A us-fallback would WIPE the
French/German text the English block legitimately lacks — so an empty/absent per-language entry is carried as `''`
(the engine returns `String.Empty`, harmless). The per-language block SELECTION is the `want_txids`-driven
coverage + language-score path `read_field_dialogue` already uses (a field references a contiguous txid subset, so
the best-overlap block is its own; the function-word `_lang_score` then picks the right per-language copy among the
zone's per-lang blocks — passing the field's referenced txids is load-bearing, as a blind block read mis-picks the
language).

---

## 4. THE TWO CONSUMERS (census, all 676 fields)

| Bucket carry serves | Count | Note |
|---|---|---|
| Carried NPCs with a real tag-3 dialogue window | **637 / 665** (95.8%) | the larger prize — every talkable carried NPC |
| **TEXT-classed player funcs** (`scan_player_funcs` safety == "text") | **46** funcs / 30 fields | the 12.5% slice the player graft refused — un-refused by carry |
| Window txids that are static immediates (remappable) | **24166 / 24166** | 0 computed game-wide |
| Ex-variant windows (0x95/0x96, operand 3) | 3576 / 24166 (14.8%) | handled — `WINDOW_OPS` encodes the operand index |

**Consumer A — carried NPC tag-3 talk.** The object graft already carries a talkable NPC's tag-3 func whole; carry
just remaps its window txids + ships the words. ~50% of carried NPC interactions are a single txid, ~75% are ≤ 3.

**Consumer B — grafted TEXT player funcs (the un-refusal hook).** A `text` player func (one with a `WindowSync`)
was REFUSED by the player graft (it would show an empty window). Carry un-refuses it: `scan_objects_verbatim(...,
carry_text=True)` admits `text` to `graftable_player` (so the seeding object carries its interactive tag whole),
`graft_player_funcs(..., graftable_safeties=("clean","text"))` grafts the func, and carry remaps its window. The 46
text funcs are 89% a single line, 100% static immediates, only the plain 0x1F/0x20 variants — a free rider on the
NPC subsystem.

---

## 5. PRIMITIVES (all verified against the real code)

- **`dialogue.WINDOW_OPS = {0x1F:2, 0x20:2, 0x95:3, 0x96:3}`** — opcode → the operand index carrying the txid.
  `argsize(op, opnd) == 2` for all four (verified live); operand 1 = flags (0x80 = a real dialogue box).
- **`content.object._arg_byte_offset(ins, opnd)`** — the decoder-derived byte offset of an immediate operand;
  byte off 4 for the plain variants, 5 for the Ex variants (verified). The same-length patch writes the 2 little-
  endian bytes at `ins.off + bo`. The remap guards `argsize == 2` so it never touches a non-2-byte operand.
- **`dialogue._load_field_text(txids, lang, zone_id=…)`** — reads a real field's `<zone>.mes` block, per-language;
  `_field_text_loader(field)` wires it to the field's `eventIDToMESID` zone.
- **`content.text.mes_entry`** is NOT reused for the carried entries (it forces a default `STRT=10,1` /
  `TAIL=UPR`). A carried entry preserves the donor's exact `STRT` (window geometry) and only emits `TAIL` if the
  donor had one (`_mes_entry_verbatim`) — else the window resizes.
- **`content.object.graft_objects(..., out_slot_map=…)`** — returns the donor_idx→fork-slot map carry needs to
  find each grafted entry; existing callers omit it and are unaffected.

---

## 6. RELATION TO `import --dialogue`

`--dialogue` appends EDITABLE `[[npc]]` stubs (the words become kit-authored content you re-write). `--carry-text`
ships the donor words VERBATIM + remaps (no re-authoring). They are different paths: carry is the faithful default
for grafted `[[object]]` content; the editable stubs remain for fields the author wants to rewrite. For an object
that carries whole, carry SUPERSEDES the stub (the stub is the lossy player-clone re-author path). They can coexist
in one project — the stubs are commented by default, carry is live — but they describe the same NPCs two ways;
remove one.

---

## 7. SCOPE / GUARDRAILS

- **Import-only, opt-in.** No `[carry_text]` ⇒ build is byte-identical to no-carry. The authored path
  (`content/text.py` + `build.collect_text`), the dialogue pillar (`dialogue.py` / `--dialogue`), and the
  object/player/jump/ladder grafts are untouched. Single-field authored builds stay byte-identical (hut golden).
- **Provenance.** Carried strings are SE-derived → the `<name>.carrytext.json` sidecar is gitignored (mirrors
  `.object*.bin` / `.playerfunc*.bin` / `.dialogue.json`). The repo ships zero SE bytes.
- **What carry does NOT do.** It carries only the text the grafts SHOW (a carried NPC's talk, a grafted text
  player func) — not a field's whole `.mes`. A refused object / a dropped (`init_only`) interactive tag carries no
  text (its window is never shown). Computed txids don't exist in real fields, so there is no fallback path.

---

## 8. WHAT REMAINS (the human, per Hard-Constraint §2)

The closing proof — a forked NPC speaks the donor's real line in-game — is the human playtest. Offline, the kit
verifies: the grafted windows point at the carried band, the `.eb` round-trips byte-exact, the per-language `.mes`
ships the donor text verbatim, and the authored band is undisturbed (`tests/test_textcarry.py`, 17 tests incl. 5
install-fed full-pipeline).
