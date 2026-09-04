#!/usr/bin/env python3
"""Replay the memoria-patches stack, per file, from the base commit -- diagnose, snapshot, or EMIT.

WHY: every patch capture in memoria-patches/README.md was gated by hand -- rebuild each file's
pre-round baseline by replaying its lineage, diff to live, apply forward and reverse, compare bytes.
It was done four times by hand for s83 alone and it produced a patch that LOOKED perfect and was
missing a hunk (the README's s83 row). This is that procedure as a tool, with the traps it learned
built in:

  * the DEAD patches (README: s12/s18/s21 never applied; s59 withdrawn) are skipped -- applying s21
    is what made s22/s37/s44 look fuzzy; without it the whole live stack lands at ZERO fuzz;
  * base blobs are CRLF-matched to the autocrlf=true working tree; each patch SECTION's line endings
    are normalised to its target file's (the LF-stored s48 onto a CRLF file);
  * the s22-created DebugMenu blob is BOM-less while the live file carries a BOM -- a BOM is not a
    hunk any patch should own, so comparisons BOM-match;
  * emitted patches are captured as BYTES with `core.autocrlf=false` for that one command (the global
    autocrlf=true clean-filters CRLF worktree files to LF and emits a patch that can never apply), with
    canonical `a/Assembly-CSharp/...` headers and a proper `/dev/null` header for a created file;
  * numbering is CAPTURE order, stack position can differ: POSITION_AFTER pins s84 after s57.

Modes:
  diag       replay and print, per file, whether the result equals LIVE (optionally after stripping
             known insertions from LIVE with --strip, a Python file defining STRIP = {path: [(old,new)]}).
  snapshot   replay (honouring --stop-after) and write the file set to OUT/snap-<label>/.
  emit       replay, then write a patch = diff(tree -> LIVE[stripped]) for --files to --emit-to.

  --skip a,b                extra patch names to skip
  --stop-after NAME         stop after that patch
  --insert-after NAME=PATH  apply PATH right after NAME (an uncaptured patch's stack position)
  --replace NAME=PATH       apply PATH instead of NAME (a regenerated patch, before installing it)
  --files a,b               the file set (default: the netsync / harness / dialog set below)
  --clone PATH              the Memoria source clone (default $MEMORIA_CLONE or C:\\gd\\FFIX\\Memoria)

Gate a capture the way the README rows do: `emit` it, `snapshot` its baseline, `git apply --check` +
`patch -p1 -F0 --dry-run` onto the snapshot, `git apply -R --check` against the clone, then `diag`
with the patch installed -- every file must print `==`.
"""
import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PATCHES = REPO / "memoria-patches"
DEAD = {"s12-engine-edits.patch", "s18-field-reload-hotkey.patch", "s21-dev-hotkeys-f6-f10.patch",
        "s59-debug-warp-settle.patch"}
BOM = b"\xef\xbb\xbf"

DEFAULT_FILES = [
    "Assembly-CSharp/Global/Dialog/Dialog.cs",
    "Assembly-CSharp/Global/Dialog/DialogManager.cs",
    "Assembly-CSharp/Global/UI/UIKey/UIKeyTrigger.cs",
    "Assembly-CSharp/Global/UI/UIKey/Ff9mkDebugMenu.cs",
    "Assembly-CSharp/Global/Hono/HonoInputManager.cs",
    "Assembly-CSharp/Global/TitleUI.cs",
    "Assembly-CSharp/Global/Bundle/BundleSceneSelector.cs",
    "Assembly-CSharp/UnityXInput/Input.cs",
    "Assembly-CSharp/Memoria/Harness/HarnessAgent.cs",
    "Assembly-CSharp/Memoria/Netsync/NetSyncClient.cs",
    "Assembly-CSharp/Memoria/Netsync/NetSyncSocket.cs",
    "Assembly-CSharp/Memoria/Netsync/NetSyncRelay.cs",
    "Assembly-CSharp/Memoria/Netsync/NetSyncState.cs",
    "Assembly-CSharp/Memoria/Netsync/NetSyncField.cs",
    "Assembly-CSharp/Memoria/Netsync/NetSyncBattle.cs",
    "Assembly-CSharp/Memoria/Netsync/NetSyncDiorama.cs",
    "Assembly-CSharp/Memoria/Netsync/NetSyncParty.cs",
    "Assembly-CSharp/Memoria/Netsync/NetSyncVisitor.cs",
]

