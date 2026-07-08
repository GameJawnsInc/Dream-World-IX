#!/usr/bin/env python
"""Fork-gate VERIFICATION HARNESS — prove the IN-GAME-UNVERIFIED s29 (and leftover s32/s33) fork-gate fixes.

Background (project-ff9-fork-verification-harness, project-ff9-doeventcode-fork-gates): s24/s30/s31 are
in-game proven; s32's control/menu/rain gates are proven on 3 sites; s29's ~10 late-disc SOFTLOCK wraps and a
handful of s32/s33 cosmetic siblings were BATCHED on confidence (the transform is identical to the proven
wraps + identity-safe for real ids) and are still ⚠ UNVERIFIED.

The proven verification vehicle = a **1-member VERBATIM fork** deployed via ``deploy_campaign --no-warp`` into
its own scratch id, which emits ``ForkDonorPatch.txt`` (``<forkId> <donorId>`` — the linchpin the whole
EffectiveFieldId/Name remap needs). Reach it via F6 → Warp. The conclusive A/B: comment the ForkDonorPatch
line + relaunch (fix OFF) vs present (fix ON).

★ THE LOAD-BEARING FINDING (2026-07-07, this harness): unlike the PROVEN 2507 (a walkmesh hotfix that fires
at field LOAD, so a cold fork + F6 warp reaches it), **the remaining s29 gates fire mid-CUTSCENE / post-BATTLE
/ on an abnormal PARTY** — states a cold fork boots PAST. So they are mostly NOT crisply F6-testable; that is
exactly why they stayed unverified. Each target below carries an OBSERVABILITY verdict:

  crisp-at-load     the gate fires on field load -> a cold F6 warp reaches it (the 2507 class). TESTABLE.
  needs-scripted    fires only inside a scripted scroll/cutscene a cold fork skips; reachable only by seeding
                    the exact beat AND triggering the scripted sequence. HARD, often impractical via F6.
  low-signal-party  a party-SHAPE guard: silently fixes a "wrong" party. With a NORMAL party you see NOTHING;
                    proving it needs an ABNORMAL party at the exact SC. Code-verified + identity-safe --
                    accept as mechanism-proven (the memory did the same for the s33 BGM/mesh-combine siblings).
  ending-only       fires only in the Epilogue Stage; untestable outside a full ending run.

So this harness's honest job is: (1) capture the per-gate seed RE (else re-done every session); (2) emit the
exact fork+deploy playbook for whoever attempts one; (3) recommend the verdict. It does NOT execute deploys
(they need the game + a Memoria.ini FolderNames edit + relaunch) -- like ``reference-arcs``, it scaffolds the
commands. Run ``--emit <field>`` to get the copy-paste playbook for a target.

Usage:
    py tools/verify_fork_gates.py --list                 # the full gate table + verdicts (offline)
    py tools/verify_fork_gates.py --emit 2512            # the fork+deploy+F6 playbook for one target
    py tools/verify_fork_gates.py --emit 2512 --folder FF9CustomMap-vfy --id 31060
"""
from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass


@dataclass(frozen=True)
class Target:
    field: int              # the real donor field id
    fbg: str                # its FBG selector (import-chain selector; a numeric id is NOT a valid selector)
    zone: str               # human place name
    patch: str              # the s-patch that wraps its gate
    site: str               # the engine call-site(s) the wrap covers
    seed: "int | None"      # [startup] scenario to boot the beat (None = beat-agnostic); from fork-report
    roster: str             # static / story-event
    observability: str      # crisp-at-load / needs-scripted / low-signal-party / ending-only
    expect: str             # what the fix DOES (what breaks without it)


