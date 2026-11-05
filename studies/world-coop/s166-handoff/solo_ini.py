"""Run a SOLO s165 bench under the precondition ini: [Netsync] Enabled 0 + FollowHost 1, backed up first (the MAIN repo's
backups/), restored byte-exact afterwards whatever happens.  Usage: py solo_ini.py <label> -- <command...>"""
import os
import subprocess
import sys
from pathlib import Path

#: [ff9mapkit netsync s166] the checkout this script lives in (studies/world-coop/s166-handoff/ -> the worktree root), the bench's cwd
#: and import path -- never another worktree's (it named dreamy-allen-a2375f: a bench there ran THAT branch's scenario). SOLO_INI_WT
#: overrides it.
WT = Path(os.environ.get("SOLO_INI_WT") or Path(__file__).resolve().parents[3])
sys.path.insert(0, str(WT / "studies" / "test-harness" / "scenarios"))
sys.path.insert(0, str(WT / "tools"))
import _coop_peer_bench as pb  # noqa: E402

GAME = Path(r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX")


def main() -> int:
    label = sys.argv[1]
    cmd = sys.argv[sys.argv.index("--") + 1:]
    values = {"Enabled": 0}
    if os.environ.get("SOLO_INI_FOLLOW", "1") == "1":     # the s165 solo bench's precondition; 0 = the s144/s145 solo benches' own
        values["FollowHost"] = 1
    guard = pb.IniGuard(GAME / "Memoria.ini", values, label=label)
    rc = 99
    try:
        print("[solo_ini]", guard.apply(), flush=True)
        rc = subprocess.call(cmd, cwd=str(WT), env=os.environ.copy())
    finally:
        ok, detail = guard.restore()
        print(f"[solo_ini] restore {'OK' if ok else 'FAILED'}: {detail}", flush=True)
        if not ok:
            rc = rc or 98
    return rc


if __name__ == "__main__":
    sys.exit(main())
