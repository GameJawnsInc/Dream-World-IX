"""B4/B5 STAGE 3 -- THE STOCK MENU FIRST LOOK + CAPTURE, the arc's GO/NO-GO (memoria-patch s102), solo, unattended.

THE QUESTION (studies/battle-coop/B4-B5-DESIGN.md 3.2, 4.3, section 7 stage 3, risk 1). B4 replaces the guest's digit
panel with the STOCK battle HUD, but no stock panel except the party panel had ever been seen inside the diorama's
`BattleMapDebug` (its debug branch skips BattleHUDScene.Loading). And a stock commit there would re-simulate the host's
fight on the guest's REAL bag. s102 captures every commit site (SendCommand / SendDoubleCastCommand /
SendAutoAttackCommand forward ONE v1 frame; SendMixCommand refuses) before any write, gates the side paths
(OpenMainMenu, manual Trance, the Vivi swap, CanForceNextTurn), and adds a SELFTEST BENCH OPENER (`netsync bmenu open
<L>`: local slot L onto the stock ReadyQueue through the stock feeder) so the real panels can be looked at.

THE BENCH. Field 30602, `netsync selftest 1`, `netsync dioboot 67 0`; the panels are driven like a player's (press /
cursor labels), read back through `battle.hud` (NetDescribeHud: what the NGUI draws) and photographed with the harness's
in-engine shot. The party: the bench warps through COOPPARTY (30604) when it is registered, so a member with a
learned/equipped Ability-type command is seated (Vivi's Black Magic / Garnet's White Magic) -- else Zidane's Skill
list must serve, and the precondition check says so if it cannot. The ability panel is judged on the seated slot
whose list holds an enabled MP-COSTING ability (slot order breaks ties), so its MP column has a number to draw;
a list of 0-MP abilities only (Zidane's Flee/Detect) is judged too -- the stock list draws a 0-MP cell BLANK
(BattleHUD.cs:845 `mp == 0 ? String.Empty`), so each drawn-on row's cell is held to `menus`' own cost for that ability.

WHAT IS PROVEN (outcomes; the forwarded frame is decoded HERE in Python, independently of the engine's decoder):
  P      the capability (`netsync.battle.menu.captures`; `battle.hud` / `battle.seq` inside the diorama).
  L      THE FIRST LOOK (the GO/NO-GO): the command root opens for the bench slot, then the ability list, the item list
         and the target cursor each COMPOSE (the expected group/panel, labelled rows) and TAKE INPUT (the cursor moves
         onto the asked entry, Confirm/Cancel move between panels). One PNG per panel, each decoded non-blank:
           s3-panel-1-command.png  s3-panel-2-ability.png  s3-panel-3-item.png  s3-panel-4-target.png
         READ them after the run -- the GO/NO-GO is decided on those four pictures plus S3-GO.
  C      an Attack commit is CAPTURED: captures +1, `captured` == the pick (wire slot, action 0, menu 0, id 0, the
         target bit under the cursor, cursor 0, local slot 0, site SendCommand), the hex decodes to exactly that in
         Python, the stock bookkeeping ran (0 in turn.done, the panel closed), and NOTHING EXECUTED LOCALLY (cmd_busy
         bit 0 clear, the target's hp_raw unchanged, r9_refused still 0 -- the capture fired before R9 could).
  I      an Item (Potion) commit is captured as {action 3, id 236, the target under the cursor} and the guest's REAL
         Potion count is unchanged 5 s later (`menus 0`).
  K      SAME-DLL CALIBRATION: `bmenu capture off` -> the same Attack and Item commits run their STOCK bodies into R9:
         captures unchanged, r9_refused +1 each (site BattleHUD.SendCommand, the R9 line), still nothing executed, the
         Potion count still N. Proves the capture fired in C/I AND that R9 stands behind it. (`COOP_STOCK_5B=1` adds
         the throwaway 5b: capture off + `containment 0` -> the Attack REALLY enqueues and the swing plays.)
  X      the side gates: `bmenu mainmenu` is refused (side_refused +1, side_why names AccessMenu / OnKeyMenu,
         main_menu false, still BattleHUD 30 frames later); Change from the root is refused (capture_refused +1,
         'Change is outside the v1 command scope', the menu stays). `can_force_next` reads false: a LEDGER CHECK
         (S3-X2) only when the install's Memoria.ini says [Battle] Speed=2 -- CanForceNextTurn is `Speed == 2 && ...`,
         so on any other speed it reads false with or without the s102 gate and is only NOTED, never counted green.
  T      teardown with a menu open: 'stock menu: closed all (the diorama tore down) -- 1 slot(s) drained, bench-opened
         mask 0x1' then the torn-down line; a REAL `battle 67` afterwards still opens its own command menu (no stale
         button group skipped InitialBattle).
  R      `reset` with the capture lever left OFF restores it ('stock-menu capture back ON (released with the harness)').
NOT PROVEN HERE (two-machine sitting 1): a non-identity wire/local mapping (the bench seats the guest's own party, so
the mapping is identity); the production ready mirror (stage 8).

CALIBRATION.
  * PRE-STAGE DLL (s101): the probe fails closed -- no `menu.captures`, no `battle.hud`/`battle.seq`, and `netsync bmenu`
    answers "netsync: unknown sub-verb 'bmenu' (...|bctl)". P0/P1 RED and every L/C/I/K/X/T/R check RED "not reached"
    with that refusal (the opener does not exist). GREEN there: S0 and PRE (the bag and the party).
  * The DEPLOYED DLL at writing (s99): the same red set (`netsync.battle` absent entirely); T2 is "not reached" (no
    stock window was open at the teardown, so a healthy real battle afterwards would prove nothing).
  * The in-run reds are leg K (and the opt-in 5b) on the stage DLL itself.

    py tools/play.py studies/test-harness/scenarios/coop_stock_menu.py --field 30602
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _coop_battle as cb                                  # noqa: E402 - the shared bench helpers beside this file

HarnessError = cb.HarnessError

RUN_5B = os.environ.get("COOP_STOCK_5B", "").strip() not in ("", "0")
CMD_GROUP, TARGET_GROUP, ABILITY_GROUP, ITEM_GROUP = "Battle.Command", "Battle.Target", "Battle.Ability", "Battle.Item"
OPEN_S = 3.0                             # bmenu open -> the HUD's next ready pass opens the panel
QUIET_S = 3.0                            # after a commit: nothing may execute in this window
POTION_WAIT_S = 5.0
MAIN_MENU_WHY = "the in-battle main menu (AccessMenu / OnKeyMenu)"
CLOSED_ALL = "stock menu: closed all (the diorama tore down) -- 1 slot(s) drained, bench-opened mask 0x1"
TORN = "diorama torn down -- state restored, isDebug cleared; r9_refused="


def _catalog(speed2: bool = False) -> dict:
    c = {
        "S3-S0": "the harness forced the selftest role for this process (Memoria.ini untouched)",
        "S3-P0": "the engine publishes `netsync.battle.menu.captures` (memoria-patch s102, stage 3)",
        "S3-P1": "inside the diorama the battle doc carries `battle.hud` and `battle.seq`",
        "S3-PRE1": "precondition: the guest owns at least 1 Potion (`menus 0` lists item 236 with count N >= 1)",
        "S3-PRE2": "precondition: a seated member has an Ability-type command with at least one enabled ability "
                   "(an MP-costing one preferred)",
        "S3-L1": "`bmenu open 0` opens the COMMAND ROOT for slot 0: turn.slot 0 (0 ready), hud.panel 'command', group "
                 "'Battle.Command', hud.slot 0, labelled commands with Attack drawn on (state 2), bench_open bit 0, the "
                 "'bench opener -- local slot 0' line",
        "S3-L2": "the ABILITY list composes and takes input: the cursor walks onto the Ability-type command, Confirm "
                 "opens hud.panel 'ability' with labelled rows (>= 1 drawn on) whose MP column agrees with `menus` "
                 "(a number for an MP cost, BLANK for a 0-MP ability), Cancel returns to the root",
        "S3-L3": "the ITEM list composes and takes input: Confirm on Item opens hud.panel 'item' whose rows carry id 236 "
                 "with the bag's count N, Cancel returns to the root",
        "S3-L4": "the TARGET cursor composes and takes input: Confirm on Attack opens hud.panel 'target' (group "
                 "'Battle.Target') listing the enemies (raw 1 = selectable)",
        "S3-L5": "one in-engine PNG per panel (command, ability, item, target), each decoded NON-BLANK",
        "S3-GO": "GO/NO-GO: all four stock panels composed and took input inside BattleMapDebug (L1-L4)",
        "S3-C1": "an Attack commit is CAPTURED: captures +1 and `captured` == {wire slot 0, action 0, menu 0, id 0, the "
                 "target bit under the cursor, cursor 0, local_slot 0, cmd 1, site 'SendCommand'}",
        "S3-C2": "...its 9-byte hex DECODES IN PYTHON to exactly those fields",
        "S3-C3": "...the stock bookkeeping ran: 0 in turn.done and the panel closed (hud.panel 'none')",
        "S3-C4": "...NOTHING EXECUTED LOCALLY: for 3 s units[0].cmd_busy bit 0 clear, the target's hp_raw unchanged, "
                 "r9_refused still 0",
        "S3-C5": "...one 'stock menu: captured SendCommand -- local slot 0 Attack -> v1 frame [' line",
        "S3-I1": "an Item commit (Potion on the default target) is CAPTURED: captures +1, `captured` == {action 3, id 236, "
                 "menu 0, cursor 0, the target bit under the cursor}, and its hex decodes to that in Python",
        "S3-I2": "...the guest's REAL bag is untouched: `menus 0` shows Potion still N after 5 s; r9_refused still 0",
        "S3-K1": "CALIBRATION lever: `bmenu capture off` -> menu.capture_off true",
        "S3-K2": "...the same Attack commit runs the STOCK body into R9: captures unchanged, r9_refused +1, r9_site "
                 "'BattleHUD.SendCommand', one 'diorama R9: refused a local enqueue ... cmd[0]' line, cmd_busy bit 0 "
                 "clear, the target's hp_raw unchanged",
        "S3-K3": "...the same Item commit too: captures unchanged, r9_refused +1, Potion still N",
        "S3-K4": "`bmenu capture on` -> capture_off false",
        "S3-X1": "`bmenu mainmenu` is REFUSED: the verb succeeds, side_refused +1, side_why names the in-battle main menu "
                 "(AccessMenu / OnKeyMenu), hud.main_menu false, ui_state still BattleHUD 30 frames later",
        "S3-X3": "Change from the command root is REFUSED: capture_refused +1, capture_why 'Change is outside the v1 "
                 "command scope', no capture, the menu stays open on slot 0",
        "S3-T1": "teardown with a menu open: 'stock menu: closed all (the diorama tore down) -- 1 slot(s) drained, "
                 "bench-opened mask 0x1', then 'diorama torn down ... r9_refused=<n>'",
        "S3-T2": "a REAL `battle 67` afterwards: turn.enabled rises and the normal local menu opens (turn.slot >= 0)",
        "S3-R": "`reset` with the capture lever left OFF: 'stock-menu capture back ON (released with the harness)', "
                "capture_off false",
    }
    if RUN_5B:
        c["S3-K5"] = ("5b (throwaway): capture off + `containment 0` -> the Attack REALLY enqueues (units[0].cmd_busy bit 0 "
                      "set) and the local swing plays (the target's hp_raw drops)")
    if speed2:
        # asked only where it can fail: CanForceNextTurn is `Configuration.Battle.Speed == 2 && ...` (BattleHUD.Public.cs)
        c["S3-X2"] = "hud.can_force_next reads false while contained ([Battle] Speed=2, where the s102 gate decides it)"
    return c


def _battle_speed(g) -> str | None:
    """Memoria.ini [Battle] Speed (read-only), or None when the file or the key is absent."""
    v = cb.ini_value(g, "Battle", "Speed")
    return None if v is None else v.split(";", 1)[0].strip()


GO_PARTS = ("S3-L1", "S3-L2", "S3-L3", "S3-L4")


# ------------------------------------------------------------------------------------------- helpers
class _Ctx:
    """The run's facts, learned live."""
    potion_n = None              # the bag's Potion count (menus 0)
    potion_label = "Potion"
    ability_slot = None          # a seated slot with an Ability-type command that has an enabled ability
    ability_menus: list = []     # ...that slot's candidate BattleCommandMenu indices (`menus` type 1), MP-costing first
    ability_mp: dict = {}        # ...menu -> {ability id: `menus`' MP cost}, every learned ability of that command
    ability_costly = False       # ...whether one of its enabled abilities costs MP (the MP column then draws a number)
    target_uid = None            # the Attack's target (btl_id) -- the first live enemy
    shots: dict = {}


