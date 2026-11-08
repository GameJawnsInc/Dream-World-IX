"""The nightly gate's per-test results log -- a pytest plugin that writes one JSON line per finished test AS IT FINISHES.

Why it exists (tools/nightly_gate.md, "A killed run still names its failures"): the gate kills a suite that overruns
its cap, and a killed pytest never prints its summary -- on 2026-11-08 the run died at 87% with 73 ``F`` marks in its
progress lines and not one of them had a name. JUnit XML and the terminal summary are both written at session END; this
file is written test by test and flushed every line, so whatever finished before the kill is on disk, named.

Loaded only by the gate: ``-p ff9_gate_results --gate-results=<path>``, with this directory on PYTHONPATH (it holds
nothing else, so it can shadow nothing). The ``=`` is load-bearing: an xdist worker reads a SEPARATE value as a
positional path before this plugin registers the option, and its rootdir drifts to the common ancestor of the tests
and the log (``nightly_gate.plugin_args`` says what that cost). Under xdist the plugin imports in every worker -- they parse the same args --
but only the CONTROLLER writes: it receives every worker's reports through ``pytest_runtest_logreport``, so one process
owns the file and lines never interleave. Without ``--gate-results`` the plugin is inert.

Record shapes (``nightly_gate.parse_results`` is the reader):
  {"ev": "start", "pid": 123, "workers": 6}
  {"id": "<nodeid>", "w": "call", "o": "passed", "d": 1.23, "s": 0.04, "wk": "gw3"}
      w = the phase (setup/call/teardown, or "???" for an xdist worker crash); o = that report's outcome, with xfail
      folded in (xfailed / xpassed); d = its duration; s = the setup time already spent on this test (call rows only)
  {"id": "<nodeid>", "w": "collect", "o": "failed"}     a collection error
  {"ev": "finish", "exitstatus": 1}                     ABSENT after a kill -- that absence is how the reader knows
"""
from __future__ import annotations

import json
import os

import pytest


def pytest_addoption(parser):
    parser.getgroup("ff9 nightly gate").addoption(
        "--gate-results", default=None, metavar="PATH",
        help="append one JSON line per finished test to PATH, flushed as each test finishes (the nightly gate's "
             "kill-proof results log)")


def _is_worker(config) -> bool:
    return hasattr(config, "workerinput")


class GateResults:
    def __init__(self, path: str, workers: int):
        self.fh = open(path, "a", encoding="utf-8", buffering=1)
        self._setup = {}
        self.write({"ev": "start", "pid": os.getpid(), "workers": workers})

    def write(self, rec: dict) -> None:
        self.fh.write(json.dumps(rec) + "\n")
        self.fh.flush()

    @pytest.hookimpl(tryfirst=True)
    def pytest_runtest_logreport(self, report):
        when, outcome = report.when, report.outcome
        if hasattr(report, "wasxfail"):
            outcome = "xfailed" if outcome == "skipped" else "xpassed" if outcome == "passed" else outcome
        if when == "setup" and outcome == "passed":
            self._setup[report.nodeid] = report.duration       # spent before the call row, carried onto it
            return
        if when == "teardown" and outcome == "passed":
            self._setup.pop(report.nodeid, None)
            return
        rec = {"id": report.nodeid, "w": when, "o": outcome, "d": round(report.duration or 0.0, 3)}
        if when == "call":
            rec["s"] = round(self._setup.get(report.nodeid, 0.0), 3)
        node = getattr(report, "node", None)                   # xdist's WorkerController on the controller
        gw = getattr(getattr(node, "gateway", None), "id", None)
        if gw:
            rec["wk"] = gw
        self.write(rec)

    def pytest_collectreport(self, report):
        if report.failed:
            self.write({"id": report.nodeid, "w": "collect", "o": "failed"})

    @pytest.hookimpl(trylast=True)
    def pytest_sessionfinish(self, session, exitstatus):
        self.write({"ev": "finish", "exitstatus": int(exitstatus)})
        self.fh.close()


def pytest_configure(config):
    path = config.getoption("--gate-results", default=None)
    if not path or _is_worker(config):
        return
    workers = getattr(config.option, "numprocesses", None) or 0
    config.pluginmanager.register(GateResults(path, workers if isinstance(workers, int) else 0), "ff9-gate-results")
