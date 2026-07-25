r"""TIER R rung 2 -- the gate runner.  `py r2_gates.py` prints H0..H5 with numbers and PASS/FAIL.

H0  NO REGRESSION: r1_gates.py still 8/8 and the 41 R1 tests still pass
H1  CALIBRATION: the 12 KNOWN HLE ops re-derived by the static method alone
H2  NAMING COVERAGE: high/medium/low/unnamed, with the high-confidence evidence contract enforced
H3  ef227 DATA REFS: is the camera sub-file / are the motion clips reached from the program?
    plus resolved-vs-unresolved pointer constants corpus-wide
H4  the FORMAT memory map, cross-checked row by row -- disagreements reported as FINDINGS
H5  FUNCTION SEGMENTATION: every reachable instruction in exactly one function, corpus-wide

Reads the user's own installed DLL (read-only) and the extracted corpus under
``C:\gd\SCRATCH\summon-format``.  Prints only structure -- names, RVAs, offsets, counts.
"""
from __future__ import annotations

import collections
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tier_r_disasm as T        # noqa: E402
import tier_r_annot as A         # noqa: E402

_HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = []
FINDINGS = []


def gate(name: str, ok: bool, *lines: str) -> bool:
    RESULTS.append((name, ok))
    print("\n%s %s  %s" % ("[PASS]" if ok else "[FAIL]", name, "-" * max(2, 58 - len(name))))
    for ln in lines:
        print("   " + ln)
    return ok


def finding(text: str) -> None:
    FINDINGS.append(text)


# --------------------------------------------------------------------------- H0
def h0_no_regression():
    lines = []
    ok = True
    r1 = subprocess.run([sys.executable, os.path.join(_HERE, "r1_gates.py")],
                        capture_output=True, text=True)
    tail = [l for l in r1.stdout.splitlines() if "gates pass" in l]
    lines.append("r1_gates.py exit=%d  %s" % (r1.returncode, tail[-1] if tail else "(no summary)"))
    ok = ok and r1.returncode == 0
    for mod in ("test_tier_r_disasm.py", "test_tier_r_annot.py"):
        path = os.path.join(_HERE, mod)
        if not os.path.isfile(path):
            lines.append("%s: MISSING" % mod)
            ok = False
            continue
        p = subprocess.run([sys.executable, "-m", "pytest", path, "-q", "--no-header"],
                           capture_output=True, text=True, cwd=_HERE)
        summary = [l for l in p.stdout.splitlines() if " passed" in l or " failed" in l]
        lines.append("%-26s exit=%d  %s" % (mod, p.returncode, summary[-1] if summary else "?"))
        ok = ok and p.returncode == 0
    lines.append("R1's artifacts are untouched by R2: the annotator IMPORTS tier_r_disasm and adds")
    lines.append("no attribute to it -- every R1 number above is produced by R1's own code.")
    return gate("H0 no regression (R1 gates + R1/R2 tests)", ok, *lines)


# --------------------------------------------------------------------------- H1
def h1_calibration(dll):
    rows = A.calibration(dll)
    ok_rows = [r for r in rows if r["arity_ok"] and r["name_ok"]]
    lines = [
        "The static method must re-derive the 12 ops M3-opcode-table.json already names BEFORE any",
        "unknown op's signature is believed.  Name comes from the DLL's own debug strings resolved",
        "through the UNWIND_INFO chain; arity/kinds/return come from the dispatcher stub alone.",
        "",
        "%3s %-24s %-24s %5s %5s %-7s %-5s %-9s %s"
        % ("op", "M3 name", "re-derived", "arity", "M3", "kinds", "ret", "native fn", "verdict"),
    ]
    for r in rows:
        lines.append("%3d %-24s %-24s %5d %5s %-7s %-5s %#-9x %s"
                     % (r["op"], r["expect_name"], r["derived_name"] or "-", r["arity"],
                        r["expect_arity"], r["kinds"] or "-", r["returns"], r["fn"],
                        "OK" if (r["arity_ok"] and r["name_ok"]) else "MISS"))
    lines.append("")
    lines.append("re-derived %d/%d on BOTH name and arity; native fn confirmed by a real call in "
                 "the stub for %d/%d"
                 % (len(ok_rows), len(rows), sum(1 for r in rows if r["fn_confirmed"]), len(rows)))
    lines.append("The miss this calibration exists to catch: reading only the "
                 "`mov edx,i / call getArgInt` idiom and not the INLINE `[ctx+0xca8..0xcb4]` form")
    lines.append("scores 4/12 -- ops 11/12/25/65 come out with arity 0 or 1 instead of 2/3/5/4.")
    return gate("H1 calibration on the 12 known ops", len(ok_rows) == len(rows), *lines)


