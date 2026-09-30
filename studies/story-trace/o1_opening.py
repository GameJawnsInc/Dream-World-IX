"""THE STORY-WRITE TRACE, O1 -- THE OPENING: New Game to Alexandria, stock Prima Vista against its verbatim whole-zone
fork, on the game's own route, both sides played by one driver (studies/story-trace/PLAN.md, "O1").

    py tools/play.py studies/story-trace/o1_opening.py --label story-o1 --timeout 240
    py studies/story-trace/o1_opening.py --offline-check           # the build against its donors, the keys against the bytes
    py studies/story-trace/o1_opening.py --preflight               # the live install (read-only)
    py studies/story-trace/o1_opening.py --analyse <run dir>       # the analysis alone, on saved traces
    py studies/story-trace/o1_opening.py --freeze                  # write o1_predictions_v1.json (once, before any run)

THE SIDES (o1_forks.json; the chain deployed to FF9CustomMap 31200-31219, ONE RELAUNCH before the session):
  S  stock: the install's scripts. Start: 50 (Prima Vista, the Cargo Room).
  F  `import-chain 50 --verbatim --whole-zone --fresh-ids --id-base 31200 --name-prefix O1`: the tshp zone's 20
     fields. Start: 31200 (its 50). Field 100 (alxt) is no member, so member(52)'s `Field(100)` is a seam into the
     real game: the segment's end on both sides.

THE ENTRY: New Game, trace on, then in field 70 a raw `warp <start> 0 -1` (rung 3's start). The New-Game override is
left alone; the warp skips FMV001 and field 70's two post-FMV writes on both sides alike.

THE ROUTE (:func:`drive`, one driver for both sides). It acts only on what the game shows, first match wins:
  field 100 -> the end; the naming screen -> accept_name(); a battle -> fight() (it closes the tutorial screen,
  attacks, and leaves the result screen); a READY choice -> the frozen rule table (by option text) or VOID; a dialogue
  page -> Confirm; control held in 50 before the candle -> route to the candle and interact; control held anywhere
  else -> VOID. Optional pickups are never taken.

THE SESSION: one launch, S F S F S F; a side short of min_covered covered runs re-runs (S first), at most rerun.max.
Each run's trace and log are saved as it ends, the session record rewritten after every run. The shared install is
fingerprinted around every run: a run begun on a changed install is skipped, one the install changed under is never
read (both VOID).

THE ANALYSIS (:func:`analyse`): each covered run is cut at its first row in the end field, digested
(storytrace.digest, the fork side with its members) and compared (storytrace.compare). The checks and the verdict
read the predictions the session recorded, and nowhere else.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
import traceback
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "ff9mapkit"))
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(HERE))

from ff9mapkit import storytrace as T                                   # noqa: E402

#: v1 (sha 49fd880f) walked to the candle region's CENTRE, which is the table: session story-o1 run 1 stood in the
#: region with the "?" up, pressed against the table (the owner, watching), and went VOID. v2 walks to that spot.
#: v2 (sha 681398ac) matched the candle choice on "Light the candle": the agent publishes that first choice line as
#: "ight the candle" (the line after [CHOO][MOVE=18,0] loses its first character) -- session story-o1b run 1 VOID.
#: v3 (sha 05fb803e) counted the battle won only at result 1: scene 336 ends by script (RunBattleCode) and the engine
#: reports 2, "victory-no-pose" -- session story-o1c run 1, which reached 100 with every beat. v4 counts 1 or 2.
PREDICTIONS = HERE / "o1_predictions_v4.json"
MANIFEST = HERE / "o1_forks.json"
SESSION_FILE = "o1_session.json"
CHAIN_DIR = Path(r"C:\gd\_ns_playtest\o1\fork")
BUILD_DIR = Path(r"C:\gd\_ns_playtest\o1\build")
SIDES = ("S", "F")
THROWS = {"NullReferenceException", "InvalidCastException", "IndexOutOfRangeException", "DivideByZeroException",
          "ArgumentOutOfRangeException", "KeyNotFoundException"}
WHERE = ("EventEngine", "EBin", "StoryTrace", "HarnessAgent")


# ======================================================================== the predictions
def chain_from_campaign(campaign: Path = CHAIN_DIR / "campaign.toml") -> tuple:
    """``({fork id: donor}, {fork id: member name})`` of the built chain."""
    import tomllib
    d = tomllib.loads(Path(campaign).read_text(encoding="utf-8"))
    return ({int(f["id"]): int(f["source"]) for f in d["field"]}, {int(f["id"]): f["name"] for f in d["field"]})


def draft_predictions() -> dict:
    """The registered claims. Every number here was read off the stock bytes (the --offline-check re-derives each
    one) or the chain's campaign.toml; nothing is read from a run."""
    members, names = chain_from_campaign()
    key = lambda donor, sid, tag, ip, off, target, value, what: {                     # noqa: E731
        "donor": donor, "m": T.FIELD_MODE, "src": "eb", "sid": sid, "tag": tag, "ip": ip, "off": off,
        "target": target, "value": value, "what": what}
    return {
        "version": 4,
        "what": "O1: New Game -> 50 -> 52 -> Field(100), stock vs the tshp zone's verbatim fork (PLAN.md, O1)",
        "supersedes": "v3 (05fb803e): it counted only result 1 as a won battle, and scene 336 ends at 2 (story-o1c "
                      "VOID); v2 (681398ac): its candle rule missed the published 'ight the candle' (story-o1b VOID); "
                      "v1 (49fd880f): its candle point was the region's centre, the table (story-o1 VOID)",
        "order": ["S", "F", "S", "F", "S", "F"],
        "min_covered": 2,
        "rerun": {"max": 2},
        "budget": {"run_s": 720, "run_min_s": 540, "session_s": 7200, "settle_s": 1.0},
        "start": {"S": 50, "F": 31200},
        "entrance": 0,
        "end_field": 100,
        "stock_fields": [50, 52, 100],
        "members": {str(f): d for f, d in sorted(members.items())},
        "names": {str(f): n for f, n in sorted(names.items())},
        # the candle: regions e4-e7 of 50, four triangles meeting at (0, 350) -- where the table stands -- spanning
        # x -300..300, z 120..650. This point is where session story-o1's run 1 stood with the "?" up, right of the
        # table; a Confirm there opens "Light the candle / Cancel".
        "candle": {"donor": 50, "x": 180.0, "z": 290.0, "tolerance": 45.0},
        # a READY choice is answered by the first rule whose `match` is a substring of any option line
        "choices": [
            {"donor": 50, "match": "the candle", "pick": "the candle", "beat": "candle"},   # published: "ight the candle"
            {"donor": 52, "match": "Garnet", "pick": "Garnet", "beat": "garnet"},
            {"donor": None, "match": "want to skip", "pick": "default", "beat": None},   # the skip-movie window
        ],
        # O1-LADDER: every covered run of both sides writes each of these, in donor terms (WriteKey)
        "ladder": [
            key(50, 17, 1, 1804, 1249, "Global.UInt16[0]", 1000, "SC 0 -> 1000, before control in 50"),
            key(50, 17, 1, 3240, 2685, "Global.Byte[6]", 1, "Byte[6] |= 1, after the naming screen"),
            key(50, 15, 1, 635, 536, "Global.Int16[2]", 100, "FieldEntrance := 100, 50's exit to 52"),
            key(52, 3, 1, 1249, 1140, "Global.Int16[2]", 102, "FieldEntrance := 102, 52's exit to 100"),
        ],
        "sc_writes": 1,              # SC (field rows, Global.UInt16[0]) is written exactly once in a covered run
        # registered noise: never a STOCK ONLY / FORK ONLY / UNSTABLE finding. Scene 336's AI (not a field row).
        "noise": [
            {"not_m": T.FIELD_MODE, "target": "Global.Byte[206]", "why": "the Masked Man AI's random wait"},
            {"not_m": T.FIELD_MODE, "target": "Global.Byte[199]", "why": "set only if a member carries status 512"},
        ],
        "beats": ["candle", "named", "battle", "garnet"],
        # the battle beat is done at a WIN: 1 victory, 2 victory-no-pose (the scripted end, RunBattleCode)
        "battle_won": [1, 2],
    }


