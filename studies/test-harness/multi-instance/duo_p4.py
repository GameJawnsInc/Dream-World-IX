"""Probe P4 re-expressed as a DUO scenario: two REAL FF9s pair over loopback, harness-driven (tools/harness/duo.py).

    py tools/harness/duo.py studies/test-harness/multi-instance/duo_p4.py                    # T-bridge-local (default)
    py tools/harness/duo.py studies/test-harness/multi-instance/duo_p4.py --topology relay   # T-relay-direct

What p4_pairing.py hand-rolled, the duo now owns: C0 (the private ports free), C1 (the local relay with --tap; for
bridge, one netsync_bridge per player naming its game with --hang-pid), and :meth:`Duo.pair` -- C2 (each game takes its
role from its OWN root's ini: a short wait, then one same-field warp), C3 (both legs on the relay as host / guest), C4
(the guest paired on the host's field 250), C5 (a ghost on 250 in BOTH games), C6 (the guest's state mirror ARMED). This
file adds what P4 judged after the pairing:

  C7  the guest's story byte 1121 reads the HOST's 0xA5 (its own New-Game save holds 0) -- the mirror's first proof
  C8  the host's own battle is published ('battle intro:'), and the guest boots its diorama on scene 67 and goes LIVE
  C9  both games show the battle (ui_state BattleHUD) -- a cross-instance parity read off the two channels
  info  the host's s114 start-hold lines: a REAL guest's report now releases the hold

PAIR seeds the host's party through COOPPARTY (when registered, as p4 did) before it warps to 250. Prereqs: both roots
built (``py tools/harness/instance.py ensure C:\\gd\\ff9-inst\\host`` and ``...\\guest``), no FF9 running from either,
no controller connected, nobody at the keyboard.
"""
import datetime as _dt
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "scenarios"))
import _coop_battle as cb                                          # noqa: E402

SCENE = 67


#: duo.py's CLI calls ``d.pair(**PAIR)``: the host's party is seeded before the bench warp, exactly like p4.
PAIR = {"host_setup": lambda g: cb.seed_party(g, back_to=250)}


def run_duo(d) -> None:
    d.expect_mirror(cid="C7")
    at = _dt.datetime.now() - _dt.timedelta(seconds=1)
    gh = d.host
    gh.start_battle(SCENE, group=-1, rand=bool(getattr(gh.state, "coop_intro_mirror", False)))
    d.expect_line("host", "intro", "the host's own battle is published ('battle intro:')", timeout=20.0, after=at,
                  cid="C8-intro")
    d.expect_line("guest", "boot", f"the guest's diorama BOOTs scene {SCENE}", timeout=30.0, after=at,
                  pred=lambda m: int(m.group(1)) == SCENE, cid="C8-boot")
    d.expect_line("guest", "live", "the guest's diorama goes LIVE on the host's nonce", timeout=30.0, after=at,
                  cid="C8-live")
    hold = [m for _t, _l, m in d.lines("host") if "start hold" in m]
    d.note("host s114 start-hold lines: " + (" | ".join(h[:160] for h in hold[:6]) or "none"))
    d.expect_parity("both games show the battle (ui_state)", lambda s: s.ui_state, want="BattleHUD", timeout=20.0,
                    cid="C9")
    time.sleep(2.0)
    d.note("archived mid-run logs: " + ", ".join(f"{k}={v}" for k, v in d.archive("p4").items()))
