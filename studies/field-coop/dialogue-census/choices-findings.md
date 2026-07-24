# CHOICES lane — byte census of every player-choice construct in the FF9 field corpus (F3)

> **Scope:** the CHOICES sub-lane of the F3 netsync dialogue-lockstep census. Reads every real field's
> compiled `.eb` live from the Steam install (818 fields, all present) and walks **raw decoded opcodes +
> expression token streams** — never a text transcript (the CENSUS LAW). Read-only research; nothing built.
> Companion: `../dialogue-sync.md` (the L0–L3 design ladder + the MAP-vs-GLOB divergence census) and
> `../interactions-census.md` (the 8358 IsButton / talk-suppression census). This doc answers the CHOICES
> questions those two flagged but did not enumerate.
>
> **Reproduce:** `cd ff9mapkit && python ../studies/field-coop/dialogue-census/choice_census.py --dump-tables`
> (deterministic, sorted id order; raw table dump → `choices_census_output.txt`). All numbers below are that
> script's output, cross-checked against the engine (`C:\gd\FFIX\Memoria`) and the kit's own byte-grounded
> `content/choice.py`.

---

## 1. The choice idiom — the exact opcode, variable, and text tag (Q1)

A dialogue choice has **two byte halves**, one in the `.mes` TEXT and one in the `.eb` SCRIPT:

- **Text side (the rows + cancel):** the option rows live *inside a text entry* as an inline `[CHOO]` tag
  (the kit calls it `[CHOO][MOVE=18,0]<row>\n<row>…`); `[PCHC=count,cancel]` sets count/cancel/default
  without hiding rows, `[PCHM=count,cancel]` additionally applies a hide-mask. `Dialog.HasChoices`
  (`Dialog.cs`) is driven by `TextParser.ParseStep.ChoiceSetup` finding `startChoiceRow >= 0` — i.e. **which
  lines are choices is parsed out of the text, not signalled by a separate opcode** (confirmed against the
  engine in `../dialogue-sync.md §1b`). This half is NOT in the `.eb` and is out of this census's byte scope
  (see the Method note); it is fully characterized in the kit source `content/choice.py:99-129`.

- **Setup opcode (optional):** `EnableDialogChoices` (**`0x7C`**, `CHOOSEPARAM`) → `ETb.SetChooseParam(mask,
  default)` presets the availability bitmask + the initially-highlighted row for the *next* window. Present in
  **412** places corpus-wide (not every choice uses it — a plain menu takes its count from the rows).

- **The carrier of the chosen index — the load-bearing fact for F3:** the script reads the pick with the
  expression token **`B_SYSVAR` (`0x7A`) with code `9`** → `EventEngine.GetSysvar(9)` → `ETb.GetChoose()`
  (0-based row). **In bytes it is `7A 09` inside an expression stream.** `DialogManager.SelectChoice` (a single
  machine-local static, filled at window close) is what `GetChoose()` returns — never transmitted today.

Three verified byte exemplars (field 300, Ice Cavern save-moogle, `entry 3 tag 3`):

| construct | bytes | meaning |
|---|---|---|
| switch dispatch | `05 7a 09 7f` · `0b 06 00 00 …` | `push GetChoose()` then `switch` with **6** case arms |
| if-compare | `05 7a 09 7d 06 00 20 7e 00 00 0a 00 4f 27 7f` · `02 0b 00` | `if (GetChoose()==6 && (0xA0000 B_KEYON)) { 11 bytes }` |
| store-the-pick | `05 d6 09 7a 09 2c 7f` | `Instance.Byte[9] = GetChoose()` |

**Corpus totals:** **2134** GetChoose (`B_SYSVAR[9]`) reads across **392 / 818 fields (48%)** and **864
functions**. Essentially every read (2131 / 2134) sits in a standalone expression statement `op_05`; 3 are
embedded in another opcode's expression arg (`SetTextVariable(…GetChoose…)` = echo the pick into text, one
`RemoveItem`, one `EnableDialogChoices`).

