"""``.ff9build.json`` -- what a built mod folder says about itself, and what changed since last time.

Nothing in the kit recorded the link between a deployed mod and the source that produced it. ``ModDescription.xml``
is the only descriptive file a build writes and it carries no id at all, so a live folder could not answer
"what am I, and from what?" -- which is why "what did this change invalidate?" had no mechanism behind it.

The stamp is a per-member resolution table: ``{name, id, text_block, flag_lo, flag_hi}``. Those last two are
the point. A member's story-flag window is ``flag_base + i * flags_per_field`` computed from its POSITION in
the manifest and stored NOWHERE, so it moves silently whenever the position or the width changes -- deleting a
member, reordering the ``[[field]]`` rows, a recompose resetting ``flags_per_field``, or appending one field to
an earlier campaign of a journey (which slides every later campaign's window). The bits are save-persistent, so
a moved window means a live save reads the wrong ones: doors already open, cutscenes replaying, a gated NPC
permanently mute. Every one of those was invisible because no artifact recorded where the window used to be.

So the stamp is written to be DIFFED, not merely to exist. :func:`diff` classifies a moved flag window or a
moved text block as BLOCKING -- the build refuses rather than silently relocating a player's story state --
while an id change is reported only, because that one is already loud (``lint_campaign``'s manifest/artifact
reconciliation, and ``reid``'s own report).

It ships with the dist through ``deploy``'s existing ``copytree``, so an installed folder self-identifies.
"""

from __future__ import annotations

import datetime
import hashlib
import json
from dataclasses import dataclass, field as _dcfield
from pathlib import Path

from . import fsutil

STAMP_NAME = ".ff9build.json"
STAMP_VERSION = 1


def stamp_path(out_root) -> Path:
    return Path(out_root) / STAMP_NAME


def compute(projects, *, mod_name: str, source=None, context: str = "standalone") -> dict:
    """The stamp for a set of built projects. Pure -- derivable BEFORE anything is written, which is what
    lets the diff refuse a bad build instead of reporting one that already happened."""
    from . import __version__
    members = []
    for p in projects:
        base = getattr(p, "flag_base", None)
        width = getattr(p, "flags_per_field", None)
        lo = int(base) if base is not None else None
        hi = (lo + int(width) - 1) if (lo is not None and width) else None
        members.append({"name": str(p.name), "id": int(p.id), "text_block": int(p.text_block),
                        "flag_lo": lo, "flag_hi": hi})
    return {
        "stamp_version": STAMP_VERSION,
        "kit_version": __version__,
        "built_utc": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "mod_name": str(mod_name),
        # A campaign built INSIDE a journey gets its flag window and mesID base assigned by the journey
        # (campaign.build_campaign's flag_base / text_block_base overrides), and both journey and standalone
        # builds land in the SAME <campaign>/dist. Those two are legitimately different numbers for the same
        # source, so the diff must not treat one following the other as a corrupting move -- it records the
        # context and reports that case instead of blocking it. (It IS a real divergence: the same
        # campaign.toml built two ways yields saves that are not interchangeable. Reporting keeps it visible
        # without training the author to pass --reflow-flags on every build, which would kill the gate.)
        "context": str(context),
        "source": str(source) if source else None,
        "members": sorted(members, key=lambda m: m["id"]),
    }


# A 64-bit prefix of the sha256, not the whole digest. This detects DRIFT -- a file that changed since the
# build wrote it -- not an adversary, so collision resistance is not the property being bought; 1900 files at
# 64 hex chars is 120KB of JSON shipped into every mod folder for no gain.
_DIGEST_CHARS = 16


def _rel(root: Path, p: Path) -> str:
    """POSIX-style relative path -- the stamp travels between a dist and an install, and a backslash key
    written on Windows would never match a lookup made anywhere else."""
    return p.relative_to(root).as_posix()


