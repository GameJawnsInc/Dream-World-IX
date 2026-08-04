"""``.ff9links.json`` -- what a journey patched into an INSTALLED folder, and whether it is still there.

A journey's cross-campaign doors are not built; they are applied to the LIVE install.
:func:`ff9mapkit.journey.apply_link_rewrites` opens the boundary member's deployed ``.eb`` and patches the
``Field()`` literal (or replaces a world-map walk-out region body) in every language copy. Nothing in any
dist contains that edit -- by construction, because the destination is another campaign's id and only the
journey knows it.

So a later single-campaign ``deploy-campaign`` DESTROYS them. It is ``rmtree`` + ``copytree`` of the dist
over the live folder (deploy.py), and the dist holds the UNPATCHED bytes. The door silently reverts to
whatever the donor pointed at -- in the real game, or nowhere. deploy_journey already orders its own link
step LAST for exactly this reason, and ``docs/JOURNEYS.md`` warns about it in prose, which is not a
mechanism: the fast loop (iterate on one campaign) wipes the slow loop's output (assemble the journey) with
nothing to say so.

The receipt is that mechanism. It records what was patched, into which files, and the digest each file
carried immediately AFTER patching -- so three different questions become answerable:
  * are the journey's doors still applied?          (:func:`check` -> satisfied)
  * did a redeploy revert them?                     (files present, digests back to something else)
  * did something else eat them?                    (files gone entirely)

IT ALSO KEEPS ``verify-build`` HONEST. Patching the install makes the folder differ from the
``.ff9build.json`` digest the build wrote, so a perfectly legitimate journey deploy would otherwise report
as drift -- and a drift check that fires on the correct workflow is one nobody reads. The patch step
re-finalizes the stamp, making the patched state the folder's new truth, and the receipt is what
distinguishes "patched on purpose" from "someone edited the install".
"""

from __future__ import annotations

import datetime
import json
from dataclasses import dataclass, field as _dcfield
from pathlib import Path

from . import fsutil
from .stamp import _DIGEST_CHARS, _rel, content_digest
from .stamp import RECEIPT_NAME  # named in stamp so the digest can skip it without a cycle
RECEIPT_VERSION = 1


def receipt_path(folder) -> Path:
    return Path(folder) / RECEIPT_NAME


def build_receipt(folder, results, *, source=None) -> dict:
    """A receipt from :func:`journey.apply_link_rewrites` results. Records the POST-patch digest of every
    file touched, so a revert is detectable by content rather than by hoping the file vanished."""
    from . import __version__
    folder = Path(folder)
    digests = content_digest(folder)
    links = []
    for r in results:
        if not r.get("found"):
            continue                                  # nothing matched -- there is no patch to protect
        files = []
        for f in r.get("files", []):
            try:
                rel = _rel(folder, Path(f))
            except ValueError:                        # patched a file outside this folder (single-folder mode)
                continue
            files.append({"path": rel, "digest": digests.get(rel, "")})
        if files:
            links.append({"eb": r.get("eb"), "mode": r.get("mode"), "dst_id": r.get("dst_id"),
                          "remap": {str(k): v for k, v in (r.get("remap") or {}).items()},
                          "files": files})
    return {
        "receipt_version": RECEIPT_VERSION,
        "kit_version": __version__,
        "applied_utc": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": str(source) if source else None,
        "links": links,
    }


def write_receipt(folder, receipt: dict) -> "Path | None":
    """Write the receipt, or REMOVE a stale one when this journey patched nothing into this folder --
    a receipt describing links that are no longer part of the journey would block a deploy forever."""
    p = receipt_path(folder)
    if not receipt.get("links"):
        p.unlink(missing_ok=True)
        return None
    fsutil.atomic_write_text(p, json.dumps(receipt, indent=2) + "\n", newline="\n")
    return p


def read_receipt(folder) -> "dict | None":
    p = receipt_path(folder)
    if not p.is_file():
        return None
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) and isinstance(data.get("links"), list) else None


@dataclass
class LinkStatus:
    folder: Path
    receipt: "dict | None" = None
    intact: list = _dcfield(default_factory=list)     # (eb, path) still carrying the patched bytes
    reverted: list = _dcfield(default_factory=list)   # (eb, path) present, different bytes -- a redeploy
    missing: list = _dcfield(default_factory=list)    # (eb, path) gone entirely

    @property
    def has_receipt(self) -> bool:
        return bool(self.receipt)

    @property
    def satisfied(self) -> bool:
        """Every file the journey patched still carries the patched bytes."""
        return self.has_receipt and not (self.reverted or self.missing)

    def render(self) -> str:
        if not self.has_receipt:
            return f"{self.folder}: no journey links applied here"
        n = len(self.receipt.get("links", []))
        head = (f"{self.folder}\n  {n} journey link(s) applied "
                f"{self.receipt.get('applied_utc', '?')} from "
                f"{self.receipt.get('source') or 'an unrecorded manifest'}")
        if self.satisfied:
            return head + f"\n  all {len(self.intact)} patched file(s) INTACT"
        L = [head, "  THE JOURNEY'S CROSS-CAMPAIGN DOORS ARE NOT APPLIED HERE ANY MORE:"]
        for eb, f in self.reverted[:12]:
            L.append(f"    ~ {eb}: {f} (reverted -- a campaign redeploy overwrote it)")
        for eb, f in self.missing[:12]:
            L.append(f"    - {eb}: {f} (gone)")
        L.append("  Re-run the journey's link step (deploy-journey) to restore them.")
        return "\n".join(L)


def check(folder) -> LinkStatus:
    """Are the journey's patches still in this installed folder?"""
    folder = Path(folder)
    st = LinkStatus(folder=folder, receipt=read_receipt(folder))
    if not st.has_receipt:
        return st
    for lk in st.receipt.get("links", []):
        eb = lk.get("eb", "?")
        for f in lk.get("files", []):
            rel, want = f.get("path", ""), f.get("digest", "")
            p = folder / rel
            if not p.is_file():
                st.missing.append((eb, rel))
                continue
            import hashlib
            h = hashlib.sha256()
            with open(p, "rb") as fh:
                for chunk in iter(lambda: fh.read(1 << 20), b""):
                    h.update(chunk)
            (st.intact if h.hexdigest()[:_DIGEST_CHARS] == want else st.reverted).append((eb, rel))
    return st