### Three consumption MODES (how the script uses the pick) — the atomic breakdown

| mode | reads | % | shape |
|---|---:|---:|---|
| **SWITCH** | 643 | 30.1% | `op_05{7A 09 7F}` immediately followed by a jump-table (`0x0B`/`0x06`/`0x0D`); one arm per row |
| **IF** | 1157 | 54.2% | `op_05{7A 09 7D k <cmp> …}` followed by `JMP_FALSE 0x02`; one read per compared row |
| **STORE** | 330 | 15.5% | `op_05{<var> 7A 09 <assign>}`; the pick copied into a variable, re-read later |
| OTHER | 4 | 0.2% | GetChoose used mid-expression (not a branch/store) |

IF compare operators: `==` 711, compound/other `?` 325 (the read is ANDed/combined, e.g. with a `B_KEYON`
gate as in the exemplar), `<` 117 (a range test on the pick), `!=` 4.

STORE target scope (**the key F3 signal — where the pick lands**): **Instance 296, Map 28, Global 6**. The
pick is copied into a *transient per-object/per-field* var **98.2%** of the time (the `Instance.Byte[9] =
GetChoose()` idiom above), and into a save-persistent Global flag only **6** times corpus-wide.

---

## 2. Shapes — rows, default, cancel, and the softlock class (Q2)

### Row counts

Switch dispatch gives an **exact** row count (one arm per row). If-chains are grouped into menus
heuristically (the `.eb` has no window marker — see Method), so lead with the switch data:

| rows | switch sites | | rows | switch sites |
|---:|---:|---|---:|---:|
| 1 | 41 | | 7 | 10 |
| 2 | 156 | | 8 | 2 |
| 3 | 161 | | 9 | 3 |
| 4 | 40 | | **10** | **84** |
| 5 | 66 | | 11 | 1 |
| 6 | 78 | | 16 | 1 |

**643 switch menus** total. The mass is 2–3 rows (yes/no + one extra), but there is a hard **spike at 10 rows
(84 sites)** — a recurring shared menu, overwhelmingly in tag-3 talk handlers (86 of the ≥10-row menus break
down `tag3:59, tag1:26, tag2:1`), i.e. the save-point / shop / Mognet-style option lists that repeat across
dozens of fields. If-chains skew **small** (grouped: 541 single-pick guards, 159 two-row, 53 five-row, 5
six-row) — confirming the division of labour: **switches carry the big and the nested-safe menus; if-chains
carry the yes/no confirms and lone `if (GetChoose()==k)` guards.**

### Default index

`EnableDialogChoices` arg1 (the highlighted row): **0 → 322, 1 → 6, 8 → 2**. Default is row 0 in 98% of the
412 setups; the two `default=8` cases are the ≥9-row menus. No default `≥ 16`.

### Cancel behaviour

Cancel index is set by the **text-side** `[PCHC/PCHM=count,cancel]` tag, not the `.eb`, so it is not
byte-censused here — but the engine law is established and load-bearing: **with no `[PCHC]/[PCHM]` override,
CANCEL (B) returns the LAST row**, and cancel is enabled by default (`ETb.SetChooseParam`; kit `content/
choice.py:20,119` — "engine default cancel = last row … put the decline option last"). For F3 this means a
guest pressing B yields the last index — mechanically just another possible index, no special case.

### The softlock class

The project's known softlock — **`Party(4,·)` under four characters is unescapable** — is **NOT** a dialogue
`GetChoose`. It is the **`Menu` opcode (`0x75`) with menu-id 4** (party-change), a different construct
(`opcodes.menu`; menu-id 3 = save, 5 = chocograph; the party-menu min is now a runtime `partychk` clamp per
the project brief). Census of `Menu(0x75)` arg0 corpus-wide: **id0: 23, id1: 17, id2: 130, id4 (party): 65,
id5 (chocograph): 5** — **65 fields open `Menu(4,*)`**. This is the softlock family to special-case for F3,
orthogonal to the dialog-choice lane.

