#!/usr/bin/env python3
"""Run many scenarios through ONE game launch.

WHY THIS EXISTS. One launch answered one scenario: a cold boot is 40-240 seconds, plus a 10-second
title settle, plus the New Game cutscene, before a single assertion runs. Ten scenarios cost ten of
those. The whole cost is fixed overhead, and it is paid again for every question asked.

WHAT MAKES IT HONEST, which is the harder half. Sharing a launch means sharing state, and a scenario
that leaves the game in a menu, mid-battle, mid-dialogue or on a black screen would otherwise poison
whatever runs next -- producing failures that belong to the runner and get reported against the game.
This arc has already published three confident false statements of exactly that shape. So:

* **The baseline is the TITLE SCREEN**, because every scenario opens with ``newgame()`` and that verb
  requires it. Not "a field", not "wherever the last one finished".
* **Every rung of the recovery ladder is VERIFIED**, never assumed -- ``Session.restore_baseline``
  re-checks the precondition after each rung and escalates exactly one step on failure.
* **A scenario that could not be given a clean baseline is `poisoned`, not `failed`.** It never ran;
  it cannot have failed. Recording it as a failure would be the harness blaming the game for its own
  inability to clean up, and given the history the default must be to blame itself.
* **A run that records no checks is `proved-nothing`**, not a pass -- the same three-verdict rule the
  single-scenario report already uses.

⚠ AND IT IS STILL NOT AN ORACLE. A green suite says the mechanisms it exercised still behave as they
did; it says nothing about anything it was not told to look at, and nothing about whether any of it
feels right. That judgment stays with the human.

    py tools/play.py --suite studies/test-harness/suites/core.toml
"""
from __future__ import annotations

import datetime as _dt
import importlib.util
import inspect
import json
import time
import traceback
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:                       # pragma: no cover - Python < 3.11
    tomllib = None

from .channel import HarnessError

#: Verdicts a scenario can end with. `poisoned` and `proved-nothing` are the two that exist to stop
#: the suite laundering its own problems into claims about the game.
VERDICTS = ("pass", "fail", "error", "poisoned", "proved-nothing")


class Scenario:
    """One entry in a suite manifest."""

    __slots__ = ("path", "field", "label")

    def __init__(self, path: Path, field: int | None = None, label: str | None = None):
        self.path = Path(path)
        self.field = field
        self.label = label or self.path.stem

    def __repr__(self) -> str:
        return f"<Scenario {self.label} field={self.field}>"


def load_manifest(path: Path, repo: Path) -> tuple[dict, list[Scenario]]:
    """Read a suite manifest.

    TOML because the rest of this kit is TOML-driven and an author should not have to learn a second
    format to list six files. Paths are resolved against the REPO ROOT, not the manifest, so a
    manifest reads the same as the command line a human would have typed.
    """
    if tomllib is None:
        raise HarnessError("suite manifests need Python 3.11+ (tomllib)")
    path = Path(path)
    try:
        doc = tomllib.loads(path.read_text(encoding="utf-8"))
    except OSError as err:
        raise HarnessError(f"cannot read the suite manifest {path}: {err}") from err
    except ValueError as err:
        raise HarnessError(f"{path} is not valid TOML: {err}") from err

    meta = dict(doc.get("suite", {}))
    default_field = meta.get("field")
    rows = doc.get("scenario", [])
    if not rows:
        raise HarnessError(f"{path} lists no [[scenario]] entries -- a suite that runs nothing "
                           f"would report a vacuous pass")
    scenarios = []
    for i, row in enumerate(rows):
        rel = row.get("path")
        if not rel:
            raise HarnessError(f"{path}: [[scenario]] #{i + 1} has no `path`")
        resolved = (repo / rel).resolve()
        if not resolved.exists():
            raise HarnessError(f"{path}: [[scenario]] #{i + 1} points at {resolved}, which does not "
                               f"exist. Refusing to start -- a suite that silently skips a member "
                               f"reports a smaller pass than it claims.")
        # ⚠ NO per-scenario `timeout` key. One was accepted and stored and never read, which is
        # worse than not offering it: a manifest author would reasonably read it as a hang guard and
        # get none. A real one needs the scenario to run somewhere it can be interrupted; until that
        # exists, an unknown key is refused rather than silently ignored.
        unknown = set(row) - {"path", "field", "label"}
        if unknown:
            raise HarnessError(
                f"{path}: [[scenario]] #{i + 1} has unknown key(s) {sorted(unknown)}. Refusing rather "
                f"than ignoring them -- a key that is silently dropped reads as a setting that works."
            )
        scenarios.append(Scenario(resolved, field=row.get("field", default_field),
                                  label=row.get("label")))
    return meta, scenarios