def content_digest(root) -> dict:
    """``{relative path: digest}`` for every file under ``root`` except the stamp itself.

    This is the half the first version left out. The resolution table answers "did a member's window move";
    it cannot answer "is what is installed still what the build produced". Nothing else can either --
    ModDescription.xml carries no id, and the deploy ledger records that an id was deployed, not what bytes
    landed. So a hand-edited ``.eb`` in the live folder, a half-finished copy, or an install left behind by
    another worktree all read as healthy."""
    root = Path(root)
    out = {}
    for p in sorted(root.rglob("*")):
        if not p.is_file() or p.name == STAMP_NAME:
            continue
        h = hashlib.sha256()
        with open(p, "rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 20), b""):
                h.update(chunk)
        out[_rel(root, p)] = h.hexdigest()[:_DIGEST_CHARS]
    return out


def finalize(stamp: dict, root) -> dict:
    """Add the content digest to a stamp, AFTER the build wrote its files.

    Deliberately separate from :func:`compute`, which must stay pure over the projects so the diff can
    REFUSE a bad build before anything is written. Hashes can only exist once the bytes do."""
    return {**stamp, "files": content_digest(root)}


@dataclass
class VerifyReport:
    """What a folder's own stamp says about it now."""
    root: Path
    stamp: "dict | None" = None
    missing: list = _dcfield(default_factory=list)     # the build wrote it; it is not there now
    changed: list = _dcfield(default_factory=list)     # there, with different bytes
    extra: list = _dcfield(default_factory=list)       # there, and no build put it there

    @property
    def has_stamp(self) -> bool:
        return bool(self.stamp)

    @property
    def has_digest(self) -> bool:
        return bool(self.stamp and self.stamp.get("files"))

    @property
    def clean(self) -> bool:
        return self.has_digest and not (self.missing or self.changed or self.extra)

    def render(self) -> str:
        if not self.has_stamp:
            return (f"{self.root}: NO {STAMP_NAME} -- nothing here records what built this folder, so drift "
                    f"cannot be judged. Rebuild it with a current kit to give it one.")
        s = self.stamp
        head = (f"{self.root}\n  built {s.get('built_utc', '?')} by kit {s.get('kit_version', '?')} "
                f"({s.get('context', '?')}) from {s.get('source') or 'an unrecorded source'}\n"
                f"  mod {s.get('mod_name', '?')}, {len(s.get('members', []))} member(s)")
        if not self.has_digest:
            return head + "\n  (this stamp predates content hashing -- identity only, no drift check)"
        if self.clean:
            return head + f"\n  {len(s['files'])} file(s) match the build EXACTLY"
        L = [head, f"  DRIFT vs the build that wrote this folder:"]
        for f in self.changed[:20]:
            L.append(f"    ~ {f} (different bytes)")
        for f in self.missing[:20]:
            L.append(f"    - {f} (gone)")
        for f in self.extra[:20]:
            L.append(f"    + {f} (not from this build)")
        n = len(self.changed) + len(self.missing) + len(self.extra)
        if n > 60:
            L.append(f"    ... and {n - 60} more")
        return "\n".join(L)


def verify(root) -> VerifyReport:
    """Re-hash a folder and compare it to its own stamp. Works on a dist AND on a live mod folder -- the
    stamp ships with the dist through deploy's copytree, so an install can answer for itself."""
    root = Path(root)
    rep = VerifyReport(root=root, stamp=read(root))
    if not rep.has_digest:
        return rep
    recorded = rep.stamp["files"]
    actual = content_digest(root)
    rep.missing = sorted(set(recorded) - set(actual))
    rep.extra = sorted(set(actual) - set(recorded))
    rep.changed = sorted(k for k in set(recorded) & set(actual) if recorded[k] != actual[k])
    return rep


def read(out_root) -> "dict | None":
    """The stamp already in ``out_root``, or ``None`` when absent / unreadable / malformed. A missing stamp
    is the FIRST-BUILD case and must stay silent -- but see :func:`write`, which is deliberately not
    best-effort, so a stamp can only be missing because none was ever written."""
    p = stamp_path(out_root)
    if not p.is_file():
        return None
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) and isinstance(data.get("members"), list) else None


