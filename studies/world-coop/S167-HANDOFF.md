# s167 round B (the guest's free walk): handoff

**Status 2026-11-06: s167 DEPLOYED as `12be3220520813a6` (revert to s166 = `20261106-031939`) and BENCHED: OLD on s166 12/12 calibrated, NEW every leg green (only S167-WR-GATE, the owner's s167 ROAM tape), LEVER 14/14 calibrated after two kit fixes; the REGRESSION set green, 38 launches (only S166-RM-GATE, the owner's s166 ROAM tape, red on the instrument as in s166's own round).** The design is round B of
`S166-DESIGN.md` (decisions 13-25) plus decisions 27-28 (the owner, 2026-11-05: Select closes a frozen guest's minimap;
the s165 hint stays quiet for the rest of the visit after a Select close). The live DLL is still s166 `b24e0123ac93960c`.

## Where it stands

| Piece | What | State |
|---|---|---|
| Clone | `C:\gd\FFIX\Memoria` | TAKEN for s167 in the round queue (2026-11-05), verified s158..s166 (diag 60/60) before any edit |
| W1 | recon, B-core, the walk wiring (B1-B3, the re-arm), the fingerprint / TPS / caps (B4, B5, W3A-T4, W3C-1, W3C-4), decisions 27-28 + decision 23 (B6) + B7's engine half, an adversarial review | **built, reviewed, NOT deployed**: 96 hunks over 15 files, every hunk tagged `[ff9mapkit netsync s167]`; `--no-deploy` clean; offline proof `world walk selftest: OK (532 rows, 196 mutants)` (s166: 323 / 110); the review fixed R1 (major: the full-map close before an s145 boot never ran) and R2 (minor: `walk off` still gathered the facts) |
| W2 | the kit core (stand-in twins, coop_peer section 11 + digest, the stage pins), the round-B solo / T2 / duo legs, the regression re-keys, runners `s167/round_b_*.sh`, the kit texts (B7), a critic, the reconcile | **done, green offline** (`675244b2`; `s167/s167-w2-wf.js`): the stand-in models every round-B rule with its faults; coop_peer carries caps 3, the digest and section 11; the legs (solo free/refuse/stale/entry/decline/tps/minimap/map, T2 walk/stallhole/hostb, the 13-row duo b) each with OLD / NEW / LEVER; every frozen-guest regression leg pulls the s166 lever set (`walk off`, `refuse silent`, `stallhold old`, `decline old`, `fp off`, `minimap old`, `fullmap old`) on an s167 build; runners `s167/round_b_*.sh`; the kit texts; final offline pass 4396 passed, 6 timing reds green alone. W2's reports: `w2_result.json` + `w2_digest.md` in the scratchpad |
| Bench | OLD on s166 (before the build), the build, NEW in the design's Order, LEVER, the regression set | **OLD 12/12** calibrated on s166 (`20261106-030431-old`); **built + deployed `12be3220520813a6`** (backup `20261106-031939`); **NEW every leg green** (`-032012-new`: the walk 6.1 u on 9011 and 9002, the duo 25/25 -- the guest walked 26 u, its ghost on the host matched by seq 64/64, the rejoin pulled it from 538 u, a host battle booted it and returned it at its own pose; the refusal's readers confirmed in game: the location 1 / place 4, the kit cell 0, the boat 15 / 169, the ferryman 16 / 100; the minimap close and the quiet hint; the full map for a walker on 9010/9011; the fingerprint 2.4 ms + 30.7 ms per world load over 626 reads / 13.1 MB; only S167-WR-GATE red, the owner's tape); **LEVER 14/14** (`-033511-lever` 12/14, the two misses the kit's, fixed in `204455d6` and re-run green in `-040258-rerun`); **REGRESSION green** (`-040938-regress`, 38 launches, every frozen-guest leg under the s166 lever set: round A's 14 legs, s165 follow 5, s144 wait 4, s145 battle 5 + the party duo, the s131-s143 tapes 4, dress 2, climb peer, host code, ramp title; only S166-RM-GATE red, the owner-gated s166 tape on the synthetic instrument -- the same red s166's own round carried) |
| W3 | the whole-diff review, the s167 patch emit, the README row, the laptop package, `TWO-PC-CHECKS-S167.md` | pending |