# The verification target table -- the durable RE capture (seeds from `fork-report`, sites from
# FORK_IDGATE_MAP.md, verdicts from the load-bearing finding above). 2507 is listed PROVEN as the reference.
TARGETS: tuple[Target, ...] = (
    Target(2507, "fbg_n43_ipsn_map748a_ip_cnt_1", "Ipsen's Castle (ladders/stairs)", "s29",
           "FieldMap.cs:102 + :139 (DelayedActiveTri: walkmesh tris + NPC-collision)", None, "static",
           "crisp-at-load",
           "★ PROVEN 2026-06-23. Disables tris 174/175/177/178 + chest collision 0.5s after load so the "
           "back-strip crossing is walkable; a fork without it snags on the chests. (Also caught + fixed a "
           "real kit bug: the baked walkmesh_tri_toggles fought the engine's delayed fix -> chests one floor "
           "low. Now engine_remapped=True, no baked toggle.)"),
    Target(2512, "fbg_n43_ipsn_map748b_ip_cnt_2", "Ipsen's Castle (scroll)", "s29",
           "FieldMap.cs:1966 (bind playerController when null for 3D scroll)", 10520, "static",
           "needs-scripted",
           "Binds the player controller so a scripted 3D scroll has something to follow; without it the scroll "
           "camera stalls. Fires only during the scripted scroll cutscene -- a cold F6 warp (you already hold "
           "control) won't null the controller, so hard to trigger."),
    Target(1656, "fbg_n31_iftr_map556a_if_pts_1", "Iifa Tree (vine scroll)", "s29",
           "FieldMap.cs:1495 + :1972 (scroll crutch: bind uid 8 / CrutchForEvaMap)", 6970, "static",
           "needs-scripted",
           "Same scroll-crutch class as 2512, on the Iifa vine. Iifa is a POOR testbed (the 1655/1663 saga: "
           "story-climax, F6 framing artifacts). Skip unless forking Iifa for real."),
    Target(768, "fbg_n13_brmc_map278_bu_int_1", "Burmecia Palace (post-Beatrix)", "s29",
           "EventEngine.updateModelsToBeAdded.cs:80 (reposition 7 actors, fix #664)", 3900, "story-event",
           "needs-scripted",
           "After the Beatrix battle, repositions/re-poses Brahne/Kuja/Zidane/Vivi/Freya/Quina/Beatrix to "
           "fixed cutscene spots; a fork loses it -> actors scattered. Fires in the POST-BATTLE reinit, which "
           "a cold fork doesn't run -- needs the actual Beatrix fight, not just the seed."),
    Target(2200, "fbg_n38_sdpl_map640_sp_rro_0", "Desert Palace (Gulug Stone)", "s29",
           "EventEngine.cs:657 (clear party after the Gulug Stone)", 9450, "story-event",
           "low-signal-party",
           "A party-correctness hotfix (clears 4 slots after obtaining the Gulug Stone). Only matters with the "
           "specific abnormal party the script would otherwise leave; a normal party shows nothing."),
    Target(2207, "fbg_n38_sdpl_map645_sp_kpw_0", "Desert Palace (Hall)", "s29",
           "EventEngine.cs:667 + FieldMapActorController.cs:799 (forced team + collision-unstick skip)", 9835,
           "story-event", "low-signal-party",
           "Forces exactly Oeilvert's team when bringing the Gulug Stone back (prevents a later soft-lock). "
           "Party-shape guard -> needs an abnormal party to observe."),
    Target(2301, "fbg_n35_estg_map602_eg_rm1_0", "Esto Gaza (Altar)", "s29",
           "EventEngine.cs:687 (force a normal char for the Priest cutscene)", 9950, "static",
           "low-signal-party",
           "Ensures >=1 normal character (forces Zidane+Steiner) for the Priest cutscene. Only observable if "
           "the party has none of Garnet/Steiner/Freya/Quina/Amarant -- an abnormal-party setup."),
    Target(2362, "fbg_n36_glgv_map802_gv_mgs_0", "Gulug (Path bottom)", "s29",
           "EventEngine.cs:700 (force a normal team for the bottom cutscene)", None, "static",
           "low-signal-party",
           "Forces Zidane/Vivi/Steiner/Garnet for the bottom-of-Gulug cutscene when the party is odd. "
           "Beat-agnostic to reach, but the guard is a no-op with a normal party."),
    Target(3009, "fbg_n00_tshp_map011c_th_stg_3", "Epilogue: Stage", "s29",
           "Dialog.cs:820 (ForceControlByEvent + yield-break in AutoHide)", None, "story-event",
           "ending-only",
           "Hands dialog control back to the event on the Epilogue Stage; a fork falls through to the timed "
           "AutoHide. Untestable outside a full ending run."),
    Target(3010, "fbg_n00_tshp_map011f_th_stg_6", "Epilogue: Stage", "s29",
           "Dialog.cs:826 (same handoff as 3009) + VoicePlayer.cs:251 (VA-only)", None, "story-event",
           "ending-only",
           "Same Epilogue dialog-handoff as 3009. Ending-only."),
)

_BY_FIELD = {t.field: t for t in TARGETS}

_VERDICT_ORDER = ("crisp-at-load", "needs-scripted", "low-signal-party", "ending-only")
_VERDICT_HELP = {
    "crisp-at-load": "F6-TESTABLE — fires at field load; warp in and observe",
    "needs-scripted": "hard — fires only inside a scripted scroll/cutscene a cold fork skips",
    "low-signal-party": "accept as code-verified — a party-shape guard, invisible with a normal party",
    "ending-only": "untestable outside a full ending run",
}


