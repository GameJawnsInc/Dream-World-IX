"""THE STORY-WRITE TRACE's segment driver, shared by O1 and O2 (research/o2_design.md, sections 1.4 and 2).

``RouteVoid`` and ``pick_for`` moved here from ``o1_opening`` (which imports and re-exports both): O1's rules and
O1's ``raise RouteVoid(msg)`` behave exactly as they did. What O2 adds is additive and optional:
  - a RouteVoid may carry its VOID class (``v``: "V1".."V14"), its beat-table ``cell`` (``[donor, sc]``) and who it
    is attributed to (``by``: "driver" or "game"), so the session record and the analysis can read VOIDs per side;
  - a choice rule may carry ``sc`` (the published scenarios it applies at), ``once`` (a second answer is VOID V2)
    and ``take: "default"`` (the pick must be the game's own ready cursor, else VOID V3).
"""
from __future__ import annotations


class RouteVoid(Exception):
    """The route met something it has no rule for: the run is VOID (never a finding about the scripts).

    ``v`` / ``cell`` / ``by`` are the VOID's class, its beat-table cell and its attribution (2.7); each is None
    unless given, so O1's ``raise RouteVoid(msg)`` still works and its runs record no class."""

    def __init__(self, msg: str = "", *, v: str | None = None, cell: list | None = None, by: str | None = None):
        super().__init__(msg)
        self.v, self.cell, self.by = v, cell, by


def pick_for(choice: dict, donor: int, pred: dict, *, sc: int | None = None, answered=()) -> tuple:
    """``(absolute option index or "default", the rule)`` for a ready choice, by the frozen rule table; raises
    RouteVoid when no rule matches. ``choice["options"]`` is ``[prompt, *shown lines]``; ``active`` the absolute
    index of each shown line.

    Three rule keys are optional, each skipped when absent (so O1's rules read exactly as before):
      - ``sc`` (a list): the rule applies only when the published scenario ``sc`` is in it; ``None`` = any;
      - ``once``: a rule whose index (its position in ``pred["choices"]``) is in ``answered`` is asked again:
        VOID V2;
      - ``take: "default"``: the resolved pick must be ``choice["selected"]``, the game's own ready cursor: else
        VOID V3 -- stepping the cursor is not the route.
    A choice no rule matches (V1 to the beat-table driver) and a pick on other than one line raise as O1's did,
    with no class."""
    lines = list(choice.get("options") or [])[1:]
    active = list(choice.get("active") or range(len(lines)))
    for n, rule in enumerate(pred["choices"]):
        if rule["donor"] not in (None, donor):
            continue
        if rule.get("sc") is not None and sc not in rule["sc"]:
            continue
        if not any(rule["match"] in ln for ln in [choice.get("options", [""])[0], *lines]):
            continue
        if rule.get("once") and n in answered:
            raise RouteVoid(f"choice in {donor} at SC {sc}: rule {rule['match']!r} answers once and was answered "
                            f"already: {choice.get('options')}", v="V2", cell=[donor, sc], by="game")
        if rule["pick"] == "default":
            return "default", rule
        hits = [active[i] for i, ln in enumerate(lines) if rule["pick"] in ln]
        if len(hits) != 1:
            raise RouteVoid(f"choice in {donor}: rule {rule['match']!r} picks {rule['pick']!r}, which is on "
                            f"{len(hits)} lines of {lines}")
        if rule.get("take") == "default" and hits[0] != choice.get("selected"):
            raise RouteVoid(f"choice in {donor} at SC {sc}: the frozen pick {rule['pick']!r} (option {hits[0]}) is "
                            f"not the game's default {choice.get('selected')}: stepping the cursor is not the route",
                            v="V3", cell=[donor, sc], by="game")
        return hits[0], rule
    raise RouteVoid(f"choice in {donor} with no rule: {choice.get('options')}")
