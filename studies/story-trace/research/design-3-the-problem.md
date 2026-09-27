## 1. THE PROBLEM
- **The blind spot** (PLAN.md:57-59): naive same-function byte-adjacency gives an SC window to only 32.6% of 12322 bit-write sites. Rung 0 predicted dominance analysis would lift that past 55% (PLAN.md:90).
- **Falsified** (PLAN.md:139-146): 77% of the raw 12268 sites were dispatch noise (the byte-23 handshake plus the Mognet bands). On the 2832 real story sites, coverage was 18.3% direct, 29.4% with armed context, and 36.2% adding E3. 257 of 974 story bits got hard windows (255 after the fixes, :174-175). The reason: about 90% of story sites sit outside Main_Init, and 32% are once-flag gated and triggered by interaction, not by the beat.
- **E1–E5** (PLAN.md:95): E1 equality gate, E2 window gate, E3 SC advance in the same function, E4 the writer field's SC envelope, E5 milestone fallback. storyseed.py:10-12 uses different meanings (E1/E2 = a proven window, direct then armed). The re-plan made E1–E3 the precision core and gave the long tail to E4 and E5 (PLAN.md:147-152).
- **Proven**: rung 1 (:176-181), rung 2 (:182-186), and the hub lane (PLAYTEST.md:251-260: the Dali 2600 morning played through into real field 404).
- **Open**: the decision gate shelved rungs 3–6 (PLAN.md:187-191). The interval solver and calibration harness this trace would feed do not exist. Discs 3–4 have no ground truth (:74-75).
- **PLAN.md never mentions a trace** (no hits for trace, dynamic or runtime). The nearest lines are :162-164 ("opcode side effects and cross-script interleaving are unmodeled") and :144-146.
- **Best motivating case** (PLAYTEST.md:166-180): Dali's real ATE machine was found by hand-reading the decompiled `.ebs` source. Bit 2102 is written only by field 450, which was missing from the chain. A stock-vs-chain diff would have named that writer directly.
- **The board is out of date**: BOARD.md:34 still pitches "past ~55%" as open, but PLAN.md:139-146 already falsified it.

## 2. THE WORKLIST
Items in FORK_FIDELITY.md that are currently asserted by hand:
1. **:197-200** Story-writes axis: a static list of candidates, and "The author still *asserts* the beat" (forkreport.py:214-226).
2. **:283-287** "assert the beat with `[startup] scenario=N`."
3. **:128-130** The Dali Inn door stays closed at scenario zero because it reads 2064/2073/2078. PLAYTEST.md:173-175 later showed 2073/2078 are XOR latches the controller flips *during* the morning.
4. **:60-65** with forkreport.py:199-200: a synth fork DROPS the donor's writes, and exits don't advance the SC. A per-function diff would list exactly the dropped writers.
5. **:436-439** Dynamic walkmesh hotfixes keyed on story-var state are "flagged… rather than auto-applied."

Out of reach: :311 ATE seen-state (it lives in `AchievementState`, flags.py:429-433) and party state (PLAN.md:15-16). Neither is in `gEventGlobal`.

## 3. MASKS
Regions from `BIT_REGIONS` (flags.py:236-320), given as bits (bytes):
- **MASK** (rewritten mechanically):
  - field_menu_guard 184 and boot_scratch 191 (byte 23, :269-272)
  - readmail_payload 8512-8711 (bytes 1064-1088, :302-308)
  - qte_scratch 16144-16255 (:309-313)
  - netsync_coop_cells 16256-16319 (bytes 2032-2039, :314-317). These are written by C# every frame, so a `.eb` write hook never sees them; a memcmp would.
  - choice_scratch 16320-16335 (:318-319)
  - behavior blackboard: flags 14864-14959 and bytes 1876-1989 (:244-262)
- **Separate channel** (letter state driven by player choice): mognet_mailbox 8192-8367 (bytes 1024-1045) and the Mognet lock bands 8376-8511 (:281-301).
- **KEEP**:
  - worldmap_unlocks 736-823 (:273-280). This region is `reserved=True` but it is real progression (forkreport.py:203). **Mask by region name, never by the `reserved` flag.**
  - Label the kit bands 14664-15007 and 16048-16143 as "kit", and tag the treasure-hunter ranges (:436).
  - ScenarioCounter (bytes 0-1) becomes the epoch column; FieldEntrance (bytes 2-3) is context.
  - `FIRST_SAFE_FLAG` = 8712 (:53).