def _menus(g, slot: int) -> dict:
    """`menus <slot>` (raw: Session.menus refuses a diorama) -> battle.menu stamped for this slot, or {}."""
    ok, why = cb.try_send(g, f"menus {int(slot)}")
    if not ok:
        g.note(f"menus {slot} refused: {why[:160]}")
        return {}
    st = cb.poll(g, lambda s: int(cb.battle(s).get("menu", {}).get("slot", -1)) == int(slot), 3.0,
                 f"the menu for slot {slot}")
    return cb.battle(st).get("menu", {}) if st is not None else {}


def _potions(g, slot: int = 0):
    m = _menus(g, slot)
    it = next((i for i in m.get("items", []) if int(i.get("sub", -1)) == cb.POTION), None)
    return None if it is None else int(it.get("count", -1)), (it or {}).get("name") or "Potion"


def _ability_commands(m: dict) -> list:
    """The menu indices of every offered Ability-type command (CharacterCommandType.Ability = 1) with >= 1 enabled
    ability, MP-costing commands first, else menu order -- tried in turn: the first whose Confirm opens the ability list
    is the one judged."""
    out = []
    for c in m.get("commands", []):
        if int(c.get("type", -1)) != 1 or not c.get("offered", True):
            continue
        if any(int(a.get("menu", -1)) == int(c.get("menu", -2)) and a.get("enabled") for a in m.get("abilities", [])):
            out.append(int(c["menu"]))
    return sorted(out, key=lambda mn: not _costly(m, mn))   # stable: menu order within each group