For dialog choices proper, the "count exceeds displayable/selectable" degeneracy the kit documents is a
**mask/default mismatch**, and it is rare in stock: **37** `EnableDialogChoices` masks have bit 15 set (the
`0xFFFF`-sign-extension class `pre_choose` warns about — where `SetChooseParam`'s `while availMask>0` loop can
collapse the default to 0), and **0** have a default row `≥ 16`. Dialog windows themselves render tall
option lists fine (the 10- and 16-row menus ship and work), so the dialog-choice softlock surface is the
mask degeneracy, not row count.

---

## 3. Consumption — where the chosen index flows (Q3)

Every GetChoose read is, by construction, an **immediate branch or a store** — there is no third thing. The
question that matters for F3 is what the *branch arms / the store target* then do. Arms are delimited from
the `.eb` (switch: each case arm `[target, next-edge-target)`, excluding the far-jumping default; if: the
`JMP_FALSE` skip), and every var-write in the delimited region is classified by its variable-token **source**
(`token & 3`: `0=Global`=save-backed & **mirrored** to the guest, `1=Map` / `2=Instance` = transient &
**not** mirrored).

**Per branch site (1402 sites = 643 switch + 759 grouped if-chain):**

| consequence bucket | sites | % | meaning for F3 |
|---|---:|---:|---|
| DIV_GLOB | 726 | 51.8% | arm writes transient **and** a GLOB flag — **story mirrors**, only presentation can differ |
| DIV_ONLY | 376 | 26.8% | arm writes **only** transient MAP/INST — per-visit divergence, wiped on field reload |
| INERT | 197 | 14.1% | no write/warp/item/menu — pure reply text/SFX, nothing to diverge |
| GLOB_only | 90 | 6.4% | arm writes only Global flags — fully mirrored |
| ITEM_MENU | 13 | 0.9% | arm only grants an item / opens a menu |
| WARP (exclusive) | 0 | 0% | (warps never appear *alone* — they co-occur with a flag write; see below) |

**Overlapping arm attributes** (a site may have several — the honest view of "what an arm can do"):
**any-GLOB-write 816 (58%)**, any-transient-write 1102 (79%), **warp (`Field()`) 236**, opens a menu 159,
grants an item 127, advances `ScenarioCounter` 12.

**Per STORE read (330):** Global (mirrored) **6 (1.8%)**, Map/Instance (transient) **324 (98.2%)**.

So: the pick's *immediate* effect is a branch (85%) or a transient capture (15%). Its *downstream* effect is
a **GLOB flag write on 58% of branch sites** (mirrored to the guest by the existing state mirror) and a
**transient MAP/INST write on 79%** (not mirrored). Crucially the two overlap heavily — **more than half of
all branch sites (51.8%) write BOTH**, so the durable half of the outcome is already synced even when the
guest picks differently.

---

## 4. Nesting / chaining / ATE (Q4)

- **Choice-inside-a-choice-result (nesting):** **219** branch sites have an arm that contains *another*
  GetChoose read. This is exactly the hazard the kit's `switch_on_choice` exists to defuse (a nested window
  overwrites `DialogManager.SelectChoice`, so re-reading `GetChoose()` in a later arm reads the *inner*
  answer) — and it is why the 10-row menus are switch-dispatched, not if-chains.
- **Choices in sequence within one function:** **123** functions hold **more than one** branch site (a
  menu, then a follow-up menu) — the multi-step conversation/shop pattern.
- **Choice inside an ATE:** **22** choice-bearing functions also contain an `AICON` (`0xD7`) op — i.e. a
  choice rendered under the ATE-icon/`winATE` flavour. Small but non-zero; per `../dialogue-sync.md §2d` an
  ATE accept is the same `GetChoose` mechanism plus the (never-mirrored) `AteCheckArray` achievement write.

---

## 5. What this means for F3 — the cost of a guest choosing differently (Q5)

