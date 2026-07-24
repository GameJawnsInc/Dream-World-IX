# Window-lifecycle census — findings (2026-07-23)

> The advance-mechanisms lane of the 3-lane F3 dialogue census. All 818 real field `.eb`
> scripts decoded on raw opcodes (kit eb model, live from the install; 0 skipped). Scripts:
> `census_windows.py` (opcode pass), `census_text.py` (textId→.mes tag resolution),
> `census_concurrency.py` (cross-thread). Regenerate the per-site dumps
> (`window_sites*.json`, untracked — 4-6MB) by re-running them.

## Headline

FF9 opens **28,678 dialogue windows** (MES/MESN/MESA/MESAN) across 816 of 818 fields
(median 23/field, max 311). The advance mechanism decomposes on TWO independent axes:

- **The opcode** — does the script thread block: 59.4% SYNC (MES/MESA set `wait=254` inline)
  vs 40.6% ASYNC (MESN/MESAN return; 7,018 of those are then blocked by a `WAITMES` on the
  same winnum).
- **The window's own close lives in the `.mes` TEXT, not the opcode**: `[TIME=N>0]` = timed
  auto-close, button-inhibited (2.7%); `[TIME=-1]` = script-closed (9.8%); `[CHOO]` = choice
  (4.9%); no `[TIME]` tag = player-confirm (82.7%). **`[IMME]`/`[FEED]` are print/layout
  tags, NOT auto-advance** — a common misread, now settled: [IMME] appears on 11,841 windows
  and means instant print only.

**The F3 budget: 82.7% (23,713 windows) are confirm/choice-gated on a blocking thread and
MUST be lockstepped; ~17% self-syncs for free** (timed/script-paced).

## The alignment key — verified, with one caveat

`(fldMapNo, winnum, textId)`:
- **Unique among concurrently-LIVE windows** — `ETb.NewMesWin` (ETb.cs:91-96) force-disposes
  any window already on the winnum before opening; `CheckDialogShowing` keys on winnum alone.
- **Always statically resolvable**: 0 expression-winnum sites, 0 expression-textId sites;
  winnum ∈ {0..7} exactly (hist: 0:8439, 1:4430, 2:2242, 3:1502, 4:933, 5:2548, 6:4305, 7:4279).
- **NOT a globally-unique instance id**: 14.2% of sites (4,078) are exact-duplicate
  (winnum,textId) reopens within one function; 2,082 of 6,336 window-opening functions reopen
  a triple more than once. → the mirror must lean on FIFO order + peek-until-match (as the
  ratified design already specifies), never treat the triple as an instance id.

## Multi-page and concurrency

- Pagination is **separate windows**, not `[PAGE]`-in-one-textId (5,389 same-winnum reopen
  runs, up to 71 windows long, vs only 37 `[PAGE]` tags — 99.3% separate-window). So the
  confirm-mirror frame rate = the LINE rate (dozens per cutscene). 8-byte frames make this
  a non-issue.
- **571 fields open the same winnum from >1 entry** (1,175 (field,winnum) pairs — the
  destructive-replace hazard); 150 fields run a winATE window concurrently with a plain
  window; 156 fields statically hold ≥2 live windows in one function (max 5). A blanket
  "one live window" assumption is false for ~19% of fields — the mirror must be
  winnum-scoped (the design already is).
- **127 orphan WAITMES** (1.8%): a wait on a winnum opened by a DIFFERENT entry (director
  opens, helper waits). L2's suppression treats opener+waiter as one logical unit for free
  (it keys on the window, not the opener).

## Outliers to document

~7 engine-hardcoded **language-conditional** window overrides (ETb.IsSkipped fields
1652/1659/2209; DoEventCode MES 1060 Cleyra lang-remap / 1757 / 2172 JP forces
SelectChoice=15; WAITMES 1650 JP skips the wait; NewMesWin 1657/1850). A cross-language
pair diverges on these fields → **require same-language sessions** (document; do not
special-case seven fields).

## Numbers table (definitions in the lane report)

| measure | value |
|---|---|
| window opens (MES/MESN/MESA/MESAN) | 28,678 |
| SYNC blocking / ASYNC | 17,033 (59.4%) / 11,645 (40.6%) |
| CONFIRM / TIME=-1 / CHOICE / TIMED | 23,706 (82.7%) / 2,803 (9.8%) / 1,407 (4.9%) / 762 (2.7%) |
| must-lockstep | 23,713 (82.7%) |
| free (timed + script-paced) | ~4,965 (17.3%) |
| expression winnum / textId sites | 0 / 0 |
| exact-duplicate triple reopens | 4,078 sites (14.2%) |
| same-winnum-across-entries fields | 571 |
| orphan WAITMES | 127 (1.8%) |
| ATE-captioned windows | 1,001 |
| tag placement | tag1 director 11,410 · tag3 talk 6,579 · tag0 init 1,700 · tag2 tread 1,356 |