def _costly(m: dict, menu: int) -> bool:
    """Whether command ``menu`` holds an ENABLED ability that costs MP (`menus`' own cost: CollectNetMenus)."""
    return any(int(a.get("menu", -1)) == int(menu) and a.get("enabled") and int(a.get("mp", 0) or 0) > 0
               for a in m.get("abilities", []))


def _ability_costs(m: dict, menu: int) -> dict:
    """{ability id: `menus`' MP cost} for every learned ability of command ``menu`` (the id the HUD row carries:
    NetDescribeList's cc.GetAbilityId == CollectNetMenus' active id, `sub`)."""
    return {int(a["sub"]): int(a.get("mp", 0) or 0) for a in m.get("abilities", [])
            if int(a.get("menu", -1)) == int(menu) and "sub" in a}


def _mp_column(on: list, costs: dict | None) -> tuple:
    """The MP column as the STOCK list draws it, judged per drawn-on row: BattleHUD.cs:845 writes
    `mp == 0 ? String.Empty : mp.ToString()`, so a cell is BLANK exactly when the ability costs 0 and digits otherwise.
    Held to `menus`' cost for that ability (matched by id) -- blank iff 0; the number itself is only reported (the HUD's
    cost is command-aware, `menus`' is not, so a mod's per-command MP patch may differ by design). A list `menus` does
    not describe (a drawn Ability1/2 entry of another type), or rows no id matches, are judged on the cell's form alone
    (blank or digits). (ok, detail)."""
    cells = [(r.get("id"), cb.strip_tags(r.get("label")), cb.strip_tags(r.get("number"))) for r in on]
    malformed = [c for c in cells if c[2] and not c[2].isdigit()]
    matched = [(i, lbl, n, costs[int(i)]) for i, lbl, n in cells
               if costs and isinstance(i, int) and int(i) in costs]
    wrong = [(i, lbl, n, mp) for i, lbl, n, mp in matched if (n == "") != (mp == 0)]
    differ = [(i, lbl, n, mp) for i, lbl, n, mp in matched if n and mp and n != str(mp)]
    form_only = not matched
    ok = not malformed and not wrong
    return ok, (f"MP cells {[(c[1], c[2]) for c in cells][:8]}; "
                + ("judged on form only (no `menus` cost matched a row id); " if form_only else
                   f"{len(matched)} row(s) held to `menus` (blank iff 0 MP); ")
                + (f"WRONG blank/number {wrong[:4]}; " if wrong else "")
                + (f"malformed {malformed[:4]}; " if malformed else "")
                + (f"number differs from `menus` (reported only) {differ[:4]}" if differ else ""))


def _to_root(g) -> bool:
    """Cancel back to the command root after a panel that went somewhere unexpected (a target cursor, a list)."""
    for _ in range(4):
        st = g.state
        if cb.hud(st).get("panel") == "command" and cb.cursor_group(st) == CMD_GROUP:
            return True
        if cb.hud(st).get("panel") in ("none", None) or st.turn_slot < 0:
            return False                                   # nothing open any more (a commit, the turn gone)
        g.press("cancel", 4)
        g.wait_frames(14)
    st = g.state
    return cb.hud(st).get("panel") == "command" and cb.cursor_group(st) == CMD_GROUP


def _hud_cmd(st, menu: int) -> dict | None:
    return next((r for r in cb.hud(st).get("commands") or [] if int(r.get("menu", -9)) == int(menu)), None)


def _open(g, slot: int) -> tuple:
    """`bmenu open <slot>` and wait for its command root. (ok, why, state)."""
    ok, why = cb.try_ns(g, "bmenu", "open", slot)
    if not ok:
        return False, why, g.state
    st = cb.poll(g, lambda s: s.turn_slot == slot and cb.hud(s).get("panel") == "command"
                 and cb.cursor_group(s) == CMD_GROUP, OPEN_S, f"slot {slot}'s command root")
    return st is not None, "" if st else f"the command root never opened for slot {slot} " \
                                         f"(turn.slot={g.state.turn_slot} hud={_hud_brief(g.state)})", st or g.state


def _close(g, slot: int) -> None:
    cb.try_ns(g, "bmenu", "close", slot)
    cb.poll(g, lambda s: s.turn_slot != slot, 2.0, f"slot {slot}'s panel to close")