**Headline: no stock choice can permanently diverge the story.** Every durable consequence of a choice is a
**Global (`gEventGlobal`) write**, and the existing state mirror (`NetSyncState.ApplyStory`) overwrites the
guest's entire `gEventGlobal` from the host's snapshot at the guest's next field-load boundary (outside only
the reserved coop cells 2032–2041, which no stock choice touches). So **if the guest picks differently, the
host's Global result reaches the guest anyway** — the save state converges.

That shrinks F3's *required* scope dramatically. Sort the 1402 branch sites by what a free guest pick actually
costs:

- **Cosmetically free today (story mirrors / follows / local): 1042 sites (74%)** =
  DIV_GLOB 726 + GLOB_only 90 + INERT 197 + ITEM_MENU 13, **plus** the 236 warp-arm sites are host-
  authoritative via **follow-warp** (a guest who picks a different destination is yanked to the host's field —
  a mirror boundary — regardless). For these, forcing the guest's index buys **only** the elimination of a
  *transient, per-visit* visual mismatch (the guest briefly seeing a different branch play out) that already
  self-heals at the next field load. Item-grant arms are additionally erased by the session exit ramp
  (`../interactions-census.md §3`).
- **The genuine F3 target: 376 DIV_ONLY sites (26.8%) + the 324 transient STORE captures** — the pick drives
  **only** MAP/Instance state with **no GLOB backstop in the arm**. Here a differing guest pick produces a
  per-visit divergence the mirror will not reconcile (it self-limits on field exit, since MAP/INST reset on
  field reload, but it is visible for the whole visit). This is the *only* class where forcing the index
  changes the durable-within-visit outcome rather than just tidying a transient flicker.
- **Field-level scoping:** of the 392 fields with choices, **176 (45%) have EVERY choice story-safe** — a
  following guest can pick freely on nearly half of all choice fields with zero lasting effect. The other
  **216 fields** hold ≥1 purely-transient choice — the concrete F3 special-handling set (versus special-
  casing all 392, or all 818).

**Concrete F3 recommendation from the CHOICES data:** F3's "force the host's chosen index" only needs to fire
where a divergent guest pick isn't already covered by (a) the GLOB mirror or (b) follow-warp — i.e. the
**376 DIV_ONLY sites across 216 fields**, and their **324 Instance/Map STORE captures**. Everywhere else,
mirroring the confirm/pace (L2) already forces the same branch, and the *choice-only* variant `../dialogue-
sync.md §3` floats — forward just the final `selectChoice` when a choice window closes — is sufficient
because the durable half of the outcome is a Global write the guest was going to receive from the host anyway.
The single cleanest interception point remains `ETb.GetChoose()` / `DialogManager.SelectChoice`: overwrite it
with the host's index at the moment the guest's copy of the same window closes (the `(fldMapNo, winnum,
textId)` alignment key from `../dialogue-sync.md §1e`), and every one of the three consumption modes (switch,
if, store) reads the forced value with no per-idiom special-casing.

**Caveats (stated, not hidden):**
- "Story never permanently divergent" rests on the ApplyStory mirror overwriting all of `gEventGlobal` —
  verified in `../dialogue-sync.md §2` / `../interactions-census.md §3`, not re-derived here.
- The if-chain **site** count (759) is approximate (the `.eb` carries no window boundary; grouping restarts on
  a re-seen row-0 handler). The **read** count (2134) and the **switch** site/row counts (643, exact one-arm-
  per-row) are not approximate. F3 scope keys off reads and DIV_ONLY sites, both robust.
- Arm write-scope is delimited from jump/switch targets; a DIV_GLOB/DIV_ONLY label reflects *any* transient
  write in the arm, some of which is throwaway scratch (e.g. the `Instance.Byte[9]` pick copy) rather than
  semantically meaningful state — so DIV_ONLY (376) is an **upper bound** on visually-divergent sites, not a
  lower bound. It is the safe direction for scoping.
- The cancel index and exact per-menu row text live in the `.mes` (text-tag half); the engine default
  (cancel = last row) is cited from source, not corpus-counted.