def load_predictions(path: Path = PREDICTIONS) -> tuple:
    data = Path(path).read_bytes()
    return json.loads(data), hashlib.sha256(data).hexdigest()


def freeze(path: Path = PREDICTIONS) -> str:
    """Write the predictions ONCE (LF, sorted keys); refuses to overwrite a frozen file."""
    if Path(path).exists():
        raise SystemExit(f"!! {path} exists: the predictions are frozen. A new version is a new file.")
    text = json.dumps(draft_predictions(), indent=1, sort_keys=True) + "\n"
    Path(path).write_bytes(text.encode("utf-8"))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def members_of(pred: dict) -> dict:
    return {int(f): int(d) for f, d in pred["members"].items()}


def wkey(k: dict) -> T.WriteKey:
    return T.WriteKey(k["donor"], k["m"], k["src"], k["sid"], k["tag"], k["off"], k["target"], k["value"])


def is_noise(k: T.WriteKey, pred: dict) -> bool:
    return any(k.m != n["not_m"] and k.target == n["target"] for n in pred["noise"])


# ======================================================================== offline: the build and the keys
def _stock_lang(game=None):
    from ff9mapkit.extract import EventBundle
    bundles: dict = {}

    def get(fid: int, lang: str) -> bytes | None:
        if lang not in bundles:
            bundles[lang] = EventBundle(game, lang=lang)
        return bundles[lang].eb_for_id(fid)
    return get


