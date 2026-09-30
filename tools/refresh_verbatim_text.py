#!/usr/bin/env python3
"""Repair the us/uk text of verbatim forks imported before master aa627d52, without re-importing them.

THE DEFECT. Until aa627d52 the kit picked each language's copy of a field text block by a stopword score, which
reads the us and uk copies as the same language. Every verbatim fork therefore carries ONE English body as both
its us and its uk text: the US copy in blocks where uk got it wrong (2, 33, 187, 276, ...), the UK copy where us
did (8, 47, 53, ...). A verbatim fork keeps that text in ``<NAME>.verbatim_mes.json``, written once at IMPORT, and
every later build re-ships it. So a re-deploy after the fix changes nothing: the sidecar has to be rewritten.

WHY NOT RE-IMPORT. ``import``/``import-chain`` would regenerate it, but they rewrite the whole fork project: the
field.toml (its [startup] seed, retarget table, any hand edits) and every asset. This tool rewrites only the
sidecar, from the donor its field.toml records (``[verbatim_eb] donor``), through the same
``dialogue.extract_field_mes_all_langs`` the import calls, in the import's exact format.

WHAT IT REWRITES, AND WHAT IT REFUSES. Only a sidecar whose difference from the donor's real text is exactly the
defect: its us and uk are one body, that body is the donor's real us or uk, and every other language already
matches. Anything else (a language hand-edited, the wrong donor, a language missing) is REFUSED and named, and
``--force`` is needed to overwrite it. It runs only when the install's resource-path index reads, so the text it
writes is the engine's own per-language asset, never a re-guess.

SAFETY. Dry run by default. ``--apply`` copies each sidecar it rewrites to ``<sidecar>.pre-refresh-<stamp>``
(create-exclusive, next to it), then writes atomically. Nothing else is touched: rebuild and re-deploy each
fork afterwards to ship the fix. NOT covered: the world-map place-name override (``FF9CustomMap-world``
``text/<lang>/field/68.mes``), which ``deploy_marker_renames`` merges onto the deployed file.

Exit status: 0 = every fork checked, none refused; 1 = something was refused or skipped (no donor recorded,
an unreadable toml/sidecar/donor text); 2 = the install or its resource-path index can't be read.

Usage:  py tools/refresh_verbatim_text.py <dir-or-field.toml> [...] [--apply] [--force] [--game <FF9 folder>]
"""
import argparse, json, os, sys, tomllib
from datetime import datetime
from pathlib import Path

KIT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "ff9mapkit"))
sys.path.insert(0, KIT)
from ff9mapkit import dialogue
from ff9mapkit._fieldtext import EVENT_ID_TO_MES
from ff9mapkit.fsutil import atomic_write_text

ENGLISH = ("us", "uk")


def sidecars(roots):
    """``[(field.toml, sidecar, donor-or-None)]`` for every verbatim fork under ``roots`` (dirs or field.tomls)
    that ships text -- one row per sidecar. A field.toml that won't parse is a row with ``sidecar=None``."""
    tomls = []
    for r in map(Path, roots):
        tomls += [r] if r.is_file() else sorted(r.rglob("*.field.toml"))
    rows, seen = [], set()
    for t in tomls:
        try:
            vb = tomllib.loads(t.read_text(encoding="utf-8")).get("verbatim_eb") or {}
        except (OSError, tomllib.TOMLDecodeError):
            rows.append((t, None, None))
            continue
        if not vb.get("text"):
            continue
        side = (t.parent / vb["text"]).resolve()
        if side not in seen:
            seen.add(side)
            rows.append((t, side, vb.get("donor")))
    return rows