# Same-number ties, pinned explicitly.
TIE_ORDER = {
    "s48-debug-vehicle-rows.patch": 0, "s48-sfx-output-capture.patch": 1,
    "s83-debug-flag-batch-keyitem.patch": 0, "s83-harness-agent.patch": 1,
}
# Numbering is CAPTURE order; stack position can differ. s84 (F3, built 2026-07-23 night, captured
# 2026-09-04) replays right after s57 -- before s58 -- because s83's DebugMenu/UIKeyTrigger hunks were
# captured from a tree that already carried F3.
POSITION_AFTER = {"s84-netsync-dialogue-lockstep.patch": "s57-netsync-transition-intent.patch"}


def base_commit():
    p = PATCHES / "BASE_COMMIT"
    if p.exists():
        m = re.search(r"(?m)^\s*([0-9a-f]{7,40})\s*$", p.read_text(encoding="utf-8", errors="replace"))
        if m:
            return m.group(1)
    return "6b8bb2d5"


def stack():
    names = [p.name for p in PATCHES.glob("s*.patch")]
    def key(n):
        m = re.match(r"s(\d+)", n)
        return (int(m.group(1)), TIE_ORDER.get(n, 0), n)
    ordered = sorted(names, key=key)
    for moved, anchor in POSITION_AFTER.items():
        if moved in ordered and anchor in ordered:
            ordered.remove(moved)
            ordered.insert(ordered.index(anchor) + 1, moved)
    return ordered


SECTION_RE = re.compile(rb"(?m)^diff --git ")


def sections(patch_bytes):
    starts = [m.start() for m in SECTION_RE.finditer(patch_bytes)]
    if not starts:
        starts = [m.start() for m in re.finditer(rb"(?m)^--- (?:a/|/dev/null)", patch_bytes)]
    out = []
    for i, s in enumerate(starts):
        e = starts[i + 1] if i + 1 < len(starts) else len(patch_bytes)
        sec = patch_bytes[s:e]
        m = re.search(rb"(?m)^\+\+\+ (?:b/)?(\S+)", sec)
        path = m.group(1).decode("utf-8", "replace") if m else None
        out.append((path, sec))
    return out


def normalise_eol(sec, target_crlf):
    has_crlf = b"\r\n" in sec
    if target_crlf and not has_crlf:
        return sec.replace(b"\n", b"\r\n")
    if not target_crlf and has_crlf:
        return sec.replace(b"\r\n", b"\n")
    return sec


def git(*args, cwd, check=True, input=None):
    r = subprocess.run(["git", *args], cwd=str(cwd), capture_output=True, input=input)
    if check and r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed:\n{r.stderr.decode('utf-8', 'replace')}")
    return r