def list_targets() -> str:
    """The full gate table grouped by observability verdict (offline; the RE capture)."""
    out = ["Fork-gate verification targets (s29 late-disc softlocks + siblings)",
           "=" * 72]
    for verdict in _VERDICT_ORDER:
        rows = [t for t in TARGETS if t.observability == verdict]
        if not rows:
            continue
        out.append("")
        out.append(f"[{verdict}]  {_VERDICT_HELP[verdict]}")
        for t in rows:
            seed = f"seed {t.seed}" if t.seed is not None else "beat-agnostic"
            proven = "  ★ PROVEN" if "PROVEN" in t.expect else ""
            out.append(f"  field {t.field:<5} {t.zone:<32} {t.patch}  ({seed}){proven}")
            out.append(f"        {t.site}")
    out.append("")
    out.append("Verdict: only the crisp-at-load class is F6-testable on a cold fork (2507 = proven). The rest")
    out.append("need the real scripted beat or an abnormal party; the low-signal-party + ending-only gates are")
    out.append("code-verified + identity-safe -- accept as mechanism-proven (as the s33 BGM/mesh-combine were).")
    out.append("Emit a fork+deploy playbook for any target:  py tools/verify_fork_gates.py --emit <field>")
    return "\n".join(out)


def emit_playbook(field: int, *, folder: str = "FF9CustomMap-vfy", scratch_id: int = 31060) -> str:
    """The copy-paste fork + deploy + F6-test playbook for one target (scaffold, not executed)."""
    t = _BY_FIELD.get(field)
    if t is None:
        raise KeyError(f"field {field} is not a verification target (see --list)")
    out_dir = f"C:/Users/skaki/ff9verify/v{t.field}"
    seed_note = (f"# EDIT the member .field.toml — add:  [startup] / scenario = {t.seed}"
                 if t.seed is not None else "# beat-agnostic: no [startup] scenario needed")
    lines = [
        f"Verification playbook — field {t.field} ({t.zone}), gate {t.patch}",
        "=" * 72,
        f"Gate site   : {t.site}",
        f"Observability: {t.observability} — {_VERDICT_HELP[t.observability]}",
        f"Expect      : {t.expect}",
        "",
    ]
    if t.observability == "low-signal-party":
        lines += ["⚠ LOW-SIGNAL: this is a party-shape guard — invisible with a normal party. Only worth an",
                  "  in-game A/B with an ABNORMAL party seeded at the exact SC. Otherwise accept as code-verified.",
                  ""]
    elif t.observability == "ending-only":
        lines += ["⚠ ENDING-ONLY: fires only in the Epilogue Stage; not reachable via a fork harness. Accept as",
                  "  code-verified (identity-safe transform, same as the proven wraps).", ""]
    elif t.observability == "needs-scripted":
        lines += ["⚠ NEEDS THE SCRIPTED BEAT: a cold F6 warp boots past this gate. Seed the beat AND drive the",
                  "  scripted sequence (scroll/battle) to exercise it — often impractical via F6 alone.", ""]
    lines += [
        "1) Fork it verbatim into its own scratch id (needs the FF9 install):",
        f"   cd ff9mapkit && py -m ff9mapkit import-chain {t.fbg} --ids {t.field} --verbatim \\",
        f"      --name-prefix VFY --id-base {scratch_id} --campaign-name VERIFY_{t.field} --out {out_dir}",
        "",
        f"2) {seed_note}",
        "",
        "3) Deploy into a shared verification folder (--no-warp leaves New Game alone):",
        f"   py tools/deploy_campaign.py {out_dir}/campaign.toml --mod-folder {folder} --no-warp --apply",
        f"   # then add '{folder}' to Memoria.ini [Mod] FolderNames + Priorities (highest) BY HAND, + RELAUNCH",
        f"   # confirm {folder}/ForkDonorPatch.txt has:  {scratch_id} {t.field}",
        "",
        "4) Test: F6 → Warp → " + str(scratch_id) + (f"  (set scenario {t.seed} in the Warp tab)" if t.seed else "")
        + ".",
        f"   Expect: {t.expect.split('.')[0]}.",
        "",
        "5) Conclusive A/B (isolate the fix): comment (#) the line",
        f"   '{scratch_id} {t.field}' in {folder}/ForkDonorPatch.txt → RELAUNCH → warp.",
        "   Fix OFF should break the behavior; restore + relaunch to return to working.",
    ]
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Fork-gate verification harness (list targets / emit a playbook).")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--list", action="store_true", help="print the full gate table + observability verdicts")
    g.add_argument("--emit", type=int, metavar="FIELD", help="print the fork+deploy+F6 playbook for one target")
    ap.add_argument("--folder", default="FF9CustomMap-vfy", help="the shared verification mod folder")
    ap.add_argument("--id", type=int, default=31060, dest="scratch_id", help="the scratch fork id (30000-32767)")
    args = ap.parse_args(argv)
    try:                                             # the table uses ★/⚠; keep the Windows console from choking
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    if args.list:
        print(list_targets())
        return 0
    try:
        print(emit_playbook(args.emit, folder=args.folder, scratch_id=args.scratch_id))
    except KeyError as e:
        print(str(e), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