def build_check(pred: dict, build: Path = BUILD_DIR, stock_lang=None) -> tuple:
    """O1-BUILD: every member's built US .eb IS its donor's stock US .eb with only the in-chain ``Field()``
    literals remapped (content.verbatim.remap_fields over the chain's donor -> fork map), and every other
    language's file is that same US build -- what the kit ships (content/verbatim.py:65) and what the trace runs.
    That the kit ships US bytecode where a donor's own language differs is a separate, known kit gap, not O1's
    (the stock JP scripts of 50 and 52 differ in code; the census: studies/eb-roundtrip/FINDINGS.md)."""
    from ff9mapkit.config import LANGS, ModLayout
    from ff9mapkit.content.verbatim import remap_fields
    stock_lang = stock_lang or _stock_lang()
    members, names = members_of(pred), {int(f): n for f, n in pred["names"].items()}
    retarget = {d: f for f, d in members.items()}
    lay, bad, n = ModLayout(build), [], 0
    for fid, donor in sorted(members.items()):
        paths = {L: lay.eb_path(L, f"EVT_{names[fid]}.eb.bytes") for L in LANGS}
        src = stock_lang(donor, "us")
        if src is None or not all(p.is_file() for p in paths.values()):
            bad.append(f"{fid}: {'no stock donor' if src is None else 'a language file missing'}")
            continue
        us = paths["us"].read_bytes()
        if us != remap_fields(src, retarget):
            bad.append(f"{fid} ({donor}) us: not the donor with only its Field() literals remapped")
        other = [L for L in LANGS if paths[L].read_bytes() != us]
        if other:
            bad.append(f"{fid}: {other} differ from its us build")
        n += len(LANGS)
    return (not bad, "O1-BUILD: every member's US .eb is its donor's with only in-chain Field() literals remapped, "
                     "and each other language ships that same build", "; ".join(bad[:6]) or f"{n} files")


def keys_check(pred: dict, stock) -> tuple:
    """O1-KEYS: each ladder key's (sid, tag, ip) is a verified store of its variable in the donor's stock bytes,
    at function offset ``off``; its value is the instruction's constant (read by hand from eb-src, recorded)."""
    bad = []
    for k in pred["ladder"]:
        width, byte = k["target"].split(".", 1)[1].rstrip("]").split("[")
        row = T.Row(k="w", f=0, p=0, m=k["m"], fld=k["donor"], don=k["donor"], sc=0, src="eb", sid=k["sid"], uid=0,
                    lvl=0, ip=k["ip"], tag=k["tag"], add=0, byte=int(byte), width=width, bit=-1, old=0,
                    new=k["value"], same=0)
        idx = stock(k["donor"])
        j = idx.join(row) if idx is not None else None
        if j is None or j.status != "store" or j.tag != k["tag"] or j.rel != k["off"]:
            bad.append(f"{k['what']}: {None if j is None else (j.status, j.tag, j.rel, j.reason)}")
    return (not bad, "O1-KEYS: every ladder key is a store of its variable at its ip in the donor's stock bytes",
            "; ".join(bad) or f"{len(pred['ladder'])} keys")


def offline_check(pred: dict, build: Path = BUILD_DIR) -> list:
    stock = T.stock_script_source()
    return [build_check(pred, build), keys_check(pred, stock)]


# ======================================================================== the live install (read-only)
def _roots():
    import dali_tour as D
    return D.mod_roots()


def preflight(pred: dict, roots: list, build: Path = BUILD_DIR, manifest: Path = MANIFEST) -> list:
    """What must hold before the session spends an hour: ``[(ok, what, detail)]``."""
    from ff9mapkit import extract
    from ff9mapkit.config import LANGS, ModLayout
    from ff9mapkit.scene.bgi import BgiWalkmesh
    from rung3_trace import _deployed_walkmesh, _fork_donor_rows
    out = []
    members, names = members_of(pred), {int(f): n for f, n in pred["names"].items()}
    try:
        man = json.loads(Path(manifest).read_text(encoding="utf-8"))
        got = {int(f): int(d) for f, d in man["members"].items()}
        ok = got == members and man.get("deployed") is True
        out.append((ok, "P-MANIFEST: the frozen members are the deployed chain's (o1_forks.json, deployed)",
                    f"{len(members)} members" if ok else f"manifest {got}, deployed {man.get('deployed')}"))
    except (OSError, KeyError, ValueError) as err:
        out.append((False, "P-MANIFEST: the frozen members are the deployed chain's (o1_forks.json, deployed)",
                    f"unreadable: {err}"))
    regs = [(Path(r), T.mod_registrations(r)) for r in roots]
    rows = [(Path(r), f, d) for r in roots for f, d in _fork_donor_rows(Path(r))]
    bad = []
    for fid, donor in sorted(members.items()):
        hits = [(r.name, reg[fid]) for r, reg in regs if fid in reg]
        if len(hits) != 1 or hits[0][1] != names[fid]:
            bad.append(f"{fid}: registered {hits}, want once as {names[fid]}")
        fdp = [d for _r, f, d in rows if f == fid]
        if fdp != [donor]:
            bad.append(f"{fid}: ForkDonorPatch {fdp}, want [{donor}]")
    out.append((not bad, "P-DEPLOY: every member registered once under its name, and mapped once to its donor",
                "; ".join(bad[:6]) or f"{len(members)} members"))
    lay, bad = ModLayout(build), []
    for fid in sorted(members):
        want = {L: lay.eb_path(L, f"EVT_{names[fid]}.eb.bytes").read_bytes() for L in LANGS}
        live = [r for r in roots if fid in T.mod_registrations(r)]
        for L in LANGS:
            p = ModLayout(Path(live[0])).eb_path(L, f"EVT_{names[fid]}.eb.bytes") if live else None
            if p is None or not p.is_file() or p.read_bytes() != want[L]:
                bad.append(f"{fid} {L}")
    out.append((not bad, "P-EB: every member's live .eb (7 languages) is the offline-checked build's",
                ("differs: " + ", ".join(bad[:8])) if bad else f"{len(members)} x {len(LANGS)} files"))
    bad = []
    for fid, donor in sorted(members.items()):
        mine = [b for b in (_deployed_walkmesh(Path(r), fid) for r in roots) if b is not None]
        if len(mine) != 1:
            bad.append(f"{fid}: {len(mine)} deployed walkmeshes")
        elif BgiWalkmesh.from_bytes(mine[0]).to_bytes() != extract.stock_walkmesh(donor).to_bytes():
            bad.append(f"{fid}: not donor {donor}'s walkmesh")
    out.append((not bad, "P-FLOOR: every member's deployed walkmesh is its donor's",
                "; ".join(bad[:6]) or f"{len(members)} members"))
    over = {f: [r.name for r in T.stock_overrides(f, roots)] for f in pred["stock_fields"]}
    over = {f: v for f, v in over.items() if v}
    out.append((not over, "P-STOCK: no mod folder overrides stock 50, 52 or 100", str(over) if over else "none"))
    return out


