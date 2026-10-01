"""THE STORY-WRITE TRACE's segment engine, shared by O1 and O2 (research/o2_design.md 1.2).

A SEGMENT is one stretch of the story played twice per run pair -- stock (S) against a verbatim fork chain (F) --
by one driver, traced, cut, digested and compared (studies/story-trace/PLAN.md, "O1"). O1's machinery lives here,
moved and parameterised; ``o1_opening`` keeps every public name as a thin wrapper, and the O1 regression gate
(``segment_regress.py``) proves its outputs byte-identical.

The module's PURE helpers come first: the predictions' small readers, the FROZEN place of a row, the strict noise
matcher, the two cuts, the digest's row -> key map and the verdict. Each reads only its arguments (``stock_lang``
and ``chain_from_campaign`` read the install / a campaign file when called).

Then :class:`Segment`, O1's session and analysis as methods, each citing the O1 function it came from: the
predictions' I/O and freeze, the offline build/keys checks, the preflight, the install fingerprint, the session loop
(S F S F S F, re-runs, recovery), cutting, reading, judging and reporting a session, and the CLI. A subclass gives
its constants, its check texts (``titles``), its ``draft`` and ``drive``, and whatever it adds through the
``*_extra`` hooks, ``why_void``, ``all_run_checks`` and ``core_checks``.
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

SIDES = ("S", "F")
#: THROW: the exceptions a session fails on when thrown through the engine's story machinery (``WHERE``).
THROWS = {"NullReferenceException", "InvalidCastException", "IndexOutOfRangeException", "DivideByZeroException",
          "ArgumentOutOfRangeException", "KeyNotFoundException"}
WHERE = ("EventEngine", "EBin", "StoryTrace", "HarnessAgent")
#: Where a run is taken before the soft reset back to the title: the Southern Ring hub, a field that gives control
#: at once (the F-REDEPLOY sessions warped there after New Game).
RECOVERY_FIELD = 4600

#: The eight fields of a ``storytrace.WriteKey`` a full-key noise pattern names, and their JSON types.
KEY_FIELDS = ("donor", "m", "src", "sid", "tag", "off", "target", "value")
_KEY_TYPES = {"donor": int, "m": int, "src": str, "sid": int, "tag": int, "off": int, "target": str, "value": int}
#: The metadata a full-key pattern may carry besides them (never matched on: ``ip``/``op`` are O2-KEYS's).
NOISE_META = ("ip", "op", "why")
#: O1's legacy noise shape: every key of ``target`` whose mode is NOT ``not_m``.
LEGACY_NOISE = frozenset({"not_m", "target", "why"})


# ======================================================================== the predictions' small readers
def members_of(pred: dict) -> dict:
    return {int(f): int(d) for f, d in pred["members"].items()}


def wkey(k: dict) -> T.WriteKey:
    return T.WriteKey(k["donor"], k["m"], k["src"], k["sid"], k["tag"], k["off"], k["target"], k["value"])


def chain_from_campaign(campaign) -> tuple:
    """``({fork id: donor}, {fork id: member name})`` of a built chain (its ``campaign.toml``)."""
    import tomllib
    d = tomllib.loads(Path(campaign).read_text(encoding="utf-8"))
    return ({int(f["id"]): int(f["source"]) for f in d["field"]}, {int(f["id"]): f["name"] for f in d["field"]})


def stock_lang(game=None):
    """``get(field id, lang) -> the stock .eb bytes | None`` over the install's event bundles, one per language."""
    from ff9mapkit.extract import EventBundle
    bundles: dict = {}

    def get(fid: int, lang: str) -> bytes | None:
        if lang not in bundles:
            bundles[lang] = EventBundle(game, lang=lang)
        return bundles[lang].eb_for_id(fid)
    return get


# ======================================================================== places, keys, noise
def place(fld: int, members: dict) -> int:
    """The FROZEN place of a field: a member's donor (by the predictions' members map, never the engine's ``don``),
    else the id itself. The S side passes no members: its place is its field."""
    return members.get(fld, fld)


def _check_pattern(p: dict) -> None:
    """A full-key noise pattern names EXACTLY the eight WriteKey fields, each a plain value of its type, plus at
    most the metadata ``ip``/``op``/``why``: anything else raises, so a typo is an error, never a wider match."""
    unknown = sorted(set(p) - set(KEY_FIELDS) - set(NOISE_META))
    missing = [f for f in KEY_FIELDS if f not in p]
    if unknown or missing:
        raise ValueError(f"noise pattern {p!r}: " + "; ".join(
            ([f"unknown field(s) {unknown}"] if unknown else []) + ([f"missing {missing}"] if missing else []))
            + f" -- a full-key pattern names exactly {', '.join(KEY_FIELDS)} (plus {', '.join(NOISE_META)})")
    for f in KEY_FIELDS:
        v = p[f]
        if isinstance(v, bool) or not isinstance(v, _KEY_TYPES[f]):
            raise ValueError(f"noise pattern {p!r}: {f} is {v!r}, not a plain {_KEY_TYPES[f].__name__} -- noise "
                             f"carries no operators (ranges, lists): only forbidden patterns do")


def key_matches(k: T.WriteKey, pattern: dict) -> bool:
    """Whether key ``k`` is exactly the full-key ``pattern`` (all eight fields equal, and ``k`` aligned). Strict:
    raises on a pattern that is not exactly that shape (4.6)."""
    _check_pattern(pattern)
    return k.aligned and all(getattr(k, f) == pattern[f] for f in KEY_FIELDS)


