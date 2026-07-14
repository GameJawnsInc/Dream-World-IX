# Co-op pillar — HANDOFF (2026-07-13)

> For whoever picks up the FF9 co-op multiplayer pillar next. Read this first, then
> [`README.md`](README.md) (§ "THE AUTHORITATIVE-HOST ROADMAP") and
> [`state-mirror-lane.md`](state-mirror-lane.md) (the build spec). The durable narrative lives in the
> project memory `project-ff9-multiplayer-injector.md`.

## TL;DR — where the pillar is

The co-op pillar's **north star is now the AUTHORITATIVE-HOST paradigm — "play the standard game
together"**: ONE real playthrough (the host's); the guest is a second player inside it (a following
presence on the field, controller-2 in battle). The unifying principle: the guest's client is a **puppet
that mirrors the host's authoritative game**. The federated `[[coop]]` puzzle vocabulary is demoted to a
future "custom game modes" track.

Just landed this session:
- **★ TWO-MACHINE PROVEN**: follow-warp, V2 `[[coop]]` gates (the Twin Altar), and battle co-op B0+B1 — all
  with two real players over the relay.
- **IMPLEMENTED (written + adversarially reviewed, NOT yet built)**: the **state-mirror lane** (the
  foundation of the whole paradigm — host→guest gEventGlobal sync so a following guest renders the host's
  world), the **empty-command battle-menu fix**, and **`coop host` → `FollowHost=0`**.

**The one remaining action is a single DANGEROUS engine rebuild** (deferred — the user put the test laptop
away). Everything before that step is done, committed, and green.

---

## ⚠ CRITICAL — the engine code is NOT in the repo

The state-mirror lane + the two fixes are **C# edits in the LOCAL, GITIGNORED Memoria build tree**, not the
Dream-World-IX repo:

