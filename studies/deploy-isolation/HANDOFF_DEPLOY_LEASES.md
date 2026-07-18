# Deploy isolation — per-checkout leases (HANDOFF, 2026-07-18)

> **STATUS: DEFERRED, WITH A FIRST DRAFT ALREADY FALSIFIED.** The diagnostic half shipped on
> `claude/patch-registry-guards` (the deploy ledger, `ff9mapkit/ff9mapkit/deploylog.py`). The structural
> half — per-checkout mod folders + exclusive id bands — is NOT built. A first cut was written and three
> reviewers returned needs-revision; §5 is that autopsy, and it is the most valuable part of this file.
> Read §3 before designing anything: **folder isolation alone makes the problem worse.**

Audience: an agent picking this up cold, or the owner deciding whether to fund it. Everything below was
verified against the code at `59f15a8`; file:line references are quotable.

---

## 1. The forensic record

**What happened.** On 2026-07-18 field 4003's `FieldScene` line was absent from the live
`DictionaryPatch.txt`. Six concurrent checkouts deploy into the same game install (verified: `git worktree
list` plus `C:/gd/Dream-World-IX-netsync` = six), so the first hypothesis was a lost-update race — two
deploys doing read-modify-write on one file, the later one rewriting the earlier's line away.

**It was not a race.** `revert_deploy_4003.py` was deliberately run at ~01:29 as cleanup, by a session that
was migrating itself off the shared slot onto `FF9CustomMap-idgate` / id 30500 — the migration is recorded
in commit `56aefd2` at 01:56. Nobody re-deployed 4003 afterward. The registration was **retired**, not lost.

**The 12:15 deploy of 4005 was innocent**, and its own evidence acquits it: its `preDEPLOY` snapshot of
`DictionaryPatch.txt` — taken *before* it wrote anything — already lacks the 4003 line. A deploy cannot
delete what its own pre-image proves was already gone.

**Corroborating negatives** (absence of evidence that would exist if the alternative were true):

- No `deployfield_*` directory dated Jul-18 in `%TEMP%`. `tools/deploy_field.py:78` stages every build in
  `tempfile.mkdtemp(prefix="deployfield_")`; an aborted mid-flight deploy always leaves one behind. None
  existed, so no deploy died mid-write.
- No `DictionaryPatch.txt.preDEPLOY.*` backup stamped after 01:27. `deploy_field.py:112-113` snapshots on
  every run, so a deploy after the retirement would have left a dated file. There is none.

**THE LESSON, as a law:**

> **THE MTIME NAMES THE LAST WRITER, NOT THE GUILTY ONE.**

Filesystem timestamps answer "who touched this most recently". They never answer "who removed this line",
because a removal leaves no residue — the file is simply shorter and newer. Every minute spent on the 12:15
deploy was spent because its mtime was the freshest thing near the crime scene. Reach for a *ledger* (an
append-only record of intent) before reaching for mtimes; mtime evidence can only ever exclude, never
convict.

---

## 2. The three defects, ranked by cost

### (i) Absence carries no reason — MITIGATED, not solved

A retired registration and a lost one are byte-identical: a line that is not there. Nothing on disk recorded
which it was, which is the entire reason the incident cost real investigator time.

**What shipped** (`ff9mapkit/ff9mapkit/deploylog.py`): an append-only ledger at
`<game>/ff9mapkit-deploys.log` — deliberately beside `Memoria.ini` and **outside** every mod folder,
because `deploy_campaign` rmtree+copytrees mod folders and would destroy a log kept inside one. Each line is
`when / event / field_id / mod_folder / checkout / note`, tab-separated; `checkout` is the field that
actually answers "which of my six sessions did this". Writes take a real cross-process exclusive lock
(`fcntl.flock` / `msvcrt.locking`) — see §5's last bullet for why. `deploylog.reconcile()` compares the
ledger against what the stacked `DictionaryPatch.txt` files register *right now*, and
`ff9mapkit doctor` (`cli.py:87-91`) prints the result.