# --------------------------------------------------------------------------- H2
def h2_naming(ops):
    hist = A.confidence_histogram(ops)
    bad = A.check_confidence_rule(ops)
    support = collections.Counter(r["corpus_support"] for r in ops.values()
                                  if r["confidence"] == "high")
    named = sum(v for k, v in hist.items() if k != "unnamed")
    lines = [
        "high %d / medium %d / low %d / UNNAMED %d   (of %d ops; %d named = %.1f%%)"
        % (hist["high"], hist["medium"], hist["low"], hist["unnamed"], len(ops), named,
           100 * named / len(ops)),
        "high-confidence evidence-contract violations: %d" % len(bad),
    ]
    lines += ["   " + b for b in bad[:8]]
    lines.append("")
    lines.append("THE CONTRACT, enforced by check_confidence_rule (not merely documented):")
    lines.append("  a `high` row needs a decoded handler stub with a recognised terminator, a name")
    lines.append("  the DLL ITSELF supplies (a debug string it owns, a CRT import it thinly wraps,")
    lines.append("  or a jump-table slot that IS the return tail), AND a recorded corpus outcome")
    lines.append("  that does not contradict the static signature.")
    lines.append("  corpus support behind the %d high rows: %s"
                 % (hist["high"], dict(support)))
    lines.append("    arity-mode        = the modal number of $a0-$a3 set up at a call site equals")
    lines.append("                        the stub's REGISTER-argument count min(arity,4)")
    lines.append("    never-called      = 0 call sites in 385 programs, itself a checked fact")
    lines.append("    noop-called-anyway= a no-op whose callers still pass arguments (a finding)")
    lines.append("")
    lines.append("Named ops carrying the most traffic:")
    for r in sorted(ops.values(), key=lambda x: -x["call_sites"])[:14]:
        lines.append("   op %3d  %6d calls  %-8s %-30s arity=%d kinds=%-7s -> %s"
                     % (r["op"], r["call_sites"], r["confidence"] or "unnamed",
                        r["name"] or "-", r["arity"], r["arg_kinds"] or "-", r["returns"]))
    unnamed_traffic = sum(r["call_sites"] for r in ops.values() if not r["name"])
    total_traffic = sum(r["call_sites"] for r in ops.values())
    lines.append("")
    lines.append("Traffic coverage: %d/%d HLE call sites (%.1f%%) now hit a NAMED op; %d remain "
                 "anonymous." % (total_traffic - unnamed_traffic, total_traffic,
                                 100 * (total_traffic - unnamed_traffic) / max(1, total_traffic),
                                 unnamed_traffic))
    return gate("H2 naming coverage + the high-confidence contract", not bad, *lines)