class Replay:
    def __init__(self, clone, files, out):
        self.clone = clone
        self.files = files
        self.out = out
        self.base = base_commit()
        self.work = out / "tree"

    def base_blob(self, path):
        r = git("show", f"{self.base}:{path}", cwd=self.clone, check=False)
        if r.returncode != 0:
            return None
        b = r.stdout
        if b"\r\n" not in b:
            b = b.replace(b"\n", b"\r\n")
        return b

    def materialise(self):
        if self.work.exists():
            shutil.rmtree(self.work)
        self.work.mkdir(parents=True)
        git("init", "-q", cwd=self.work)
        git("config", "core.autocrlf", "false", cwd=self.work)
        git("config", "core.safecrlf", "false", cwd=self.work)
        present = 0
        for f in self.files:
            b = self.base_blob(f)
            if b is None:
                continue
            p = self.work / f
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(b)
            present += 1
        return present

    def apply(self, name, raw):
        secs = [(p, s) for p, s in sections(raw) if p in self.files]
        if not secs:
            return None
        filtered = b""
        for p, s in secs:
            tgt = self.work / p
            target_crlf = (b"\r\n" in tgt.read_bytes()) if tgt.exists() else (b"\r\n" in s)
            filtered += normalise_eol(s, target_crlf)
        touched = ", ".join(Path(p).name for p, _ in secs)
        r = git("apply", "--binary", "--whitespace=nowarn", "-p1", "-", cwd=self.work, check=False, input=filtered)
        if r.returncode == 0:
            return f"ok    {name}: {touched}"
        pf = self.out / "current.patch"
        pf.write_bytes(filtered)
        r2 = subprocess.run(["patch", "-p1", "--binary", "-F3", "-s", "-f", "--no-backup-if-mismatch",
                             "-i", str(pf)], cwd=str(self.work), capture_output=True)
        if r2.returncode != 0:
            print(f"FAIL  {name}: {touched}\n  git apply: {r.stderr.decode('utf-8', 'replace').strip()}\n"
                  f"  patch -F3: {(r2.stdout + r2.stderr).decode('utf-8', 'replace').strip()}")
            sys.exit(2)
        return f"FUZZ  {name}: {touched}  (git apply refused; GNU patch -F3 landed it)"

    def live(self, f, strip):
        lb = (self.clone / f).read_bytes()
        for old, new in strip.get(f, []):
            eol = b"\r\n" if b"\r\n" in lb else b"\n"
            o = old.replace("\n", "\r\n").encode() if eol == b"\r\n" else old.encode()
            n = new.replace("\n", "\r\n").encode() if eol == b"\r\n" else new.encode()
            if lb.count(o) != 1:
                sys.exit(f"strip anchor occurs {lb.count(o)}x in {f}")
            lb = lb.replace(o, n)
        return lb


def bom_match(tree_bytes, live_bytes):
    if live_bytes.startswith(BOM) and not tree_bytes.startswith(BOM):
        return BOM + tree_bytes
    return tree_bytes


