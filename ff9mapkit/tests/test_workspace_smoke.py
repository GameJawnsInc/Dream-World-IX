"""THE SMOKE, RUN BY THE SUITE -- because for a whole round nothing ran it and everything said it did.

WHY THIS FILE EXISTS. Three test modules' docstrings claim the Qt shell is covered:

    test_workspace_style.py:2  "The Qt shell itself is exercised by `py apps/ff9_workspace.pyw --smoke`"
    test_setup.py:256          "the Qt shell is covered by --smoke"
    test_graphview.py:5        "the widget itself is exercised by the campaign_editor --smoke"

Nothing ran it. Not the suite, not CI -- only a human typing it by hand, which means it was covered
exactly as often as somebody remembered. **A LAW WRITTEN IN A DOCSTRING IS A WISH**, this codebase's own
recurring defect, here at the level of the test suite's own coverage claim.

The cost was real and it was measured: the smoke was RED for an entire round while five commit messages
reported it green. Four independent breakages had accumulated, and the suite could not see one of them,
because the suite is 3644 tests of pure functions and rendered strings and THE SMOKE IS THE ONLY THING
THAT DRIVES THE LIVE SHELL:

  1. `assert _fqm._GUIDED is True` -- read the DEVELOPER'S prefs. On any machine with `"guided": false`
     it failed on its owner's preference, and took two more asserts with it (the Battle "Advanced drawer"
     only EXISTS in Guided, so its absence was reported as a defect).
  2. `maximumHeight() == 16` on the wrap-preview note -- QUARTO P1 re-pinned it to 18, so the filter
     matched nothing. It asserted the NUMBER when its own comment stated the LAW ("fixed-height, no
     reflow"). min == max is the law and survives the next re-pin.
  3. `"Fork a real field" in _g_empty` -- a later round made the spine SILENT on EMPTY on purpose
     (Home's lede already says it). The assert AND its comment both still taught the reversed design.
  4. a lone U+2192 in the summary -- `UnicodeEncodeError` on a default Windows console, i.e. the exact
     command the brief documents. Masked until the asserts above stopped failing first.

11 seconds. The suite runs 85. That is the whole price of the claim being true.

ISOLATED, BOTH WAYS. `LOCALAPPDATA` is repointed at a tmp dir so this neither READS nor WRITES the
developer's real prefs -- which is defect #1's root cause, and the same poison
`test_the_sheet_never_reads_the_developers_own_accessibility_slider` fences for the type dial.

PYTHONIOENCODING IS DELIBERATELY NOT SET. Setting it would hide defect #4 forever: on Windows the child
encodes its stdout with the locale codepage, so a non-ASCII character in the summary raises. That makes
this test a real ASCII guard on the dev-loop command, at the cost of being trivially true on a UTF-8 CI.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

pytest.importorskip("PySide6")

_APP = Path(__file__).resolve().parents[2] / "apps" / "ff9_workspace.pyw"


def test_the_workspace_shell_smoke_passes(tmp_path):
    """Drive the real Workspace end to end in a subprocess and demand exit 0.

    A SUBPROCESS, not an in-process call: `_smoke` pins module globals (beginner-mode) and `main()` does
    `_smoke(win); return` on the assumption the process is about to die. Importing that into a shared
    pytest process would leak the pinned state into whatever ran next -- and this file's whole subject is
    tests that quietly depend on state nobody set on purpose.
    """
    assert _APP.is_file(), f"the smoke entry point moved: {_APP}"
    env = dict(os.environ)
    env["LOCALAPPDATA"] = str(tmp_path)           # never read OR write the developer's real prefs
    env["QT_QPA_PLATFORM"] = "offscreen"
    env["FF9MAPKIT_NO_THUMBS"] = "1"              # deterministic: no worker threads
    env.pop("PYTHONIOENCODING", None)             # see the module docstring -- this is the ASCII guard
    r = subprocess.run([sys.executable, str(_APP), "--smoke"],
                       capture_output=True, text=True, env=env, timeout=300)
    assert r.returncode == 0, (
        "the workspace shell smoke is RED -- this is the only test that drives the live shell, so a "
        "green suite means nothing here:\n" + (r.stdout + r.stderr)[-4000:]
    )
    assert "smoke ok" in r.stdout, f"the smoke exited 0 but printed no verdict: {r.stdout[-500:]!r}"


def test_the_smoke_survives_a_hostile_prefs_file(tmp_path):
    """THE SMOKE MUST NOT DEPEND ON THE DEVELOPER'S PREFERENCES -- and a clean tmp dir cannot prove that.

    This fence exists because the obvious one does NOT work, which is worth more than the fence itself.
    `test_the_workspace_shell_smoke_passes` above repoints LOCALAPPDATA at an EMPTY tmp dir, so prefs fall
    back to their factory defaults -- `guided: True` -- and the pin in `_smoke` is redundant there. Re-break
    the pin and that test STAYS GREEN: the isolation hides the exact defect the isolation was added for.

        AN ISOLATED TEST PROVES YOUR CODE WORKS IN ISOLATION. IT SAYS NOTHING ABOUT THE USER'S MACHINE.

    So this one does the opposite: it BUILDS the machine that broke. Every value here is deliberately the
    non-default, because the defect was never "guided is false" -- it was "the smoke inherits state nobody
    told it about", and `guided` is simply the one that happened to bite:

        guided        False     <- the real prefs on the machine where this was found. Three asserts
                                   depend on it, incl. a Battle drawer that only EXISTS in Guided, so its
                                   correct absence was reported as a defect.
        density       compact   <- a different padding profile
        text_scale    150       <- CALIBRE, which HEED seeds from the Windows slider, so a user can land
                                   here without ever opening Preferences
        theme         light     <- the palette half of the app most tests never render
        motion        off       <- animate/no-animate paths
        restore_session True    <- the startup path that opens the last project

    If the smoke passes here, it is measuring the product. If it fails, it is measuring its owner.
    """
    import json
    cfg = tmp_path / "ff9mapkit" / "config"
    cfg.mkdir(parents=True)
    (cfg / "prefs.json").write_text(json.dumps({
        "guided": False, "density": "compact", "text_scale": 150,
        "theme": "light", "motion": "off", "restore_session": True, "recent": [],
        # getstarted_hidden: the round-8 key, added THE SAME DAY it shipped -- because this fence's own
        # `layout` comment below documents what happens otherwise ("covering the keys that came to
        # mind"), and the round's adversarial review caught the omission within hours: the smoke's
        # newcomer asserts read the dismissal live, so a machine whose owner clicked Hide went red.
        # The dismissal is now stubbed in-memory inside _smoke; this key keeps that pin honest.
        "getstarted_hidden": True,
        # `layout` WAS THE ONE KEY THIS FENCE SKIPPED -- and it is the exact key THE DOC PANE proved was
        # the defect ("the defect is entirely the PERSISTED layout"). A fence whose thesis is "every value
        # deliberately non-default" that omits the one key a sibling commit is about is not covering the
        # product, it is covering the keys that came to mind. A wide layout replayed narrow is the real
        # case; the 1-element console_split is the CORRUPT case, which used to reach an unguarded index
        # and raise IndexError (prefs.layout() checked type and sign but never arity).
        "layout": {"central_split": [300, 1198, 420], "console_split": [1],
                   "console_collapsed": True},
    }), encoding="utf-8")
    env = dict(os.environ)
    env["LOCALAPPDATA"] = str(tmp_path)
    env["QT_QPA_PLATFORM"] = "offscreen"
    env["FF9MAPKIT_NO_THUMBS"] = "1"
    r = subprocess.run([sys.executable, str(_APP), "--smoke"],
                       capture_output=True, text=True, env=env, timeout=300)
    assert r.returncode == 0, (
        "the smoke FAILS against a non-default prefs file, so it is testing the developer's settings "
        "rather than the app. Pin what it needs (see `_smoke`'s beginner-mode pin and main()'s "
        "`pick_palette(\"dark\" if smoke else ...)`) instead of inheriting it:\n"
        + (r.stdout + r.stderr)[-4000:]
    )


def test_the_smoke_summary_is_ascii_safe():
    """The dev-loop command must not die on a default Windows console.

    `py apps/ff9_workspace.pyw --smoke` is the command the brief documents, and cmd.exe's default codepage
    is cp1252. A single U+2192 in the summary string raised UnicodeEncodeError there -- AFTER every assert
    had passed, so the run was green and reported as broken. It stayed hidden only because the asserts
    above were failing first.

    Checked against the SOURCE rather than a run, so it holds on a UTF-8 CI where the run cannot fail.
    (The probe that first measured this printed the offending character and died on the same encode it was
    written to diagnose, before it could write its fix. Print the codepoint, not the character.)
    """
    from ff9mapkit.workspace import shell
    src = Path(shell.__file__).read_text(encoding="utf-8")
    i = src.find("workspace shell smoke ok")
    assert i > 0, "the smoke's summary string moved -- this fence can no longer see what it guards"
    tail = src[i:i + 5000]
    bad = sorted({ord(c) for c in tail if ord(c) > 127})
    assert not bad, (
        f"non-ASCII codepoints {[hex(b) for b in bad]} in the --smoke summary: this raises "
        f"UnicodeEncodeError on a default Windows console, which is where the documented dev-loop "
        f"command runs. Use '->' (as the rest of this summary already does)."
    )