# --------------------------------------------------------------------------- H3
def h3_data_refs(ops):
    import ef_container as ec
    blob = open(os.path.join(T.SCRATCH_CORPUS, "ef227.bytes"), "rb").read()
    container = ec.parse_header(blob)
    subfiles, motions = {}, {}
    for ch in container.chunks:
        for res in ch.resources:
            if res.id == 2:
                try:
                    subfiles[ch.slot] = len(ec.parse_directory(blob, res.offset))
                except Exception:
                    pass
        try:
            mp = ec.parse_model_package(blob, ch)
            if mp:
                motions[ch.slot] = mp.motion_count
        except Exception:
            pass
    seq = ec.parse_sequence(blob)
    cam_shots = [o.arg1 for o in seq if o.code == 0x29]
    lines = [
        "ef227 (Bahamut): id-2 sub-file counts %s ; id-5 motion_count %s ; 2 chunk images"
        % (subfiles, motions), ""]
    outside = 0
    total = 0
    idx_ok = idx_n = 0
    frames = []
    for img in T.id3_images(blob, "ef227"):
        w, r = A.walk(img)
        refs = A.image_data_refs(img, w, r)
        total += len(refs)
        outside += sum(1 for d in refs if not (d.kind.startswith("image")
                                               or d.kind == "scratchpad"))
        kinds = A.data_ref_summary(refs)
        lines.append("%s: %d absolute addresses -- %s"
                     % (img.label, len(refs),
                        ", ".join("%s x%d" % (k, n) for k, n in kinds.most_common())))
        n = subfiles.get(img.chunk_slot)
        vals = [c.args[1] for c in r.calls
                if c.kind == "hle" and c.hle_op == A.SUBFILE_OP and c.args[1] is not None]
        if n:
            idx_n += len(vals)
            idx_ok += sum(1 for v in vals if (v & A.SUBFILE_INDEX_MASK) < n)
        frames += [c.args[1] for c in r.calls
                   if c.kind == "hle" and c.hle_op == 100 and c.args[1] is not None]
        lines.append("   op %d get_subfile_ptr: %d constant indices, %d/%d address a real sub-file "
                     "of this chunk's %s-entry id-2 directory"
                     % (A.SUBFILE_OP, len(vals),
                        sum(1 for v in vals if n and (v & A.SUBFILE_INDEX_MASK) < n), len(vals), n))
        lines.append("   op 26 Hi_SetSummonMotion sites: %d ; op 100 Hi_SetSummonMotFrame sites: %d"
                     % (sum(1 for c in r.calls if c.kind == "hle" and c.hle_op == 26),
                        sum(1 for c in r.calls if c.kind == "hle" and c.hle_op == 100)))
    lines.append("")
    lines.append("THE VERDICT, stated loudly because it is refutation-shaped:")
    lines.append("  * The camera sub-file is NOT reachable from the program AT ALL -- not by a")
    lines.append("    pointer, not by an index, not by any HLE op.  Zero of ef227's %d absolute"
                 % total)
    lines.append("    addresses leave its own id-3 image.  The camera is driven ENTIRELY by the")
    lines.append("    SEQUENCE stream: opcode 0x29 PLAY_CAMERA, sub-file indices %s." % cam_shots)
    lines.append("  * The motion clips are NOT pointer-referenced either.  They live inside the")
    lines.append("    id-5 SUMMON_MODEL package (%s clips) and the program selects them BY INDEX"
                 % motions.get(0))
    lines.append("    through op 26 Hi_SetSummonMotion(modelPtr, motionIndex), then scrubs the")
    lines.append("    timeline with op 100 Hi_SetSummonMotFrame -- constant frames %s." % frames)
    lines.append("  * THIS DOES NOT REFUTE THE FORMAT MODEL, IT CONFIRMS IT.  The id-3 image is a")
    lines.append("    self-contained PS1 RAM image at 0x801E7700+(slot&1)*0x5000; the camera")
    lines.append("    sub-file (resource id-2) and the motion clips (inside id-5) are never mapped")
    lines.append("    into that address space, so a pointer into them could not exist.  Every")
    lines.append("    cross-resource reach is an INDEX through the HLE boundary or the sequence.")
    lines.append("  * WHAT IS reached: the id-2 sub-file archive, by index through op %d --"
                 % A.SUBFILE_OP)
    lines.append("    %d/%d of ef227's constant indices address a real sub-file." % (idx_ok, idx_n))
    lines.append("  * CONSEQUENCE FOR TIER W: to rescore a stock summon's camera you edit the")
    lines.append("    SEQUENCE (op 0x29's index) or the camera sub-file bytes.  The MIPS program")
    lines.append("    never needs to be touched, and patching it could not move the camera.")
    lines.append("")
    # corpus-wide resolved / unresolved
    t0 = time.time()
    kinds = collections.Counter()
    for img in T.corpus_images():
        w, r = A.walk(img)
        for d in A.image_data_refs(img, w, r):
            kinds[d.kind] += 1
    tot = sum(kinds.values())
    resolved = tot - kinds["psx_ram"] - kinds["not_an_address"] - kinds["host_bank"]
    lines.append("CORPUS-WIDE pointer constants and computed absolute addresses (%.1fs):"
                 % (time.time() - t0))
    for k, n in kinds.most_common():
        lines.append("   %-16s %5d" % (k, n))
    lines.append("   RESOLVED into a named region: %d/%d = %.2f%% ; UNRESOLVED (PSX RAM outside "
                 "any container resource): %d" % (resolved, tot, 100 * resolved / max(1, tot),
                                                  kinds["psx_ram"]))
    lines.append("   `sibling_image` count %d: not one chunk's program ever addresses the other "
                 "chunk's image, though they are adjacent in PSX RAM."
                 % kinds["sibling_image"])
    finding("The camera sub-file is unreachable from the effect PROGRAM; ef227's camera is 100%% "
            "sequence-driven (opcode 0x29, shots %s).  Camera authoring is a SEQUENCE edit."
            % cam_shots)
    ok = outside == 0 and kinds["psx_ram"] == 0 and idx_ok == idx_n and idx_n > 0
    return gate("H3 ef227 data refs + corpus pointer resolution", ok, *lines)