- Tree root: `C:\gd\FFIX\Memoria\Assembly-CSharp\` (shared across worktrees, gitignored, its own git).
- **New file**: `Memoria\Netsync\NetSyncState.cs`
- **Modified**: `Memoria\Netsync\NetSyncClient.cs`, `NetSyncSocket.cs`, `NetSyncRelay.cs` ·
  `Global\Honolulu\HonoluluFieldMain.cs` · `Global\SaveLoadUI.cs` ·
  `Global\battle\BattleHUD\BattleHUD.Unity.cs` · `Assembly-CSharp.csproj`
- These are **uncommitted in the Memoria tree** and **the s37 patch (`memoria-patches/s37-netsync-battle.patch`)
  has NOT been regenerated to include them.**

**Implication:** if you are on THIS machine, the changes are right there — just rebuild. If you are on a
**different machine**, you do NOT have them until either (a) you copy this machine's Memoria tree, or (b)
someone regenerates the s37 patch and commits it (then you `git apply` it onto a clean Memoria tree at
`memoria-patches/BASE_COMMIT`). **Regenerating the patch is the clean cross-machine handoff — do it before
building on a second machine.** The patch-emit recipe (baseline reconstruction for files that carry
pre-s37 edits like `BattleHUD.Unity.cs`/`SaveLoadUI.cs`/csproj, CRLF care, reverse-apply-check gate) is in
`project-ff9-memoria-build.md` + the `building-the-memoria-engine` skill; prior rounds used a
`scratchpad make_s37_patch.py`.

---

## Repo state (branch)

- Branch **`claude/battle-coop-feasibility-e6fb2e`**, **up to date with `master`** (merged 2026-07-13; 0
  behind / your merge + 4 coop commits ahead). **Full suite green: 3438 passed, 2 skipped.**
- Repo-side changes this session: `ff9mapkit/ff9mapkit/coop.py` (FollowHost=0), and the study docs
  (`studies/battle-coop/README.md`, `state-mirror-lane.md`, this file).
- The coop test fields live on THIS machine's install: **30003** (hangout), **30110** (Twin Altar), **30111**
  (twin vault) in `FF9CustomMap`. The laptop update package is at `Desktop\FF9Coop-laptop-update-20260713\`.

## Read-first

1. [`README.md`](README.md) § "THE AUTHORITATIVE-HOST ROADMAP" — the north star, the flags→party→diorama
   ladder, the **honest cutscene ceiling** (shared world+battle, NOT a shared cutscene timeline), the MVP.
2. [`state-mirror-lane.md`](state-mirror-lane.md) — the full build spec that was implemented (wire format,
   apply hook, spectator-save, fail-safe, acceptance tests, § 12 build discipline).
3. Memory: `project-ff9-multiplayer-injector.md` (durable narrative), `project-ff9-memoria-build.md` (the
   DANGEROUS rebuild recipe), `project-ff9-story-flags.md` (gEventGlobal).

---

## NEXT STEP 1 — the rebuild (DANGEROUS; do when a test session is possible)

Per `state-mirror-lane.md` § 12 and the `building-the-memoria-engine` skill:
1. **Close FF9** (the DLL is file-locked while running).
2. **Back up** `Assembly-CSharp.dll` x64 AND x86 → `backups/<file>.<timestamp>` (e.g. `.preSTATEMIRROR.*`).
   The engine build AUTO-DEPLOYS with no backup — this is the only safety net.
3. Build via the standard MSBuild recipe (`/p:SolutionDir=C:\gd\FFIX\Memoria\`).
4. **First proof is SOLO** — launch, `ff9mapkit coop host` (selftest is fine), enter any field, and check
   the log for: `[NetSync] state-mirror selftest: gEventGlobal codec round-trip OK`. Also retest the
   **empty-command fix** (a character with an all-unlearned Ability command — e.g. Steiner's Swd Art with
   nothing learned — should NOT appear in the guest menu / reach a target prompt).
5. Regenerate `memoria-patches/s37-netsync-battle.patch` (reverse-apply-check CLEAN) and commit — `SaveLoadUI.cs`
   and `BattleHUD.Unity.cs` are NEWLY in the s37 change set this round.
6. Re-cut the laptop package with the new DLLs (wire v5→**v6**: old peers won't sync — update BOTH machines).

## NEXT STEP 2 — two-machine validation (backlog; needs the laptop out)

The state-mirror acceptance tests (`state-mirror-lane.md` § 11):
- **Render-match**: host warps to a field with a ScenarioCounter/flag-gated NPC or door; the following guest
  sees the SAME state (not its own scenario-zero). This is the headline proof of the paradigm.
- **Save-safety**: after a session the guest's OWN save is unchanged (spectator-save restored); a mid-field
  link-drop reverts the guest cleanly; a save attempt while following is refused (deny beep).
- **Fail-safe**: a v5 (old-DLL) peer + a v6 host simply don't sync — no half-state, no crash.
- Sequential follow-warp is ALREADY validated (5+ fields, overworld the known exception) — no separate check.

## NEXT STEP 3 — the roadmap forward (only after the lane is two-machine-proven)

1. **Party mirror (rung 2)** — extend the SAME state-mirror lane with a party section (section 1). It's felt
   on the field AND it is the diorama's actor-spawn input (zero throwaway — the lane is section-tagged for
   exactly this).
2. **The battle diorama (B3)** — boot the host's battle on the guest via `BattleMapDebug` (AI/ATB off via the
   `isDebug` suppression), spawn the mirrored party, drive from the existing B0 state stream. NEVER
   re-simulate (unseeded-RNG dead-end). This is "the guest SEES the fight." Highest-risk, isolated, LAST.
3. **Cutscene-drive** — the research frontier that turns "fight together" into "experience the story
   together" (host streams window-close / chosen-choice / tread-fired events; the guest force-applies). The
   "remaster, not a feature" tier — documented, not scheduled.
- **Federated `[[coop]]` custom modes** — parked; resume once the authoritative headline is solid.

---

## Gotchas / laws to carry

- **`[Netsync] TargetField` must be 0** (everywhere mode) for follow to pair off the target field — follow
  gates on `onField` (ignores TargetField), sync gates on `inScope` (`fld==TargetField`). A stale
  `TargetField=30003` silently breaks pairing everywhere but 30003.
- **`coop host` forces `FollowHost=0`** now — a host must never follow its guest (FollowHost fires
  regardless of role). If you see a host getting dragged to the guest's field, that's the cause.
- **The state-mirror is HOST→GUEST one-way**; only `_role=="host"` produces `TypeState`, only a following
  non-host guest applies it. The **spectator-save** blocks the guest saving while mirroring (`SaveLoadUI`
  gates on `NetSyncClient.IsMirroringStory`) so the guest's own save is never overwritten.
- **The honest ceiling**: flag-mirror buys a shared WORLD + (with the diorama) a shared BATTLE — NOT a shared
  cutscene timeline. ~a third of the game "just works" naively; dungeons are the sweet spot.
- **The engine rebuild is DANGEROUS** (auto-deploys, no backup): close FF9, back up both DLLs first.

## Environment quick-ref

- Kit CLI: `py -m ff9mapkit <cmd>` from `ff9mapkit/` (run from the kit root). Tests:
  `FF9MAPKIT_DATA="C:/gd/Dream-World-IX/ff9mapkit/ff9mapkit/data" py -m pytest -n 6`.
- Game install: `C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX\`; `[Netsync]` in
  `Memoria.ini`. Co-op setup: `ff9mapkit coop host|join <code>` (+ `--guest-slots/--ghost-as/--follow-host`).
- Engine build tree: `C:\gd\FFIX\Memoria\` (gitignored, shared). Patch stack: `memoria-patches/`.
