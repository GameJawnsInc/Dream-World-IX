"""review2 (runner slice): a pytest plugin (-p) that removes kill()'s own proc.kill() from JobRunner, so the J5
fence (test_a_killed_job_s_process_ends) can be run against the mutant without editing the package. It also
prints, per kill, whether the worker was still inside Popen (job["proc"] None) when kill() ran.
  cd ff9mapkit; PYTHONPATH=../studies/overworld-editor/perf py -m pytest -p review2_runner_mutant_kill_plugin \
      tests/test_worldedit.py::test_a_killed_job_s_process_ends -q -p no:cacheprovider
"""
import inspect
import sys
import textwrap

LANDED = []


def pytest_configure(config):
    import ff9mapkit.workspace.worldforest as WF
    src = textwrap.dedent(inspect.getsource(WF.JobRunner.kill)).replace("proc.kill()", "pass")
    ns = dict(vars(WF))
    exec(compile(src, "<mutant kill>", "exec"), ns)
    mutant = ns["kill"]

    def kill(self):
        if self._job is not None:
            LANDED.append("inside Popen" if self._job["proc"] is None else "after Popen")
        mutant(self)
    WF.JobRunner.kill = kill


def pytest_unconfigure(config):
    sys.__stdout__.write(f"[mutant kill() landed: {LANDED}]\n")