def fingerprint(roots: list, pred: dict) -> dict:
    """What the runs rely on in the SHARED install, JSON-shaped (two reads compare with ==)."""
    from rung3_trace import _deployed_walkmesh, _fork_donor_rows

    def sha(b) -> str | None:
        return hashlib.sha256(b).hexdigest() if b is not None else None
    fresh = T.mod_script_source(roots)
    regs = [(Path(r).name, T.mod_registrations(r)) for r in roots]
    rows = [(Path(r).name, f, d) for r in roots for f, d in _fork_donor_rows(Path(r))]
    out = {"folders": [Path(r).name for r in roots],
           "stock": {str(f): [r.name for r in T.stock_overrides(f, roots)] for f in pred["stock_fields"]}}
    for fid in sorted(members_of(pred)):
        try:
            idx = fresh(fid)
            eb = sha(idx.data) if idx is not None else None
        except T.TraceError as err:
            eb = f"unreadable: {str(err)[:120]}"
        out[str(fid)] = {"reg": [[n, reg[fid]] for n, reg in regs if fid in reg],
                         "fdp": [[n, d] for n, f, d in rows if f == fid], "eb": eb,
                         "bgi": [sha(b) for b in (_deployed_walkmesh(Path(r), fid) for r in roots) if b is not None]}
    return out


def _changed(before: dict, now: dict) -> str:
    keys = [k for k in sorted(set(before) | set(now)) if before.get(k) != now.get(k)]
    return (f"{len(keys)} changed: " + ", ".join(keys[:8])) if keys else ""


# ======================================================================== the driver
class RouteVoid(Exception):
    """The route met something it has no rule for: the run is VOID (never a finding about the scripts)."""


def pick_for(choice: dict, donor: int, pred: dict) -> tuple:
    """``(absolute option index or "default", the rule)`` for a ready choice, by the frozen rule table; raises
    RouteVoid when no rule matches. ``choice["options"]`` is ``[prompt, *shown lines]``; ``active`` the absolute
    index of each shown line."""
    lines = list(choice.get("options") or [])[1:]
    active = list(choice.get("active") or range(len(lines)))
    for rule in pred["choices"]:
        if rule["donor"] not in (None, donor):
            continue
        if not any(rule["match"] in ln for ln in [choice.get("options", [""])[0], *lines]):
            continue
        if rule["pick"] == "default":
            return "default", rule
        hits = [active[i] for i, ln in enumerate(lines) if rule["pick"] in ln]
        if len(hits) != 1:
            raise RouteVoid(f"choice in {donor}: rule {rule['match']!r} picks {rule['pick']!r}, which is on "
                            f"{len(hits)} lines of {lines}")
        return hits[0], rule
    raise RouteVoid(f"choice in {donor} with no rule: {choice.get('options')}")


