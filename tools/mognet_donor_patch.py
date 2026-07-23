#!/usr/bin/env python3
"""Patch a REAL Mognet moogle field in place -- the donor-fork lane (project memory
`project-ff9-mognet-protocol`, "THE DONOR-FORK CLASS"). Generates, FROM YOUR OWN INSTALL, a patched
copy of the donor field's .eb + an additive .mes override, and writes both into your Memoria mod
folder (per-language). Three faces, all optional per run:

  --name NAME                     the 42nd roster row at this donor (fixes the blank sender name)
  --letter VARIANT "TEXT"         letter CONTENT shown when OUR letter (variant) is delivered here
  --inbound VARIANT --from-id N   this donor OFFERS a letter to our moogle (from = its roster id)
      --prompt "..." [--line "..."]

The written files are DERIVED FROM THE INSTALL at run time and live only in the mod folder -- never
commit them (the extract-templates provenance rule). Content hot-reloads (~ -> Reload field); no
relaunch (the donor field + its text block are already registered).

Example (Kupo, Alexandria Steeple, field 1865):
  py tools/mognet_donor_patch.py 1865 --name Mogwai \\
      --letter 56 "Mogwai here, kupo! Come visit the new save point!" \\
      --inbound 57 --from-id 1 --prompt "Would you deliver my letter to Mogwai, kupo?" \\
      --line "Take good care of it, kupo!"

Revert: tools/scroll_out/revert_mognet_donor_<field>.py (deletes the written overrides).
"""
import argparse
import os
import sys
import tomllib
from pathlib import Path

KIT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "ff9mapkit"))
sys.path.insert(0, KIT)
from ff9mapkit import dialogue                                        # noqa: E402
from ff9mapkit.config import find_game_path, ModLayout, LANGS         # noqa: E402
from ff9mapkit.extract import extract_event_script, ID_TO_EVT         # noqa: E402
from ff9mapkit._fieldtext import EVENT_ID_TO_MES                      # noqa: E402
from ff9mapkit.content import mognetdonor                             # noqa: E402

_REPO = Path(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


def _worktree_cfg():
    f = _REPO / ".ff9deploy.toml"
    if f.is_file():
        try:
            return tomllib.loads(f.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def main():
    cfg = _worktree_cfg()
    ap = argparse.ArgumentParser(description="Patch a real Mognet moogle field (donor-fork lane).")
    ap.add_argument("field", type=int, help="the donor field id (e.g. 1865 = Kupo, Alexandria Steeple)")
    ap.add_argument("--name", default=None, help="our moogle's name -> the 42nd roster row here")
    ap.add_argument("--letter", nargs=2, action="append", metavar=("VARIANT", "TEXT"), default=[],
                    help="letter content for OUR variant delivered here (repeatable)")
    ap.add_argument("--inbound", type=int, default=None, metavar="VARIANT",
                    help="this donor offers a letter (VARIANT) addressed to our moogle")
    ap.add_argument("--from-id", type=int, default=None, help="the donor moogle's own roster id")
    ap.add_argument("--prompt", default=None, help="the inbound offer window text")
    ap.add_argument("--line", default=None, help="the inbound Yes-side send-off line")
    ap.add_argument("--langs", default="all", help='comma list or "all" (default)')
    ap.add_argument("--mod-folder", default=os.environ.get("FF9_MOD_FOLDER") or cfg.get("mod_folder")
                    or "FF9CustomMap")
    args = ap.parse_args()

    letters = {int(v): t for v, t in args.letter}
    inbound = None
    if args.inbound is not None:
        if args.from_id is None or not args.prompt:
            ap.error("--inbound needs --from-id (the donor's roster id) and --prompt")
        inbound = {"variant": args.inbound, "from_id": args.from_id,
                   "prompt": args.prompt, "line": args.line}
    if not (args.name or letters or inbound):
        ap.error("nothing to patch: give --name, --letter, and/or --inbound")

    fid = args.field
    evt = ID_TO_EVT.get(fid)
    mes_id = EVENT_ID_TO_MES.get(fid)
    if not evt or mes_id is None:
        raise SystemExit(f"field {fid}: no EVT/mes mapping -- not a patchable field")
    game = find_game_path()
    live = ModLayout(game / args.mod_folder)
    langs = list(LANGS) if args.langs == "all" else [x.strip() for x in args.langs.split(",")]

    written = []
    for lang in langs:
        try:
            eb = extract_event_script(str(fid), lang=lang)
            mes = dialogue.extract_field_mes(fid, lang)
        except Exception as e:
            print(f"  {lang}: SKIP ({e})")
            continue
        if not eb or not mes:
            print(f"  {lang}: SKIP (no stock eb/mes)")
            continue
        patched, add_mes = mognetdonor.patch_donor_field(
            eb, mes, roster_name=args.name, content_letters=letters or None, inbound=inbound)
        ep = live.eb_path(lang, f"{evt}.eb.bytes")
        mp = live.mes_path(lang, mes_id)
        ep.parent.mkdir(parents=True, exist_ok=True)
        mp.parent.mkdir(parents=True, exist_ok=True)
        ep.write_bytes(patched)
        mp.write_text(add_mes, encoding="utf-8", newline="\n")
        written += [ep, mp]
        print(f"  {lang}: eb {len(eb)} -> {len(patched)} B at {ep.name}; mes +{len(add_mes)} B (block {mes_id})")

    if not written:
        raise SystemExit("nothing written (no language succeeded)")
    out = _REPO / "tools" / "scroll_out"
    out.mkdir(exist_ok=True)
    rv = out / f"revert_mognet_donor_{fid}.py"
    lines = "\n".join(f"Path(r'{p}').unlink(missing_ok=True)" for p in written)
    rv.write_text("from pathlib import Path\n" + lines +
                  f"\nprint('mognet donor patch for field {fid} reverted')\n", encoding="utf-8")
    print(f"donor field {fid} patched ({len(written)} files). In-game: ~ -> Reload field (content "
          f"hot-reloads; no relaunch needed).\nrevert: {rv}")


if __name__ == "__main__":
    main()
