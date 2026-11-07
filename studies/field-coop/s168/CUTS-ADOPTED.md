> The coordinator's verdict on review round 3's simplification proposals (2026-11-06), kept as written. Applied to
> `../S168-DESIGN.md`; see its "Cut in round 3" list.

# The coordinator's verdict on round 3's simplification proposals (binding)

All fourteen proposals in s168_review3.json 'simplification' are ADOPTED, each WITH its verifier's correction. Apply them to
S168-DESIGN.md as a coherent rewrite of the affected decisions, rows, levers, ops, keys and tables, not as patches on top.
Supersede (remove or rewrite) any earlier-round text and any round-3 lifecycle fix (LC-1..LC-10) that a cut makes moot; keep
every LC fix that still applies. Specifics and the coordinator's additions:

1. SIMP-DOOR. The press only pre-checks (audible refusal, or stock OnKeyMenu) and arms nothing. The door (UIManager.ChangeUIState
   FieldHUD/WorldHUD -> MainMenu, guestSession true, lever not `old`) is the ONE open verdict for EVERY such entry; pass = seat,
   and the guest-menu session begins at the seat; fail = buzz, the why's line, GetSceneFromState(this.state).Show(null). Add
   `_worldOutCommittedTo >= 0` to term 10. Remove step 0, the `closing` why, `door_unarmed`, the press-to-door expiry, the
   `move` trigger and its lever/words, GM0-WINDOW. COORDINATOR ADDITION (the verifier's ramp-in-window cost): keep ONE press
   timestamp; the ramp's settle term (both branches) reads "no guest Menu press younger than CloseCapMs" so a ramp cannot fire
   inside the press-to-door fade. COORDINATOR ADDITION (LC-6): a Menu press while UIManager.IsLoading goes to stock OnKeyMenu
   (a silent no-op), never an audible `ui` refusal.
2. SIMP-SWALLOW. Replace THE INPUT SWALLOW with the held-bit write into ETb.sKey (Confirm, Cancel, Special, Menu held now)
   immediately before EVERY route that ends a seat at the HUD (the close's ChangeUIState(HUD), the watchdog's sweep and its HUD
   Show, the tick's fault step). Use the verifier's precedent wording (sKey is externally edited state; the cited sites clear
   bits for the opposite purpose). Name the costs (B_KEY level readers; a held button is a KeyOn after a following load, as in
   stock; a re-press inside the show fade is read as held). GM0-SWALLOW becomes the KeyOn-count row.
3. SIMP-FADE. Every close ends in stock's own fade (root: stock root-Cancel statements with NeedTweenAndHideSubMenu = true set
   BEFORE the Hide; below MainMenu: ItemUI.WaitForFade's form). Remove THE FADE CHOICE, the black hold, the tail's black-hold
   duty and GM0-FADE's black legs; keep a fade row that judges "the follow starts like a follow from a guest on the HUD" and
   the GM0-TIMING measurement. State the visible cost honestly (a brighten-then-darken below MainMenu at FadeDuration 300).
   If THE CLOSE TAIL then has no remaining duty, remove it and put its HUD-Show recovery in the watchdog/tick fault path.
4. SIMP-STRIP. Restore skeleton D3: UIKeyTrigger's dialogue-path read (:889) stays byte for byte. Remove the narrowing, its
   sub-rules, MenuKeyRoute's dialogue verdict, its proof rows and the related HUDSTRIP/CAPS legs; remove that Departure. Known
   limit (with the verifier's corrections): "the guest menu does not open while the location keeps a window up -- a
   persistent kit HUD strip or a transient stock window -- and the press there is s121's silent drop". Keep one measured
   Known-limit row on a kit strip field.
5. SIMP-CONFIG (the greyed form). EnabledSubMenus while seated = {Item, Ability, Equip, Status, Folklore} (+ Journal if it is a
   main-menu row in this build: check) -- Config AND Card greyed like Order and Party. Remove step 4 (key capture, Tutorial),
   the G1/G2 hooks and rows, C1, the Config Known limit, GM0-CFG-RAMP, the Tutorial/key-capture/booster legs. Keep the quit
   wait (QuitUI is still reachable through Alt+F4). Re-key GM0-BROWSE (Config and Card are 102 rows). Note in "The owner's
   calls" as a coordinator scope call the owner may reverse later: the study's screen table listed Config and Card as local.
6. SIMP-RAMP. No hold clock: the world branch's `settled` gains `!(seated && ui.State != WorldHUD)` (and the press-timestamp
   term from item 1 on both branches); safeToLoad, _exitRampSafeSince and the settle clock untouched; ExitRampSettleMaxMs is
   the bound; the fire backstop restores past it. The `close` request at the arm stays.
7. SIMP-LEVERS. One lever `guestmenu close old|act`; per-trigger proof mutants; restate GM0-TITLE's (and any ramp-reaching
   leg's) prediction under THE CAL RULE per the verifier.
8. SIMP-QUIT with its correction: the close waits while QuitScene.isShowQuitUI, the watchdog clock paused; ONE QuitScene.Hide on
   the ramp's fire path before the fire backstop and ExitMirrorToOwnSave; the battle-cut report stays BUSY (not BOOTING) while
   the quit prompt holds the close, so the host's gauges are never held for it.
9. SIMP-RESEAT. s168 seats once per open; s169 re-seats member C only from the frame that answers C's entry (or at the pending
   hold's expiry); reword decision 25 accordingly. Remove the re-seat compare, the scratch-set bookkeeping and the sort
   permutation re-apply (item sort then simply lasts until close, as the owner's "Item sort" decision allows).
10. SIMP-FRAMECAP with its correction: TrailReserve = 424 + 6 (+ section 13's maximum + 3 from s169), recomputed by one proof row
    from HeaderLen, OpenLen, OpenCap, the count byte, RingCap and EventLen; section 13 appended only when 12 was. BuildStateFrame's
    order and the 5+7 one-snapshot rule untouched. Remove `frame big`, `guard off`, GM0-FRAME's S row and mutant.
11. SIMP-STATESWAP with its corrected cost. Remove the `state swap` op and GM0-STATEID.
12. SIMP-SAVEGATES. Keep only the autosave ladder's seat term; drop the other three edits, rows and mutants (name the lost layer).
13. SIMP-BACKSTOP with its correction: the Replace backstop restores and ends the session; Replace('Title') quietly, other
    targets with the alarm; no close request, no dropped-Replace detector, no `backstop` cause.
14. SIMP-CLOSELINE. The forced-close line lives on its own 4 s timer only; a newer close line replaces it. Remove the landing
    tracking and the D7 Departure.

After the cuts: update "Departures from the skeleton" (several entries disappear; add the D8 re-seat cut, the D11 lever cut and
the Config/Card greying as coordinator calls), the engine pieces (files touched shrink), the bench (rows, mutants, CAL), the
keys, the lever/ops list and its release chain, and the Known limits. Every row id, lever, op and key named anywhere must still
exist exactly once.