def is_noise(k: T.WriteKey, pred: dict) -> bool:
    """Whether ``k`` is registered noise. Two shapes, told apart by their key sets: O1's legacy
    ``{not_m, target, why}`` (every key of that target whose mode is not ``not_m`` -- so O1's battle-AI noise never
    covers a FIELD-mode key of the same byte), and the full-key form (:func:`key_matches`). Every pattern is
    checked first, so a malformed one raises even when another matches."""
    legacy = [set(n) == LEGACY_NOISE for n in pred["noise"]]
    for n, old in zip(pred["noise"], legacy):
        if not old:
            _check_pattern(n)
    return any((k.m != n["not_m"] and k.target == n["target"]) if old else key_matches(k, n)
               for n, old in zip(pred["noise"], legacy))


# ======================================================================== the cuts (frozen places)
def cut_at_end(rows: list, end_places, members: dict) -> tuple:
    """``(the run up to its first write in an end place, that row's line or None)``. Kept after the cut: the epoch
    rows (so the run still reads closed) and the epoch's closing ``c`` counts of every site whose place is NOT an
    end place (a site is per field, so none of those was written after the cut). Places are FROZEN
    (:func:`place`); with no member whose donor is an end place, this is O1's field rule exactly."""
    ends = set(end_places)
    at = next((r.line for r in rows if r.k in ("w", "r") and place(r.fld, members) in ends), None)
    if at is None:
        return rows, None
    return [r for r in rows if r.line < at or r.k == "e" or (r.k == "c" and place(r.fld, members) not in ends)], at


def cut_at_start(rows: list, start_place: int, members: dict) -> tuple:
    """``(kept, at, pre)``: the run from its START ROW -- the first ``w`` row whose (frozen) place is
    ``start_place``; never an ``r`` row, so residue landing in the start place cannot become the start and hide
    itself among the kept rows. Every row before it but the epoch rows is cut and returned in ``pre`` (line order),
    and so is each ``c`` row whose site was written only before it (field 70's). ``at`` is None when no ``w`` row
    stands in the start place: then nothing is cut (the caller's "never reached the start field")."""
    at = next((r.line for r in rows if r.k == "w" and place(r.fld, members) == start_place), None)
    if at is None:
        return list(rows), None, []
    before = [r for r in rows if r.line < at and r.k != "e"]
    gone = {r.site for r in before if r.k == "w"}
    kept_sites = {r.site for r in rows if r.k == "w" and r.line >= at}
    late = [r for r in rows if r.line >= at and r.k == "c" and r.site in gone and r.site not in kept_sites]
    cut = {id(r) for r in before} | {id(r) for r in late}
    return [r for r in rows if id(r) not in cut], at, before + late


# ======================================================================== a digest's rows -> its keys
def row_keys(d: T.RunDigest) -> dict:
    """``{(Row.site, value): WriteKey}`` from the digest's own Observed entries, its keys then its seam keys: every
    row the digest keyed, looked up with :func:`key_of` -- so a check reads each row on its JOINED key (donor through
    the members map, ``off`` as the digest aligned it), never its raw ``ip``. Keyed by value too: one site can store
    several values (a counter), each its own key. A row the digest did not key (a join failure, a masked site, a
    harness poke) has no entry."""
    out: dict = {}
    for keys in (d.keys, d.seam_keys):
        for k, o in keys.items():
            out.setdefault((o.row.site, k.value), k)
    return out


def key_of(rk: dict, r: T.Row) -> T.WriteKey | None:
    """The key :func:`row_keys` gave a ``w`` row (its ``new``) or a ``c`` row (its suppressed ``last``)."""
    return rk.get((r.site, r.new if r.k == "w" else r.last))


# ======================================================================== the verdict
def verdict(checks: list) -> str:
    fails = [w.split(":")[0] for ok, w, _d in checks if ok is False]
    voids = [w.split(":")[0] for ok, w, _d in checks if ok is None]
    if fails:
        return "NOT PROVEN: " + ", ".join(fails)
    if voids:
        return "VOID: " + ", ".join(voids)
    return "PROVEN"


_stock_lang_source = stock_lang          # the module's reader, where a method's parameter shadows the name


def _changed(before: dict, now: dict) -> str:
    keys = [k for k in sorted(set(before) | set(now)) if before.get(k) != now.get(k)]
    return (f"{len(keys)} changed: " + ", ".join(keys[:8])) if keys else ""


def _show(keys, n: int = 6) -> str:
    ks = sorted(keys, key=T.WriteKey.sort_key)
    s = [f"{k.donor} m{k.m} e{k.sid} t{k.tag} {k.off:+d} {k.target}={k.value}" for k in ks[:n]]
    return "; ".join(s) + (f" (+{len(ks) - n} more)" if len(ks) > n else "")


#: A check's text when the segment's ``titles`` does not give one: O1's wording, with the segment's tag. ``{tag}``,
#: ``{manifest}`` (the manifest's file name) and a check's own fields (``{min_covered}``) are filled by
#: :meth:`Segment.title`.
DEFAULT_TITLES = {
    "P-CAP": "P-CAP: the engine advertises the story trace at proto 1",
    "P-MANIFEST": "P-MANIFEST: the frozen members are the deployed chain's ({manifest}, deployed)",
    "P-DEPLOY": "P-DEPLOY: every member registered once under its name, and mapped once to its donor",
    "P-EB": "P-EB: every member's live .eb (7 languages) is the offline-checked build's",
    "P-FLOOR": "P-FLOOR: every member's deployed walkmesh is its donor's",
    "P-STOCK": "P-STOCK: no mod folder overrides the segment's stock fields",
    "BUILD": "{tag}-BUILD: every member's .eb, in every language, is its donor's in that language with only in-chain "
             "Field() literals remapped",
    "KEYS": "{tag}-KEYS: every registered key is a store of its variable at its ip in the donor's stock bytes",
    "FROZEN": "{tag}-FROZEN: the predictions are the file the session recorded, unchanged",
    "COVER": "{tag}-COVER: at least {min_covered} covered runs a side",
    "NULL": "{tag}-NULL: STOCK ONLY and FORK ONLY are empty outside the registered noise",
    "STABLE": "{tag}-STABLE: no key outside the registered noise is written in some runs of a side and not others",
    "JOIN": "{tag}-JOIN: every script row joins a store in the bytes its field ran",
    "THROW": "{tag}-THROW: nothing thrown through the event engine, the evaluator, the tracer or the agent",
}