def write(out_root, stamp: dict) -> Path:
    """Write the stamp. NOT best-effort, unlike the advisory engine stamp: a swallowed failure here would
    leave the NEXT build with no baseline, and a gate that silently stops gating is worse than no gate."""
    p = stamp_path(out_root)
    p.parent.mkdir(parents=True, exist_ok=True)
    fsutil.atomic_write_text(p, json.dumps(stamp, indent=2) + "\n", newline="\n")
    return p


@dataclass
class StampDiff:
    """What moved between two builds of the same mod folder."""
    added: list = _dcfield(default_factory=list)          # names
    removed: list = _dcfield(default_factory=list)        # names
    moved_ids: list = _dcfield(default_factory=list)      # (name, old, new)          -- reported
    moved_flags: list = _dcfield(default_factory=list)    # (name, (lo,hi), (lo,hi))  -- BLOCKING
    moved_blocks: list = _dcfield(default_factory=list)   # (name, old, new)          -- BLOCKING
    total: int = 0
    prior_kit: str = ""
    context_changed: "tuple | None" = None                # (old, new) when the build CONTEXT differs

    @property
    def blocking(self) -> bool:
        """A moved flag window or text block relocates state a SAVE already depends on. An id change does
        not qualify: it is already caught by lint's manifest/artifact reconciliation and reported by reid.

        A CONTEXT change (standalone <-> journey) is exempt ONLY for the moves it can actually explain.
        The first version exempted the lot, which disarmed the gate for exactly the workflow it was written
        for: a journey and a standalone build share one <campaign>/dist/.ff9build.json, so DELETING a member
        and then pressing the Workspace's Build-campaign button flips the context, and the real drift shipped
        under a banner calling it the journey's assignment.

        What a rebase actually looks like is a UNIFORM shift: the journey hands the campaign a new
        flag_base/text_block_base, so EVERY member moves by the same delta and keeps its width. A member that
        moved by a different delta, changed width, or appeared/vanished did not move because of the rebase --
        that is real drift, and it still blocks."""
        if not (self.moved_flags or self.moved_blocks):
            return False
        if not self.context_changed:
            return True
        if self.added or self.removed:
            return True                      # a changed member set is not something a rebase explains
        widths_kept = all((a[1] - a[0]) == (b[1] - b[0]) for _, a, b in self.moved_flags)
        flag_deltas = {b[0] - a[0] for _, a, b in self.moved_flags}
        block_deltas = {b - a for _, a, b in self.moved_blocks}
        # ...and a rebase moves EVERY member, not a subset. If only some moved, the campaign was not
        # rebased -- something inside it shifted, and a matching context flip is coincidence, not cause.
        whole = (not self.moved_flags or len(self.moved_flags) == self.total) and \
                (not self.moved_blocks or len(self.moved_blocks) == self.total)
        return not (whole and widths_kept and len(flag_deltas) <= 1 and len(block_deltas) <= 1)

    @property
    def changed(self) -> bool:
        """Anything at all moved. Deliberately NOT derived from `blocking`: a context change makes the
        moves non-blocking, and reporting them as "unchanged" would hide the very divergence that makes
        two builds' saves incompatible."""
        return bool(self.added or self.removed or self.moved_ids
                    or self.moved_flags or self.moved_blocks)

    def render(self) -> str:
        # DISTINCT members, not change-count: one member can move its id and its window at once, and
        # "2 of 1 members changed" is not a sentence anyone should have to read.
        n = len(set(self.added) | set(self.removed) | {x[0] for x in self.moved_ids}
                | {x[0] for x in self.moved_flags} | {x[0] for x in self.moved_blocks})
        if not self.changed:
            return f"unchanged since the last build of this folder ({self.total} members)"
        L = [f"{n} of {self.total} members changed since the last build:"]
        if self.context_changed:
            L.append(f"    (build context {self.context_changed[0]} -> {self.context_changed[1]}: the "
                     f"journey assigns its own flag/text windows, so the moves below are that assignment, "
                     f"not drift. Saves are NOT interchangeable between the two.)")
        for nm in self.added:
            L.append(f"    + {nm} (new)")
        for nm in self.removed:
            L.append(f"    - {nm} (gone)")
        for nm, a, b in self.moved_ids:
            L.append(f"      {nm}: id {a} -> {b}")
        for nm, a, b in self.moved_blocks:
            L.append(f"    ! {nm}: text block {a} -> {b}")
        for nm, a, b in self.moved_flags:
            L.append(f"    ! {nm}: flag window {a[0]}-{a[1]} -> {b[0]}-{b[1]}")
        return "\n".join(L)

    def refusal(self) -> str:
        """Why the build stopped, and the two honest ways forward."""
        L = ["this build MOVES state that an existing save already depends on:"]
        for nm, a, b in self.moved_flags:
            L.append(f"  - {nm}: story-flag window {a[0]}-{a[1]} -> {b[0]}-{b[1]}")
        for nm, a, b in self.moved_blocks:
            L.append(f"  - {nm}: dialogue text block {a} -> {b}")
        L += [
            "",
            "A flag window is computed from a member's POSITION (flag_base + i * flags_per_field) and stored "
            "nowhere, so deleting or reordering a member -- or changing flags_per_field -- slides every later "
            "member's bits. Those bits are save-persistent: a save made before this build would read the "
            "WRONG ones (doors already open, cutscenes replaying, a gated NPC permanently mute).",
            "",
            "If no save matters (a fresh playtest, a campaign never released), re-run with --reflow-flags to "
            "accept the move. Otherwise restore the member order / flags_per_field that produced the previous "
            "window -- the last build's numbers are in the report above and in .ff9build.json.",
        ]
        return "\n".join(L)


