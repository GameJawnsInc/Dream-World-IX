"""Multi-instance probe P3: TWO FF9 instances at once (Netsync off), each from its own instance root, both harness-driven.

    py studies/test-harness/multi-instance/p3_two_instances.py [host_root] [guest_root]

Roots default to C:\\gd\\ff9-inst\\host and ...\\guest (build them with instance_root.py). The STOCK Session is used as is:
only its pid probe is path-scoped (the default refuses while ANY FF9.exe runs), and the stock -single-instance flag stays
(its mutex is keyed on the exe path, which differs per root). Sequence: boot HOST + the stock smoke (New Game, warp 30602,
walk); boot GUEST beside it + the same smoke; then frame rates for BOTH across focus legs (as launched, host foreground, guest
foreground, host minimized, guest minimized); then each warps to 250 (a field with art) and photographs it; memory per
process; each root's Memoria.log / output_log.txt grepped for audio, window-hook and error lines. Results ->
<host run dir>/p3.json and stdout. Nothing here touches the real install (verify with instance_root.py fingerprint).
"""
import contextlib
import ctypes
import json
import subprocess
import sys
import time
from ctypes import wintypes
from pathlib import Path

WT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(WT / "tools"))
sys.path.insert(0, str(WT / "ff9mapkit"))
import harness                                                     # noqa: E402
assert Path(harness.__file__).resolve().is_relative_to(WT), harness.__file__
from harness import Session                                        # noqa: E402
from harness.session import ff9_pids                               # noqa: E402
import play                                                        # noqa: E402  (tools/play.py: smoke, _png_is_not_blank)
from ff9mapkit.hangdump import process_image_path                  # noqa: E402

HOST = Path(sys.argv[1] if len(sys.argv) > 1 else r"C:\gd\ff9-inst\host")
GUEST = Path(sys.argv[2] if len(sys.argv) > 2 else r"C:\gd\ff9-inst\guest")
BENCH, ART = 30602, 250
LEG_S = 6.0
U32 = ctypes.WinDLL("user32", use_last_error=True)


def probe_for(root: Path):
    exe = (root / "x64" / "FF9.exe").resolve()

    def probe() -> list:
        out = []
        for pid in ff9_pids():
            try:
                if Path(process_image_path(pid)).resolve() == exe:
                    out.append(pid)
            except OSError:
                pass
        return out
    return probe


def hwnd_of(pid: int):
    found = []
    cb_t = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    def cb(hwnd, _):
        p = wintypes.DWORD()
        U32.GetWindowThreadProcessId(hwnd, ctypes.byref(p))
        if p.value == pid and U32.IsWindowVisible(hwnd):
            found.append(hwnd)
        return True
    U32.EnumWindows(cb_t(cb), 0)
    return found[0] if found else None


def fg_pid() -> int:
    p = wintypes.DWORD()
    U32.GetWindowThreadProcessId(U32.GetForegroundWindow(), ctypes.byref(p))
    return p.value


def mem_mb(pid: int):
    out = subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"], capture_output=True, text=True).stdout
    try:
        return int(out.strip().split('","')[-1].strip('" K').replace(",", "").replace(".", "")) // 1024
    except (ValueError, IndexError):
        return None


def rates(gs: dict, secs: float = LEG_S) -> dict:
    f0 = {k: g.state.frame for k, g in gs.items()}
    t0 = time.time()
    time.sleep(secs)
    f1 = {k: g.state.frame for k, g in gs.items()}
    dt = time.time() - t0
    return {k: round((f1[k] - f0[k]) / dt, 1) for k in gs}


def grep(path: Path, needles) -> list:
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError as e:
        return [f"<unreadable: {e}>"]
    return [ln[:200] for ln in lines if any(n.lower() in ln.lower() for n in needles)]


def main() -> int:
    res = {"roots": {"host": str(HOST), "guest": str(GUEST)}, "legs": [], "notes": []}
    with contextlib.ExitStack() as stack:
        gs, pids = {}, {}
        for role, root in (("host", HOST), ("guest", GUEST)):
            t0 = time.time()
            g = stack.enter_context(Session(label=f"mi-p3-{role}", game_path=root, pid_probe=probe_for(root),
                                            window_size=(960, 540)))
            res[f"{role}_boot_s"] = round(time.time() - t0, 1)
            pids[role] = probe_for(root)()
            print(f"[p3] {role} up: pids {pids[role]} channel {g.channel.dir if hasattr(g.channel, 'dir') else '?'}")
            play.smoke(g, BENCH)
            gs[role] = g
        res["pids"] = pids
        assert all(len(v) == 1 for v in pids.values()), f"expected one process per root: {pids}"
        hp, gp = pids["host"][0], pids["guest"][0]
        hw = {"host": hwnd_of(hp), "guest": hwnd_of(gp)}
        res["hwnd"] = {k: bool(v) for k, v in hw.items()}
        res["mem_mb_after_boot"] = {"host": mem_mb(hp), "guest": mem_mb(gp)}

        def leg(name, action=None):
            ok = None
            if action:
                ok = action()
                time.sleep(1.5)
            r = rates(gs)
            row = {"leg": name, "action_ok": ok, "fg": {hp: "host", gp: "guest"}.get(fg_pid(), f"other({fg_pid()})"),
                   "fps": r, "ui": {k: g.state.ui_state for k, g in gs.items()}}
            res["legs"].append(row)
            print(f"[p3] leg {name}: {row}")

        leg("as-launched")
        leg("host-foreground", lambda: bool(U32.SetForegroundWindow(hw["host"])))
        leg("guest-foreground", lambda: bool(U32.SetForegroundWindow(hw["guest"])))
        leg("host-minimized", lambda: bool(U32.ShowWindow(hw["host"], 6)))
        U32.ShowWindow(hw["host"], 9)
        leg("host-restored")
        leg("guest-minimized", lambda: bool(U32.ShowWindow(hw["guest"], 6)))
        U32.ShowWindow(hw["guest"], 9)
        leg("guest-restored")

        res["shots"] = {}
        for role, g in gs.items():
            g.warp(ART)
            time.sleep(2.0)
            shot = g.shot(f"p3-{role}-{ART}")
            res["shots"][role] = {"path": str(shot), "bytes": shot.stat().st_size, "not_blank": play._png_is_not_blank(shot)}
            print(f"[p3] {role} shot {shot} not_blank={res['shots'][role]['not_blank']}")
        res["mem_mb_end"] = {"host": mem_mb(hp), "guest": mem_mb(gp)}
        for role, root in (("host", HOST), ("guest", GUEST)):
            res[f"{role}_log"] = grep(root / "Memoria.log", ["SaXAudio", "XAudio", "audio", "active window", "WndProc",
                                                             "already running", "Exception", "error"])
            res[f"{role}_unity"] = grep(root / "x64" / "FF9_Data" / "output_log.txt",
                                        ["D3D", "device", "Failed", "Exception", "audio", "already"])
        res["run_dirs"] = {k: str(g.run_dir) for k, g in gs.items()}
        out = Path(gs["host"].run_dir) / "p3.json"
        out.write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
        print(f"[p3] results -> {out}")
    still = {r: probe_for(p)() for r, p in (("host", HOST), ("guest", GUEST))}
    print(f"[p3] after exit, processes left: {still}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
