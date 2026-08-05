r"""Path D Rung 6, WORLD-SIDE half (1/2): splice the 9013 EXIT TRIGGER into EVT_WORLD_WORLD13.

WHAT THIS DOES, in one sentence: for each of the 7 locales it reads that locale's OWN live
``EVT_WORLD_WORLD13.eb.bytes`` out of ``FF9CustomMap-world``, backs it up, and adds ONE function to
object-0 (entry 0) tagged with the trigger cell's tag, whose body fades out, records the world
state, and calls ``Field(30950)``.

WHY THIS SHAPE (byte-verified, see studies/path-d-new-world/rung6/):

* Walking a terrain tile whose IDALL event bits are set fires ``ff9.WorldEvent(cellX, cellZ, id)``,
  which packs the cell tag ``0x8000 | (cz<<8) | (cx<<2) | id`` and ``GetIP``-matches it against
  **object-0's function tags** in the LOADED world dispatcher. So the trigger is an object-0
  function keyed by cell, not a switch arm -- ``entrance.pack_cell_tag(13, 17, 1) = 0x9135``.
* WORLD13's ``.eb`` is a byte-exact per-locale clone of pristine stock WORLD11, so object-0 already
  exists with 45 functions and the file is an ordinary, well-formed dispatcher. ``add_function``
  splices onto it cleanly (proven offline on the live bytes, 2026-08-05).
* The body is ``entrance.entrance_func_body_direct(...)``: the template's vehicle/on-foot gate, the
  "!" FICON bubble, the ``B_KEYON(Confirm)`` gate, then the real ``zone_in_body`` choreography
  (control lock + fade-to-black BEFORE ``Field()`` + the ``D8:2 = 9999`` worldmap-arrival sentinel),
  ``GLOB[1062] = 9013``, ``Field(30950)``, ``RETURN``. It bypasses the AREA switch entirely --
  that switch only carries real base-game destinations, so a custom field cannot be a case.
* ``author_entrance`` is NOT usable here: it discovers its targets through ``load_all_dispatchers``,
  which reads p0data and therefore cannot see WORLD13 at all (dry-run proven: 9 targets, none of
  them world13). Only the BODY builder is reused, with ``dispatchers=`` handed in.

THE PER-LOCALE RULE (entrance.load_all_dispatchers' own warning): the world dispatchers are NOT
language-identical -- jp carries localized inline dialogue and a different byte layout. Each locale
is therefore patched against ITS OWN base; nothing is ever cloned across locales. The script asserts
this two ways: the 84-byte PSX name region must survive byte-identical per file, and it reports the
pre-image sha/size of all 7 so a jp-from-us clone would be visible at a glance.

IDEMPOTENT: a re-run whose tag is already present takes the ``replace_function_body`` path; if the
body is also already identical it writes nothing at all.

  py splice_exit.py --dry-run
  py splice_exit.py
  py splice_exit.py --target-root <scratch>     # offline verification against copies
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _common as C  # noqa: E402


def parse_cell(s: str):
    cx, cz = (int(v) for v in str(s).replace(" ", "").split(","))
    return cx, cz


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="splice the Path-D 9013 exit trigger into WORLD13's .eb")
    ap.add_argument("--game", default=str(C.DEFAULT_GAME),
                    help="the REAL install -- read-only here; the p0data source for WORLD00's trigger "
                         "template (entrance.load_world_dispatchers). Default: the Steam install.")
    ap.add_argument("--target-root", default=None,
                    help="root that CONTAINS the mod folder to patch (default: --game). Point this at "
                         "a scratch copy to author/verify without touching the install.")
    ap.add_argument("--mod-folder", default=C.MOD_FOLDER)
    ap.add_argument("--eb-name", default=C.WORLD_EB_NAME)
    ap.add_argument("--dest", type=int, default=C.DEST_FIELD, help="destination field id for Field()")
    ap.add_argument("--world-state", type=int, default=C.WORLD_STATE,
                    help="wldMapNo recorded into GLOB[1062] (worldexit.WORLD_STATE_VAR) so the "
                         "destination field's return gateway knows which world to go back to")
    ap.add_argument("--cell", default="%d,%d" % C.TRIGGER_CELL, help="trigger cell 'cx,cz'")
    ap.add_argument("--event", type=int, default=C.TRIGGER_EVENT, help="event bits 1..3")
    ap.add_argument("--no-prompt", action="store_true",
                    help="AUTO-WARP instead of the faithful '!' + Confirm action prompt. Real "
                         "overworld entrances are confirm-gated; only use this for a scripted exit.")
    ap.add_argument("--backup-dir", default=None)
    ap.add_argument("--dry-run", action="store_true", help="verify everything, write nothing")
    ap.add_argument("--report", default=None, help="write a JSON report here")
    ap.add_argument("--log", default=None, help="write the transcript here")
    ap.add_argument("--dump-disasm", default=None,
                    help="directory to drop per-locale disassembly of the spliced function")
    args = ap.parse_args(argv)

    C.import_kit()
    from ff9mapkit.eb import edit as E
    from ff9mapkit.eb.model import EbScript
    from ff9mapkit.world import entrance as EN

    log = C.Log()
    game = Path(args.game)
    target_root = Path(args.target_root) if args.target_root else game
    cx, cz = parse_cell(args.cell)
    tag = EN.pack_cell_tag(cx, cz, args.event)
    bx, by = EN.cell_to_block(cx, cz)
    prompt = not args.no_prompt
    backup_dir = C.resolve_backup_dir(args.backup_dir, label="eb")
    rep: dict = {"script": "splice_exit.py", "dry_run": bool(args.dry_run), "game": str(game),
                 "target_root": str(target_root), "mod_folder": args.mod_folder,
                 "eb_name": args.eb_name, "dest_field": args.dest, "world_state": args.world_state,
                 "cell": [cx, cz], "block": [bx, by], "event": args.event,
                 "cell_tag": f"0x{tag:04X}", "prompt": prompt,
                 "backup_dir": str(backup_dir), "locales": {}, "ok": False}

    log.rule("Path D Rung 6 -- WORLD-SIDE (1/2): the 9013 exit trigger")
    log(f"  game (read-only, p0data template) : {game}")
    log(f"  target root (gets patched)        : {target_root}")
    log(f"  mod folder                        : {args.mod_folder}")
    log(f"  trigger cell                      : ({cx},{cz}) -> block ({bx},{by}), "
        f"centre {EN.cell_world_center(cx, cz)}")
    log(f"  cell tag (object-0 GetIP key)     : 0x{tag:04X}  unpack={EN.unpack_cell_tag(tag)}")
    log(f"  destination                       : Field({args.dest}), GLOB[1062] = {args.world_state}")
    log(f"  action prompt ('!' + Confirm)     : {prompt}")
    log(f"  backup dir                        : {backup_dir}")
    log(f"  MODE                              : {'DRY RUN (no writes)' if args.dry_run else 'WRITE'}")

    # ---------------------------------------------------------------- the body (built once)
    log.rule("(1) build the trigger body from WORLD00's proven template (p0data, read-only)")
    disp = EN.load_world_dispatchers(str(game))
    log(f"  load_world_dispatchers -> {len(disp)} dispatchers; template donor "
        f"evt_world_world00 present={('evt_world_world00' in disp)}")
    body = EN.entrance_func_body_direct(args.dest, world_state=args.world_state, prompt=prompt,
                                        dispatchers=disp)
    st, n_instr, err = C.parse_body(body)
    log(f"  body: {len(body)} bytes, {n_instr} instructions, decode={st}"
        + (f"  ERR {err}" if err else ""))
    log(f"  hex: {body.hex()}")
    if st != "clean":
        log("  FATAL: the freshly built body does not decode -- refusing to touch any file")
        rep["error"] = f"body decode {st}: {err}"
        C.write_report(args.report, rep)
        log.save(args.log)
        return 2
    if body[-1] != 0x04:
        log(f"  FATAL: body does not end in RETURN(0x04) (ends 0x{body[-1]:02X})")
        rep["error"] = "body missing terminal RETURN"
        C.write_report(args.report, rep)
        log.save(args.log)
        return 2
    ops = _body_ops(body)
    log(f"  opcodes: {ops}")
    if 0x2B not in ops:
        log("  FATAL: no Field(0x2B) in the body")
        rep["error"] = "no Field opcode"
        C.write_report(args.report, rep)
        log.save(args.log)
        return 2
    if 0x2A in ops:
        log("  FATAL: opcode 0x2A (Battle) present -- that is the classic warp-that-is-a-battle trap")
        rep["error"] = "0x2A Battle opcode present"
        C.write_report(args.report, rep)
        log.save(args.log)
        return 2
    rep["body"] = {"bytes": len(body), "instructions": n_instr, "sha256": C.sha(body),
                   "hex": body.hex(), "opcodes": [f"0x{o:02X}" for o in ops]}

    # ---------------------------------------------------------------- pre-flight: all 7 present
    log.rule("(2) pre-flight -- all 7 locale files present and parseable")
    pre: dict = {}
    for lang in EN.LANGS:
        p = C.world_eb_path(target_root, lang, mod_folder=args.mod_folder, name=args.eb_name)
        if not p.is_file():
            log(f"  MISSING {lang}: {p}")
            rep["error"] = f"missing locale file: {p}"
            C.write_report(args.report, rep)
            log.save(args.log)
            return 2
        data = p.read_bytes()
        try:
            eb = EbScript(data)
        except ValueError as ex:
            log(f"  UNPARSEABLE {lang}: {ex}")
            rep["error"] = f"unparseable {lang}: {ex}"
            C.write_report(args.report, rep)
            log.save(args.log)
            return 2
        pre[lang] = {"path": p, "data": data, "eb": eb}
        log(f"  {lang}: {len(data):>6} B  sha {C.sha(data)[:16]}  entries={eb.entry_count}  "
            f"entry0 funcs={eb.entry(0).func_count}  has tag 0x{tag:04X}="
            f"{eb.entry(0).func_by_tag(tag) is not None}")
    # the per-locale independence evidence: jp MUST differ from us (16 B shorter on WORLD00,
    # 12 B on WORLD11/13). Identical bytes across all 7 would mean someone already cloned one.
    sizes = {l: len(v["data"]) for l, v in pre.items()}
    distinct = sorted(set(sizes.values()))
    log(f"  pre-image sizes: {sizes}")
    log(f"  distinct sizes: {distinct}  (jp differing is the proof each locale has its own base)")
    if len(distinct) == 1:
        log("  WARNING: every locale is the same size -- if jp was cloned from us its dialogue is "
            "already gone. This script cannot undo that; it only refuses to make it worse.")
    rep["preimage_sizes"] = sizes

    # ---------------------------------------------------------------- splice per locale
    log.rule("(3) splice, per locale, each against ITS OWN base")
    all_ok = True
    for lang in EN.LANGS:
        p, data, eb = pre[lang]["path"], pre[lang]["data"], pre[lang]["eb"]
        row: dict = {"path": str(p), "pre_bytes": len(data), "pre_sha256": C.sha(data)}
        e0 = eb.entry(0)
        if e0.empty:
            log(f"  {lang}: FATAL entry 0 is empty -- this is not a world dispatcher")
            row["error"] = "entry 0 empty"
            rep["locales"][lang] = row
            all_ok = False
            continue
        existing = e0.func_by_tag(tag)
        if existing is not None:
            old_body = data[existing.abs_start:existing.abs_end]
            if old_body == body:
                mode, out = "already-current", data
            else:
                mode, out = "replace", E.replace_function_body(data, 0, tag, body)
            row["prior_body_bytes"] = len(old_body)
        else:
            mode, out = "add", E.add_function(data, 0, tag, body)
        row["mode"] = mode

        ok, checks = _verify(data, out, body, tag, mode, log_prefix=f"  {lang}: ")
        row["checks"] = checks
        row["post_bytes"] = len(out)
        row["post_sha256"] = C.sha(out)
        row["delta"] = len(out) - len(data)
        log(f"  {lang}: mode={mode:<15} {len(data)} -> {len(out)} B (delta {len(out)-len(data):+d})  "
            f"verify={'PASS' if ok else 'FAIL'}")
        for k, v in checks.items():
            log(f"        {'ok ' if v.get('ok') else 'FAIL'} {k}: {v.get('detail')}")
        if not ok:
            all_ok = False
            rep["locales"][lang] = row
            continue

        if args.dump_disasm:
            d = Path(args.dump_disasm)
            d.mkdir(parents=True, exist_ok=True)
            f = EbScript(out).entry(0).func_by_tag(tag)
            txt = C.disasm_text(out[f.abs_start:f.abs_end],
                                f"{lang} EVT_WORLD_WORLD13 entry0 tag 0x{tag:04X} "
                                f"-> Field({args.dest})")
            (d / f"trigger_{lang}.disasm.txt").write_text(txt, encoding="utf-8")
            row["disasm"] = str(d / f"trigger_{lang}.disasm.txt")

        # ---- backup + write ----
        if mode == "already-current":
            log(f"        (no write: the file already carries this exact body)")
            row["backup"] = None
            row["written"] = False
        else:
            row["backup"] = C.backup_file(p, backup_dir, f"eb/{lang}/{args.eb_name}",
                                          dry_run=args.dry_run)
            if args.dry_run:
                row["written"] = False
                log(f"        DRY RUN: would back up -> {row['backup']['backup']}")
                log(f"        DRY RUN: would write {len(out)} B -> {p}")
            else:
                tmp = p.with_suffix(p.suffix + ".tmp-rung6")
                tmp.write_bytes(out)
                tmp.replace(p)
                row["written"] = True
                back = p.read_bytes()
                row["readback_sha256"] = C.sha(back)
                same = back == out
                log(f"        wrote {len(out)} B; read-back identical={same}")
                if not same:
                    all_ok = False
                    row["error"] = "read-back mismatch"
        rep["locales"][lang] = row

    # ---------------------------------------------------------------- manifest + summary
    if not args.dry_run and any(v.get("backup") for v in rep["locales"].values()):
        C.write_report(backup_dir / "manifest-eb.json",
                       {k: rep[k] for k in ("script", "game", "target_root", "mod_folder",
                                            "eb_name", "cell", "cell_tag", "dest_field",
                                            "world_state", "locales")})
        log(f"  backup manifest -> {backup_dir / 'manifest-eb.json'}")

    rep["ok"] = all_ok
    log.rule("RESULT: " + ("PASS" if all_ok else "FAIL"))
    log(f"  7 locales, tag 0x{tag:04X} -> Field({args.dest}); "
        f"{'nothing written (dry run)' if args.dry_run else 'written'}")
    C.write_report(args.report, rep)
    log.save(args.log)
    return 0 if all_ok else 1


def _body_ops(body: bytes) -> list:
    from ff9mapkit.eb import disasm as D
    return [i.op for i in D.iter_code(body, 0, len(body))]


def _verify(before: bytes, after: bytes, body: bytes, tag: int, mode: str, *, log_prefix="") -> tuple:
    """Every post-splice check the rung demands, as ``{name: {"ok": bool, "detail": str}}``.

    The load-bearing ones: the file still parses; the structural walk finds no NEW ragged function
    (16 zero-length funcs are a stock WORLD11 feature, not damage); the new function is present with
    the EXACT body bytes; the size delta is exactly what the splice primitive should produce; every
    OTHER function in the file is byte-identical; and the per-locale name region is untouched.
    """
    from ff9mapkit.eb.model import EbScript
    out: dict = {}

    def chk(name, ok, detail):
        out[name] = {"ok": bool(ok), "detail": detail}
        return bool(ok)

    ok = True
    try:
        eb_a = EbScript(after)
        ok &= chk("reparse", True, f"{eb_a.entry_count} entries")
    except ValueError as ex:
        chk("reparse", False, str(ex))
        return False, out

    eb_b = EbScript(before)
    ok &= chk("entry_count_stable", eb_a.entry_count == eb_b.entry_count,
              f"{eb_b.entry_count} -> {eb_a.entry_count}")
    ok &= chk("name_region_preserved", eb_a.name_region == eb_b.name_region,
              "the 84-byte per-locale PSX name field survived byte-identical "
              "(a cross-locale clone would change it)")

    # THE GATE IS "NO **NEW** RAGGED FUNCTION", not "zero ragged": the pristine stock WORLD11
    # baseline this file clones already decodes 16 of its funcs as ragged, and every one of those is
    # a ZERO-LENGTH body (fpos == the next func's fpos -- a legitimate stock shape that
    # ``parse_body`` classifies as "empty", so they should not even appear here). Any ragged entry
    # that is NOT in the baseline is real damage. Both counts are reported either way.
    wb, wa = C.structural_walk(before), C.structural_walk(after)
    # compare ragged funcs by (entry, func_index, tag) -- the error string can differ harmlessly
    key = lambda r: (r[0], r[1], r[2])                                          # noqa: E731
    base_keys = {key(r) for r in wb["ragged"]}
    new_ragged = [r for r in wa["ragged"] if key(r) not in base_keys]
    ok &= chk("structural_walk", not new_ragged,
              f"before: {wb['funcs']} funcs / {wb['clean']} clean / {wb['empty']} empty / "
              f"{len(wb['ragged'])} ragged || after: {wa['funcs']} funcs / {wa['clean']} clean / "
              f"{wa['empty']} empty / {len(wa['ragged'])} ragged || NEW ragged: "
              f"{len(new_ragged)}{(' ' + str(new_ragged[:3])) if new_ragged else ''}")

    f = eb_a.entry(0).func_by_tag(tag)
    ok &= chk("func_present", f is not None, f"entry 0 tag 0x{tag:04X}")
    if f is not None:
        got = after[f.abs_start:f.abs_end]
        ok &= chk("body_exact", got == body,
                  f"{len(got)} B at abs {f.abs_start}..{f.abs_end}; sha {C.sha(got)[:16]}")
        ok &= chk("func_count", eb_a.entry(0).func_count ==
                  eb_b.entry(0).func_count + (1 if mode == "add" else 0),
                  f"entry0 funcs {eb_b.entry(0).func_count} -> {eb_a.entry(0).func_count}")

    delta = len(after) - len(before)
    if mode == "add":
        want = len(body) + 4                       # body + one 4-byte func-table slot
        ok &= chk("size_delta", delta == want, f"{delta:+d} == body({len(body)}) + 4 slot bytes")
    elif mode == "replace":
        f_old = eb_b.entry(0).func_by_tag(tag)
        want = len(body) - (f_old.abs_end - f_old.abs_start)
        ok &= chk("size_delta", delta == want, f"{delta:+d} == body({len(body)}) - old body")
    else:
        ok &= chk("size_delta", delta == 0, "no-op re-run")

    # EXACTLY ONE function may differ, and only the one we meant: `add` changes nothing and adds
    # one; `replace` changes the entry-0 function carrying our tag and adds none; `already-current`
    # (an idempotent re-run) changes nothing at all.
    mb, ma = C.func_map(before), C.func_map(after)
    changed = [k for k in mb if k not in ma or ma[k] != mb[k]]
    added = [k for k in ma if k not in mb]
    expected_changed = ([k for k in mb if k[0] == 0 and mb[k][0] == tag]
                        if mode == "replace" else [])
    ok &= chk("other_funcs_untouched",
              sorted(changed) == sorted(expected_changed) and len(added) == (1 if mode == "add" else 0),
              f"{len(mb)} -> {len(ma)} funcs; changed={changed or 'none'} "
              f"(expected {expected_changed or 'none'}); added={added or 'none'}")

    hr = C.eb_headroom(after)
    ok &= chk("u16_headroom", hr["ok"],
              f"max entry off {hr['max_entry_off']} (headroom {hr['off_headroom']}), "
              f"budget used {hr['budget_used']} (headroom {hr['budget_headroom']}); ceiling 0xFFFF")
    return ok, out


if __name__ == "__main__":
    raise SystemExit(main())