**What it covers:** every removal path, including uninstrumented ones — a campaign wipe, a hand edit, a
foreign deploy's drop, and the ~30 legacy revert scripts on disk that will never record anything themselves.
Reconciliation is what buys that coverage, not per-removal instrumentation.

**What it does NOT cover:**
- It is **diagnostics, never load-bearing.** It cannot stop a clobber, only explain one afterward.
- It records **field deploys** only. Battle scenes, campaign deploys, and world deploys write nothing.
- Retirements are recorded only where the current tooling calls `record()`. A pre-existing revert script run
  by hand still leaves nothing; `reconcile` catches it as `missing`, which is right but is a *detection*,
  not an *explanation*.
- It says nothing about ids that were never deployed from a ledger-aware checkout.

### (ii) Isolation was never engaged

`.ff9deploy.toml` — the per-checkout pin for `mod_folder` and scratch `id` — **exists in ZERO of six
checkouts.** Verified by direct stat across all six worktree roots.

It cannot arrive by itself: `.gitignore:130` ignores it, so it survives neither `git clone` nor
`git worktree add`. Nothing in the tooling creates it. The resolvers all fall through to their defaults
(`deploy_field.py:36-37`), so every checkout resolves to `FF9CustomMap`.

**CLAUDE.md §3's claim that the mod folder is "pinned in a gitignored `.ff9deploy.toml`" is currently false
everywhere.** That sentence describes a mechanism nobody has ever engaged — this project's own "a law in a
docstring is a wish", at the level of the brief.

### (iii) Every checkout defaults to the same scratch id

`_def_id = int(_cfg.get("id", 4003))` (`deploy_field.py:37`). With (ii) true, that default is universal:
six checkouts, one folder, one id. Incident 1 (`56aefd2`, "the shared ForkDonorPatch.txt is racy") and
incident 2 are the same root cause seen from two angles.

---

## 3. THE SEQUENCING TRAP — folder isolation alone makes things WORSE

**Read this before writing any code.**

The tempting cheap fix is "give each checkout its own mod folder" — it is one file and an afternoon. Do not
ship it alone.

`FF9DBAll.EventDB` and `SceneData` are **GLOBAL across every folder in `Memoria.ini [Mod] FolderNames`.**
Distinct folders do not give you distinct id spaces. So separate folders plus a shared default id trades a
loud failure for a quiet one:

| | today (shared folder, shared id) | folders only (shared id) |
|---|---|---|
| symptom | a `FieldScene` line vanishes | your id loads **another session's room** |
| in game | black screen, null `.eb` | a field that renders, wrongly |
| reads as | a deploy bug | a **content** bug |
| time to diagnose | minutes | hours, if you get there at all |

A lost line is self-announcing. A contended id is a room that looks like your walkmesh is wrong.

> **Bands and folders MUST land in the same commit.** There is no acceptable intermediate state.

---

## 4. The proposed design: per-checkout deploy leases

**Direction, not reviewed code.** The sketch below is illustrative; §5 lists what the first attempt at it
got wrong.

A checkout **claims** a deploy target exactly once, and **never releases it**.

The never-release property is the whole point. Every lease system that goes wrong goes wrong in its
stale-claim heuristic — "is this lock abandoned?" — and every such heuristic exists only to *free* a lock.
Slots are cheap; worktrees are not long-lived enough for exhaustion to beat the complexity of getting
liveness detection right (but see §5 on capacity, which is a real bound, not a hypothetical one).

**Registry.** One file in the game install (the directory all checkouts already share, same reasoning as the
ledger): `<game>/ff9mapkit-leases/`. One file per slot, `slot-<n>.toml`. Claiming is
`os.open(path, O_CREAT | O_EXCL)` — the one primitive that is genuinely atomic on both platforms and needs
no lock. Whoever creates the file owns the slot; `FileExistsError` means try the next `n`.

