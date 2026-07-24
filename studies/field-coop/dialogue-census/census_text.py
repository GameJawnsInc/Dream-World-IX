#!/usr/bin/env python3
"""F3 dialogue-lockstep census -- TEXT-TAG resolution pass (refines the opcode census).

For every window-open site recorded by census_windows.py (window_sites.json), resolve the site's
immediate textId against the field's real .mes text (read live from the install through the kit's
dialogue._load_field_text), and classify the WINDOW's close/advance mechanism from the text tags.

Engine-grounded tag semantics (verified in C:/gd/FFIX/Memoria this pass):
  * [TIME=N] with N>0  -> DialogBoxSymbols.OnTime: EndMode=N + FlagButtonInh=true. AfterShown starts the
                          AutoHide coroutine (Dialog.cs:639-646): the window auto-closes after N frames,
                          player button INHIBITED.  => TIMED auto-close (identical on both machines).
  * [TIME=-1] (or IncreaseSignal) -> FlagButtonInh=true, NO auto-hide. The window lingers until a SCRIPT
                          close (CloseWindow/CloseAllWindows) or page-feed.  => SCRIPT-DRIVEN.
  * no [TIME]          -> FlagButtonInh=false. The window closes on the player's confirm key
                          (UIKeyTrigger -> DialogManager.OnKeyConfirm).  => CONFIRM-GATED.
  * [CHOO]             -> the window carries selectable choice rows (Dialog.HasChoices). CONFIRM-GATED and
                          BRANCH-RELEVANT (GetChoose reads the result).
  * [PAGE]             -> a page break WITHIN one textId (multi-page dialogue in ONE window/one textId).
  * [IMME]             -> instant print (typewriter OFF). NOT an advance mechanism (common misread).
  * [FEED=n]           -> horizontal indent. NOT an advance mechanism (common misread).

Deterministic: sites processed in the order census_windows.py emitted them (field-id ascending).
Re-runnable: reads window_sites.json; writes census_text.json. No writes outside this directory.
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
KIT = HERE.parents[2] / "ff9mapkit"
sys.path.insert(0, str(KIT))

from ff9mapkit import dialogue                              # noqa: E402
from ff9mapkit._fieldtext import EVENT_ID_TO_MES            # noqa: E402

_TIME_RE = re.compile(r"\[TIME=(-?\d+)\]")
_CHOO = "[CHOO]"
_PAGE = "[PAGE]"
_IMME = "[IMME]"


def classify_text(text):
    """(mechanism, time_value_or_None, has_page, has_imme) for one window's verbatim .mes text."""
    if text is None:
        return "UNRESOLVED", None, False, False
    times = [int(m.group(1)) for m in _TIME_RE.finditer(text)]
    has_choo = _CHOO in text
    has_page = _PAGE in text
    has_imme = _IMME in text
    pos_time = [t for t in times if t > 0]
    neg_time = [t for t in times if t == -1]
    # precedence: a positive [TIME] auto-closes regardless of everything else (button inhibited)
    if pos_time:
        return "TIMED", min(pos_time), has_page, has_imme
    if has_choo:
        return "CHOICE", None, has_page, has_imme
    if neg_time:
        return "TIME_NEG1", -1, has_page, has_imme      # button inhibited, script-driven close
    return "CONFIRM", None, has_page, has_imme