def load_scenario_module(path: Path):
    spec = importlib.util.spec_from_file_location(f"scenario_{path.stem}", path)
    if spec is None or spec.loader is None:
        raise HarnessError(f"cannot import a scenario from {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    if not hasattr(mod, "run"):
        raise HarnessError(f"{path} defines no run(g) function")
    return mod


def _accepts_field(fn) -> bool:
    try:
        params = list(inspect.signature(fn).parameters.values())
    except (TypeError, ValueError):
        return False
    positional = [p for p in params if p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD)]
    return len(positional) >= 2 or any(p.kind == p.VAR_POSITIONAL for p in params)


class SuiteRunner:
    """Drives a list of scenarios through one Session, restoring the baseline between each."""

    def __init__(self, session, scenarios: list[Scenario], *, meta: dict | None = None,
                 run_dir: Path | None = None, verbose: bool = True):
        self.session = session
        self.scenarios = list(scenarios)
        self.meta = dict(meta or {})
        self.run_dir = Path(run_dir) if run_dir else session.run_dir
        self.verbose = verbose
        self.results: list[dict] = []
        # The session's own report.json shares this directory with suite.json. Tell it so, or it
        # scores the LAST member's checks and publishes them as the run's verdict.
        session._suite_owned = True

    # -- reporting ----------------------------------------------------------------------------
    def _log(self, msg: str) -> None:
        if self.verbose:
            print(f"[suite] {msg}", flush=True)

    @property
    def passed(self) -> bool:
        """A suite passes only when EVERY member passed.

        `poisoned` and `proved-nothing` are deliberately not passes: the first means a scenario never
        ran, the second that it ran and asserted nothing. Counting either as green is how a suite
        starts reporting a number bigger than what it actually verified.
        """
        return bool(self.results) and all(r["verdict"] == "pass" for r in self.results)

    # -- the loop -----------------------------------------------------------------------------
    def run(self) -> list[dict]:
        """Every scenario gets a verdict, and the report is always written.

        ⚠ Both halves are load-bearing. An exception escaping the loop used to drop the current
        scenario's row, leave every later one with NO verdict at all -- not even `poisoned` -- and
        skip `suite.json` entirely, so the last machine-readable word about a suite that died at
        member 2 of 10 was a single PASS. The design's own rule is that a scenario the runner cannot
        serve is voided, never dropped; that rule has to survive the runner's own failures too.
        """
        total = len(self.scenarios)
        self._log(f"{total} scenario(s), one launch")
        # The game spends several seconds in "Initial" after launch -- before anything a baseline
        # check could be true of. Waiting here keeps the first scenario from being measured against
        # a booting game and escalated to a soft reset that cannot land yet.
        try:
            self.session.wait_for(lambda s: s.ui_state in ("Title", "FieldHUD", "WorldHUD"),
                                  timeout=180, what="the game to finish booting")
        except HarnessError as err:
            self._log(f"the game never finished booting: {err}")
        try:
            for index, scenario in enumerate(self.scenarios, start=1):
                self.results.append(self._run_one(index, total, scenario))
        except BaseException as err:                       # noqa: BLE001 - see the docstring
            done = len(self.results)
            for index, scenario in enumerate(self.scenarios[done:], start=done + 1):
                self.results.append({
                    "index": index, "label": scenario.label, "path": str(scenario.path),
                    "field": scenario.field, "verdict": "poisoned", "checks": [], "seconds": 0.0,
                    "detail": f"the suite aborted before this scenario ran: {err}",
                })
            self._log(f"the suite aborted after {done} scenario(s): {err}")
            self._write_report()
            raise
        self._write_report()
        return self.results

    def _run_one(self, index: int, total: int, scenario: Scenario) -> dict:
        label = f"{index:02d}-{scenario.label}"
        started = time.time()
        row = {
            "index": index, "label": scenario.label, "path": str(scenario.path),
            "field": scenario.field, "verdict": "error", "checks": [], "detail": "",
        }
        self._log(f"[{index}/{total}] {scenario.label}")

        # ---- the precondition, verified ------------------------------------------------------
        try:
            ok, why = self.session.restore_baseline()
        except HarnessError as err:
            ok, why = False, str(err)
        if not ok:
            # VOID, not FAIL. It never ran.
            row["verdict"] = "poisoned"
            row["detail"] = (f"the baseline could not be restored, so this scenario never ran: {why}")
            row["seconds"] = round(time.time() - started, 1)
            self._log(f"    POISONED -- {why}")
            return row
        self._log(f"    baseline: {why}")

        # ---- run it ---------------------------------------------------------------------------
        try:
            # ⚠ INSIDE the guard. begin_scenario does a BLOCKING send (its note()), so against a game
            # that has died it raises -- and out here that exception escaped the whole run.
            self.session.begin_scenario(label)
            module = load_scenario_module(scenario.path)
            run = module.run
            if scenario.field is not None and _accepts_field(run):
                run(self.session, scenario.field)
            else:
                if scenario.field is not None:
                    self._log(f"    note: {scenario.label} takes no field argument -- "
                              f"ignoring field {scenario.field}")
                run(self.session)
        except HarnessError as err:
            row["verdict"] = "error"
            row["detail"] = self._raised_detail(str(err))
            self._log(f"    ERROR -- {err}")
        except Exception as err:                                  # noqa: BLE001 - a scenario is code
            row["verdict"] = "error"
            row["detail"] = self._raised_detail(f"{type(err).__name__}: {err}")
            row["traceback"] = traceback.format_exc()
            self._log(f"    ERROR -- {type(err).__name__}: {err}")
        else:
            checks = list(self.session.checks)
            if not checks:
                row["verdict"] = "proved-nothing"
                row["detail"] = "the scenario ran and recorded no checks"
            else:
                failed = [c for c in checks if not c["ok"]]
                row["verdict"] = "fail" if failed else "pass"
                row["detail"] = f"{len(checks) - len(failed)}/{len(checks)} checks passed"

        row["checks"] = list(self.session.checks)
        row["seconds"] = round(time.time() - started, 1)
        self._collect(label, row)
        self._log(f"    {row['verdict'].upper()} in {row['seconds']}s -- {row['detail']}")
        return row

    def _raised_detail(self, message: str) -> str:
        """Describe a raise WITHOUT losing the checks that already failed before it.

        A scenario that recorded three failures and then raised is `error`, and `error` alone reads
        as "it blew up" -- the tally shows zero fails and the three real findings are invisible in
        the summary. They are still in `checks`, but a reader who trusts the tally never opens it.
        """
        failed = [c for c in self.session.checks if not c["ok"]]
        if failed:
            return (f"raised after {len(failed)} check(s) had already FAILED "
                    f"({'; '.join(c['what'] for c in failed[:3])}"
                    f"{' ...' if len(failed) > 3 else ''}): {message}")
        return message

    def _collect(self, label: str, row: dict) -> None:
        """Give every scenario its own artifact directory.

        The screenshots are already namespaced by `Session.shot_prefix`, so they can be sorted out of
        the shared channel directory by name -- which is what stops two scenarios that both captured
        "walk-before" from overwriting each other's evidence.
        """
        # ⚠ SANITISE THE DIRECTORY NAME TOO, not just the glob. A label like "walk: north" is an
        # illegal Windows path component, so this raised OSError, the except swallowed it, and the
        # scenario silently lost its whole artifact directory -- including the automatic screenshot
        # of its first failure.
        safe = "".join(c if (c.isalnum() or c in "-_.") else "_" for c in label)
        dest = self.run_dir / safe
        row.setdefault("shots", [])
        row.setdefault("collect_error", None)
        try:
            dest.mkdir(parents=True, exist_ok=True)
            shots = self.session.channel.shots
            moved = []
            if shots.is_dir():
                import shutil
                out = dest / "shots"
                # ⚠ The SANITISED label: `shot()` rewrites the name it sends (a space or a colon
                # is illegal in a filename and would also split the request line), so globbing the
                # raw label silently collects nothing for any label that needed sanitising -- and
                # what goes uncollected is the failing scenario's evidence.
                for png in sorted(shots.glob(f"{safe}-*.png")):
                    out.mkdir(exist_ok=True)
                    shutil.copy2(png, out / png.name)
                    moved.append(png.name)
            row["shots"] = moved
            (dest / "report.json").write_text(json.dumps(row, indent=2), encoding="utf-8")
        except OSError as err:
            # Record it: a reader comparing two scenarios cannot otherwise tell "captured nothing"
            # from "the evidence could not be written down".
            row["collect_error"] = str(err)
            self._log(f"    (could not collect artifacts: {err})")

    def _write_report(self) -> None:
        tally = {v: sum(1 for r in self.results if r["verdict"] == v) for v in VERDICTS}
        report = {
            "suite": self.meta.get("name", "suite"),
            "description": self.meta.get("description", ""),
            "when": _dt.datetime.now().isoformat(timespec="seconds"),
            "engine_protocol": self.session.engine_protocol,
            "passed": self.passed,
            "tally": tally,
            "scenarios": self.results,
        }
        try:
            (self.run_dir / "suite.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        except OSError as err:
            self._log(f"could not write suite.json: {err}")

    def summary(self) -> str:
        lines = []
        width = max((len(r["label"]) for r in self.results), default=10)
        for r in self.results:
            lines.append(f"  {r['verdict'].upper():<14} {r['label']:<{width}}  "
                         f"{r['seconds']:>5.1f}s  {r['detail']}")
        tally = {v: sum(1 for x in self.results if x["verdict"] == v) for v in VERDICTS}
        parts = [f"{n} {v}" for v, n in tally.items() if n]
        lines.append("")
        lines.append(f"  {len(self.results)} scenario(s): " + ", ".join(parts))
        if tally["poisoned"]:
            lines.append("  !! POISONED scenarios never ran -- the runner could not restore a clean "
                         "baseline. That is the harness's problem, not the game's.")
        if tally["proved-nothing"]:
            lines.append("  !! PROVED-NOTHING scenarios ran and asserted nothing.")
        return "\n".join(lines)