**A slot carries:**
- `mod_folder` — e.g. `FF9CustomMap-w03`
- `id_base` / `id_end` — a 64-id exclusive band out of the 30000-32767 scratch range (~43 slots)
- `checkout` — the absolute repo root, the key a re-entering session matches on
- `claimed` — an ISO timestamp, diagnostic only, never a liveness input

**Lifecycle:** on deploy, read the registry, find the slot whose `checkout` matches this repo root, use it.
No match → claim the lowest free `n`. **Never** delete a slot file.

**Sketch:**

```python
def acquire(game, checkout):
    """The slot this checkout owns, claiming one on first use. Never releases: a stale-claim
    heuristic only ever exists to FREE a lock, and every one of them is a bug farm."""
    d = Path(game) / "ff9mapkit-leases"
    d.mkdir(parents=True, exist_ok=True)
    key = str(Path(checkout).resolve())
    for f in sorted(d.glob("slot-*.toml")):
        if _read(f).get("checkout") == key:
            return _read(f)
    for n in range(MAX_SLOTS):
        try:
            fd = os.open(d / f"slot-{n:02d}.toml", os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            continue
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(_render(n, key))          # see the TOML-quoting defect in section 5
        return _read(d / f"slot-{n:02d}.toml")
    raise SlotsExhausted(d)                    # NOT SystemExit -- see section 5
```

`MAX_SLOTS` and the band width are the same number twice: `30000 + n*64 .. 30000 + n*64 + 63`.

**Then, in the same commit:** the id default becomes the slot's `id_base`, and the mod-folder default
becomes the slot's `mod_folder`. Neither alone (§3).

---

## 5. Known defects in the first draft — do not re-derive these

Three independent reviewers returned needs-revision on the first cut. Each of these is a real bug that was
in written code, not a hypothetical.

**1. TOML backslash quoting — the cascading one.** A Windows path (`C:\gd\Dream-World-IX`) written unescaped
into `checkout = "..."` is invalid TOML: `\g` and `\D` are illegal escapes and `tomllib` raises
`TOMLDecodeError` on read. The cascade is total — every lease file is unreadable, so no lease ever matches
its own checkout, so `acquire()` mints a **new** slot on every single deploy until all are exhausted. Use
TOML literal strings (`'C:\gd\...'`, single quotes, no escape processing) or forward slashes, and add a
test that round-trips a real backslash path through `tomllib`.

**2. Writing `.ff9deploy.toml` unconditionally HIJACKS five other resolvers.** The draft had `acquire()`
materialize `.ff9deploy.toml`. But that file is read by more than `deploy_field`, and the other readers'
fallbacks are **purpose-specific and load-bearing** — `import-chain`/campaign work falls through to
`FF9CustomMap-ow` (`cli.py:5039`), and `-world` and `-story` are live purpose folders. **The file's ABSENCE
is currently load-bearing**, which is exactly why defect (ii) has been survivable. Writing it points
overworld and campaign deploys at a scratch folder. Two honest options: (a) write a **distinct key only
`deploy_field` reads**, or (b) migrate every resolver in the SAME commit. Additionally, the draft *rewrote*
the file from a handful of keys — that destroys `campaign_id_base` (`cli.py:5021`) and `text_block`
(`deploy_field.py:52`), which other call sites read. Any write must merge, never replace.

**3. A hard id-collision abort breaks the daily loop.** The draft aborted when the requested id was
registered by another folder. Post-lease, *every purpose folder's id counts as another folder's* — so
iterating a campaign field with `--id 6000` would `SystemExit` on a perfectly normal action. The guard must
distinguish "an id inside somebody else's exclusive scratch band" (refuse) from "an id in a shipped/purpose
band" (warn, proceed).

