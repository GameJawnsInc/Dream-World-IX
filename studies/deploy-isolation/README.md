# Deploy isolation — concurrent checkouts sharing one game install (2026-07-18)

> **STATUS: diagnostic half SHIPPED, structural half DEFERRED with a written brief.**
> Six checkouts deploy into the same install and the same mod folder, because the per-checkout
> isolation file `.ff9deploy.toml` exists in **zero** of them. Two incidents came of it. The
> ledger (`ff9mapkit/ff9mapkit/deploylog.py`, `ff9mapkit doctor`) now makes a missing registration
> explain itself; per-checkout leases + exclusive id bands are NOT built.

**Read first:** [`HANDOFF_DEPLOY_LEASES.md`](HANDOFF_DEPLOY_LEASES.md) — the forensic record, the three
defects, the sequencing trap, the proposed design, the first draft's six known defects, the untouched
residue with file:line, and a staged plan.

Two things in there that cost real time to learn, and should not be re-derived:

- **THE MTIME NAMES THE LAST WRITER, NOT THE GUILTY ONE.** Field 4003's vanished registration was not a
  race; it was a deliberate retirement eleven hours earlier. The deploy with the freshest mtime was
  acquitted by its own pre-deploy snapshot.
- **FOLDER ISOLATION ALONE MAKES THINGS WORSE.** `FF9DBAll.EventDB`/`SceneData` are GLOBAL across stacked
  `FolderNames` folders, so separate folders plus a shared default id upgrades a visible clobber (black
  screen, minutes to diagnose) into a silent id collision that loads another session's room and reads as a
  content bug. Bands and folders must land in the same commit.

**The one in-game check that de-risks the design** (§7 Stage 0): does Memoria auto-register a mod folder
from `ModDescription.xml`, or must `Memoria.ini [Mod] FolderNames` be written? One relaunch decides a
design branch. Everything else in the plan is provable offline with tmpdir fixtures.