- **Region masks are not enough.** Field 552's Main_Init writes `Global.Int16[9]=1582` and `Int16[239]=552` on every entry, with no guard, and neither is registered. The trace also needs an "unguarded every-entry Main_Init write" filter.
- **Three masks disagree today**: dominance_census.py:215-217 masks 184-191 + 8192-8711; forkreport.py:205-211 masks 184-191 + 8376-8511; storyseed.py:30 masks 184-191 only. Byte 1046 (bits 8368-8375) belongs to no region.
- **BUG**: storyseed.py:175 and build.py:5919 call `named_word_at(bit // 8)`, but that function takes a bit (flags.py:488-497; test_flags.py:37-42). As a result:
  - bits 1520-1535 (MoveControl/ChocoDigLevel) and 1816-1823 (MagicDisabledFlag) get past the "non-negotiable" refusal;
  - bits 32-127 are refused when they shouldn't be.

## 4. MAPPING A WRITE BACK TO SOURCE
- **Census key**: field (the real id), entry, func (a TAG), and `off` (the absolute file offset of the 0x05 opcode) (dominance_census.py:177; cfg.py:797).
- **Engine side**:
  - `sid` is the entry index. `allObjsEBData[sid]` is the file bytes from 0x80+ofs (EventEngine.cs:607-613), which is the kit's `Entry.abs_start` (model.py:92,143).
  - `ip` is relative to the entry (`GetIP` returns 2+fpos, EventEngine.cs:1103-1121).
  - SET runs through EBin.next → jumpToCommand case 5 → `expr()` (EBin.cs:195-205, 1477), not DoEventCode. So `_lastIP` (DoEventCode.cs:34) misses it; the hook must capture `s1.ip-1` when `expr()` is entered.
  - The tag can be recovered offline from the offset (model.py:75-76).
- **So the join is direct, with caveats:**
  - (a) Key on (donor, entry, tag, offset within the function). The `[startup]` prepend (build.py:5892) shifts Main_Init offsets. The `Field()` retarget (content/verbatim.py `pack_into` at `i.off+2`) keeps offsets. Hub members carry no seed stamp, so their offsets match the donor's.
  - (b) The census is built from US-language bytes (dominance_census.py:3); JP differs in 71% of fields (PLAN.md:100).
  - (c) A fork runs at a 30xxx id, so the row needs `EffectiveFieldId`.
  - (d) Some writes have no census row: 0xD3 computed-index writes (the census keeps only literal-index assigns, :157-195), C# writers, and addition-command buffers (Obj.cs:566-573).
- **Naming**:
  - Function names come from `logic_map.kind_label`/`entry_label` (logic_map.py:211-222).
  - `ebsrc` prints no offsets. Use `cmdasm.disassemble_items` (cmdasm.py:283), which gives (rel_off, text) per source line; ebsrc.py:418 joins on it the same way.
  - `FieldFlow.guards_at` (cfg.py:917) attaches each hit's static guards.
- ⚠ **The board's memcmp design will not give per-function results.** Its rows (BOARD.md:35) are (frame, byte, new, EffectiveFieldId, ScenarioCounter), with no entry or offset. It also misses writes of the same value and a set-then-clear inside one frame. The per-function diff needs a write-site hook; memcmp can serve as a cross-check and to catch C# writers.

## 5. THE CALIBRATION
- **The case**: a verbatim fork of Lindblum 552 with scenario 3115 and byte 236 = 0x0F (four menu rows) boots the real Small-Town Knight ATE (ATE_SYSTEM.md:340-345, 362-364, slot 30006). `story-seed` re-derived it at slot 30823, and the owner confirmed it (PLAYTEST.md:85-92).
- **The proof was visual.** Nobody recorded the write order, so the falsifier's baseline "write order reproduces" can only be the static order below.
- **Static expected order** (field 552, entry 0, tag 0, from `eb-src`):
  1. the seed stamp: bytes 0-1 = 3115, bytes 236-237 = 0x000F
  2. 191 and 184 (masked)
  3. `Int16[9]` = 1582
  4. `Int16[239]` = 552
  5. `SByte[238]` = 1
  6. `Int16[241]` = `UInt16[236]`
  7. `UInt16[251]` |= `UInt16[236]`

  Map bits 152/153/155 are not in `gEventGlobal`. ATE_SYSTEM.md:338 does not mention 239, 241 or 251.
- **Save corpus** (PLAN.md:70-82): 19 saves.
  - SC 2540–3110: 5 points.
  - SC 6000: 1 save, in the encrypted container only.
  - SC 7200: 6 saves, some carrying co-op cell values.

  Beat 3115 sits just above the band's top (3110); Dali 2600 is inside it.
- **No intervals exist yet.** Rung 4 (order intervals) and rung 5 (`story-model --diff-save`) were shelved and never built; searching for them found nothing. `story-seed` gives only a one-sided `lo` (storyseed.py:100,116-126).
- **So the falsifier's baseline has to be built first**: for each bit, the bracket [last save SC with the bit clear, first save SC with it set]. Stock-side trace runs should start from corpus saves, because a run booted from a derived seed cannot check the derivation independently.

Scratch decompile of field 552: `<archive>\scratchpad\f552.ebs`