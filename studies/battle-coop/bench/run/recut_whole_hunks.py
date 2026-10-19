"""Re-cut chosen file sections of an emitted memoria patch so that named BLOCKS sit WHOLE in one hunk.

WHY: the capture law "a selftest block rewritten from an earlier patch must sit WHOLE in one hunk" (the repo tests read a block off
ONE patch's new side -- `_cs_block` / `_s13N_block`); `memoria_stack_replay.py emit` writes git's -U3 hunks, which split a block
that a patch edits in several places. s132 did this by hand (50 lines of context); this is that step as a script.

The alignment is git's own (`git diff --no-index -U0` of the same two files); only the context policy changes: every change keeps
3 lines of context; every forced new-side range [start marker .. stop marker] (the stop line INCLUDED -- the readers stop AT it)
that contains a change is included whole; runs that touch are one hunk; and every hunk's leading and trailing context are padded
to the SAME length (GNU patch reads asymmetric context as anchored to the file's start / end, and -F0 cannot relax it). The
section's diff/index/---/+++ header lines are kept; sections not in the spec pass through byte for byte.

usage (after `memoria_stack_replay.py emit ... --out <OUT> --emit-to <patch>`):
    py -X utf8 recut_whole_hunks.py <patch> <OUT>/emit-a <OUT>/emit-b s140_whole_hunks.json
spec: {"<repo path>": [["<start prefix>", "<stop prefix>"], ...] | "all"}   ("all" = one hunk from the first change to the last)
Then re-run every capture gate (apply --check onto the baseline snapshot, patch -F0 --dry-run, apply -R --check vs the clone,
--numstat, diag): the re-cut must replay byte-exact.
"""
import json, re, subprocess, sys
from pathlib import Path

CTX = 3


def split_keep(b):
    out, i = [], 0
    while i < len(b):
        j = b.find(b"\n", i)
        if j < 0:
            out.append(b[i:])
            break
        out.append(b[i:j + 1])
        i = j + 1
    return out


def rows_of(old_p, new_p, old, new):
    r = subprocess.run(["git", "-c", "core.autocrlf=false", "diff", "--no-index", "-U0", "--binary", str(old_p), str(new_p)],
                       capture_output=True)
    hunks = []
    for ln in r.stdout.split(b"\n"):
        m = re.match(rb"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@", ln)
        if m:
            os_, ol = int(m.group(1)), int(m.group(2) if m.group(2) is not None else 1)
            ns_, nl = int(m.group(3)), int(m.group(4) if m.group(4) is not None else 1)
            o0 = os_ if ol == 0 else os_ - 1
            n0 = ns_ if nl == 0 else ns_ - 1
            hunks.append((o0, ol, n0, nl))
    rows, o, n = [], 0, 0
    for o0, ol, n0, nl in hunks:
        while o < o0:
            assert old[o] == new[n], (o, n)
            rows.append(("=", o, n)); o += 1; n += 1
        assert n == n0, (n, n0)
        for k in range(ol):
            rows.append(("-", o + k, None))
        for k in range(nl):
            rows.append(("+", None, n + k))
        o += ol; n += nl
    while o < len(old):
        assert old[o] == new[n]
        rows.append(("=", o, n)); o += 1; n += 1
    assert n == len(new)
    return rows


def funcname(old, o_start):
    for i in range(o_start - 1, -1, -1):
        t = old[i].rstrip(b"\r\n")
        if re.match(rb"^[A-Za-z_$]", t):
            return b" " + t
    return b""