# ======================================================================== the segment
class Segment:
    """One segment's session and analysis (O1's, moved: each method names the ``o1_opening`` function it was).

    A subclass sets the constants below, ``draft()`` and ``drive()``; everything else is shared and only extended
    through the hooks. ``titles`` maps a check id to its full text (O1's are its archived strings, byte for byte);
    an id it does not give reads :data:`DEFAULT_TITLES`."""

    tag = "SEG"                             # the check-id prefix and the report title; the print tag is tag.lower()
    doc = __doc__                           # the CLI's description (its first paragraph)
    predictions: Path | None = None         # the frozen file a session loads
    manifest: Path | None = None            # <tag>_forks.json
    session_file = "segment_session.json"
    report_file = "segment_report.txt"
    chain_dir: Path | None = None
    build_dir: Path | None = None
    accept_us_build = False                 # BUILD accepts the us-bytecode generation (O1's deployed chain) too
    recovery = RECOVERY_FIELD
    #: S3 (research/o3_design.md 1.2): how long :meth:`end_run` waits, in a battle's END sequence, for the field the
    #: battle hands over before it warps -- the same cap as a battle row's ``land_cap_s`` (2.1), never below it.
    battle_end_wait_s = 120.0
    #: S5 (research/o3_design.md 1.2): True ends the session as every run between ends -- :meth:`end_run`, the warp
    #: to ``recovery`` first (S3's battle rule) -- recorded in ``session["ended"]``. False (O1, O2): the bare
    #: ``restore_baseline()`` where the last run stopped, exactly as before.
    end_session_warps = False
    titles: dict = {}
    core_ids = ("NULL", "STABLE", "JOIN")   # the core checks, in order: each is VOID when a side is short

    def title(self, cid: str, **fields) -> str:
        text = self.titles.get(cid)
        if text is None:
            text = DEFAULT_TITLES[cid].replace("{tag}", self.tag).replace(
                "{manifest}", Path(self.manifest).name if self.manifest else "the manifest")
        for k, v in fields.items():
            text = text.replace("{" + k + "}", str(v))
        return text

    # -- the predictions (pure) ---------------------------------------------------------------------------------
    def draft(self) -> dict:
        raise NotImplementedError(f"{type(self).__name__} drafts its own predictions")

    def load(self, path=None) -> tuple:
        """o1 load_predictions: ``(the predictions, the sha256 of the bytes read)``."""
        data = Path(path or self.predictions).read_bytes()
        return json.loads(data), hashlib.sha256(data).hexdigest()

    def freeze(self, path=None) -> str:
        """o1 freeze: write the draft ONCE (LF, sorted keys); refuses to overwrite a frozen file."""
        path = Path(path or self.predictions)
        if path.exists():
            raise SystemExit(f"!! {path} exists: the predictions are frozen. A new version is a new file.")
        text = json.dumps(self.draft(), indent=1, sort_keys=True) + "\n"
        path.write_bytes(text.encode("utf-8"))
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    # -- offline (reads the install and the build; writes nothing) ----------------------------------------------
    def stock_source(self):
        """``field id -> the stock ScriptIndex | None`` the analysis and the key check read (US bytes)."""
        return T.stock_script_source()

    def offline_check(self, pred: dict, build=None) -> list:
        """o1 offline_check: BUILD and KEYS, then :meth:`offline_extra`."""
        stock = self.stock_source()
        return [self.build_check(pred, build), self.keys_check(pred, stock)] + self.offline_extra(pred, build)

    def offline_extra(self, pred: dict, build=None) -> list:
        return []

    def build_check(self, pred: dict, build=None, stock_lang=None) -> tuple:
        """o1 build_check: every member's built US .eb IS its donor's stock US .eb with only the in-chain ``Field()``
        literals remapped (content.verbatim.remap_fields over the chain's donor -> fork map). Every other language
        must be its OWN donor language remapped the same way; with ``accept_us_build`` a file equal to the us build
        is accepted too (the kit before 3d8b7f1b shipped US bytecode everywhere), and the detail counts each kind."""
        from ff9mapkit.config import LANGS, ModLayout
        from ff9mapkit.content.verbatim import remap_fields
        stock_lang = stock_lang or _stock_lang_source()
        members, names = members_of(pred), {int(f): n for f, n in pred["names"].items()}
        retarget = {d: f for f, d in members.items()}
        lay, bad, n = ModLayout(Path(build or self.build_dir)), [], 0
        gens = {"own": 0, "us": 0}
        for fid, donor in sorted(members.items()):
            paths = {L: lay.eb_path(L, f"EVT_{names[fid]}.eb.bytes") for L in LANGS}
            src = stock_lang(donor, "us")
            if src is None or not all(p.is_file() for p in paths.values()):
                bad.append(f"{fid}: {'no stock donor' if src is None else 'a language file missing'}")
                continue
            us = paths["us"].read_bytes()
            if us != remap_fields(src, retarget):
                bad.append(f"{fid} ({donor}) us: not the donor with only its Field() literals remapped")
            for L in LANGS:
                if L == "us":
                    continue
                got, own = paths[L].read_bytes(), stock_lang(donor, L)
                if own is not None and got == remap_fields(own, retarget):
                    gens["own"] += 1
                elif self.accept_us_build and got == us:
                    gens["us"] += 1
                elif self.accept_us_build:
                    bad.append(f"{fid} ({donor}) {L}: neither its own donor language nor the us build, remapped")
                else:
                    bad.append(f"{fid} ({donor}) {L}: not its own donor language with only its Field() literals "
                               f"remapped")
            n += len(LANGS)
        detail = (f"{n} files; other languages: {gens['own']} own-language, {gens['us']} us-build"
                  if self.accept_us_build else f"{n} files, every language its own donor's")
        return not bad, self.title("BUILD"), "; ".join(bad[:6]) or detail

    def keys_check(self, pred: dict, stock, lists=("ladder",)) -> tuple:
        """o1 keys_check, over every list named: each key's ``(sid, tag, ip)`` is a verified store of its variable in
        the donor's stock bytes, at function offset ``off``. A bit target is joined as the engine writes it (its
        byte, and the bit)."""
        bad, n = [], 0
        for name in lists:
            for k in pred[name]:
                n += 1
                width, index = k["target"].split(".", 1)[1].rstrip("]").split("[")
                bit = int(index) if width in T.BIT_WIDTHS else -1
                row = T.Row(k="w", f=0, p=0, m=k["m"], fld=k["donor"], don=k["donor"], sc=0, src="eb", sid=k["sid"],
                            uid=0, lvl=0, ip=k["ip"], tag=k["tag"], add=0, byte=int(index) >> 3 if bit >= 0
                            else int(index), width=width, bit=bit, old=0, new=k["value"], same=0)
                idx = stock(k["donor"])
                j = idx.join(row) if idx is not None else None
                if j is None or j.status != "store" or j.tag != k["tag"] or j.rel != k["off"]:
                    label = k.get("what") or k.get("why") or f"{k['donor']} e{k['sid']} t{k['tag']} ip{k['ip']}"
                    bad.append(f"{label}: {None if j is None else (j.status, j.tag, j.rel, j.reason)}")
        return not bad, self.title("KEYS"), "; ".join(bad) or f"{n} keys"

    # -- the live install (read-only) ---------------------------------------------------------------------------
    def roots(self) -> list:
        """o1 _roots: the stacked mod folders, in Memoria.ini's order."""
        import dali_tour as D
        return D.mod_roots()

    def preflight(self, pred: dict, roots: list, build=None, manifest=None) -> list:
        """o1 preflight: what must hold before the session spends an hour -- ``[(ok, what, detail)]``: P-MANIFEST,
        P-DEPLOY, P-EB, P-FLOOR, P-STOCK, then :meth:`preflight_extra`."""
        from ff9mapkit import extract
        from ff9mapkit.config import LANGS, ModLayout
        from ff9mapkit.scene.bgi import BgiWalkmesh
        from rung3_trace import _deployed_walkmesh, _fork_donor_rows
        build, manifest = Path(build or self.build_dir), Path(manifest or self.manifest)
        out = []
        members, names = members_of(pred), {int(f): n for f, n in pred["names"].items()}
        try:
            man = json.loads(Path(manifest).read_text(encoding="utf-8"))
            got = {int(f): int(d) for f, d in man["members"].items()}
            ok = got == members and man.get("deployed") is True
            out.append((ok, self.title("P-MANIFEST"),
                        f"{len(members)} members" if ok else f"manifest {got}, deployed {man.get('deployed')}"))
        except (OSError, KeyError, ValueError) as err:
            out.append((False, self.title("P-MANIFEST"), f"unreadable: {err}"))
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
        out.append((not bad, self.title("P-DEPLOY"), "; ".join(bad[:6]) or f"{len(members)} members"))
        lay, bad = ModLayout(build), []
        for fid in sorted(members):
            want = {L: lay.eb_path(L, f"EVT_{names[fid]}.eb.bytes").read_bytes() for L in LANGS}
            live = [r for r in roots if fid in T.mod_registrations(r)]
            for L in LANGS:
                p = ModLayout(Path(live[0])).eb_path(L, f"EVT_{names[fid]}.eb.bytes") if live else None
                if p is None or not p.is_file() or p.read_bytes() != want[L]:
                    bad.append(f"{fid} {L}")
        out.append((not bad, self.title("P-EB"),
                    ("differs: " + ", ".join(bad[:8])) if bad else f"{len(members)} x {len(LANGS)} files"))
        bad = []
        for fid, donor in sorted(members.items()):
            mine = [b for b in (_deployed_walkmesh(Path(r), fid) for r in roots) if b is not None]
            if len(mine) != 1:
                bad.append(f"{fid}: {len(mine)} deployed walkmeshes")
            elif BgiWalkmesh.from_bytes(mine[0]).to_bytes() != extract.stock_walkmesh(donor).to_bytes():
                bad.append(f"{fid}: not donor {donor}'s walkmesh")
        out.append((not bad, self.title("P-FLOOR"), "; ".join(bad[:6]) or f"{len(members)} members"))
        over = {f: [r.name for r in T.stock_overrides(f, roots)] for f in pred["stock_fields"]}
        over = {f: v for f, v in over.items() if v}
        out.append((not over, self.title("P-STOCK"), str(over) if over else "none"))
        return out + self.preflight_extra(pred, roots)

    def preflight_extra(self, pred: dict, roots: list) -> list:
        return []

    def fingerprint(self, roots: list, pred: dict) -> dict:
        """o1 fingerprint: what the runs rely on in the SHARED install, JSON-shaped (two reads compare with ==),
        plus :meth:`fingerprint_extra`."""
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
                             "bgi": [sha(b) for b in (_deployed_walkmesh(Path(r), fid) for r in roots)
                                     if b is not None]}
        out.update(self.fingerprint_extra(roots, pred))
        return out

    def fingerprint_extra(self, roots: list, pred: dict) -> dict:
        return {}

    def scripts_source(self, roots: list):
        """``field id -> the ScriptIndex the fork side will run``: the members' scripts, snapshotted into the run
        directory before the first run."""
        return T.mod_script_source(roots)

    # -- the session (in game) ----------------------------------------------------------------------------------
    def capabilities(self, g) -> list:
        """o1 run's P-CAP, as a list a subclass extends: ``[(ok, what, detail)]``."""
        cap = g.state.storytrace
        return [(isinstance(cap, dict) and cap.get("proto") == T.PROTO, self.title("P-CAP"), str(cap))]

    def start_run(self, g, side: str, pred: dict, marks: dict | None = None) -> tuple:
        """o1 run's entry: New Game, the story mark, the trace armed, then a raw ``warp <start> <entrance>
        <scenario>`` (-1 when the predictions have no ``scenario``) and the wait for the start field. ``marks`` gets
        the story mark (``"story"``) the moment it is taken, so a start that raises after arming still hands the
        session its trace to collect. Returns the mark."""
        marks = {} if marks is None else marks
        g.newgame()
        g.wait_frames(30)
        marks["story"] = smark = g.story_mark()
        g.storytrace(True)
        start = pred["start"][side]
        g._check_field_id(start, "warp", True)
        g.send(f"warp {start} {pred['entrance']} {pred.get('scenario', -1)}")
        g.wait_for(lambda s: s.field_id == start, timeout=60.0, what=f"field {start} to load")
        return smark

    def drive(self, g, pred: dict, side: str, log: list, *, deadline: float, progress: dict | None = None) -> dict:
        raise NotImplementedError(f"{type(self).__name__} drives its own route")

    def end_run(self, g, log: list, *, recovery: int | None = None) -> None:
        """o1 end_run: back to the title after a run. A covered run stands in its end field as the next scene
        plays, and the soft reset may not reach the title through it (session story-o1d: 45 s, then VOID). So the
        run first LEAVES by debug warp -- which works mid-movie -- to ``recovery`` (the segment's), and resets from
        there; the trace is already closed. A warp that is refused falls back to the ladder where it stands. A naming
        screen swallows the soft reset: accepted first when it is up.

        S3 (research/o3_design.md 1.2, 0.2 #9) -- a run stopped INSIDE a battle. The agent refuses a warp outside
        FieldHUD, and the soft-reset combo fires in one battle state only: BattleHUD, mid-fight (``GetKey`` answers
        false outside FieldHUD/WorldHUD/BattleHUD/QuadMistBattle; BattleResult swallows it). So mid-fight (BattleHUD,
        result 0) the run resets at once, with no warp. In a battle's END sequence (a result set, or BattleResult)
        it waits up to :attr:`battle_end_wait_s` for the field the battle hands over, then warps and climbs the ladder
        as any run does. Outside a battle: exactly the old path. Decided on ONE read of the state."""
        from harness import HarnessError
        recovery = self.recovery if recovery is None else recovery
        st = g.state
        if st.ui_state != "Title":
            if st.in_battle and st.ui_state == "BattleHUD" and st.battle_result == 0:   # mid-fight: the one state
                log.append({"k": "recover-in-battle", "scene": st.battle.get("scene"), "ui": st.ui_state,
                            "result": st.battle_result})
                try:
                    g.soft_reset()
                    log.append({"k": "recover-reset"})
                except HarnessError as err:
                    log.append({"k": "recover-reset-failed", "why": str(err)[:200]})
            else:
                if st.in_battle:                    # the end sequence: a result is set, or BattleResult
                    log.append({"k": "recover-battle-ending", "scene": st.battle.get("scene"), "ui": st.ui_state,
                                "result": st.battle_result})
                    try:
                        st = g.wait_for(lambda s: not s.in_battle and s.ui_state == "FieldHUD" and s.field_id > 0,
                                        timeout=self.battle_end_wait_s, what="the battle's end to hand over a field")
                        log.append({"k": "recover-battle-ended", "field": st.field_id})
                    except HarnessError as err:
                        log.append({"k": "recover-battle-ending-failed", "why": str(err)[:200]})
                try:
                    g.warp(recovery)
                    log.append({"k": "recover-warp", "field": recovery})
                except HarnessError as err:
                    log.append({"k": "recover-warp-failed", "why": str(err)[:200]})
        ok, why = g.restore_baseline()
        if not ok and g.state.ui_state == "NameSetting":
            g.accept_name()
            log.append({"k": "end-naming"})
            ok, why = g.restore_baseline()
        if not ok:
            raise HarnessError(f"the title could not be restored: {why}")

    def run(self, g) -> None:
        """o1 run: the whole session. P-CAP and the preflight, the install fingerprint, the members' scripts
        snapshotted, then S F S F S F (the predictions' ``order``) with each run's trace and log saved as it ends and
        the session record rewritten after every run; a side short of ``min_covered`` covered runs re-runs, at most
        ``rerun.max`` -- unless one of its runs is VOID in a FINDING class (``rerun.stop_on``): that side is held, and
        ``rerun_held`` records why. The shared install is fingerprinted around every run: a run begun on a changed
        install is skipped, one the install changed under is never read (both VOID). A RouteVoid's class (``v``,
        ``cell``, ``by``) is copied into its run record. The session then leaves the game at the title: the bare
        ladder where the last run stopped, or (``end_session_warps``) :meth:`end_run`, recorded in
        ``session["ended"]``. Then the analysis, its report, and THROW."""
        from harness import HarnessError
        from segment_drive import RouteVoid

        caps = self.capabilities(g)
        for ok, what, detail in caps:
            g.check(ok, what, detail)
        if not all(ok for ok, _w, _d in caps):
            return
        pred, sha = self.load()
        b = pred["budget"]
        roots = self.roots()
        pre = self.preflight(pred, roots)
        for ok, what, detail in pre:
            g.check(ok, what, detail)
        if not all(ok for ok, _w, _d in pre):
            return
        fp0 = self.fingerprint(roots, pred)
        ran = self.scripts_source(roots)
        scripts = g.run_dir / "scripts"
        scripts.mkdir(exist_ok=True)
        for fid in sorted(members_of(pred)):
            (scripts / f"{fid}.eb").write_bytes(ran(fid).data)
        session = {"label": g.run_dir.name, "predictions": str(self.predictions), "predictions_sha256": sha,
                   "predictions_version": pred["version"], "order": pred["order"], "budget": b,
                   "preflight": [[ok, what, detail] for ok, what, detail in pre],
                   "started": time.strftime("%Y-%m-%dT%H:%M:%S"), "install": fp0, "runs": []}

        def save() -> None:
            (g.run_dir / self.session_file).write_text(json.dumps(session, indent=1), encoding="utf-8")

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
                moved = _changed(fp0, self.fingerprint(roots, pred))
                if moved:
                    rec["install"] = "before the run: " + moved
            if rec.get("skipped") or rec.get("install"):
                session["runs"].append(rec)
                save()
                return
            log: list = []
            progress: dict = {}
            outcome = {"end": "void", "why": "not driven"}
            marks: dict = {}
            rec["t0"] = round(time.time() - t0)
            g.shot_prefix = f"run{i}-{side}"
            try:
                if i > 1:
                    self.end_run(g, log)
                self.start_run(g, side, pred, marks)
                outcome = self.drive(g, pred, side, log, deadline=min(deadline, time.time() + b["run_s"]),
                                     progress=progress)
            except RouteVoid as err:
                outcome = {"end": "void", "why": f"route: {err}"}
                if err.v is not None:
                    outcome.update(v=err.v, cell=err.cell, by=err.by)
            except HarnessError as err:
                outcome = {"end": "void", "why": f"STOPPED: {str(err)[:300]}"}
            except Exception as err:                  # noqa: BLE001 -- one run's bug must not cost the others
                outcome = {"end": "void", "why": f"STOPPED (unexpected): {type(err).__name__}: {str(err)[:300]}"}
                log.append({"k": "error", "traceback": traceback.format_exc()[-3000:]})
            finally:
                g.shot_prefix = ""
                for k, v in progress.items():              # how far a run that raised got
                    outcome.setdefault(k, v)
                smark = marks.get("story")
                if smark is not None:
                    try:
                        rec["traced"] = g.collect_story(g.run_dir / trace_name, smark)
                    except HarnessError as err:
                        rec["trace_error"] = str(err)[:300]
                rec.update(end=outcome.get("end"), why=outcome.get("why"), beats=outcome.get("beats"),
                           t1=round(time.time() - t0))
                for k in ("v", "cell", "by"):              # a classed VOID, for the analysis to read per side
                    if outcome.get(k) is not None:
                        rec[k] = outcome[k]
                moved = _changed(fp0, self.fingerprint(roots, pred))
                if moved:
                    rec["install"] = "during the run: " + moved
                (g.run_dir / log_name).write_text(json.dumps({"outcome": outcome, "log": log}, indent=1),
                                                  encoding="utf-8")
                session["runs"].append(rec)
                save()
                print(f"[{self.tag.lower()}] run {i} ({side}) at {rec['t1']}s: {rec['end']} -- {rec['why']}",
                      flush=True)

        for i, side in enumerate(pred["order"], 1):
            one(i, side)
        reruns = 0
        # S2 (research/o3_design.md 1.2): a side with any run VOID in a FINDING class is not re-run however short it
        # is -- re-running a finding only repeats it, and the analysis (VOID-ASYM) already reads it. No ``stop_on``
        # (O1, O2): exactly the old loop, which read the session once per side per pass; this reads it once a pass.
        stop_on = set(pred["rerun"].get("stop_on") or ())
        while reruns < pred["rerun"]["max"]:
            runs = self.read_session(g.run_dir, pred, session=session)
            held = {s for s in SIDES if any(r["side"] == s and r["rec"].get("v") in stop_on for r in runs)}
            short = [s for s in SIDES if s not in held
                     and sum(1 for r in runs if r["side"] == s and r["covered"]) < pred["min_covered"]]
            if held:
                session["rerun_held"] = {s: sorted({r["rec"]["v"] for r in runs if r["side"] == s
                                                    and r["rec"].get("v") in stop_on}) for s in sorted(held)}
            if not short or time.time() + b["run_min_s"] > deadline:
                break
            reruns += 1
            one(len(session["runs"]) + 1, short[0], rerun=True)
        session["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        save()
        if self.end_session_warps:                 # S5: the session ends through end_run, recorded, never raised
            end_log: list = []
            try:
                self.end_run(g, end_log)
                session["ended"] = {"log": end_log, "ok": True, "why": ""}
            except HarnessError as err:
                session["ended"] = {"log": end_log, "ok": False, "why": str(err)[:300]}
            save()
        else:
            try:
                g.restore_baseline()
            except HarnessError:
                pass
        checks, report = self.analyse(g.run_dir)
        (g.run_dir / self.report_file).write_text(report, encoding="utf-8")
        print(report[:6000], flush=True)
        for ok, what, detail in checks:
            g.check(ok is True, what, ("VOID -- " if ok is None else "") + detail)
        ours = [e for e in g.exceptions_since(mark) if e.name in THROWS
                and (not e.trace or any(k in fr for fr in e.trace for k in WHERE))]
        g.check(not ours, self.title("THROW"), str([(e.name, e.where) for e in ours[:5]]) if ours else "none")

    # -- reading a session (pure, offline, but for the stock scripts) --------------------------------------------
    def cut(self, rows: list, pred: dict, side: str) -> tuple:
        """``(kept, start line, end line, pre)``: with ``cut_start``, :func:`cut_at_start` from the start field's
        place; then :func:`cut_at_end` at the end places (``end_fields``, else ``[end_field]``). Places are frozen:
        the F side's through the members, the S side's its own fields."""
        members = members_of(pred) if side == "F" else {}
        start, pre = None, []
        if pred.get("cut_start"):
            rows, start, pre = cut_at_start(rows, place(pred["start"][side], members), members)
        kept, end = cut_at_end(rows, pred.get("end_fields") or [pred["end_field"]], members)
        return kept, start, end, pre

    def why_void(self, rec: dict, r: dict, pred: dict) -> list:
        """The segment's extra reasons a run is not covered: ``[(reason, class, by)]`` (base: none)."""
        return []

    def read_session(self, run_dir, pred: dict, *, session: dict | None = None, stock=None) -> list:
        """o1 read_session: every recorded run, read: ``[{i, side, rec, rows, cut, start, pre, digest, covered,
        why_void, void}]``. A run is COVERED only when its drive reached the end with every beat done, its trace
        closed whole, the install held, and :meth:`why_void` has nothing to add. ``void`` gives each reason its
        class and attribution (research/o2_design.md 5.1): the drive's own V-class when its record carries one."""
        run_dir = Path(run_dir)
        session = session or json.loads((run_dir / self.session_file).read_text(encoding="utf-8"))
        stock = stock or self.stock_source()
        members = members_of(pred)
        saved = {f: T.ScriptIndex((run_dir / "scripts" / f"{f}.eb").read_bytes(), field_id=f, label=f"member {f}")
                 for f in members if (run_dir / "scripts" / f"{f}.eb").is_file()}
        fork_scripts = lambda fid: saved.get(fid) or stock(fid)                          # noqa: E731
        # S1 (research/o3_design.md 1.2): a REGISTERED battle's beat is done only when it holds an int result in its
        # row's ``won`` (a defeat's 3, a None, a True are not). O1's ``battle`` beat keeps its legacy rule (the
        # predictions' ``battle_won``), any other beat its truthiness; predictions with no ``battles`` read as before.
        won = {b["beat"]: list(b["won"]) for b in pred.get("battles") or ()}

        def done(b: str, beats: dict):                         # truthy when the beat is done (the legacy rules' value)
            if b in won:
                v = beats.get(b)
                return type(v) is int and v in won[b]          # True == 1: a bool is never a battle's result
            return beats.get(b) in pred["battle_won"] if b == "battle" else beats.get(b)
        out = []
        for rec in session["runs"]:
            void: list = []
            r = {"i": rec["i"], "side": rec["side"], "rec": rec, "rows": [], "cut": None, "start": None, "pre": [],
                 "digest": None}
            if rec.get("skipped"):
                void.append({"why": f"not run: {rec['skipped']}", "class": "A-SKIPPED", "by": "driver"})
            if rec.get("install"):
                void.append({"why": f"install changed {rec['install']}", "class": "A-INSTALL", "by": "driver"})
            if rec.get("end") != "reached":
                stopped = str(rec.get("why") or "").startswith("STOPPED")
                void.append({"why": f"the drive did not reach the end: {rec.get('why')}",
                             "class": rec.get("v") or ("V13" if stopped else "V?"), "by": rec.get("by") or "driver",
                             "cell": rec.get("cell")})
            beats = rec.get("beats") or {}
            missed = [b for b in pred["beats"] if not done(b, beats)]
            if rec.get("end") == "reached" and missed:
                why = (f"beats not done: {missed} (battle result {beats.get('battle')})" if not won   # O1's, exactly
                       else f"beats not done: {missed} (" + ", ".join(f"{b} result {beats.get(b)!r}" for b in won)
                       + ")")
                void.append({"why": why, "class": "A-BEATS", "by": "driver"})
            path = run_dir / rec.get("trace", "")
            if not rec.get("skipped") and path.is_file():
                try:
                    kept, start, end, pre = self.cut(T.read_trace(path), pred, rec["side"])
                    r["rows"], r["cut"], r["start"], r["pre"] = kept, end, start, pre
                    d = T.digest(f"{rec['side']}#{rec['i']}", kept,
                                 scripts=fork_scripts if rec["side"] == "F" else stock, donor_scripts=stock,
                                 members=members if rec["side"] == "F" else None)
                    r["digest"] = d
                    if d.incomplete:
                        void.append({"why": f"trace incomplete: {d.incomplete[:120]}", "class": "A-TRACE",
                                     "by": "driver"})
                except T.TraceError as err:
                    void.append({"why": f"trace unreadable: {str(err)[:200]}", "class": "A-TRACE", "by": "driver"})
            elif not rec.get("skipped"):
                void.append({"why": "no trace file", "class": "A-TRACE", "by": "driver"})
            void += [{"why": why, "class": cls, "by": by} for why, cls, by in self.why_void(rec, r, pred)]
            r["void"] = void
            r["why_void"] = [v["why"] for v in void]
            r["covered"] = not void
            out.append(r)
        return out

    def judge(self, runs: list, pred: dict, *, frozen: tuple) -> list:
        """o1 judge: ``[(True | False | None, what, detail)]`` -- None = VOID. FROZEN, COVER, then
        :meth:`all_run_checks` (judged over every run, covered or not), then :meth:`core_checks` over the covered
        runs -- each VOID ("too few covered runs") when a side has fewer than ``min_covered``."""
        checks = [frozen]
        cov = {s: [r for r in runs if r["side"] == s and r["covered"]] for s in SIDES}
        enough = all(len(cov[s]) >= pred["min_covered"] for s in SIDES)
        checks.append((enough if enough else None, self.title("COVER", min_covered=pred["min_covered"]),
                       ", ".join(f"{s} {len(cov[s])} of {sum(1 for r in runs if r['side'] == s)}" for s in SIDES)
                       + "".join(f"; {r['side']}#{r['i']} VOID: {'; '.join(r['why_void'])[:160]}"
                                 for r in runs if not r["covered"])))
        checks += self.all_run_checks(runs, pred)
        if not enough:
            return checks + [(None, f"{self.tag}-{cid}", "too few covered runs") for cid in self.core_ids]
        return checks + self.core_checks(runs, cov, pred)

    def all_run_checks(self, runs: list, pred: dict) -> list:
        return []

    def comparison(self, cov: dict, pred: dict) -> T.Comparison:
        return T.compare([r["digest"] for r in cov["S"]], [r["digest"] for r in cov["F"]], members=members_of(pred))

    def core_checks(self, runs: list, cov: dict, pred: dict) -> list:
        """o1 judge's NULL, STABLE and JOIN (a subclass adds its own around them, in ``core_ids`` order)."""
        c = self.comparison(cov, pred)
        return [self.null_check(c, pred), self.stable_check(c, pred), self.join_check(cov)]

    def null_check(self, c: T.Comparison, pred: dict) -> tuple:
        so = [k for k in c.stock_only if not is_noise(k, pred)]
        fo = [k for k in c.fork_only if not is_noise(k, pred)]
        return (not so and not fo, self.title("NULL"),
                f"STOCK ONLY {len(so)}: {_show(so)} / FORK ONLY {len(fo)}: {_show(fo)}" if so or fo
                else f"{len(c.matched)} keys matched; noise set aside: "
                     f"{len(c.stock_only) - len(so)} stock-only, {len(c.fork_only) - len(fo)} fork-only")

    def stable_check(self, c: T.Comparison, pred: dict) -> tuple:
        un = [k for k in c.unstable if not is_noise(k, pred)]
        return (not un, self.title("STABLE"),
                f"{len(un)}: {_show(un)}" if un else f"{len(c.unstable)} unstable, all registered noise")

    def join_check(self, cov: dict) -> tuple:
        covered = cov["S"] + cov["F"]
        fails = [(r["side"], r["i"], len(r["digest"].failures)) for r in covered if r["digest"].failures]
        return (not fails, self.title("JOIN"),
                str(fails) if fails else f"{sum(len(r['rows']) for r in covered)} rows, 0 failures")

    def report(self, run_dir, session: dict, pred: dict, sha: str, runs: list, checks: list) -> str:
        """o1 analyse's report: the title, the verdict, every check, one line per run, the comparison
        (``storytrace.report``) when both sides have a covered run, then :meth:`report_extra`."""
        lines = [f"{self.tag} -- {session['label']}  (predictions v{pred['version']} {sha[:8]})", "",
                 f"VERDICT: {verdict(checks)}", ""]
        for ok, what, detail in checks:
            lines.append(f"{'PASS' if ok is True else 'FAIL' if ok is False else 'VOID'}  {what}\n      {detail}")
        lines.append("")
        for r in runs:
            rec = r["rec"]
            lines.append(f"run {r['i']} {r['side']}: {'covered' if r['covered'] else 'VOID'} -- {rec.get('why')}; "
                         f"beats {rec.get('beats')}; {len(r['rows'])} rows, cut at line {r['cut']}")
        cov = {s: [r["digest"] for r in runs if r["side"] == s and r["covered"]] for s in SIDES}
        if cov["S"] and cov["F"]:
            lines += ["", T.report(T.compare(cov["S"], cov["F"], members=members_of(pred)),
                                   title=f"{self.tag} stock vs fork")]
        lines += self.report_extra(Path(run_dir), session, pred, runs, checks)
        return "\n".join(lines) + "\n"

    def report_extra(self, run_dir: Path, session: dict, pred: dict, runs: list, checks: list) -> list:
        return []

    def analyse(self, run_dir, *, pred_path=None, stock=None) -> tuple:
        """o1 analyse: ``(checks, report text)`` for a session directory, against the predictions the session
        recorded (or ``pred_path``: FROZEN then compares its sha with the recorded one)."""
        run_dir = Path(run_dir)
        session = json.loads((run_dir / self.session_file).read_text(encoding="utf-8"))
        path = Path(pred_path or session["predictions"])
        pred, sha = self.load(path)
        frozen = (sha == session["predictions_sha256"], self.title("FROZEN"),
                  f"{path.name} sha {sha[:8]}" + ("" if sha == session["predictions_sha256"]
                                                   else f", recorded {session['predictions_sha256'][:8]}"))
        runs = self.read_session(run_dir, pred, session=session, stock=stock)
        checks = self.judge(runs, pred, frozen=frozen)
        return checks, self.report(run_dir, session, pred, sha, runs, checks)

    # -- the CLI ------------------------------------------------------------------------------------------------
    def add_arguments(self, ap: argparse.ArgumentParser) -> None:
        """A subclass's own flags (base: none)."""

    def handle(self, args) -> int | None:
        """A subclass's own flags, run before the shared ones: an exit code, or None to go on (base: None)."""
        return None

    def main(self, argv=None) -> int:
        """o1 main: ``--freeze``, ``--analyse RUN_DIR [--predictions P]``, ``--offline-check``, ``--preflight``."""
        ap = argparse.ArgumentParser(description=(self.doc or "").split("\n\n")[0])
        ap.add_argument("--offline-check", action="store_true")
        ap.add_argument("--preflight", action="store_true")
        ap.add_argument("--analyse", metavar="RUN_DIR")
        ap.add_argument("--predictions", type=Path)
        ap.add_argument("--freeze", action="store_true")
        self.add_arguments(ap)
        args = ap.parse_args(argv)
        done = self.handle(args)
        if done is not None:
            return done
        if args.freeze:
            print("frozen:", Path(self.predictions).name, self.freeze())
            return 0
        if args.analyse:
            checks, report = self.analyse(args.analyse, pred_path=args.predictions)
            print(report)
            return 0 if all(ok is True for ok, _w, _d in checks) else 1
        pred, _sha = self.load(args.predictions or self.predictions)
        checks = (self.offline_check(pred) if args.offline_check
                  else self.preflight(pred, self.roots()) if args.preflight else None)
        if checks is None:
            ap.print_help()
            return 2
        for ok, what, detail in checks:
            print(f"{'PASS' if ok else 'FAIL'}  {what}\n      {detail}")
        return 0 if all(ok for ok, _w, _d in checks) else 1