def _hud_brief(st) -> str:
    h = cb.hud(st)
    return (f"panel={h.get('panel')!r} group={h.get('group')!r} slot={h.get('slot')!r} "
            f"cursor={cb.cursor_label(st)!r}")


def _pick(g, menu: int, *, expect_panel: str) -> tuple:
    """Cursor onto the command of ``menu`` (by its drawn label), Confirm, wait for ``expect_panel``. (ok, why, st)."""
    st = g.state
    row = _hud_cmd(st, menu)
    if row is None or not row.get("label"):
        return False, f"no drawn command for menu {menu} ({cb.hud(st).get('commands')})", st
    if not _to_root(g):
        return False, f"not at the command root ({_hud_brief(g.state)})", g.state
    found, seen = cb.walk_to_label(g, row["label"], group=CMD_GROUP)
    if not found:
        return False, f"the cursor never reached {row['label']!r} (saw {seen})", g.state
    g.press("confirm", 4)
    st = cb.wait_panel(g, expect_panel)
    if st is None:
        why = f"Confirm on {row['label']!r} opened no {expect_panel!r} panel ({_hud_brief(g.state)})"
        _to_root(g)                                        # never leave the next leg stranded in a stray panel
        return False, why, g.state
    return True, "", st


def _back(g) -> bool:
    g.press("cancel", 4)
    return cb.poll(g, lambda s: cb.hud(s).get("panel") == "command" and cb.cursor_group(s) == CMD_GROUP, 3.0,
                   "Cancel back to the command root") is not None


def _shot(g, ctx: _Ctx, key: str, name: str) -> None:
    g.wait_frames(10)
    p, why = cb.shot(g, name)
    ctx.shots[key] = (p, why)
    g.note(f"shot {name}: {p if p else why}")


def _target_mask(st) -> tuple:
    """The bit of the unit under the target cursor (by its drawn name), and that name."""
    name = cb.cursor_label(st)
    hits = [u for u in cb.units(st) if name and cb.strip_tags(u.get("name") or u.get("name_raw") or "") == name]
    if len(hits) == 1:
        return int(hits[0]["id"]), name
    # A PARTY row's label is a name TOKEN ([FRYA], [ZDNE], ...) that strip_tags empties -- read its NGUI button
    # instead: "Character k" is party slot k-1, whose target bit is 1 << (k-1) (players hold bits 0-3).
    button = str(st.battle_cursor.get("button") or "")
    if cb.cursor_group(st) == "Battle.Target" and button.startswith("Character "):
        try:
            k = int(button.split()[1])
        except ValueError:
            return None, name
        return (1 << (k - 1) if 1 <= k <= 4 else None), name or button
    return None, name


def _commit_target(g) -> tuple:
    """On the target cursor: read who is under it, Confirm. (expected mask or None, name)."""
    mask, name = _target_mask(g.state)
    g.press("confirm", 4)
    return mask, name


def _quiet(g, uid: int, seconds: float = QUIET_S) -> tuple:
    """(no local execution?, detail): units[0].cmd_busy bit 0 clear and the target's hp_raw steady."""
    samples = cb.hold_for(g, seconds)
    busy = [cb.raw(x).get("frame") for x in samples if ((cb.unit(x, 0) or {}).get("cmd_busy") or 0) & 1]
    hps = sorted({next((u.get("hp_raw") for u in cb.units(x) if int(u.get("id", -1)) == uid), None) for x in samples},
                 key=str)
    return (bool(samples) and not busy and len(hps) == 1 and hps[0] is not None,
            f"{len(samples)} publish(es); cmd_busy bit 0 on {busy[:5]}; target 0x{uid:02X} hp_raw {hps}")


def _captured(st) -> dict:
    c = cb.bmenu(st).get("captured")
    return c if isinstance(c, dict) else {}


# ------------------------------------------------------------------------------------------- the run
def run(g, field: int = cb.FIELD):
    speed = _battle_speed(g)
    led = cb.Ledger(g, _catalog(speed2=speed == "2"), finals=("S3-R",))
    g.note(f"[Battle] Speed={speed!r} (Memoria.ini, read-only): S3-X2 (can_force_next) is "
           + ("a ledger check" if speed == "2" else "only NOTED -- falsifiable solely under Speed=2"))
    ctx = _Ctx()
    ctx.shots, ctx.ability_menus, ctx.ability_mp = {}, [], {}
    try:
        _run(g, led, ctx, field)
    finally:
        g.note(f"Memoria.log archived: {cb.archive_log(g, 'stock-menu')}")
        led.close()
        try:
            if cb.dio(g.state).get("booted"):
                cb.leave(g, field)
        except HarnessError as err:
            g.note(f"could not leave the diorama before the release: {str(err)[:160]}")
        _release(g, led)
        led.close(final=True)


def _run(g, led: cb.Ledger, ctx: _Ctx, field: int) -> None:
    ok, why = cb.setup(g, field, label="B4/B5 stage 3: the stock menu first look + capture (s102), solo -- the GO/NO-GO")
    led.check("S3-S0", ok, why)
    st = g.state
    led.check("S3-P0", cb.has(st, "netsync.battle.menu.captures"),
              f"netsync.battle.menu keys: {sorted(cb.bmenu(st))}" if cb.has(st, "netsync.battle") else
              "no `netsync.battle` at all (a pre-s100 engine)")
    booted, why = cb.boot(g)
    if not booted:
        led.close(why)
        cb.back_to_field(g, field)
        return
    st = cb.wait_steady(g)
    if st is None:
        led.close("the diorama never reached its command phase (PHASE_NORMAL + turn.enabled)")
        cb.leave(g, field)
        return
    led.check("S3-P1", isinstance(cb.battle(st).get("hud"), dict) and "seq" in cb.battle(st),
              f"battle keys: {sorted(cb.battle(st))}")
    _preconditions(g, led, ctx, st)
    m0 = cb.bmenu(g.state)
    c0, r90 = m0.get("captures"), m0.get("r9_refused")
    _first_look(g, led, ctx)
    _attack_commit(g, led, ctx, c0, r90)
    _item_commit(g, led, ctx)
    _ability_elsewhere(g, led, ctx)
    _shots_verdict(g, led, ctx)
    led.check("S3-GO", all(led.done.get(c) for c in GO_PARTS),
              "; ".join(f"{c}={'ok' if led.done.get(c) else 'FAIL' if c in led.done else 'not run'}" for c in GO_PARTS)
              + "; shots: " + ", ".join(f"{k}={'ok' if v[0] else v[1]}" for k, v in sorted(ctx.shots.items())))
    _calibration(g, led, ctx)
    _side_gates(g, led, ctx)
    _teardown(g, led, field)