def main():
    sites = json.loads((HERE / "window_sites.json").read_text(encoding="utf-8"))
    # group sites by field so each field's text loads once
    by_field = defaultdict(list)
    for s in sites:
        by_field[s["fid"]].append(s)

    mech_counter = Counter()                      # overall mechanism
    mech_by_opclass = defaultdict(Counter)        # opcode-class x text-mechanism cross-tab
    time_values = Counter()                       # [TIME=N] value distribution
    page_windows = 0
    imme_windows = 0
    unresolved = 0
    resolved = 0
    choice_windows = 0
    # the crux: how many windows genuinely require a player CONFIRM to advance (must lockstep) vs
    # advance for free (TIMED / TIME_NEG1-script / replaced / script-closed)?
    fields_done = 0

    enriched = []
    for fid in sorted(by_field):
        zone = EVENT_ID_TO_MES.get(int(fid))
        txids = sorted({s["textid"] for s in by_field[fid]
                        if isinstance(s["textid"], int)})
        textmap = {}
        if zone is not None and txids:
            try:
                d = dialogue._load_field_text(txids, "us", zone_id=zone)
                textmap = {k: v.text for k, v in d.items()}
            except Exception as e:                # noqa: BLE001
                print(f"WARN field {fid} text load: {e}", file=sys.stderr)
        for s in by_field[fid]:
            t = s["textid"]
            text = textmap.get(t) if isinstance(t, int) else None
            mech, tval, has_page, has_imme = classify_text(text)
            if mech == "UNRESOLVED":
                unresolved += 1
            else:
                resolved += 1
            mech_counter[mech] += 1
            mech_by_opclass[s["klass"]][mech] += 1
            if tval is not None and tval > 0:
                time_values[tval] += 1
            if has_page:
                page_windows += 1
            if has_imme:
                imme_windows += 1
            if mech == "CHOICE":
                choice_windows += 1
            s2 = dict(s)
            s2["mech"] = mech
            s2["time"] = tval
            s2["page"] = has_page
            enriched.append(s2)
        fields_done += 1

    # F3 impact: the FINAL advance mechanism after combining opcode-fate + text.
    #  - TIMED / TIME_NEG1 (button inhibited) -> advances the same on both machines for free (self/script).
    #  - async_close / async_replaced -> the SCRIPT closes/replaces it -> free (both scripts run the op).
    #  - CONFIRM / CHOICE on a sync_blocking or async_wait window -> requires a real player input to advance
    #    -> THIS is the surface F3 must lockstep.
    must_lockstep = 0
    free_timed = 0
    free_script = 0
    for s in enriched:
        blocking = s["klass"] in ("sync_blocking", "async_wait")
        if s["mech"] in ("TIMED", "TIME_NEG1"):
            free_timed += 1
        elif s["klass"] in ("async_close", "async_replaced", "async_closeall"):
            free_script += 1
        elif blocking and s["mech"] in ("CONFIRM", "CHOICE"):
            must_lockstep += 1
        elif s["mech"] == "UNRESOLVED" and blocking:
            must_lockstep += 1                    # conservative: unknown text on a blocking window
        else:
            free_script += 1                      # fireforget async etc.

    out = {
        "sites_total": len(enriched),
        "resolved": resolved, "unresolved": unresolved,
        "mechanism_overall": dict(mech_counter.most_common()),
        "mechanism_by_opcode_class": {k: dict(v.most_common()) for k, v in mech_by_opclass.items()},
        "time_value_hist": dict(sorted(time_values.items())),
        "page_windows": page_windows,
        "imme_windows": imme_windows,
        "choice_windows": choice_windows,
        "f3_impact": {
            "must_lockstep_confirm_or_choice": must_lockstep,
            "free_timed_or_buttoninhibited": free_timed,
            "free_script_closed_or_replaced": free_script,
        },
    }
    (HERE / "census_text.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    (HERE / "window_sites_enriched.json").write_text(json.dumps(enriched), encoding="utf-8")

    p = print
    p("=" * 78)
    p("F3 TEXT-TAG RESOLUTION  (window close/advance mechanism from the real .mes)")
    p("=" * 78)
    p(f"sites: {out['sites_total']}   resolved: {resolved}   unresolved: {unresolved} "
      f"({100*unresolved/out['sites_total']:.1f}%)")
    p("")
    p("-- window advance/close mechanism (from text tags) --")
    for k, v in out["mechanism_overall"].items():
        p(f"   {k:12s} {v:6d}  ({100*v/out['sites_total']:.1f}%)")
    p("")
    p("-- mechanism x opcode-class cross-tab --")
    for kl in ("sync_blocking", "async_wait", "async_close", "async_replaced",
               "async_closeall", "fireforget"):
        row = out["mechanism_by_opcode_class"].get(kl, {})
        if row:
            p(f"   {kl:16s} {dict(row)}")
    p("")
    p(f"-- [TIME=N] value histogram (frames; N/FieldTPS sec auto-close): {out['time_value_hist']}")
    p(f"-- windows with [PAGE] (multi-page in ONE textId): {page_windows}")
    p(f"-- windows with [IMME] (instant print, NOT advance): {imme_windows}")
    p(f"-- CHOICE windows ([CHOO], branch-relevant): {choice_windows}")
    p("")
    p("-- F3 IMPACT (combining opcode-fate + text mechanism) --")
    fi = out["f3_impact"]
    tot = out["sites_total"]
    p(f"   MUST lockstep (confirm/choice on a blocking window): {fi['must_lockstep_confirm_or_choice']}"
      f"  ({100*fi['must_lockstep_confirm_or_choice']/tot:.1f}%)")
    p(f"   FREE  timed/button-inhibited [TIME]:                 {fi['free_timed_or_buttoninhibited']}"
      f"  ({100*fi['free_timed_or_buttoninhibited']/tot:.1f}%)")
    p(f"   FREE  script-closed / replaced / fire-forget:        {fi['free_script_closed_or_replaced']}"
      f"  ({100*fi['free_script_closed_or_replaced']/tot:.1f}%)")
    p("=" * 78)


if __name__ == "__main__":
    main()