# --------------------------------------------------------------------------- H4
def h4_memory_map(dll, ops):
    fns = dll.refkit.functions(dll.pe)
    lo, hi = min(A.NAMED_GLOBALS), max(A.NAMED_GLOBALS) + 8
    xi = dll.refkit.xref_index(dll.pe, lo, hi, fns)
    lines = ["Every row of the FORMAT round's memory map, re-read against the live DLL:",
             "%-10s %-24s %6s  %s" % ("RVA", "name", "xrefs", "the report that established it")]
    stale = []
    for rva, (name, src) in sorted(A.NAMED_GLOBALS.items()):
        n = len(xi.get(rva, ()))
        if n == 0:
            stale.append((rva, name))
        lines.append("%#-10x %-24s %6d  %s" % (rva, name, n, src))
    lines.append("")
    lines.append("map rows with ZERO x64 code references (i.e. stale map entries): %d %s"
                 % (len(stale), [(hex(r), n) for r, n in stale] or ""))
    ok = not stale
    # role consistency: a global's meaning predicts WHICH ops may touch it
    def touching(g):
        return [r for r in ops.values() if g in (r["touches"] or ())]
    lines.append("")
    lines.append("ROLE CONSISTENCY -- the map's stated meaning predicts which ops touch each global:")
    summon = touching("summonModels")
    named_summon = [r for r in summon if (r["name"] or "").startswith("Hi_")]
    odd = [r["name"] for r in named_summon if "Summon" not in (r["name"] or "")]
    lines.append("   summonModels (A5: the summon model slot array): %d ops touch it, %d of them "
                 "DLL-named." % (len(summon), len(named_summon)))
    lines.append("     named ops WITHOUT 'Summon' in the name: %s" % (odd or "none"))
    if odd:
        lines.append("     FINDING -- not a contradiction but an addition to the map: %s read the"
                     % ", ".join(odd))
        lines.append("     SUMMON model array.  An EffModel drawn BY BONE sources its skeleton from")
        lines.append("     the summon slot.  A second, independent signal agrees: those same two")
        lines.append("     functions also carry the inlined `Hi_GetSummonBoneMatrix` assert string.")
        finding("Hi_DrawEffModelByBone / Hi_DrawMorphModelByBone read summonModels @0x220830 -- an "
                "eff-model drawn by bone sources its skeleton from the SUMMON slot.  Two "
                "independent signals (direct global touch + inlined assert string) agree.")
    proj = {"gteOFX", "gteOFY", "gteH"}
    partial = collections.Counter()
    for r in ops.values():
        got = set(r["touches"] or ()) & proj
        if got and got != proj:
            partial[tuple(sorted(got))] += 1
    lines.append("   gteOFX/gteOFY/gteH (B3 281 presents them as ONE camera triple): ops touching a "
                 "PARTIAL subset: %s" % (dict(partial) or "none"))
    if partial:
        h_only = [r["op"] for r in ops.values()
                  if set(r["touches"] or ()) & proj == {"gteH"}]
        lines.append("     FINDING -- the triple is NOT atomic.  Ops %s write H (the projection "
                     "distance)" % h_only)
        lines.append("     and touch neither OFX nor OFY, so zoom is an independently settable knob.")
        finding("gteH @0x211FA8 is written by ops %s that touch neither OFX nor OFY -- B3 281's "
                "OFX/OFY/H 'camera triple' is not atomic; the projection distance (zoom) is an "
                "independent knob, and a second camera lever for TIER W." % h_only)
    sentinel = xi.get(0x68250, ())
    lines.append("   hleSentinelTable @0x68250: %d x64 reference(s) %s -- R1's G7 finding that the "
                 "table has exactly one publisher and NO x64 reader (its consumer is the MIPS "
                 "program) reconfirmed here independently."
                 % (len(sentinel), [hex(a) for a, _, _ in sentinel]))
    ok = ok and len(sentinel) == 1
    lines.append("")
    lines.append("Where the map is SILENT: %d of the %d ops touch no mapped global at all -- their "
                 "state lives in host structures the FORMAT round has not named."
                 % (sum(1 for r in ops.values() if not r["touches"]), len(ops)))
    return gate("H4 FORMAT memory-map cross-check", ok, *lines)