def _preconditions(g, led: cb.Ledger, ctx: _Ctx, st) -> None:
    n, label = _potions(g, 0)
    ctx.potion_n, ctx.potion_label = n, label
    led.check("S3-PRE1", isinstance(n, int) and n >= 1, f"Potion count {n!r} (slot 0's `menus`)")
    # the first seated slot whose list holds an enabled MP-COSTING ability (Vivi / Garnet), else the first with any
    # (Zidane's Flee / Detect cost 0: their MP cells draw blank, and L2 holds them to exactly that)
    seen = []
    for slot in cb.player_slots(st):
        m = _menus(g, slot)
        hits = _ability_commands(m)
        if not hits:
            continue
        costly = _costly(m, hits[0])
        seen.append(f"slot {slot} menu(s) {hits}{' (MP-costing)' if costly else ' (0-MP only)'}")
        if ctx.ability_slot is None or (costly and not ctx.ability_costly):
            ctx.ability_slot, ctx.ability_menus, ctx.ability_costly = slot, hits, costly
            ctx.ability_mp = {mn: _ability_costs(m, mn) for mn in hits}
        if ctx.ability_costly:
            break
    led.check("S3-PRE2", ctx.ability_slot is not None,
              f"judged: slot {ctx.ability_slot} menu(s) {ctx.ability_menus} "
              f"({'an MP-costing ability' if ctx.ability_costly else '0-MP abilities only: the MP cells draw blank'}); "
              f"candidates {seen}" if ctx.ability_slot is not None else
              f"no seated member ({cb.player_slots(st)}) has an Ability-type command with an enabled ability -- deploy "
              f"COOPPARTY (30604) so Vivi/Garnet sit in the party")
    foe = cb.first_enemy(g.state)
    ctx.target_uid = None if foe is None else int(foe["id"])


def _first_look(g, led: cb.Ledger, ctx: _Ctx) -> None:
    g.note("L: the first look -- bmenu open 0, then every stock panel, photographed")
    at = cb.mark(g)
    ok, why, st = _open(g, 0)
    lines = cb.wait_log(g, at, "harness: bench opener -- local slot 0", 2.0)
    h = cb.hud(st)
    atk = _hud_cmd(st, 0) or {}
    labels = [r.get("label") for r in h.get("commands") or []]
    led.check("S3-L1", ok and st.turn_slot == 0 and 0 in (cb.turn(st).get("ready") or []) and h.get("panel") == "command"
              and h.get("group") == CMD_GROUP and h.get("slot") == 0 and labels and all(labels)
              and atk.get("state") == 2 and cb.mask_bits(cb.bmenu(st).get("bench_open")) & 1
              and cb.count(lines, "harness: bench opener -- local slot 0") == 1,
              why or f"{_hud_brief(st)} commands={[(r.get('menu'), r.get('label'), r.get('state')) for r in h.get('commands') or []]} "
                     f"ready={cb.turn(st).get('ready')} bench_open={cb.bmenu(st).get('bench_open')!r}; "
                     f"{cb.grep(lines, 'bench opener')}")
    if not ok:
        led.unreached(("S3-L2", "S3-L3", "S3-L4", "S3-L5", "S3-C1", "S3-C2", "S3-C3", "S3-C4", "S3-C5"),
                      f"the command root never opened: {why}")
        return
    _shot(g, ctx, "command", "s3-panel-1-command")
    # the ability list, when slot 0 is the one that has it
    if ctx.ability_slot == 0:
        _ability_panel(g, led, ctx)
    # the item list
    ok, why, st = _pick(g, 4, expect_panel="item")
    rows = cb.hud(st).get("rows") or []
    pot = next((r for r in rows if int(r.get("id", -1)) == cb.POTION), None)
    if ok:
        _shot(g, ctx, "item", "s3-panel-3-item")
    back = ok and _back(g)
    led.check("S3-L3", ok and cb.cursor_group(st) == ITEM_GROUP and pot is not None
              and cb.strip_tags(pot.get("number")) == str(ctx.potion_n) and back,
              why or f"group={cb.cursor_group(st)!r} rows={[(r.get('id'), r.get('label'), r.get('number')) for r in rows][:8]} "
                     f"(want id {cb.POTION} x{ctx.potion_n}); back to the root: {back}")
    # the target cursor (left OPEN: the Attack commit below confirms on it)
    ok, why, st = _pick(g, 0, expect_panel="target")
    rows = cb.hud(st).get("rows") or []
    foes = [r for r in rows if int(r.get("raw", -1)) == 1 and int(r.get("id", -1)) >= 4]
    led.check("S3-L4", ok and cb.cursor_group(st) == TARGET_GROUP and bool(foes),
              why or f"group={cb.cursor_group(st)!r} rows={[(r.get('id'), r.get('label'), r.get('raw')) for r in rows]}")
    if ok:
        _shot(g, ctx, "target", "s3-panel-4-target")


def _ability_panel(g, led: cb.Ledger, ctx: _Ctx) -> None:
    whys = []
    ok, st = False, g.state
    # `menus`' Ability-type commands first; then any other drawn Ability1/Ability2 entry (a mislabelled type must not
    # cost the leg -- only an opened ability LIST is judged)
    drawn = [m for m in (2, 3) if (_hud_cmd(st, m) or {}).get("state") == 2 and m not in ctx.ability_menus]
    opened = None
    for menu in list(ctx.ability_menus) + drawn:
        ok, why, st = _pick(g, menu, expect_panel="ability")
        if ok:
            opened = menu
            break
        whys.append(f"menu {menu}: {why}")
    rows = cb.hud(st).get("rows") or []
    on = [r for r in rows if r.get("state") == 2]
    mp_ok, mp_why = _mp_column(on, ctx.ability_mp.get(opened)) if ok else (False, "no list opened")
    if ok:
        _shot(g, ctx, "ability", "s3-panel-2-ability")
    back = ok and _back(g)
    led.check("S3-L2", ok and cb.cursor_group(st) == ABILITY_GROUP and bool(on)
              and all(r.get("label") for r in on) and mp_ok and back,
              ("; ".join(whys) + "; " if whys else "")
              + f"slot {ctx.ability_slot} menu {opened}: group={cb.cursor_group(st)!r} rows="
                f"{[(r.get('id'), r.get('label'), r.get('number'), r.get('state')) for r in rows][:10]}; {mp_why}; "
                f"back to the root: {back}")