def drive(g, pred: dict, side: str, log: list, *, deadline: float, floor_for=None, prior_for=None,
          progress: dict | None = None) -> dict:
    """Play the segment from the start field to the end field. Returns the run's outcome:
    ``{"end": "reached" | "void", "why", "beats", "pages", "choices", "t"}``. ``floor_for(donor)`` / ``prior_for(donor)``
    give the candle walk its walkmesh and movement prior (default: the donor's stock walkmesh as the player walks it,
    and :meth:`key_prior` of the donor -- a member's own are its donor's, P-FLOOR). ``progress`` (a dict) is filled
    with the live beats/pages/choices, so a run that raises still says how far it got."""
    from harness import HarnessError
    from ff9mapkit import extract
    from ff9mapkit.content import pathfind
    floor_for = floor_for or (lambda d: pathfind.PlayerWalkmesh(extract.stock_walkmesh(d)))
    prior_for = prior_for or g.key_prior
    members = members_of(pred) if side == "F" else {}
    beats = {"candle": False, "named": False, "battle": None, "garnet": False}
    pages: list = []
    taken: list = []
    overlays: list = []
    tries = {"candle": 0}
    held = {"n": 0, "at": None}
    settle_polls = max(1, int(pred["budget"]["settle_s"] / 0.05))
    t0 = time.time()
    if progress is not None:
        progress.update(beats=beats, pages=pages, choices=taken)

    def out(end: str, why: str) -> dict:
        return {"end": end, "why": why, "beats": beats, "pages": pages, "choices": taken,
                "t": round(time.time() - t0, 1)}

    while time.time() < deadline:
        st = g.state
        fid = st.field_id
        donor = members.get(fid, fid)
        if fid == pred["end_field"]:
            log.append({"k": "end", "field": fid, "t": round(time.time() - t0, 1)})
            return out("reached", f"field {fid}")
        if st.ui_state == "NameSetting":
            g.accept_name()
            beats["named"] = True
            log.append({"k": "named", "field": fid})
            continue
        if st.ui_state == "Tutorial" and not st.in_battle:
            g._dismiss_tutorial()
            continue
        if st.in_battle:
            result = g.fight(timeout=max(30.0, deadline - time.time()), finish=True)
            beats["battle"] = result
            log.append({"k": "battle", "field": fid, "result": result, "turns": (g.last_fight or {}).get("turns")})
            continue
        if st.choice is not None:
            held["n"] = 0
            if not g._choice_ready(st):
                time.sleep(0.05)
                continue
            snap = json.dumps(st.choice, sort_keys=True)
            if held["at"] is None or held["at"][0] != snap:
                held["at"] = (snap, time.time(), st.frame)
                time.sleep(0.05)
                continue
            if time.time() - held["at"][1] < pred["budget"]["settle_s"] or st.frame <= held["at"][2]:
                time.sleep(0.05)
                continue
            held["at"] = None
            index, rule = pick_for(st.choice, donor, pred)
            if index == "default":
                took = g._take_default_choice(st)
                taken.append({"field": fid, "donor": donor, "options": st.choice.get("options"), "index": "default",
                              "took": took})
            else:
                g.choose(index)
                taken.append({"field": fid, "donor": donor, "options": st.choice.get("options"), "index": index})
                if rule.get("beat"):
                    beats[rule["beat"]] = True
            log.append({"k": "choice", **taken[-1]})
            continue
        if st.dialog_open and st.text.strip() and not st.control:
            # a page the script waits on (control withheld). A window up WHILE he has control is an overlay hint
            # (50's "Press the X button when the ? appears.", async, closed by the script): never paged.
            held["n"] = 0
            if not pages or pages[-1] != st.text:
                pages.append(st.text)
            g.press("confirm", 3)
            g.wait_frames(g.rate().frames_for_ticks(g.CUTSCENE_PAGE_TICKS))
            continue
        if st.control and st.player_x is not None and not st.fading:
            if st.dialog_open and st.text.strip() and st.text not in overlays:
                overlays.append(st.text)
                log.append({"k": "overlay", "field": fid, "text": st.text})
            held["n"] += 1
            if held["n"] < settle_polls:
                time.sleep(0.05)
                continue
            held["n"] = 0
            c = pred["candle"]
            if donor == c["donor"] and not beats["candle"]:
                tries["candle"] += 1
                if tries["candle"] > 2:
                    raise RouteVoid(f"two candle attempts opened no choice (at {g.state.player_x}, {g.state.player_z})")
                rec = g.route_to(c["x"], c["z"], walkmesh=floor_for(donor), prior=prior_for(donor),
                                 tolerance=c.get("tolerance", 45.0), timeout=60.0, unstick=True, smooth=True, npcs=True,
                                 overlay_ok=True)
                # a plain Confirm: interact() refuses to press while a window is up, and the region's own hint is
                # up exactly while he stands where the Confirm works
                g.press("confirm", 4)
                try:
                    g.wait_for(lambda s: s.choice is not None, timeout=4.0, what="the candle's choice")
                    opened = True
                except HarnessError:
                    opened = False
                log.append({"k": "candle", "field": fid, "reached": rec.get("reached"), "try": tries["candle"],
                            "at": [g.state.player_x, g.state.player_z], "opened": opened})
                continue
            raise RouteVoid(f"control held in {fid} (donor {donor}) where the route never gives it")
        held["n"] = 0
        time.sleep(0.05)
    raise HarnessError(f"the run's budget ran out in field {g.state.field_id}")


def end_run(g, log: list) -> None:
    """Back to the title after a run. Field 100 opens Vivi's naming screen, inside which the soft reset is
    swallowed: accept it first when it is up."""
    from harness import HarnessError
    ok, why = g.restore_baseline()
    if not ok and g.state.ui_state == "NameSetting":
        g.accept_name()
        log.append({"k": "end-naming"})
        ok, why = g.restore_baseline()
    if not ok:
        raise HarnessError(f"the title could not be restored: {why}")


