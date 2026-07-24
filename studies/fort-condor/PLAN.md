# Fort Condor in FF9 — a real-time lane-defense minigame (study)

**Goal:** emulate FFVII's Fort Condor minigame (real-time lane defense: place units for gil,
enemy waves advance, units auto-engage, a breach falls back to a real boss battle) as an FF9
field minigame built with ff9mapkit. Learn-first mandate: every mechanic gets grounded in
stock bytes before synthesis (the house method; see CLAUDE.md §6).

**The stock donor:** the **Festival of the Hunt** — FF9's own real-time, multi-actor, timed,
scored minigame (Lindblum fields 550–576, scenario band 3160–3180). Decoded in rung 0.
Secondary prior art: Chocobo Hot & Cold (timer/prize lane, `[chocobo]`), the co-op plate
gates (per-frame looping code entries), moving platforms (lockstep choreography).

## Rung ladder

- **Rung 0 — DONE (2026-07-24): the Hunt decode + the actor-budget census.**
  → `RUNG0.md`. Headline: the Hunt already ships ~90% of the RTS vocabulary in stock
  opcodes (chase loop, engagement radius, contact→battle, score economy, wave bands,
  generic countdown HUD); engine ceilings are ~250 objects / 255 entries (way above need);
  the binding risk is O(n²) collision perf with many MOVERS, unproven past stock's ~23.
- **Rung 1 — THE SWARM BENCH: BUILT + DEPLOYED (2026-07-24), ⚠ playtest pending.**
  `swarm_bench.py` (gen/deploy) → field **30400** ("SWARM", FF9CustomMap), a native fork
  of the Festival square (576) carrying **40 kit `[[npc]]` Mu chasers** whose Loop bodies
  are replaced post-deploy with the stock chase idiom (byte-verified vs field 552:
  `SetObjectFlags(7)` + `SetPathing(1)` + per-frame `Walk(obj(250).x, obj(250).z)`), a
  declarative `[[choice]]` tier lever at spawn (GLOB 8800-8803 → arm 10/20/30/40), a
  Main_Init flag-clear (=> ~ Reload resets the bench) + the generic-timer probe
  (`ChangeTimerTime(600)/ShowTimer(1)/RunTimer(1)` — the Hunt's start triplet on a custom
  id). Every chaser also evaluates a `B_PTR(250) B_DISTANCEA` poll per frame, OR-1'd
  truthy — poll cost rides ALL tiers constantly, so tier deltas isolate pure MOVER cost.
  En route: the carried 576 dressing includes 5 stock Mu-model objects (chaser detection
  keys on model + the kit standby-loop signature, never model alone). NEEDS: relaunch →
  ~ → Warp → 30400. Measure: clock visible? frame feel at each tier? chasers converge on
  the player? Revert: `tools/scroll_out/revert_deploy_30400.py`.
- **Rung 2 — TWO-LANE SKIRMISH.** One attacker marches a lane, one defender intercepts
  (chase loop, engagement radius); combat resolved script-side (HP in flags, swing anims,
  death + `TerminateEntry`) — no player battles. Proves the auto-battler core loop.
- **Rung 3 — PLACEMENT + ECONOMY.** Walk-and-place: confirm at a spot → unit-type choice
  menu (dialogue choices) → gil spend → runtime `InitObject` from a pre-authored pool
  (Ice Cavern 303 is the stock runtime-spawn precedent; entries are fixed at build → pool
  + recycle).
- **Rung 4 — WAVES + WIN/LOSS.** Timer-band wave scheduling (the Hunt's
  `GetTimerTime > 600/540/480/…` table shape), a base-HP flag, the faithful Fort Condor
  loss fallback: breach → real `Battle()` boss (the Zaghnol pattern at field 559).
- **Rung 5 — THE FORT CONDOR FIT.** Unit roster/costs/waves tuned to the FFVII design
  (owner ratifies which mechanics are essential: unit types, max 20 allies, gil costs,
  fixed artillery, win rewards). Models from the Info Hub catalog.
- Productization (`[minigame]`-style TOML lane) is deliberately deferred until rung 2
  proves the core loop.

## Standing constraints

- Pure-`.eb` is the target: it keeps the minigame playable on stock Memoria (novel fields
  need no engine patches). Engine s-patch is the escape hatch ONLY if script-side polling
  can't hold the frame budget or a persistent funds/score HUD is demanded (stock precedent
  is popup announcements + the generic timer HUD, both `.eb`-reachable).
- Contact (`_Range` tag-2) events are PLAYER-driven collision; unit-vs-unit engagement is
  `DistanceWithEntry` polling (verify in rung 1).
- One change per in-game test; the human owns feel verdicts.