def _ability_elsewhere(g, led: cb.Ledger, ctx: _Ctx) -> None:
    """The ability panel on another seated slot (slot 0 has no Ability-type list with an enabled row)."""
    if "S3-L2" in led.done:
        return
    if ctx.ability_slot is None:
        led.unreached(("S3-L2",), "no seated member has an Ability-type command with an enabled ability (S3-PRE2)")
        return
    _close(g, 0)
    ok, why, _ = _open(g, ctx.ability_slot)
    if not ok:
        led.check("S3-L2", False, f"`bmenu open {ctx.ability_slot}`: {why}")
        return
    _ability_panel(g, led, ctx)
    _close(g, ctx.ability_slot)


def _shots_verdict(g, led: cb.Ledger, ctx: _Ctx) -> None:
    if "S3-L5" in led.done:
        return
    want = ("command", "ability", "item", "target")
    bad = {k: (ctx.shots.get(k) or (None, "not taken"))[1] or "blank" for k in want
           if not (ctx.shots.get(k) or (None, ""))[0] or not cb.png_not_blank(ctx.shots[k][0])}
    led.check("S3-L5", not bad, f"{', '.join(f'{k}={v}' for k, v in bad.items()) or 'all four non-blank'}; "
                                f"{[str(v[0]) for v in ctx.shots.values() if v[0]]}")


def _attack_commit(g, led: cb.Ledger, ctx: _Ctx, c0, r90) -> None:
    st = g.state
    if "S3-L4" not in led.done or not led.done["S3-L4"] or cb.hud(st).get("panel") != "target":
        led.unreached(("S3-C1", "S3-C2", "S3-C3", "S3-C4", "S3-C5"), "the target cursor never opened (S3-L4)")
        return
    g.note("C: commit the Attack on the target cursor")
    c0 = cb.bmenu(st).get("captures")                      # just before the commit (the first look commits nothing)
    at = cb.mark(g)
    mask, name = _commit_target(g)
    uid = mask if mask is not None else ctx.target_uid
    st = cb.poll(g, lambda s: cb.bmenu(s).get("captures") == (c0 or 0) + 1, 3.0, "the capture to count") or g.state
    cap = _captured(st)
    want = {"slot": 0, "action": cb.ACT_ATTACK, "menu": 0, "id": 0, "mask": mask, "cursor": 0}
    got = {k: cap.get(k) for k in want}
    led.check("S3-C1", isinstance(c0, int) and cb.bmenu(st).get("captures") == c0 + 1 and mask is not None and got == want
              and cap.get("local_slot") == 0 and cap.get("cmd") == cb.CMD_ATTACK and cap.get("site") == "SendCommand",
              f"captures {c0!r}->{cb.bmenu(st).get('captures')!r}; captured={cap}; want {want} (target {name!r})")
    dec = cb.decode_cmd(cap.get("hex", ""))
    led.check("S3-C2", dec is not None and dec == got == want, f"hex {cap.get('hex')!r} -> {dec}; engine {got}; want {want}")
    st2 = cb.poll(g, lambda s: cb.hud(s).get("panel") == "none", 2.0, "the panel to close") or g.state
    done = cb.turn(st2).get("done") or []
    led.check("S3-C3", 0 in done and cb.hud(st2).get("panel") == "none",
              f"turn.done={done} {_hud_brief(st2)}")
    quiet, detail = _quiet(g, uid) if uid is not None else (False, "no target id")
    st3 = g.state
    led.check("S3-C4", quiet and cb.bmenu(st3).get("r9_refused") == r90 == 0,
              f"{detail}; r9_refused {r90!r}->{cb.bmenu(st3).get('r9_refused')!r}")
    lines = cb.new(g, at)
    led.check("S3-C5", cb.count(lines, "stock menu: captured SendCommand -- local slot 0 Attack -> v1 frame [") == 1,
              cb.grep(lines, "stock menu"))


def _item_commit(g, led: cb.Ledger, ctx: _Ctx) -> None:
    g.note("I: commit a Potion on the default target")
    if not isinstance(ctx.potion_n, int) or ctx.potion_n < 1:
        led.unreached(("S3-I1", "S3-I2"), "no Potion in the bag (S3-PRE1)")
        return
    _close(g, 0)
    ok, why, st = _open(g, 0)
    if not ok:
        led.unreached(("S3-I1", "S3-I2"), f"`bmenu open 0` again: {why}")
        return
    c0, r90 = cb.bmenu(st).get("captures"), cb.bmenu(st).get("r9_refused")
    ok, why = _item_to_target(g, ctx)
    if not ok:
        led.unreached(("S3-I1", "S3-I2"), why)
        return
    mask, name = _commit_target(g)
    st = cb.poll(g, lambda s: cb.bmenu(s).get("captures") == (c0 or 0) + 1, 3.0, "the item capture to count") or g.state
    cap = _captured(st)
    want = {"slot": 0, "action": cb.ACT_ITEM, "menu": 0, "id": cb.POTION, "mask": mask, "cursor": 0}
    got = {k: cap.get(k) for k in want}
    dec = cb.decode_cmd(cap.get("hex", ""))
    led.check("S3-I1", isinstance(c0, int) and cb.bmenu(st).get("captures") == c0 + 1 and mask is not None
              and got == want and dec == want,
              f"captures {c0!r}->{cb.bmenu(st).get('captures')!r}; captured={cap}; decoded {dec}; want {want} "
              f"(target {name!r})")
    cb.hold_for(g, POTION_WAIT_S)
    n, _ = _potions(g, 0)
    led.check("S3-I2", n == ctx.potion_n and cb.bmenu(g.state).get("r9_refused") == r90,
              f"Potion {ctx.potion_n} -> {n}; r9_refused {r90!r}->{cb.bmenu(g.state).get('r9_refused')!r}")