**4. Capacity, and the shape of the failure.** Never-released slots plus disposable worktrees means dated
exhaustion — this is arithmetic, not a worry. Worse, the draft's failure mode was `SystemExit` **at module
import**, i.e. the tool stops working entirely for every new checkout, at the least convenient moment.
Exhaustion must be a recoverable error with an actionable message, plus a documented reclaim path (a `doctor`
listing of slots whose `checkout` directory no longer exists — reported for a human to delete, **never**
auto-reclaimed; auto-reclaim is the stale-claim heuristic re-entering through the back door).

**5. `acquire()` at module scope breaks `--help`.** The draft called it at import time in
`tools/deploy_field.py`, so `deploy_field.py --help` on a machine with no game install would fail — and it
breaks the public-clone posture, where the kit must be inspectable without an install. Acquire lazily, after
argument parsing, only on a path that actually deploys.

**6. Windows atomicity must be proven, not asserted.** The draft asserted the POSIX `O_APPEND` small-write
guarantee. **It does not carry to Windows** — the MSVC CRT implements append by seeking to end inside
`_write`, making it a seek-then-write, which is precisely the interleaving hazard. This was *measured*: four
barrier-synchronised processes writing 20 lines each left **69 of 80** on disk. The shipped ledger therefore
takes a real cross-process lock, and `tests/test_deploylog.py` drives the real `record()` through a barrier
against a deliberate seek-then-write control that still tears. Apply the same standard here:
`O_CREAT|O_EXCL` **is** atomic on Windows (it maps to `CREATE_NEW`) — but prove any *other* claim with a
concurrency test before writing it in a docstring.

---

## 6. Residue this branch does not touch

Verified against the code at `59f15a8`. **One item in the original list was wrong and is corrected below.**

- **Two unguarded read-modify-writes in `tools/deploy_field.py`.**
  - `DictionaryPatch.txt`: read at `:191`, written at `:205`. In between it filters, rebuilds, and appends —
    a wide window with no lock.
  - `ForkDonorPatch.txt`: read at `:241`, written at `:244`. Same shape. This is the file `56aefd2` already
    called racy.
  - **The revert subprocess prelude at `:70-74` is the WIDEST window, and it sits *before* the write anyone
    would think to guard.** `subprocess.run` on `revert_deploy_<id>.py` does its own full read-modify-write
    of `DictionaryPatch.txt`, and only then does the parent read at `:191`. The unprotected interval spans a
    whole child process. Any locking scheme must cover the prelude, not just the write.

- **The sibling reverts restore by wholesale `copyfile` of a pre-deploy snapshot.** `ForkDonorPatch` (`:246`),
  the CSVs (`:402`), `BattlePatch` (`:433`), and `TextPatch` (`:456`) all revert by copying
  `*.preDEPLOY.<STAMP>` back over the live file — so **reverting field A deletes field B's line**, even
  though `TextPatch`/`BattlePatch` were carefully written with a *non-clobbering* per-field marker merge on
  the way in (`:438-455`). The asymmetry is the bug: a merging writer paired with a clobbering restorer.
  `dictpatch.revert_dictionary_patch` (`dictpatch.py:97`, used at `deploy_field.py:493`) already solves this
  correctly — it reverts only lines the reverting id **owns** — and the fix was never propagated to its
  three siblings.

- **`deploy_battle.py` — CORRECTION: the claim that it ignores `mod_folder` is FALSE.** It reads
  `.ff9deploy.toml` at `:37-41`, uses it as the `--mod-folder` default at `:63`, assigns `MOD = _args.mod_folder`
  at `:71`, and builds `ModLayout(live_root)` from it at `:104`. This path is correct as written. What it
  *does* lack is any id-band awareness — it honors no scratch `id` and writes no ledger entry, so a battle
  scene is invisible to `reconcile` (and `deploystack` documents a real `FieldScene 30011` vs `BattleScene
  30011` collision across folders). That is the gap to record, not the mod-folder one.

- **Second-granularity backup STAMPs.** `deploy_field.py:112` —
  `datetime.datetime.now().strftime("%Y%m%d-%H%M%S")`. Two deploys inside one second silently overwrite each
  other's pre-deploy snapshot, destroying the only pre-image that would acquit or convict. Under a
  lease-parallel loop this stops being theoretical. (Note the irony: it was exactly such a snapshot that
  acquitted the 12:15 deploy in §1.)