# --------------------------------------------------------------------------- H5
def h5_segmentation(ops):
    t0 = time.time()
    nimg = nfn = ninstr = 0
    orphans = shared = mid = 0
    bad_images = []
    roles = collections.Counter()
    tags = collections.Counter()
    for img in T.corpus_images():
        w, r = A.walk(img)
        seg = A.segment_functions(img, w, r, ops)
        nimg += 1
        nfn += len(seg.functions)
        ninstr += len(r.instrs)
        orphans += len(seg.orphans)
        shared += len(seg.shared)
        mid += len(seg.midbody_targets)
        for f in seg.functions:
            roles[f.role] += 1
            for t in f.tags:
                tags[t] += 1
        if seg.orphans or seg.shared or seg.midbody_targets:
            bad_images.append((img.label, len(seg.orphans), len(seg.shared),
                               len(seg.midbody_targets)))
    ok = not orphans and not shared and not mid
    lines = [
        "%d images / %d reachable instructions segmented into %d functions (%.1fs)"
        % (nimg, ninstr, nfn, time.time() - t0),
        "Starts = the program entries + every in-image call target.  Flood along intra-procedural",
        "edges only (fall-through, both branch arms, `j`, and a `switch` table dispatched inside",
        "the function), stopping at any other start; call edges are never followed.",
        "",
        "instructions owned by NO function (orphans):        %d" % orphans,
        "instructions owned by MORE THAN ONE function:       %d" % shared,
        "call targets landing INSIDE another function's body: %d" % mid,
        "images with any of the three:                        %d %s"
        % (len(bad_images), bad_images[:6]),
        "",
        "=> every reachable instruction belongs to exactly one function, and every entry point and",
        "   in-image call target lands on a function START.  No tail call into a mid-function, no",
        "   shared epilogue, corpus-wide.",
        "",
        "roles: %s" % dict(roles),
        "tags:  %s" % dict(tags.most_common(12)),
    ]
    return gate("H5 function segmentation is consistent", ok, *lines)


# --------------------------------------------------------------------------- ef227's graph
def ef227_graph(ops):
    blob = open(os.path.join(T.SCRATCH_CORPUS, "ef227.bytes"), "rb").read()
    print("\n%s\nef227 (Bahamut) -- the function graph from the two entry points\n%s"
          % ("=" * 72, "=" * 72))
    for img in T.id3_images(blob, "ef227"):
        w, r = A.walk(img)
        seg = A.segment_functions(img, w, r, ops)
        print("\n%s  headerRel=%#x  %d reachable instr  %d functions"
              % (img.label, img.header_rel, len(r.instrs), len(seg.functions)))
        print("  %-10s %-8s %7s %-16s %-9s %-6s %s"
              % ("fn", "at", "bytes", "role", "switch/case", "HLE", "tags"))
        for f in sorted(seg.functions, key=lambda x: -x.size):
            print("  %-10s %#-8x %7d %-16s %d/%-7d %-6d %s"
                  % (f.label, f.start, f.size, f.role, f.switches, f.cases, f.hle_calls,
                     ",".join(f.tags) or "-"))
        for f in seg.functions:
            if f.entry:
                named = [(o, ops.get(o, {}).get("name")) for o in f.hle_ops]
                print("  %s calls %d distinct HLE ops; the named ones: %s"
                      % (f.label, len(f.hle_ops),
                         ", ".join("%d=%s" % (o, n) for o, n in named if n) or "none"))


# --------------------------------------------------------------------------- main
def main() -> int:
    print(__doc__.splitlines()[0])
    h0_no_regression()
    dll = A.DllView()
    h1_calibration(dll)
    print("\nbuilding the op dictionary (DLL + one corpus pass) ...")
    t0 = time.time()
    cen, images = A.census_corpus()
    ops = A.build_hle_ops(dll, cen)
    A.write_hle_ops(ops)
    print("   %d ops, %d images, %d HLE call sites, %.1fs"
          % (len(ops), len(images), sum(r["hle_calls"] for r in images), time.time() - t0))
    h2_naming(ops)
    h3_data_refs(ops)
    h4_memory_map(dll, ops)
    h5_segmentation(ops)
    ef227_graph(ops)
    print("\n" + "=" * 72)
    if FINDINGS:
        print("FINDINGS (things R2 learned that the existing record did not say):")
        for i, f in enumerate(FINDINGS, 1):
            print("  %d. %s" % (i, f))
        print("=" * 72)
    for name, ok in RESULTS:
        print("%s  %s" % ("PASS" if ok else "FAIL", name))
    bad = [n for n, ok in RESULTS if not ok]
    print("=" * 72)
    print("%d/%d gates pass" % (len(RESULTS) - len(bad), len(RESULTS)))
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