def _item_to_target(g, ctx: _Ctx) -> tuple:
    ok, why, st = _pick(g, 4, expect_panel="item")
    if not ok:
        return False, why
    rows = cb.hud(st).get("rows") or []
    pot = next((r for r in rows if int(r.get("id", -1)) == cb.POTION), None)
    label = cb.strip_tags((pot or {}).get("label") or ctx.potion_label)
    found, seen = cb.walk_to_label(g, label, group=ITEM_GROUP)
    if not found:
        return False, f"the item cursor never reached {label!r} (saw {seen})"
    g.press("confirm", 4)
    st = cb.wait_panel(g, "target")
    return (st is not None), ("" if st else f"Confirm on {label!r} opened no target cursor ({_hud_brief(g.state)})")


def _calibration(g, led: cb.Ledger, ctx: _Ctx) -> None:
    g.note("K: the same commits with `bmenu capture off` -- the stock bodies must run into R9")
    ok, why = cb.try_ns(g, "bmenu", "capture", "off")
    st = cb.poll(g, lambda s: cb.bmenu(s).get("capture_off") is True, 2.0, "capture_off true") if ok else None
    led.check("S3-K1", ok and st is not None, why or f"capture_off={cb.bmenu(g.state).get('capture_off')!r}")
    if not ok:
        led.unreached(("S3-K2", "S3-K3", "S3-K4") + (("S3-K5",) if RUN_5B else ()), f"`bmenu capture off` refused -- {why}")
        return
    # K2: the Attack
    _close(g, 0)
    ok, why, st = _open(g, 0)
    if ok:
        ok, why, st = _pick(g, 0, expect_panel="target")
    if not ok:
        led.check("S3-K2", False, f"could not reach the target cursor again: {why}")
    else:
        m = cb.bmenu(st)
        c0, r0 = m.get("captures"), m.get("r9_refused")
        at = cb.mark(g)
        mask, _ = _commit_target(g)
        uid = mask if mask is not None else ctx.target_uid
        st = cb.poll(g, lambda s: cb.bmenu(s).get("r9_refused") == (r0 or 0) + 1, 3.0, "R9 to count the stock enqueue") \
            or g.state
        quiet, detail = _quiet(g, uid) if uid is not None else (False, "no target id")
        lines = cb.new(g, at)
        site = cb.bmenu(st).get("r9_site") or ""
        led.check("S3-K2", cb.bmenu(st).get("captures") == c0 and isinstance(r0, int) and cb.bmenu(st).get("r9_refused") == r0 + 1
                  and site.startswith("BattleHUD.SendCommand") and quiet
                  and len([ln for ln in lines if "diorama R9: refused a local enqueue" in ln and "cmd[0]" in ln]) == 1,
                  f"captures {c0!r}->{cb.bmenu(st).get('captures')!r} r9_refused {r0!r}->{cb.bmenu(st).get('r9_refused')!r} "
                  f"r9_site={site!r}; {detail}; {cb.grep(lines, 'diorama R9')}")
    # K3: the Item
    if not isinstance(ctx.potion_n, int) or ctx.potion_n < 1:
        led.check("S3-K3", False, "not reached: no Potion in the bag (S3-PRE1)")
    else:
        _close(g, 0)
        ok, why, st = _open(g, 0)
        if ok:
            ok, why = _item_to_target(g, ctx)
        if not ok:
            led.check("S3-K3", False, f"could not reach the Potion's target cursor again: {why}")
        else:
            m = cb.bmenu(g.state)
            c0, r0 = m.get("captures"), m.get("r9_refused")
            _commit_target(g)
            st = cb.poll(g, lambda s: cb.bmenu(s).get("r9_refused") == (r0 or 0) + 1, 3.0, "R9 to count the item") \
                or g.state
            cb.hold_for(g, POTION_WAIT_S)
            n, _ = _potions(g, 0)
            led.check("S3-K3", cb.bmenu(st).get("captures") == c0 and isinstance(r0, int)
                      and cb.bmenu(st).get("r9_refused") == r0 + 1 and n == ctx.potion_n,
                      f"captures {c0!r}->{cb.bmenu(st).get('captures')!r} r9_refused {r0!r}->"
                      f"{cb.bmenu(st).get('r9_refused')!r}; Potion {ctx.potion_n} -> {n}")
    if RUN_5B:
        _five_b(g, led, ctx)
    ok, why = cb.try_ns(g, "bmenu", "capture", "on")
    st = cb.poll(g, lambda s: cb.bmenu(s).get("capture_off") is False, 2.0, "capture_off false") if ok else None
    led.check("S3-K4", ok and st is not None, why or f"capture_off={cb.bmenu(g.state).get('capture_off')!r}")


def _five_b(g, led: cb.Ledger, ctx: _Ctx) -> None:
    """5b, opt-in and THROWAWAY: no capture, no R9 -- the Attack really enqueues and the local sim swings."""
    ok, why = cb.try_ns(g, "containment", 0)
    if not ok:
        led.check("S3-K5", False, f"`netsync containment 0` refused -- {why}")
        return
    try:
        _close(g, 0)
        ok, why, st = _open(g, 0)
        if ok:
            ok, why, st = _pick(g, 0, expect_panel="target")
        if not ok:
            led.check("S3-K5", False, f"could not reach the target cursor: {why}")
            return
        mask, _ = _commit_target(g)
        uid = mask if mask is not None else ctx.target_uid
        hp0 = next((u.get("hp_raw") for u in cb.units(st) if int(u.get("id", -1)) == uid), None)
        ever = []
        _, hit = cb.watch(g, lambda s: any(int(u.get("id", -1)) == uid and hp0 is not None and (u.get("hp_raw") or 0) < hp0
                                           for u in cb.units(s)),
                          6.0, on_sample=lambda s: ever.append(1) if ((cb.unit(s, 0) or {}).get("cmd_busy") or 0) & 1 else None)
        led.check("S3-K5", bool(ever) and hit is not None, f"cmd_busy bit 0 ever set: {bool(ever)}; hp_raw {hp0!r} -> "
                                                           f"{[u.get('hp_raw') for u in cb.units(g.state) if int(u.get('id', -1)) == uid]}")
    finally:
        cb.try_ns(g, "containment", 1)