def diff(old: "dict | None", new: dict) -> "StampDiff":
    """Compare two stamps BY MEMBER NAME. The name is the stable identity across a move: an id can change
    (that is what reid is for) while the member stays the same room, so keying on id would report every
    reid as a wholesale replacement and hide the flag drift underneath it."""
    d = StampDiff(total=len(new.get("members", [])))
    if not old:
        return d
    d.prior_kit = str(old.get("kit_version", ""))
    oc, nc = str(old.get("context", "standalone")), str(new.get("context", "standalone"))
    if oc != nc:
        d.context_changed = (oc, nc)
    a = {m.get("name"): m for m in old.get("members", []) if isinstance(m, dict)}
    b = {m.get("name"): m for m in new.get("members", []) if isinstance(m, dict)}
    d.added = sorted(set(b) - set(a))
    d.removed = sorted(set(a) - set(b))
    for nm in sorted(set(a) & set(b)):
        oldm, newm = a[nm], b[nm]
        if oldm.get("id") != newm.get("id"):
            d.moved_ids.append((nm, oldm.get("id"), newm.get("id")))
        # A text block that TRACKS the id is the member's OWN block (build.default_text_block is identity),
        # so a reid moves both together by design -- that is not a dialogue relocation and must not block,
        # or every id move would need --reflow-flags and the flag would be trained away. Only a block moving
        # INDEPENDENTLY of the id is meaningful: a donor block being abandoned, or the journey's mesID remap.
        otb, ntb = oldm.get("text_block"), newm.get("text_block")
        tracks_id = otb == oldm.get("id") and ntb == newm.get("id")
        if otb != ntb and not tracks_id:
            d.moved_blocks.append((nm, otb, ntb))
        ow = (oldm.get("flag_lo"), oldm.get("flag_hi"))
        nw = (newm.get("flag_lo"), newm.get("flag_hi"))
        if ow != nw and ow != (None, None) and nw != (None, None):
            d.moved_flags.append((nm, ow, nw))
    return d