def emit_section(out, lhs_dir, rhs_dir, f, tree_bytes, live_bytes, created):
    for d, data in ((lhs_dir, tree_bytes), (rhs_dir, live_bytes)):
        q = d / f
        q.parent.mkdir(parents=True, exist_ok=True)
        q.write_bytes(data)
    r = subprocess.run(["git", "-c", "core.autocrlf=false", "-c", "core.safecrlf=false",
                        "diff", "--no-index", "--binary", str(lhs_dir / f), str(rhs_dir / f)],
                       capture_output=True, cwd=str(out))
    d = r.stdout
    if not d:
        return b""
    lines = d.split(b"\n")
    seen_minus = seen_plus = False
    for i, ln in enumerate(lines):
        if ln.startswith(b"diff --git "):
            lines[i] = b"diff --git a/" + f.encode() + b" b/" + f.encode()
            if created:
                lines.insert(i + 1, b"new file mode 100644")
        elif not seen_minus and ln.startswith(b"--- "):
            lines[i] = (b"--- /dev/null" if created else b"--- a/" + f.encode()); seen_minus = True
        elif not seen_plus and ln.startswith(b"+++ "):
            lines[i] = b"+++ b/" + f.encode(); seen_plus = True
        if seen_minus and seen_plus:
            break
    return b"\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mode", choices=["diag", "snapshot", "emit"])
    ap.add_argument("--stop-after", default=None)
    ap.add_argument("--skip", default="")
    ap.add_argument("--insert-after", action="append", default=[])
    ap.add_argument("--replace", action="append", default=[])
    ap.add_argument("--files", default=None)
    ap.add_argument("--clone", default=os.environ.get("MEMORIA_CLONE", r"C:\gd\FFIX\Memoria"))
    ap.add_argument("--out", default=str(Path(tempfile.gettempdir()) / "memoria-stack-replay"))
    ap.add_argument("--strip", default=None)
    ap.add_argument("--emit-to", default=None)
    ap.add_argument("--label", default="snap")
    args = ap.parse_args()

    files = [f for f in args.files.split(",") if f] if args.files else list(DEFAULT_FILES)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    rp = Replay(Path(args.clone), files, out)
    skip = set(DEAD) | {s for s in args.skip.split(",") if s}
    inserts = dict(kv.split("=", 1) for kv in args.insert_after)
    replaces = dict(kv.split("=", 1) for kv in args.replace)

    present = rp.materialise()
    print(f"base {rp.base}: {present} tracked files materialised, {len(files) - present} start from /dev/null; "
          f"skipping {sorted(skip)}")
    for name in stack():
        if name in skip:
            continue
        src = Path(replaces[name]) if name in replaces else (PATCHES / name)
        line = rp.apply(name + (f" (REPLACED by {src.name})" if name in replaces else ""), src.read_bytes())
        if line:
            print(line)
        if name in inserts:
            ins = Path(inserts[name])
            line = rp.apply(f"{ins.name} (inserted after {name})", ins.read_bytes())
            print(line or f"skip  {ins.name}: touches none of the file set")
        if args.stop_after and name == args.stop_after:
            break

    strip = {}
    if args.strip:
        ns = {"__file__": str(Path(args.strip).resolve())}
        exec(Path(args.strip).read_text(encoding="utf-8"), ns)
        strip = ns["STRIP"]

    if args.mode == "snapshot":
        snap = out / f"snap-{args.label}"
        if snap.exists():
            shutil.rmtree(snap)
        for f in files:
            p = rp.work / f
            if p.exists():
                q = snap / f
                q.parent.mkdir(parents=True, exist_ok=True)
                q.write_bytes(p.read_bytes())
        print(f"snapshot written: {snap}")
        return

    if args.mode == "emit":
        if not args.emit_to:
            sys.exit("emit needs --emit-to")
        lhs, rhs = out / "emit-a", out / "emit-b"
        for d in (lhs, rhs):
            if d.exists():
                shutil.rmtree(d)
        patch = b""
        for f in files:
            created = not (rp.work / f).exists()
            tb = b"" if created else (rp.work / f).read_bytes()
            lb = rp.live(f, strip)
            sec = emit_section(out, lhs, rhs, f, bom_match(tb, lb), lb, created)
            if not sec:
                print(f"  (no delta) {f}")
            patch += sec
        Path(args.emit_to).write_bytes(patch)
        print(f"emitted {args.emit_to}: {len(patch)} bytes, {patch.count(b'diff --git')} file(s), "
              f"{patch.count(b'No newline')} no-newline marker(s)")
        return

    print("\nresidual vs LIVE" + (" (after stripping the known insertions)" if strip else "") + ":")
    exact = 0
    for f in files:
        p = rp.work / f
        if not (rp.clone / f).exists():
            print(f"  {f}: not in the live tree")
            continue
        lb = rp.live(f, strip)
        rb = bom_match(p.read_bytes() if p.exists() else b"", lb)
        if rb == lb:
            exact += 1
            print(f"  ==   {f}")
        else:
            (out / "live").mkdir(exist_ok=True)
            (out / "live" / Path(f).name).write_bytes(lb)
            r = subprocess.run(["git", "diff", "--no-index", "--stat", str(p), str(out / "live" / Path(f).name)],
                               capture_output=True)
            stat = r.stdout.decode("utf-8", "replace").strip().splitlines()[-1] if r.stdout else "?"
            print(f"  DIFF {f}: {stat}")
    print(f"{exact} of {len(files)} files byte-exact")
    sys.exit(0 if exact == len(files) else 1)


if __name__ == "__main__":
    main()