# ======================================================================== the session
def run(g) -> None:
    from harness import HarnessError

    cap = g.state.storytrace
    if not g.check(isinstance(cap, dict) and cap.get("proto") == T.PROTO,
                   "P-CAP: the engine advertises the story trace at proto 1", str(cap)):
        return
    pred, sha = load_predictions()
    b = pred["budget"]
    roots = _roots()
    pre = preflight(pred, roots)
    for ok, what, detail in pre:
        g.check(ok, what, detail)
    if not all(ok for ok, _w, _d in pre):
        return
    fp0 = fingerprint(roots, pred)
    ran = T.mod_script_source(roots)
    scripts = g.run_dir / "scripts"
    scripts.mkdir(exist_ok=True)
    for fid in sorted(members_of(pred)):
        (scripts / f"{fid}.eb").write_bytes(ran(fid).data)
    session = {"label": g.run_dir.name, "predictions": str(PREDICTIONS), "predictions_sha256": sha,
               "predictions_version": pred["version"], "order": pred["order"], "budget": b,
               "preflight": [[ok, what, detail] for ok, what, detail in pre],
               "started": time.strftime("%Y-%m-%dT%H:%M:%S"), "install": fp0, "runs": []}

    def save() -> None:
        (g.run_dir / SESSION_FILE).write_text(json.dumps(session, indent=1), encoding="utf-8")

    save()
    mark = g.log_mark()
    t0 = time.time()
    deadline = t0 + b["session_s"]

    def one(i: int, side: str, rerun: bool = False) -> None:
        trace_name, log_name = f"run{i}_{side}.jsonl", f"run{i}_{side}_log.json"
        rec = {"i": i, "side": side, "start": pred["start"][side], "trace": trace_name, "log": log_name}
        if rerun:
            rec["rerun"] = True
        if time.time() + b["run_min_s"] > deadline:
            rec["skipped"] = f"session budget: under {b['run_min_s']}s left"
        else:
            moved = _changed(fp0, fingerprint(roots, pred))
            if moved:
                rec["install"] = "before the run: " + moved
        if rec.get("skipped") or rec.get("install"):
            session["runs"].append(rec)
            save()
            return
        log: list = []
        progress: dict = {}
        outcome = {"end": "void", "why": "not driven"}
        smark = None
        rec["t0"] = round(time.time() - t0)
        g.shot_prefix = f"run{i}-{side}"
        try:
            if i > 1:
                end_run(g, log)
            g.newgame()
            g.wait_frames(30)
            smark = g.story_mark()
            g.storytrace(True)
            g._check_field_id(pred["start"][side], "warp", True)
            g.send(f"warp {pred['start'][side]} {pred['entrance']} -1")
            g.wait_for(lambda s: s.field_id == pred["start"][side], timeout=60.0,
                       what=f"field {pred['start'][side]} to load")
            outcome = drive(g, pred, side, log, deadline=min(deadline, time.time() + b["run_s"]),
                            progress=progress)
        except RouteVoid as err:
            outcome = {"end": "void", "why": f"route: {err}"}
        except HarnessError as err:
            outcome = {"end": "void", "why": f"STOPPED: {str(err)[:300]}"}
        except Exception as err:                  # noqa: BLE001 -- one run's bug must not cost the others
            outcome = {"end": "void", "why": f"STOPPED (unexpected): {type(err).__name__}: {str(err)[:300]}"}
            log.append({"k": "error", "traceback": traceback.format_exc()[-3000:]})
        finally:
            g.shot_prefix = ""
            for k, v in progress.items():              # how far a run that raised got
                outcome.setdefault(k, v)
            if smark is not None:
                try:
                    rec["traced"] = g.collect_story(g.run_dir / trace_name, smark)
                except HarnessError as err:
                    rec["trace_error"] = str(err)[:300]
            rec.update(end=outcome.get("end"), why=outcome.get("why"), beats=outcome.get("beats"),
                       t1=round(time.time() - t0))
            moved = _changed(fp0, fingerprint(roots, pred))
            if moved:
                rec["install"] = "during the run: " + moved
            (g.run_dir / log_name).write_text(json.dumps({"outcome": outcome, "log": log}, indent=1), encoding="utf-8")
            session["runs"].append(rec)
            save()
            print(f"[o1] run {i} ({side}) at {rec['t1']}s: {rec['end']} -- {rec['why']}", flush=True)

    for i, side in enumerate(pred["order"], 1):
        one(i, side)
    reruns = 0
    while reruns < pred["rerun"]["max"]:
        short = [s for s in SIDES if sum(1 for r in read_session(g.run_dir, pred, session=session)
                                         if r["side"] == s and r["covered"]) < pred["min_covered"]]
        if not short or time.time() + b["run_min_s"] > deadline:
            break
        reruns += 1
        one(len(session["runs"]) + 1, short[0], rerun=True)
    session["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    save()
    try:
        g.restore_baseline()
    except HarnessError:
        pass
    checks, report = analyse(g.run_dir)
    (g.run_dir / "o1_report.txt").write_text(report, encoding="utf-8")
    print(report[:6000], flush=True)
    for ok, what, detail in checks:
        g.check(ok is True, what, ("VOID -- " if ok is None else "") + detail)
    ours = [e for e in g.exceptions_since(mark) if e.name in THROWS
            and (not e.trace or any(k in fr for fr in e.trace for k in WHERE))]
    g.check(not ours, "O1-THROW: nothing thrown through the event engine, the evaluator, the tracer or the agent",
            str([(e.name, e.where) for e in ours[:5]]) if ours else "none")


# ======================================================================== reading a session (pure, offline)
def cut_at_end(rows: list, end_field: int) -> tuple:
    """``(the run up to its first write in the end field, that row's line or None)``. Kept after the cut: the epoch
    rows (so the run still reads closed) and the epoch's closing ``c`` counts of every site OUTSIDE the end field
    (a site is per field, so none of those was written after the cut)."""
    at = next((r.line for r in rows if r.k in ("w", "r") and r.fld == end_field), None)
    if at is None:
        return rows, None
    return [r for r in rows if r.line < at or r.k == "e" or (r.k == "c" and r.fld != end_field)], at


def read_session(run_dir, pred: dict, *, session: dict | None = None, stock=None) -> list:
    """Every recorded run, read: ``[{i, side, rec, rows, cut, digest, covered, why_void}]``. A run is COVERED only
    when its drive reached the end field with every beat done, its trace closed whole, and the install held."""
    run_dir = Path(run_dir)
    session = session or json.loads((run_dir / SESSION_FILE).read_text(encoding="utf-8"))
    stock = stock or T.stock_script_source()
    members = members_of(pred)
    saved = {f: T.ScriptIndex((run_dir / "scripts" / f"{f}.eb").read_bytes(), field_id=f, label=f"member {f}")
             for f in members if (run_dir / "scripts" / f"{f}.eb").is_file()}
    fork_scripts = lambda fid: saved.get(fid) or stock(fid)                          # noqa: E731
    out = []
    for rec in session["runs"]:
        why = []
        r = {"i": rec["i"], "side": rec["side"], "rec": rec, "rows": [], "cut": None, "digest": None}
        if rec.get("skipped"):
            why.append(f"not run: {rec['skipped']}")
        if rec.get("install"):
            why.append(f"install changed {rec['install']}")
        if rec.get("end") != "reached":
            why.append(f"the drive did not reach the end: {rec.get('why')}")
        beats = rec.get("beats") or {}
        missed = [b for b in pred["beats"] if not (beats.get(b) in pred["battle_won"] if b == "battle" else beats.get(b))]
        if rec.get("end") == "reached" and missed:
            why.append(f"beats not done: {missed} (battle result {beats.get('battle')})")
        path = run_dir / rec.get("trace", "")
        if not rec.get("skipped") and path.is_file():
            try:
                rows, cut = cut_at_end(T.read_trace(path), pred["end_field"])
                r["rows"], r["cut"] = rows, cut
                d = T.digest(f"{rec['side']}#{rec['i']}", rows, scripts=fork_scripts if rec["side"] == "F" else stock,
                             donor_scripts=stock, members=members if rec["side"] == "F" else None)
                r["digest"] = d
                if d.incomplete:
                    why.append(f"trace incomplete: {d.incomplete[:120]}")
            except T.TraceError as err:
                why.append(f"trace unreadable: {str(err)[:200]}")
        elif not rec.get("skipped"):
            why.append("no trace file")
        r["why_void"], r["covered"] = why, not why
        out.append(r)
    return out


def _show(keys, n: int = 6) -> str:
    ks = sorted(keys, key=T.WriteKey.sort_key)
    s = [f"{k.donor} m{k.m} e{k.sid} t{k.tag} {k.off:+d} {k.target}={k.value}" for k in ks[:n]]
    return "; ".join(s) + (f" (+{len(ks) - n} more)" if len(ks) > n else "")


def judge(runs: list, pred: dict, *, frozen: tuple) -> list:
    """The registered checks over the read runs: ``[(True | False | None, what, detail)]`` -- None = VOID."""
    checks = [frozen]
    cov = {s: [r for r in runs if r["side"] == s and r["covered"]] for s in SIDES}
    enough = all(len(cov[s]) >= pred["min_covered"] for s in SIDES)
    checks.append((enough if enough else None, f"O1-COVER: at least {pred['min_covered']} covered runs a side",
                   ", ".join(f"{s} {len(cov[s])} of {sum(1 for r in runs if r['side'] == s)}" for s in SIDES)
                   + "".join(f"; {r['side']}#{r['i']} VOID: {'; '.join(r['why_void'])[:160]}"
                             for r in runs if not r["covered"])))
    if not enough:
        for what in ("O1-LADDER", "O1-NULL", "O1-STABLE", "O1-JOIN"):
            checks.append((None, what, "too few covered runs"))
        return checks
    covered = cov["S"] + cov["F"]
    bad = []
    for r in covered:
        keys = set(r["digest"].keys)
        for k in pred["ladder"]:
            if wkey(k) not in keys:
                bad.append(f"{r['side']}#{r['i']} lacks {k['what']}")
        sc = [x for x in r["rows"] if x.k == "w" and x.m == T.FIELD_MODE and x.target == "Global.UInt16[0]"]
        if len(sc) != pred["sc_writes"]:
            bad.append(f"{r['side']}#{r['i']} wrote SC {len(sc)} times")
    checks.append((not bad, "O1-LADDER: every covered run writes the four ladder keys, and SC exactly once",
                   "; ".join(bad[:6]) or f"{len(covered)} runs x {len(pred['ladder'])} keys"))
    c = T.compare([r["digest"] for r in cov["S"]], [r["digest"] for r in cov["F"]], members=members_of(pred))
    so = [k for k in c.stock_only if not is_noise(k, pred)]
    fo = [k for k in c.fork_only if not is_noise(k, pred)]
    checks.append((not so and not fo, "O1-NULL: STOCK ONLY and FORK ONLY are empty outside the registered noise",
                   f"STOCK ONLY {len(so)}: {_show(so)} / FORK ONLY {len(fo)}: {_show(fo)}" if so or fo
                   else f"{len(c.matched)} keys matched; noise set aside: "
                        f"{len(c.stock_only) - len(so)} stock-only, {len(c.fork_only) - len(fo)} fork-only"))
    un = [k for k in c.unstable if not is_noise(k, pred)]
    checks.append((not un, "O1-STABLE: no key outside the registered noise is written in some runs of a side and "
                           "not others", f"{len(un)}: {_show(un)}" if un else
                   f"{len(c.unstable)} unstable, all registered noise"))
    fails = [(r["side"], r["i"], len(r["digest"].failures)) for r in covered if r["digest"].failures]
    checks.append((not fails, "O1-JOIN: every script row joins a store in the bytes its field ran",
                   str(fails) if fails else f"{sum(len(r['rows']) for r in covered)} rows, 0 failures"))
    return checks


def verdict(checks: list) -> str:
    fails = [w.split(":")[0] for ok, w, _d in checks if ok is False]
    voids = [w.split(":")[0] for ok, w, _d in checks if ok is None]
    if fails:
        return "NOT PROVEN: " + ", ".join(fails)
    if voids:
        return "VOID: " + ", ".join(voids)
    return "PROVEN"


def analyse(run_dir, *, pred_path: Path | None = None, stock=None) -> tuple:
    """``(checks, report text)`` for a session directory, against the predictions the session recorded."""
    run_dir = Path(run_dir)
    session = json.loads((run_dir / SESSION_FILE).read_text(encoding="utf-8"))
    path = Path(pred_path or session["predictions"])
    pred, sha = load_predictions(path)
    frozen = (sha == session["predictions_sha256"],
              "O1-FROZEN: the predictions are the file the session recorded, unchanged",
              f"{path.name} sha {sha[:8]}" + ("" if sha == session["predictions_sha256"]
                                               else f", recorded {session['predictions_sha256'][:8]}"))
    runs = read_session(run_dir, pred, session=session, stock=stock)
    checks = judge(runs, pred, frozen=frozen)
    lines = [f"O1 -- {session['label']}  (predictions v{pred['version']} {sha[:8]})", "",
             f"VERDICT: {verdict(checks)}", ""]
    for ok, what, detail in checks:
        lines.append(f"{'PASS' if ok is True else 'FAIL' if ok is False else 'VOID'}  {what}\n      {detail}")
    lines.append("")
    for r in runs:
        rec = r["rec"]
        lines.append(f"run {r['i']} {r['side']}: {'covered' if r['covered'] else 'VOID'} -- {rec.get('why')}; beats "
                     f"{rec.get('beats')}; {len(r['rows'])} rows, cut at line {r['cut']}")
    cov = {s: [r["digest"] for r in runs if r["side"] == s and r["covered"]] for s in SIDES}
    if cov["S"] and cov["F"]:
        lines += ["", T.report(T.compare(cov["S"], cov["F"], members=members_of(pred)), title="O1 stock vs fork")]
    # report-only: each covered fork run's dialogue beside the first covered stock run's
    logs = {r["i"]: json.loads((run_dir / r["rec"]["log"]).read_text(encoding="utf-8"))
            for r in runs if r["covered"] and (run_dir / r["rec"].get("log", "")).is_file()}
    s0 = next((logs[r["i"]]["outcome"]["pages"] for r in runs if r["side"] == "S" and r["i"] in logs), None)
    for r in runs:
        if r["side"] == "F" and r["i"] in logs and s0 is not None:
            same = logs[r["i"]]["outcome"]["pages"] == s0
            lines.append(f"report: F#{r['i']} dialogue {'==' if same else '!='} the first covered stock run's "
                         f"({len(logs[r['i']]['outcome']['pages'])} vs {len(s0)} pages)")
    return checks, "\n".join(lines) + "\n"


# ======================================================================== CLI
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--offline-check", action="store_true")
    ap.add_argument("--preflight", action="store_true")
    ap.add_argument("--analyse", metavar="RUN_DIR")
    ap.add_argument("--predictions", type=Path)
    ap.add_argument("--freeze", action="store_true")
    args = ap.parse_args(argv)
    if args.freeze:
        print("frozen:", PREDICTIONS.name, freeze())
        return 0
    if args.analyse:
        checks, report = analyse(args.analyse, pred_path=args.predictions)
        print(report)
        return 0 if all(ok is True for ok, _w, _d in checks) else 1
    pred, sha = load_predictions(args.predictions or PREDICTIONS)
    checks = offline_check(pred) if args.offline_check else preflight(pred, _roots()) if args.preflight else None
    if checks is None:
        ap.print_help()
        return 2
    for ok, what, detail in checks:
        print(f"{'PASS' if ok else 'FAIL'}  {what}\n      {detail}")
    return 0 if all(ok for ok, _w, _d in checks) else 1


if __name__ == "__main__":
    sys.exit(main())