- **The shared `.tmp` staging name in `fsutil`.** `atomic_write_bytes` (`fsutil.py:20`) and
  `atomic_write_text` (`:35`) both stage through `p.with_name(p.name + ".tmp")` — a *deterministic* sibling.
  Two processes atomically writing the same path race on the staging file itself, and the `os.replace` is
  atomic for a name that may already hold the other writer's bytes. Needs a unique suffix (pid + counter).

- **`Memoria.ini` itself** is edited by hand and by tooling with no coordination at all, and `FolderNames`
  ordering decides which folder's registrations win. Out of scope here; note it before any design assumes the
  stack is stable during a deploy.

---

## 7. Staged plan

Effort is agent-session-days. "Still broken after" is the honest residue, not a caveat.

### Stage 0 — the in-game question (≈1 relaunch). DO THIS FIRST.

**The single cheapest check that de-risks the whole design:**

> Does Memoria auto-register a new mod folder from its `ModDescription.xml`, or must
> `Memoria.ini [Mod] FolderNames` be written for the folder to be read?

One relaunch answers it, and it decides a design branch:
- **Auto-registers** → `acquire()` creates a folder with a `ModDescription.xml` and is done. Self-contained.
- **Must write `FolderNames`** → every claim mutates `Memoria.ini`, a file with its own concurrency problem
  (§6) and its own ordering semantics — and the launcher rewrites `FolderNames` from `Priorities` at every
  Play click, so `Priorities` must be written too. This roughly doubles Stage 2 and adds a failure mode that
  can black-screen the game.

Do not design Stage 2 before this is answered. Everything else in Stage 0-1 is provable offline.

### Stage 1 — the residue fixes (≈1-1.5 days, fully offline-provable)

Independent of leases, valuable on their own, and each is a small surgical diff:
propagate the `revert_dictionary_patch` ownership model to the three sibling reverts; unique `.tmp` names in
`fsutil`; sub-second (or collision-checked) backup STAMPs; ledger entries from `deploy_battle`.

Provable with tmpdir fixtures — each needs a test that fails against today's code (a revert of field A that
demonstrably deletes field B's `TextPatch` line).

**Still broken after:** everything structural. Two checkouts still share folder and id.

### Stage 2 — leases + bands, ONE commit (≈2-3 days, mostly offline)

The registry, `acquire()`, the id-band default, the mod-folder default, the collision guard from §5.3, the
resolver decision from §5.2, and the `doctor` slot listing. Every §5 defect gets a test that fails without
its fix — especially the backslash round-trip, which is the one that silently exhausts the registry.

Offline-provable: claim/re-enter/exhaustion semantics, TOML round-trip, band arithmetic, `--help` with no
install, resolver non-hijack.

**Needs a playtest:** that a freshly claimed folder is actually read by the engine (Stage 0's answer applied),
and that a field deployed at `id_base` warps and renders via F6. One session.

**Still broken after:** `Memoria.ini` concurrency; existing checkouts need a one-time claim (fine — it happens
on their next deploy); campaign/world/battle deploys still resolve by their own rules unless §5.2's option (b)
was taken.

### Stage 3 — optional hardening (≈1 day)

A lock around the `deploy_field` critical section spanning the revert prelude (§6), so even two deploys into
the *same* folder serialise. Lower value once bands land — mostly protection against hand-run reverts. Defer
until something demands it.

---

### If you fund none of it

The ledger already turns incident 2 from a multi-hour investigation into one `ff9mapkit doctor` line. The
cheapest real mitigation after that is **not** code: create `.ff9deploy.toml` by hand in each checkout with a
distinct `mod_folder` and `id`, and answer Stage 0. That is the whole design, executed manually, and it will
tell you whether the automated version is worth building.
