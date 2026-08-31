"""Does the harness's own opening WRITE THE OWNER'S SAVE FILE?

THE QUESTION, AND WHY IT COMES FIRST. Every scenario in this arc opens the same way -- ``newgame()``
then ``warp()`` -- and ``EventEngine`` autosaves on ordinary field entry, gated only by
``Configuration.SaveFile.DisableAutoSave``, which is 0 on this install. If that fires, then every
harness run so far has been stamping a scenario-zero autosave over a real player's slot on an install
shared by ~26 worktrees and used by the owner to actually play. That is a data-loss question, not a
harness question, and no amount of green scenarios makes it safe to leave unasked.

It is also the experiment that decides whether the agent needs a SAVE SANDBOX (redirecting
``SharedDataBytesStorage.MetaData`` into the channel directory while armed). Building that sandbox
before knowing the answer would be authoring surface against a hypothesis -- and a sandbox nobody
verified is a check that cannot fail.

    py tools/play.py studies/test-harness/scenarios/save_untouched.py --field 30801

⚠ THE BASELINE IS TAKEN AT IMPORT TIME, ON PURPOSE. ``play.py`` imports the scenario BEFORE it
constructs the Session, so this module-level snapshot is the only one taken before the game process
exists -- and the launch itself is part of what is under test. Reading it inside ``run(g)`` would
measure the wrong interval and could not see a write that happened during boot.
"""
import hashlib
import os
from pathlib import Path

FIELD = 30801

#: Where FF9 (Steam) keeps its saves on this machine. Both containers matter: the encrypted main file
#: and Memoria's extended sidecar, where the extra WINS on load.
SAVE_DIR = Path(os.path.expandvars(
    r"%USERPROFILE%\AppData\LocalLow\SquareEnix\FINAL FANTASY IX\Steam\EncryptedSavedData"))


def _digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def snapshot() -> dict:
    """Hash every live save container (never the .bak siblings -- those are ours, not the game's)."""
    out = {}
    if not SAVE_DIR.is_dir():
        return out
    for path in sorted(SAVE_DIR.glob("SavedData_ww*.dat")):
        try:
            out[path.name] = (_digest(path), path.stat().st_mtime, path.stat().st_size)
        except OSError:
            pass
    return out


BEFORE = snapshot()


def run(g, field: int = FIELD):
    g.note("save_untouched: does a harness run write the player's save?")
    print(f"[save] watching {len(BEFORE)} container(s) in {SAVE_DIR}")
    for name, (digest, _mtime, size) in BEFORE.items():
        print(f"[save]   {name}  {size} bytes  {digest[:16]}")

    if not BEFORE:
        g.check(False, "the save directory was found and hashed before launch", str(SAVE_DIR))
        return

    # The exact opening every other scenario uses. Nothing exotic -- the whole point is that this is
    # the ORDINARY path, so whatever it does to the save it has been doing all along.
    g.newgame()
    g.warp(field)
    g.wait_frames(60)
    g.walk("up", 60)
    g.wait_frames(30)
    g.shot("save-untouched")

    after = snapshot()
    changed = []
    for name, (digest, mtime, size) in after.items():
        old = BEFORE.get(name)
        if old is None:
            changed.append(f"{name} was CREATED ({size} bytes)")
        elif old[0] != digest:
            changed.append(f"{name} CHANGED ({old[2]} -> {size} bytes)")
    for name in BEFORE:
        if name not in after:
            changed.append(f"{name} was DELETED")

    # Assert on the OUTCOME -- the bytes on disk -- not on whether an autosave call was observed.
    # Whether the engine "meant" to save is not the question; whether the player's file moved is.
    g.check(not changed,
            "a normal harness run leaves the player's save files byte-identical",
            "; ".join(changed) if changed else
            f"{len(after)} container(s) unchanged: {', '.join(sorted(after))}")

    for line in changed:
        print(f"[save] !! {line}")
    if changed:
        print("[save] !! The harness is writing the owner's save. It needs a SANDBOX before any "
              "further unattended run -- redirect SharedDataBytesStorage.MetaData into the channel "
              "directory while armed, and publish the path so the driver can VERIFY the redirect "
              "rather than trust it.")