def _side_gates(g, led: cb.Ledger, ctx: _Ctx) -> None:
    g.note("X: the side gates -- the in-battle main menu, ForceNextTurn, Change")
    st = g.state
    s0 = cb.bmenu(st).get("side_refused")
    ok, why = cb.try_ns(g, "bmenu", "mainmenu")
    st = g.state
    g.wait_frames(30)
    st2 = g.state
    led.check("S3-X1", ok and isinstance(s0, int) and cb.bmenu(st).get("side_refused") == s0 + 1
              and cb.bmenu(st).get("side_why") == MAIN_MENU_WHY and cb.hud(st).get("main_menu") is False
              and st2.ui_state == "BattleHUD",
              why or f"side_refused {s0!r}->{cb.bmenu(st).get('side_refused')!r} side_why={cb.bmenu(st).get('side_why')!r} "
                     f"main_menu={cb.hud(st).get('main_menu')!r} ui 30 frames later={st2.ui_state!r}")
    if "S3-X2" in led.catalog:
        led.check("S3-X2", cb.hud(st2).get("can_force_next") is False,
                  f"can_force_next={cb.hud(st2).get('can_force_next')!r} under [Battle] Speed=2")
    else:
        g.note(f"X2 observed (not a ledger check -- [Battle] Speed is not 2, so CanForceNextTurn is false whatever the "
               f"gate): can_force_next={cb.hud(st2).get('can_force_next')!r}")
    _close(g, 0)
    ok, why, st = _open(g, 0)
    if not ok:
        led.check("S3-X3", False, f"`bmenu open 0`: {why}")
        return
    row = _hud_cmd(st, 5)
    if row is None or row.get("state") != 2:
        led.check("S3-X3", False, f"not reached: Change is not drawn on for slot 0 ({row})")
        return
    m = cb.bmenu(st)
    r0, c0 = m.get("capture_refused"), m.get("captures")
    found, seen = cb.walk_to_label(g, row["label"], group=CMD_GROUP)
    if not found:
        led.check("S3-X3", False, f"the cursor never reached {row['label']!r} (saw {seen})")
        return
    g.press("confirm", 4)
    st = cb.poll(g, lambda s: cb.bmenu(s).get("capture_refused") == (r0 or 0) + 1 or cb.hud(s).get("panel") == "target",
                 3.0, "Change's refusal (or its target cursor)") or g.state
    if cb.hud(st).get("panel") == "target":                # a Change that asks for a target first
        g.press("confirm", 4)
        st = cb.poll(g, lambda s: cb.bmenu(s).get("capture_refused") == (r0 or 0) + 1, 3.0, "Change's refusal") or g.state
    g.wait_frames(20)
    st2 = g.state
    m2 = cb.bmenu(st2)
    led.check("S3-X3", isinstance(r0, int) and m2.get("capture_refused") == r0 + 1 and m2.get("captures") == c0
              and str(m2.get("capture_why") or "").startswith("Change is outside the v1 command scope")
              and st2.turn_slot == 0,
              f"capture_refused {r0!r}->{m2.get('capture_refused')!r} captures {c0!r}->{m2.get('captures')!r} "
              f"capture_why={m2.get('capture_why')!r} turn.slot={st2.turn_slot} {_hud_brief(st2)}")


def _teardown(g, led: cb.Ledger, field: int) -> None:
    g.note("T: leave the diorama with a stock menu OPEN, then fight a real battle")
    st = g.state
    if st.turn_slot != 0:
        _close(g, 0)
        ok, why, st = _open(g, 0)
    else:
        ok, why = True, ""
    at = cb.mark(g)
    left, lwhy = cb.leave(g, field)
    lines = cb.wait_log(g, at, TORN, 3.0)
    i_closed = next((i for i, ln in enumerate(lines) if CLOSED_ALL in ln), None)
    i_torn = next((i for i, ln in enumerate(lines) if TORN in ln), None)
    t1 = ok and left and i_closed is not None and i_torn is not None and i_closed < i_torn
    led.check("S3-T1", t1, (why or lwhy) or cb.grep(lines, "stock menu: closed all", "torn down"))
    if not left:
        cb.back_to_field(g, field)
        led.unreached(("S3-T2",), f"no return to the field: {lwhy}")
        return
    if not ok:
        # no stock window was open at the teardown, so a healthy real battle afterwards would prove nothing
        led.unreached(("S3-T2",), f"no bench-opened stock menu was torn down (S3-T1): {why}")
        return
    try:
        g.start_battle(cb.SCENE)
    except HarnessError as err:
        led.check("S3-T2", False, f"`battle {cb.SCENE}` did not start: {str(err)[:200]}")
        return
    st = cb.poll(g, lambda s: s.commands_enabled and s.turn_slot >= 0, 60.0, "the real battle's local command menu")
    led.check("S3-T2", st is not None,
              f"turn.enabled={g.state.commands_enabled} turn.slot={g.state.turn_slot} {_hud_brief(g.state)}")
    try:
        g.fight(timeout=240.0, finish=True)
    except HarnessError as err:
        g.note(f"the real battle after the teardown did not finish cleanly: {str(err)[:160]}")
    cb.poll(g, lambda s: s.on_field and s.ui_state == "FieldHUD", 30.0, "the field after the real battle")


def _release(g, led: cb.Ledger) -> None:
    """Leave the capture lever OFF on purpose, then `reset`: the release must restore it and say so."""
    ok, why = cb.try_ns(g, "bmenu", "capture", "off")
    at = cb.mark(g)
    cb.release(g)
    st = g.state
    lines = cb.new(g, at)
    led.check("S3-R", ok and cb.count(lines, "stock-menu capture back ON (released with the harness)") == 1
              and cb.bmenu(st).get("capture_off") is False and (st.netsync or {}).get("forced") is False,
              why or f"capture_off={cb.bmenu(st).get('capture_off')!r}; {cb.grep(lines, 'released with the harness')}")
