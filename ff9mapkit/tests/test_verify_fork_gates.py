"""Offline tests for the fork-gate verification harness (``tools/verify_fork_gates.py``): the baked target
table + the playbook emitter. The actual fork/deploy/in-game A/B is a human step (Hard Constraint §2)."""

import importlib.util
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("verify_fork_gates", REPO / "tools" / "verify_fork_gates.py")
vfg = importlib.util.module_from_spec(_spec)
sys.modules["verify_fork_gates"] = vfg          # dataclass string annotations resolve via sys.modules
_spec.loader.exec_module(vfg)


def test_table_is_well_formed():
    assert vfg.TARGETS, "the target table must not be empty"
    seen = set()
    for t in vfg.TARGETS:
        assert t.field not in seen, f"duplicate field {t.field}"
        seen.add(t.field)
        assert t.observability in vfg._VERDICT_HELP, f"{t.field} has an unknown verdict {t.observability!r}"
        assert t.fbg and not t.fbg.isdigit(), f"{t.field} fbg must be a name selector, not a numeric id"
        assert t.patch.startswith("s"), t.patch
        assert t.expect


def test_2507_is_the_proven_reference():
    t = vfg._BY_FIELD[2507]
    assert t.observability == "crisp-at-load"
    assert "PROVEN" in t.expect
    # 2507 is the ONLY crisp-at-load target (the load-bearing finding: the rest fire mid-beat)
    crisp = [t for t in vfg.TARGETS if t.observability == "crisp-at-load"]
    assert crisp == [vfg._BY_FIELD[2507]]


def test_party_guards_flagged_low_signal():
    # the EventEngine.cs party-shape guards must all be low-signal (invisible with a normal party)
    for fid in (2200, 2207, 2301, 2362):
        assert vfg._BY_FIELD[fid].observability == "low-signal-party"


def test_list_renders_all_targets():
    text = vfg.list_targets()
    for t in vfg.TARGETS:
        assert str(t.field) in text
    for verdict in vfg._VERDICT_ORDER:
        assert verdict in text


def test_emit_playbook_shape():
    pb = vfg.emit_playbook(2512, folder="FF9CustomMap-vfy", scratch_id=31060)
    assert "import-chain fbg_n43_ipsn_map748b_ip_cnt_2 --ids 2512 --verbatim" in pb
    assert "--id-base 31060" in pb
    assert "scenario = 10520" in pb                       # the seeded beat
    assert "31060 2512" in pb                             # the ForkDonorPatch line to A/B
    assert "\\n" not in pb                                # no literal escape leaked into the text


def test_emit_beat_agnostic_has_no_seed():
    pb = vfg.emit_playbook(2362)                          # beat-agnostic
    assert "beat-agnostic" in pb
    assert "scenario =" not in pb


def test_emit_unknown_field_raises():
    with pytest.raises(KeyError):
        vfg.emit_playbook(9999)


def test_main_list_and_emit(capsys):
    assert vfg.main(["--list"]) == 0
    assert "verification targets" in capsys.readouterr().out.lower()
    assert vfg.main(["--emit", "2200"]) == 0
    assert "LOW-SIGNAL" in capsys.readouterr().out
