"""review2 (rest slice, 40d347f8): disc 1's Check report gains ``disc4`` only when the disc-4 dry run RETURNS. A
disc-4 replay that RAISES something its verb does not catch (anything but ValueError/FileNotFoundError -- e.g. the
struct.error a cut-short .ff9mesh now raises again, 42fb5a6b) leaves disc 1's report ok with no disc4, so the card's
pass text says "on disc 1 and on disc 4"; and "unchecked" reads the same. Run from ff9mapkit/:
  py -m pytest ../studies/overworld-editor/perf/review2_rest_disc4_crash.py -q -p no:cacheprovider -s"""
import json
import struct

import pytest

from ff9mapkit import cli
from ff9mapkit.world import discmirror as DM
from ff9mapkit.world import forestedit as FE
from ff9mapkit.world import sinkedit as SE
from ff9mapkit.world import transplant as TR
from tests.test_world_forestedit import _game, _mod, _no_real_install  # noqa: F401
from tests.test_world_sink import _island, world  # noqa: F401
from tests.test_worldsink import _drafts


def test_a_disc4_replay_that_raises(world, monkeypatch, tmp_path):
    _island(world, other=False)
    game, src = _drafts(tmp_path)
    real = TR.sink
    rep = tmp_path / "v.json"
    monkeypatch.setattr(DM, "copy_refusal", lambda blk, **k: "cells differ")

    def sink(mod, at, **k):
        if k.get("disc") == 4:
            raise struct.error("unpack_from requires a buffer of at least 72 bytes")   # a cut-short disc-4 override
        return real(mod, at, **k)
    monkeypatch.setattr(TR, "sink", sink)
    try:
        code = cli.main(["--game", str(game)] + SE.command("FF9CustomMap-world", (344.0, -360.0), report=rep))
    except struct.error as e:
        code = f"raised {type(e).__name__}"
    v = json.loads(rep.read_text())
    print("\nexit:", code, "| report ok:", v["ok"], "| disc4:", v.get("disc4"), "| card words:", FE.disc4_words(v))
    monkeypatch.setattr(TR, "sink", real)
    monkeypatch.setattr(DM, "copy_refusal", lambda blk, **k: (_ for _ in ()).throw(ValueError("no disc-4 bundle")))
    assert cli.main(["--game", str(game)] + SE.command("FF9CustomMap-world", (344.0, -360.0), report=rep)) == 0
    v = json.loads(rep.read_text())
    print("unchecked: report ok:", v["ok"], "| disc4:", v.get("disc4"), "| card words:", FE.disc4_words(v))