def classify(old: dict, new: dict) -> tuple:
    """``(verdict, detail)`` for a sidecar ``old`` against the donor's real text ``new``: ``"ok"`` (already
    right), ``"defect"`` (exactly the us/uk mis-pick, safe to rewrite) or ``"unexplained"`` (anything else)."""
    if old == new:
        return "ok", "each language is already its own asset"
    diff = sorted(L for L in set(old) | set(new) if old.get(L) != new.get(L))
    others = [L for L in diff if L not in ENGLISH]
    one = old.get("us")
    if not others and one is not None and one == old.get("uk") and new.get("us") != new.get("uk"):
        if one == new.get("us"):
            return "defect", "uk was the US text"
        if one == new.get("uk"):
            return "defect", "us was the UK text"
    return "unexplained", f"{', '.join(diff)} differ from the donor, and not as the us/uk defect does"


def refresh(roots, *, extract, apply=False, force=False, out=print) -> dict:
    """Check (and with ``apply``, rewrite) every sidecar under ``roots`` against ``extract(donor)`` ->
    ``{lang: body}``. Returns ``{verdict: count}`` over ``fixed``/``would-fix``/``ok``/``refused``/``skipped``."""
    tally = dict.fromkeys(("fixed", "would-fix", "ok", "refused", "skipped"), 0)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    for toml, side, donor in sidecars(roots):
        if side is None:
            out(f"SKIP    {toml}: the field.toml won't parse")
            tally["skipped"] += 1
            continue
        if donor is None or not side.is_file():
            out(f"SKIP    {side}: " + ("no [verbatim_eb] donor recorded" if donor is None else "sidecar missing"))
            tally["skipped"] += 1
            continue
        new = extract(int(donor))
        if not new:
            out(f"SKIP    {side}: donor {donor}'s text can't be read")
            tally["skipped"] += 1
            continue
        try:
            old = json.loads(side.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            out(f"SKIP    {side}: the sidecar won't parse as JSON")
            tally["skipped"] += 1
            continue
        verdict, detail = classify(old, new)
        where = f"donor {donor}, block {EVENT_ID_TO_MES.get(int(donor), '?')}"
        if verdict == "ok":
            out(f"OK      {side}  ({where})")
            tally["ok"] += 1
            continue
        if verdict == "unexplained" and not force:
            out(f"REFUSE  {side}  ({where}): {detail} -- inspect it; --force rewrites it anyway")
            tally["refused"] += 1
            continue
        if not apply:
            out(f"WOULD   {side}  ({where}): {detail}")
            tally["would-fix"] += 1
            continue
        with open(side.with_name(f"{side.name}.pre-refresh-{stamp}"), "xb") as fh:
            fh.write(side.read_bytes())
        atomic_write_text(side, json.dumps(new))            # the import's exact format (extract.py)
        out(f"FIXED   {side}  ({where}): {detail}")
        tally["fixed"] += 1
    return tally


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    ap.add_argument("roots", nargs="+", help="fork project dirs (searched recursively) or field.toml files")
    ap.add_argument("--apply", action="store_true", help="rewrite the sidecars (default: dry run)")
    ap.add_argument("--force", action="store_true", help="also rewrite sidecars whose difference isn't the defect")
    ap.add_argument("--game", default=None, help="the FF9 install (default: auto-detect)")
    args = ap.parse_args(argv)
    try:                                                    # the ONLY extractor main() uses is gated here
        index = dialogue._mes_path_index(args.game)
    except Exception as ex:                                 # noqa: BLE001 -- no install found (ConfigError)
        index, why = None, f" ({ex})"
    else:
        why = ""
    if index is None:
        print("!! the install's resource-path index (mainData ResourceManager) can't be read, so the text would "
              f"be re-guessed from content. Nothing was checked or written.{why}", file=sys.stderr)
        return 2
    tally = refresh(args.roots, apply=args.apply, force=args.force,
                    extract=lambda donor: dialogue.extract_field_mes_all_langs(donor, game=args.game))
    print(", ".join(f"{n} {k}" for k, n in tally.items() if n) or "no verbatim fork with text found")
    if tally["would-fix"]:
        print("(dry run -- pass --apply to rewrite them)")
    if tally["fixed"]:
        print("Rebuild + re-deploy each fixed fork to ship its text.")
    return 1 if tally["refused"] or tally["skipped"] else 0


if __name__ == "__main__":
    sys.exit(main())
