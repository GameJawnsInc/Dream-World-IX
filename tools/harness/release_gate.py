#!/usr/bin/env python3
# Windows-first tool: invoke via the py launcher --  py tools/harness/release_gate.py <run dirs> --dll <final DLL or bundle zip>
"""THE RELEASE GATE: refuse an engine release unless EVERY regression report names the final DLL.

    py tools/harness/release_gate.py .harness-runs/<run> [...] --dll C:\\gd\\dwix-custom-memoria-<v>.zip
    py tools/harness/release_gate.py .harness-runs/<set-dir> --sha 29f351aaacd3f3d8
    py tools/harness/release_gate.py .harness-runs/<run> [...]          # the final DLL = the live install's x64 one

A bench proves the DLL it drove, not the one that ships. s164's regression set ran across three live DLLs in one day (the
round's build, the review's, the arrival guard's); a green report from an earlier build says nothing about the bytes a bundle
carries. Every Session hashes the x64 ``Assembly-CSharp.dll`` it is about to launch (env.json, and report.json's
``assembly_csharp`` since the s164 hardening); every duo carries both games' in duo.json. This reads them all and refuses
(exit 1) unless each one names the final DLL's sha256 -- a report that names none (no hash, an unreadable report) refuses too:
"unknown" is not "the same".

A path is a run dir (it holds ``report.json`` or ``duo.json``) or a directory of run dirs (its children are read). The final
DLL is ``--sha`` (a hex prefix of 12 or more), ``--dll`` (a .dll, or a bundle .zip whose ``x64/FF9_Data/Managed/
Assembly-CSharp.dll`` is hashed), or else the live install's. Verdicts are listed but never judged here: a calibration run's
predicted reds make its report "fail" by design.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import zipfile
from pathlib import Path

DLL_IN_BUNDLE = "x64/FF9_Data/Managed/Assembly-CSharp.dll"
MIN_PREFIX = 12


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def final_sha(dll: Path) -> str:
    """The sha256 of a DLL, or of a bundle zip's x64 Assembly-CSharp.dll."""
    dll = Path(dll)
    if dll.suffix.lower() == ".zip":
        with zipfile.ZipFile(dll) as z:
            names = [n for n in z.namelist() if n.replace("\\", "/").lower().endswith(DLL_IN_BUNDLE.lower())]
            if len(names) != 1:
                raise ValueError(f"{dll}: expected exactly one {DLL_IN_BUNDLE}, found {names or 'none'}")
            return sha256_bytes(z.read(names[0]))
    return sha256_bytes(dll.read_bytes())


def _json(path: Path) -> dict | None:
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return doc if isinstance(doc, dict) else None


def _sha_of(block) -> str | None:
    """A recorded DLL block's sha256 ({sha256: ...}, or a bare hex string)."""
    if isinstance(block, dict):
        block = block.get("sha256")
    return block.lower() if isinstance(block, str) and block else None


def session_sha(run: Path) -> tuple[str | None, str]:
    """One Session run dir's DLL sha: report.json's ``assembly_csharp``, else env.json's ``engine.assembly_csharp`` (a run from
    before the hardening). (sha, where it came from)."""
    rep = _json(run / "report.json")
    sha = _sha_of((rep or {}).get("assembly_csharp"))
    if sha:
        return sha, "report.json"
    env = _json(run / "env.json")
    sha = _sha_of(((env or {}).get("engine") or {}).get("assembly_csharp"))
    if sha:
        return sha, "env.json"
    return None, ("no report.json" if rep is None else "report.json names no DLL") + ("" if env else ", no env.json")


def collect(path: Path) -> list[dict]:
    """Every report under ``path`` as rows {report, role, sha, source, verdict}: a duo yields one row per game, a Session one.
    A directory with neither report is read one level down (a set of runs)."""
    path = Path(path)
    duo = _json(path / "duo.json")
    if duo is not None:
        rows = []
        dirs = duo.get("session_run_dirs") or {}
        recorded = duo.get("assembly_csharp") or {}
        for role in sorted((set(dirs) | set(recorded)) or {"host", "guest"}):
            sha, src = _sha_of(recorded.get(role)), "duo.json"
            if not sha:
                sub = Path(dirs[role]) if role in dirs else path / role
                if not sub.is_dir():
                    sub = path / role
                sha, src = session_sha(sub)
            rows.append({"report": str(path), "role": role, "sha": sha, "source": src, "verdict": duo.get("verdict")})
        return rows
    if (path / "report.json").exists() or (path / "env.json").exists():
        sha, src = session_sha(path)
        return [{"report": str(path), "role": None, "sha": sha, "source": src,
                 "verdict": (_json(path / "report.json") or {}).get("verdict")}]
    rows = []
    if path.is_dir():
        for child in sorted(p for p in path.iterdir() if p.is_dir()):
            if (child / "duo.json").exists() or (child / "report.json").exists() or (child / "env.json").exists():
                rows += collect(child)
    return rows


def judge_release(final: str, rows: list[dict]) -> tuple[bool, list[str]]:
    """(ok, lines) -- ok only when there is at least one report and EVERY row's sha starts with ``final`` (PURE)."""
    final = (final or "").lower()
    if len(final) < MIN_PREFIX:
        return False, [f"the final DLL's sha {final!r} is shorter than {MIN_PREFIX} hex digits: refusing to match on it"]
    if not rows:
        return False, ["no regression report found: nothing names the final DLL"]
    lines, bad = [], 0
    for r in rows:
        who = r["report"] + (f" [{r['role']}]" if r.get("role") else "")
        sha = r.get("sha")
        if not sha:
            bad += 1
            lines.append(f"REFUSE  {who}: names no DLL ({r.get('source')})")
        elif not sha.startswith(final):
            bad += 1
            lines.append(f"REFUSE  {who}: drove {sha[:16]}, not the final {final[:16]} ({r.get('source')}; verdict {r.get('verdict')})")
        else:
            lines.append(f"ok      {who}: {sha[:16]} ({r.get('source')}; verdict {r.get('verdict')})")
    lines.append(f"{len(rows) - bad} of {len(rows)} report(s) name the final DLL {final[:16]}"
                 + ("" if not bad else f" -- {bad} do not: re-run them on the final DLL before the release"))
    return bad == 0, lines


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("runs", nargs="+", help="run dirs (or directories of run dirs) holding the regression reports")
    src = ap.add_mutually_exclusive_group()
    src.add_argument("--sha", default=None, help=f"the final DLL's sha256 (a hex prefix of {MIN_PREFIX} or more)")
    src.add_argument("--dll", default=None, help="the final Assembly-CSharp.dll, or the engine bundle .zip carrying it")
    a = ap.parse_args(argv)
    try:
        if a.sha:
            final = a.sha.strip().lower()
        elif a.dll:
            final = final_sha(Path(a.dll))
        else:
            sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "ff9mapkit"))
            from ff9mapkit.config import find_game_path                    # noqa: E402 - the live install, last resort
            final = final_sha(Path(find_game_path()) / "x64" / "FF9_Data" / "Managed" / "Assembly-CSharp.dll")
    except (OSError, ValueError, zipfile.BadZipFile) as err:
        print(f"!!! the final DLL cannot be read: {err}", file=sys.stderr)
        return 2
    rows = [r for p in a.runs for r in collect(Path(p))]
    ok, lines = judge_release(final, rows)
    print("\n".join(lines))
    print("RELEASE GATE: " + ("PASS" if ok else "REFUSED"))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