def recut(old, new, rows, forced):
    keep = [False] * len(rows)
    change = [i for i, r in enumerate(rows) if r[0] != "="]
    for i in change:
        keep[i] = True
    # context: CTX equal rows on each side of every change row
    for i in change:
        for d in (-1, 1):
            k, c = i + d, 0
            while 0 <= k < len(rows) and c < CTX:
                if rows[k][0] == "=":
                    c += 1
                keep[k] = True
                k += d
    if forced == "all":
        lo, hi = min(i for i in range(len(rows)) if keep[i]), max(i for i in range(len(rows)) if keep[i])
        for i in range(lo, hi + 1):
            keep[i] = True
    else:
        newtext = [t.rstrip(b"\r\n").strip() for t in new]
        for start, stop in forced:
            s = next((n for n, t in enumerate(newtext) if t.startswith(start.encode())), None)
            assert s is not None, start
            e = next((n for n in range(s + 1, len(newtext)) if newtext[n].startswith(stop.encode())), None)
            assert e is not None, stop
            # rows spanning new lines [s, e) and every deletion between them
            idx = [i for i, r in enumerate(rows) if r[2] is not None and s <= r[2] <= e]   # the stop line too (readers stop AT it)
            lo, hi = min(idx), max(idx)
            if any(rows[i][0] != "=" for i in range(lo, hi + 1)):
                for i in range(lo, hi + 1):
                    keep[i] = True
    # SYMMETRIC CONTEXT: GNU patch reads a hunk whose leading and trailing context differ as anchored to the file's start / end
    # (and -F0 cannot relax it), so the shorter side of every run is padded with more equal lines until both match.
    for _ in range(50):
        changed = False
        runs, i = [], 0
        while i < len(rows):
            if not keep[i]:
                i += 1
                continue
            j = i
            while j < len(rows) and keep[j]:
                j += 1
            runs.append((i, j))
            i = j
        for i, j in runs:
            lead = 0
            while i + lead < j and rows[i + lead][0] == "=":
                lead += 1
            trail = 0
            while j - 1 - trail >= i and rows[j - 1 - trail][0] == "=":
                trail += 1
            if lead == trail:
                continue
            if lead < trail:
                need, k = trail - lead, i - 1
                while need and k >= 0 and rows[k][0] == "=":
                    keep[k] = True; need -= 1; k -= 1
            else:
                need, k = lead - trail, j
                while need and k < len(rows) and rows[k][0] == "=":
                    keep[k] = True; need -= 1; k += 1
            changed = True
        if not changed:
            break
    out, i = [], 0
    while i < len(rows):
        if not keep[i]:
            i += 1
            continue
        j = i
        while j < len(rows) and keep[j]:
            j += 1
        seg = rows[i:j]
        olds = [r[1] for r in seg if r[1] is not None]
        news = [r[2] for r in seg if r[2] is not None]
        o_start = (olds[0] + 1) if olds else 0
        n_start = (news[0] + 1) if news else 0
        ol, nl = len(olds), len(news)
        assert ol and nl
        hdr = b"@@ -%d,%d +%d,%d @@" % (o_start, ol, n_start, nl) + funcname(old, o_start - 1) + b"\n"
        body = []
        for kind, o, n in seg:
            if kind == "=":
                body.append(b" " + new[n])
            elif kind == "-":
                body.append(b"-" + old[o])
            else:
                body.append(b"+" + new[n])
        out.append(hdr + b"".join(body))
        i = j
    return out


def main():
    patch_p, old_root, new_root, spec_p = sys.argv[1:5]
    spec = json.loads(Path(spec_p).read_text(encoding="utf-8"))
    data = Path(patch_p).read_bytes()
    parts = re.split(rb"(?m)^(?=diff --git )", data)
    outparts = []
    for part in parts:
        if not part:
            continue
        m = re.match(rb"diff --git a/(\S+) b/(\S+)", part)
        path = m.group(2).decode()
        if path not in spec:
            outparts.append(part)
            continue
        head_end = part.index(b"\n@@") + 1
        header = part[:head_end]
        old_p, new_p = Path(old_root) / path, Path(new_root) / path
        old, new = split_keep(old_p.read_bytes()), split_keep(new_p.read_bytes())
        rows = rows_of(old_p, new_p, old, new)
        hunks = recut(old, new, rows, spec[path])
        print(path, "hunks", len(hunks))
        outparts.append(header + b"".join(hunks))
    Path(patch_p).write_bytes(b"".join(outparts))


main()