**Files the s167 delta touches** (all CRLF but HarnessAgent.cs, LF; no new file): NetSyncWorldWalk.cs (+2352), NetSyncClient.cs
(+1130), NetSyncField.cs (+359), HarnessAgent.cs (+286), NetSyncWorldDot.cs (+210), WorldHUD.cs (+53), WorldMeshOverride.cs (+18),
NetSyncSocket.cs, Ff9mkDebugMenu.cs, NetSyncState.cs, ff9.cs, CustomFormCells.cs, WMScriptDirector.cs, SceneDirector.cs,
NetSyncRelay.cs. `WorldMeshOverride.cs` and `CustomFormCells.cs` are new to the patch stack's file set: the fingerprint's c2
records the engine's own world-mesh override reads (the patch emit and `tools/memoria_stack_replay.py` DEFAULT_FILES must carry
them).

**Working files** (this session's scratchpad, `C:\Users\skaki\AppData\Local\Temp\claude\9e463cf4f0985362\110b1b95-e2da-4a85-ab88-e0d8756cb21a\scratchpad\`):
`s166base` (the clone before s167; `s167/s167diff.py` diffs against it), `s167w1snap` (the 15 changed files at W1's end),
`w1_result.json` + `w1_digest.md` (W1's reports: every contract, deviation and open item), `s167proof` (the offline proof exe).

## What W1 decided that the design did not say (worth the owner's eye at the two-PC look)

- **A visit** (decision 20's one definition): a world load after a field or the title starts a new visit; a warm battle
  return and the ~ menu's world-to-world reload do not. Decision 28's quiet hint and the DeclineOnce re-arm both key on it,
  so the hint stays quiet after a battle and comes back after the guest's next location.
- **The fingerprint** has six components: the language; the world script actually loaded; every world-map override file the
  engine read (CRC over the bytes); the vehicles table; the environment patches; the weather table. A mismatch names the
  component on both machines. Its cost is logged at every world load (CLR measured about 25 ms; Unity's runtime unmeasured).
- **The entrance line** lasts 4 s; **"checking"** gives up with one line after 10 s. Both are seeds.
- **The full map's co-op close** also runs before the session's exit ramp, and only for a frozen guest before a rejoin or a
  battle; a released guest keeps its map and sees "Close the map to join your partner.".
- **Still s144's**: in a link stall, SpectatorField gates beyond decision 17's three (the script and party menus, NPC talk)
  lift for a world-paired guest, and a ~ menu release ends in a stall.

## Next

1. W2's open items (in `w2_digest.md`): K1's census inferences (reader ids 0/1/15/16, place codes 52/62/69/100/169, the lock bytes Map[33]/[35], the kit/boat reader order) are confirmed only by the in-game rows; unreachable by any harness verb: the refusal rows' positive controls (the ~ Release), the released guest's close-map line, the hint's display; D-BATTLE runs only in game; W-STALLHOLE's place-52 clause needs a quicksand world (9003/9009).
2. **OLD on s166** (the live DLL, before any s167 build): `bash studies/world-coop/s167/round_b_old.sh`.
3. Build s167 (`py tools/build_memoria.py`, FF9 closed; it backs up s166 first), then `round_b_new.sh`, `round_b_lever.sh`,
   `round_b_regress.sh`.
4. **The ROAM tape** (T2-B): it must be recorded on the s167 build (a walking guest needs the host's caps b1 and a matching
   fingerprint), with the owner's bridge down and the owner's go (`s166-handoff/ROAM-TAPE.md`).
5. W3: the review, the patch, the package, the two-PC checklist; merge; the owner's two-PC session.
