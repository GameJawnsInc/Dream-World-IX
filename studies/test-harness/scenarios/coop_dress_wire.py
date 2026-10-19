"""R3 GROUP 2, s139 -- G9: SECTION 8 ON A REAL WIRE AND THE HOST'S TRANSPORT SITE (a duo leg, run unattended).

    py tools/harness/duo.py studies/test-harness/scenarios/coop_dress_wire.py
    COOP_CALIBRATE=1 py tools/harness/duo.py studies/test-harness/scenarios/coop_dress_wire.py   (both roots on the s138 DLL)

WHY A DUO (R3-FIELD-MODEL-AUDIT.md 2.2 amendment 14, 4.3 G9). The solo bench (coop_self_dress.py leg G) drives only the
SELFTEST dress site: the selftest role has no socket, so neither the host's TRANSPORT site (HostDress behind GhostGuard
against a real guest's wire body) nor the producer's section 8 on a real type-5 frame is ever reached there. Two s139
games through tools/harness/duo.py reach both: the host at GhostAs auto with the COOPPARTY seed (party [0, 1, 2, 3]: slot 1
Vivi, slot 2 Garnet), field 250; the guest Role=client. The relay's ``--tap`` (relay.f9tape) is the witness the feature does
not compute: every frame either game put on the wire, as the wire carried it.

WHY A SAME-DLL DUO IS AN OLD-GUEST STAND-IN. An s139 GUEST's receive path IS the old path: no production code reads section
8 in s139 (only DressSelfTest reads it: test_harness_netsync.py pins that), and NetSyncState.cs / NetSyncParty.cs -- the
walkers an s117 laptop runs -- are untouched since s103. So the s139 guest's ApplyStory / ParseSections / TryReadSection
ARE an old guest's. The duo's one limit -- both roots junction one Managed, so it cannot MIX DLLs -- bites only box B19 (an
OLD laptop dressed by a new host), which stays a sitting box.

THE PHASES -- THREE DRESSES, ONE TRANSPORT SITE. One dress cannot tell the s139 site from the s138 rule it replaced: at
GuestSlots 2 both dress Vivi with the same translated idle, and Vivi hides nothing in field mode, so only the absent `mode`
key would go red (the review's rhost-1 / transport-blind findings). So the host's [Netsync] GuestSlots is STEPPED LIVE
(duo.Duo.set_netsync: a BEHAVIOUR key of _cfgBehaviorSig, applied by the host's 2 s ini poll with the session kept; each
step waited for on the host's own config echo, and every judged publish must PUBLISH that GuestSlots,
`netsync.battle.host.guest_slots`), each phase judged on the host's ghost of the guest, in this order:
  G9d  GuestSlots 2 (the pairing's): slot 1, VIVI (model 8, rig 1).
  G9e  GuestSlots 4: slot 2, GARNET (185, rig 2) -- AND THE REST MASK: `shown_mask == rest_mask ==` the install prefab's
       field-mode mask and `hidden` == its hides (coop_self_dress.rest_mask_verdict: ModelFactory's rule over the prefab off
       p0data, the host root's [Graphics] GarnetHair, the host's published scenario counter): ONE hairstyle. It pins the
       transport site's `else if (hostRule) ApplyGhostMask(_ghostRestMask)`: without it every renderer EnsureGhost enabled
       stays on (both hairstyles), and the s138 client branch applies no rest mask either.
  G9f  GuestSlots 0: a SPECTATOR (owner D2) -- the MOOGLE (220, rig 8, GEO_NPC_F0_MOG, an ANH_NPC_F0_MOG clip): the
       transport site's HostDress (the moogle when the host role's mask is 0); the s138 client rule leaves it undressed.
Each dress phase judges, on the LAST host publish whose ghost tuple held 2+ publishes on FieldHUD with `session.ghost` true
and the phase's GuestSlots published, the twin's host rule over the guest's REAL wire body (`player.model` on the guest: 98,
so GhostGuard keeps the dress): model, rig, its GEO and texture stem off the install (the kit's read_model), the clip of the
dressed rig's loco for the guest's own anim (playing), and `ghost.mode` 'ini:auto'.

THE CHECKS (every expected value computed by battlewire's twins, never asked of the engine):
  G9a  THE TAP, read LAST (it then holds every phase): every host type-5 frame the relay forwarded carries section 8 right
       after section 7 and LAST, the s103 walkers' twins land the same story / party sections / sections 4-7 with it
       stripped and a section appended after it still reads (coop_peer.tape_dress) -- AND the bodies, in TAPE ORDER, are
       the twin's for each phase the run stepped (BW.host_dress_section, GhostAs auto over the host's PUBLISHED party
       `netsync.dress.party`): 08 00 01 (Vivi), then B9 00 02 (Garnet), then DC 00 FF (the moogle) -- each frame its
       phase's body or, at a step, the NEXT phase's, never an earlier one, never a skip, every phase MIN_PHASE_FRAMES+
       frames. An s138 host's frames carry none.
  G9b  THE OLD READERS STEPPED PAST IT, live: the guest's Memoria.log reads 'state-mirror ARMED', its story mirroring
       (`netsync.session.mirroring`), and its PARTY MIRROR (`netsync.dress.mirror_party`: what ParseSections landed) == the
       host's published party.
  G9c  the guest's own body stays plain Zidane at EVERY phase: `player.model` 98 (an s139 guest dresses nothing of its own).
  G9d / G9e / G9f  the phases above.
CALIBRATION (COOP_CALIBRATE=1, both roots on the s138 DLL): exactly OLD_PREDICTED red -- G9a (no section 8 on the tap:
"none"), G9b (no `mirror_party` key), G9d and G9e (no `ghost.mode`; G9e's visibility keys absent too) and G9f, whose detail
also shows the one BEHAVIOURAL in-game red the old DLL gives: an s138 host leaves a spectator's ghost plain Zidane, not the
moogle. G9c stays green (an s138 guest is 98 too). A predicted red that reads "not reached" (a phase never stepped) fails
G9-CAL as UNPROVEN. The transport site has no host-role lever (the `selfdress` levers are selftest-only by design), so its
mask line and its D2 rule are shown red OFFLINE: each judge fed the s138 client rule's answer (test_harness_netsync.py).
NOT PROVEN HERE (sitting boxes): the guard's non-98 half on the transport site (a guest WEARING another body: B28) and the
raw wire anim on the guest's own dressed body (a guest whose wire body IS the dress: an s140+ laptop, B20) -- a same-DLL
duo guest always sends 98; an OLD laptop dressed by a new host (B19: the duo cannot mix DLLs).
[s140] AN s140 GUEST DRESSES ITSELF off the host's section 8 at each FIELD LOAD (NetSyncSelfDress.ArmFromState at the
ApplyStory success branch), so on an s140+ guest (it publishes `netsync.dress.self`) each phase after a live GuestSlots step
first RE-LOADS the guest's field (a warp to 250 at entrance 0) and waits for its re-arm (REWARP_S). This is the first proof of
the CLIENT arm off a REAL host's section 8 over a real wire (the solo bench arms only from the selftest spec):
  G9c  (s140+) the guest's own body at EVERY phase is the dress that phase's section 8 carries (BW.host_dress_section ->
       its model; `body` that model's texture stem off the install), `netsync.dress.self` why 'dressed', from 'host',
       want_model that model -- Vivi, then Garnet, then the moogle (a spectator, owner D2).
  G9t  (s140+) THE TEARDOWN LAW ON THE WIRE: right after each live step and BEFORE the guest's re-load, its live body is
       still the previous phase's dress (nothing undresses a live body; the arm moves at the next field load only), and
       the host shows that wire body AS IT IS (GhostGuard: a non-98 wire that is not the new dress).
  G9d-f (s140+) judged as above, and the guest's wire body must BE the phase's dress (the twin's want == the section-8
       model): a guest that never re-armed is red, never a pass on its stale body.
On an s139 guest nothing changes (no re-load; G9c plain Zidane; no G9t).
[s141] AN s141 GUEST'S DRESS POLISH OFF A REAL HOST'S SECTION 8. The solo bench (coop_self_dress.py leg F) proves the polish
on the SELFTEST role only; here the CLIENT lane: the same body-gated hooks (MapFootstep at CHRFX, fldmcf's source-row
fallback) on a body armed from the host's wire. An s141+ guest publishes `netsync.dress.self.steps`; an s140 guest publishes
none of these keys, so these rows run on an s141+ GUEST only (every expectation keyed by the GUEST's stage). At each phase,
on a fresh field load at entrance 0 (the re-load after each live step; for GuestSlots 2 an extra re-load in the SAME dress,
witnessed by `self.attach_cold` growing -- the pairing leaves the guest wherever `warp 250 -1` put it, and the walk needs the
spawn), against the OFFLINE oracle --
field 250's player footstep ops off the `.eb` the guest loads (coop_self_dress.eb_footsteps: Zidane_Init's twelve), each
rig's walk / run ids, footfall pairs and step sound off the install census (studies/battle-coop/dress-census/polish.json
`b_steps`), replayed by the census's own twin (polish_census.expected_steps), and the light through polish_census.light_color
over field 250's MapConfigData:
  G9s  (s141+) `netsync.dress.self.steps` (anim, frame) in table order == the replay for the phase's rig, every key's
       sndEffectID[0] the oracle's -- Vivi 571@4/14 + 419@0/9, Garnet 2086@4/15 + 2091@0/9 (919 each), the moogle [] with
       steps_dropped 12 (its pairs are -1: all twelve ops drop) -- and steps_dropped / steps_passed one load's.
  G9w  (s141+) a guest WALK (harness input on the guest: coop_self_dress._f_walk, four alternating holds, F_MIN_MOVE_TICKS+
       field ticks moved, else "not reached"): a stepping rig fires its own footfalls -- `steps_fired` +2 or more,
       `steps_fired_player` +0 (FF9Snd's own frame match on the rig's clip: the witness the table cannot give) -- and the
       moogle walks SILENT (both +0: the drop holds on a real walk).
  G9l  (s141+) `light_row` 98 (the source row: none of 8 / 185 / 220 has its own on 250) and `light_rgb` == the census tint
       of the 98 row on the published `light_floor` (the floor fldmcf lit the body by: the oracle's input), the kit
       walkmesh's floor(s) under the publish's x / z beside it (a disagreement is red).
NOT JUDGED BY G9 (leg F owns them): the ghosts' lighting (the host's ghost of the guest falls back to the HOST's plain-98
player row -- the 98 row s140 gives too -- and the guest's ghost of the host is 98, its own row: neither can show the s141
stand-in rule), held props and the mesh-op drop (no conductor on 250).
PRECONDITIONS: as duo.py's (both roots built, nobody at the keyboard, no controller); COOPPARTY (30604) registered.
"""
from __future__ import annotations

import re
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import _coop_battle as cb                                  # noqa: E402 - the shared bench helpers beside this file
import coop_self_dress as sd                               # noqa: E402 - the leg-G judges' pieces and the offline oracle

try:                                                       # duo.py puts tools/ on sys.path before it loads a scenario
    from harness import battlewire as BW                   # noqa: E402
    from harness import coop_peer as CP                    # noqa: E402
except ImportError:                                        # pragma: no cover - imported outside the driver
    sys.path.insert(0, str(cb.REPO / "tools"))
    from harness import battlewire as BW                   # noqa: E402
    from harness import coop_peer as CP                    # noqa: E402

FIELD = 250
HOST_GHOST_AS = "auto"
#: G9's PHASES in run order: (check id, the host's [Netsync] GuestSlots, judged with the rest mask). The first is the
#: pairing's own; each later one is a LIVE ini step. With the COOPPARTY party: Vivi, then Garnet, then a spectator.
PHASES = (("S139-G9d", 2, False), ("S139-G9e", 4, True), ("S139-G9f", 0, False))
HOST_GUEST_SLOTS = PHASES[0][1]
#: the prefab G9e's rest mask is judged against (Garnet: ModelFactory's two-hairstyle body)
GARNET_PREFAB = 185
#: how long the pair runs before anything is judged (the 7 Hz state frames pile up on the tap)
SETTLE_S = 8.0
#: how long the guest's party mirror is waited for after the pairing
MIRROR_S = 15.0
#: how long a live GuestSlots step's config echo is waited for (the host's Update polls its ini every 2 s)
CONFIG_S = 15.0
#: after the echo: the re-dress (EnsureGhost on the next paired frame) and a few publishes on it
GHOST_SETTLE_S = 3.0
#: each phase's host publishes are sampled this long (its last held pick judged)
HOLD_S = 2.5
#: [s140] how long an s140 guest's re-load of the field is waited for until it wears the phase's section-8 dress
REWARP_S = 30.0
#: a phase's run on the tap must hold this many host state frames (~1 s at 7 Hz): a blip is not a phase
MIN_PHASE_FRAMES = 7
#: duo.py's CLI calls ``d.pair(**PAIR)``: the host's party seeded (COOPPARTY) before the bench warp, the host's own
#: [Netsync] GhostAs / GuestSlots set in ITS root's ini (duo.Duo.role_extra; the guest keeps duo.ROLE_VALUES')
PAIR = {"host_setup": lambda g: cb.seed_party(g, back_to=FIELD),
        "role_extra": {"host": {"GhostAs": HOST_GHOST_AS, "GuestSlots": str(HOST_GUEST_SLOTS)}}}

CATALOG = {
    "S139-G9a": "the relay tap, read last: every HOST type-5 frame carries section 8 right after section 7 and last, skipped "
                "by the s103 walkers' twins (coop_peer.tape_dress), its bodies in tape order the twin's for each stepped "
                "GuestSlots over the host's PUBLISHED party (08 00 01 Vivi -> B9 00 02 Garnet -> DC 00 FF the moogle)",
    "S139-G9b": "the guest's old readers stepped past it: 'state-mirror ARMED', `session.mirroring` true and its party "
                "mirror (`netsync.dress.mirror_party`) == the host's published `dress.party`",
    "S139-G9c": "the guest's own body at every phase: plain Zidane (`player.model` 98) on an s139 guest; on an s140+ guest "
                "the dress the phase's section 8 carries, armed at its field load (`netsync.dress.self` why 'dressed' from "
                "'host', the model and its texture stem off the install)",
    "S139-G9d": "THE TRANSPORT SITE at GuestSlots 2: the host's ghost of the guest wears the twin's host rule over the guest's "
                "real wire body (GhostGuard keeps the dress on 98) -- Vivi: model, rig, the install's GEO and stem, the "
                "dressed loco clip, `mode` 'ini:auto'",
    "S139-G9e": "THE TRANSPORT SITE at GuestSlots 4: Garnet, as G9d, AND the rest mask -- shown == rest == the install "
                "prefab's field-mode mask, `hidden` its hides (one hairstyle)",
    "S139-G9f": "THE TRANSPORT SITE at GuestSlots 0: a spectator wears the MOOGLE (owner D2) -- 220, rig 8, GEO_NPC_F0_MOG, "
                "its loco clip",
    "S140-G9t": "[s140] THE TEARDOWN LAW ON THE WIRE: after each live GuestSlots step, before the guest's re-load, its live "
                "body is still the previous phase's dress and the host's ghost shows that wire body as it is",
    "S141-G9s": "[s141] the guest's own footstep table at every phase, one fresh load each: `netsync.dress.self.steps` == "
                "the census twin's replay of field 250's own ops for the phase's rig (Vivi 571@4/14 + 419@0/9, Garnet "
                "2086@4/15 + 2091@0/9, the moogle [] with 12 dropped), steps_dropped / steps_passed one load's",
    "S141-G9w": "[s141] a guest walk at every phase (harness input): a stepping rig fires its own footfalls "
                "(`steps_fired` +2 or more, `steps_fired_player` +0); the moogle walks silent (both +0)",
    "S141-G9l": "[s141] the guest's own light at every phase: `light_row` 98 (the source row) and `light_rgb` == the "
                "census tint of the 98 row on the published `light_floor`, the kit walkmesh's floor beside it",
}
#: [s140] the rows only an s140+ GUEST runs (an s139 guest dresses nothing of its own)
S140_ONLY = ("S140-G9t",)
#: [s141] the rows only an s141+ GUEST runs (an s140 guest publishes no polish key: `netsync.dress.self.steps` and on)
S141_ONLY = ("S141-G9s", "S141-G9w", "S141-G9l")
#: [s141] the SOURCE body (Zidane's 98): the row a dressed body's light falls back to, the walk / run MapFootstep maps from
SOURCE_MODEL = BW.PLAIN_ZIDANE_MODEL
G9_CHECKS = tuple(CATALOG)
#: COOP_CALIBRATE=1's prediction by the HOST's dress stage (battlewire.DRESS_PROBES): on s138 no section 8, no
#: `mirror_party`, no `ghost.mode` / visibility keys, and a spectator's ghost plain Zidane -- G9c stays green (an s138
#: guest is 98 too)
OLD_PREDICTED = {138: ("S139-G9a", "S139-G9b", "S139-G9d", "S139-G9e", "S139-G9f")}
_NR = "not reached"


def dress_stage(x) -> int | None:
    """The HIGHEST dress probe rung (BW.DRESS_PROBES) this document carries; None when none (an engine before s138)."""
    got = [s for s in sorted(BW.DRESS_PROBES) if cb.has(x, BW.DRESS_PROBES[s])]
    return got[-1] if got else None


def _party(x) -> list | None:
    d = cb.path(x, "netsync.dress.party")
    return list(d) if isinstance(d, list) and len(d) == 4 else None


def cfg_guest_slots(m) -> int:
    """(PURE) The GuestSlots a `config` line echoes (a duo.MATCHERS['config'] match): its ` guestSlots=N` -- logged only
    when N != 0, so no such word reads 0."""
    hit = re.search(r"\bguestSlots=(\d+)", m.group(4) or "")
    return int(hit.group(1)) if hit else 0


# ================================================================================================ the pure judges
def phase_bodies(host_party, slots) -> list:
    """(PURE) The section-8 body the host ships at each stepped GuestSlots: the twin's (BW.host_dress_section) for GhostAs
    auto over the host's party."""
    return [BW.host_dress_section(HOST_GHOST_AS, int(s), "host", False, host_party) for s in slots]


def section8_model(body) -> int:
    """(PURE) The model a section-8 body carries (0 = none or malformed)."""
    got = BW.parse_dress_section(body)
    return int(got[0]) if got else 0


def phase_dress_models(host_party, slots) -> list:
    """(PURE) [s140] The model an s140 guest dresses itself in at each stepped GuestSlots: its section 8's (the host's)."""
    return [section8_model(b) for b in phase_bodies(host_party, slots)]


def frame_bodies(records) -> list:
    """(PURE) Each HOST type-5 frame's section-8 body in TAPE ORDER (None: the frame carries none)."""
    out = []
    for _r, wtype, payload in CP.host_frames(records):
        if wtype != CP.TYPE_STATE:
            continue
        secs, _trunc = BW.walk_sections(payload)
        out.append(next((bytes(b) for sid, b in secs if sid == BW.SECTION_DRESS), None))
    return out


def _runs(bodies) -> list:
    """(PURE) ``bodies`` collapsed into [(hex or 'none', count)] in order -- the tap's story for a detail."""
    runs = []
    for b in bodies:
        key = BW.hex_bytes(b) if b is not None else "none"
        if runs and runs[-1][0] == key:
            runs[-1][1] += 1
        else:
            runs.append([key, 1])
    return [tuple(r) for r in runs]


def phase_runs(bodies, wants, *, min_frames: int = MIN_PHASE_FRAMES) -> tuple:
    """(PURE) (ok, detail): the host frames' section-8 ``bodies`` IN TAPE ORDER against ``wants`` (one body per phase, in
    the order the run stepped them) -- a frame carries its phase's body or, at a step, the NEXT phase's (the walk then
    advances), never an earlier phase's, never one two ahead, never none; the walk ends on the last phase and every phase
    holds ``min_frames``+ frames. Two adjacent phases with the same body cannot be told apart on the tap: "not reached"."""
    wants = [bytes(w) for w in wants]
    if not wants:
        return False, f"{_NR}: no phase was stepped"
    for a, b in zip(wants, wants[1:]):
        if a == b:
            return False, f"{_NR}: two adjacent phases give the same body {BW.hex_bytes(a)} for the host's party"
    p, counts, stray, first = 0, [0] * len(wants), 0, None
    for i, body in enumerate(bodies):
        if body is not None and bytes(body) == wants[p]:
            counts[p] += 1
        elif body is not None and p + 1 < len(wants) and bytes(body) == wants[p + 1]:
            p += 1
            counts[p] += 1
        else:
            stray += 1
            if first is None:
                first = (f"frame {i}: {BW.hex_bytes(body) if body is not None else 'no section 8'} in phase {p + 1} "
                         f"(want {BW.hex_bytes(wants[p])}" + (f" or the next, {BW.hex_bytes(wants[p + 1])}"
                                                               if p + 1 < len(wants) else "") + ")")
    short = [f"phase {i + 1} ({BW.hex_bytes(w)}): {counts[i]} frames" for i, w in enumerate(wants) if counts[i] < min_frames]
    ok = not stray and p == len(wants) - 1 and not short
    detail = (f"tape order {_runs(bodies) or 'no host state frame'}; per phase {counts} (min {min_frames})"
              + (f"; {stray} out of order -- first {first}" if stray else "")
              + (f"; SHORT {short}" if short else "")
              + ("" if p == len(wants) - 1 else f"; the walk stopped in phase {p + 1} of {len(wants)}"))
    return ok, detail


def judge_tape(records, host_party, slots=(HOST_GUEST_SLOTS,)) -> tuple:
    """G9a (PURE over the tap's records): coop_peer.tape_dress's structure (section 8 on every host state frame, right
    after section 7 and last, parsed, skipped by the old readers' twins) AND :func:`phase_runs` -- the bodies in tape order
    the twin's for each GuestSlots in ``slots`` (the ones the run stepped, in order) over the host's PUBLISHED party
    (None: "not reached")."""
    if host_party is None:
        return False, f"{_NR}: the host publishes no 4-slot `netsync.dress.party` (an engine before s138)"
    slots = [int(s) for s in slots]
    wants = phase_bodies(host_party, slots)
    d = CP.tape_dress(records, None)
    seq_ok, seq = phase_runs(frame_bodies(records), wants)
    detail = (f"{d['frames']} host state frames, {d['with8']} with section 8 (after 7: {d['after7']}, last: {d['last']}, "
              f"malformed: {d['malformed']}, old-reader differences: {d['old_diff']}); bodies "
              f"{d['bodies'] or 'none -- an s138-or-older host'}; {seq} (want, per GuestSlots {slots}: "
              f"{' -> '.join(BW.dress_section_text(w) for w in wants)}; host party {host_party})")
    if seq.startswith(_NR):
        return False, f"{_NR}: {detail}"
    return d["ok"] and seq_ok, detail


def judge_guest_mirror(armed: bool, guest, host_party) -> tuple:
    """G9b (PURE): the guest's 'state-mirror ARMED' line seen, `netsync.session.mirroring` true, and its party mirror ==
    the host's published party."""
    mirroring = cb.path(guest, "netsync.session.mirroring")
    have = cb.has(guest, "netsync.dress.mirror_party")
    mirror = cb.path(guest, "netsync.dress.mirror_party")
    shown = repr(mirror) if have else "ABSENT -- an engine before s139"
    detail = (f"ARMED line {'seen' if armed else 'MISSING'}; session.mirroring {mirroring!r}; mirror_party {shown} (the "
              f"host's party {host_party})")
    ok = bool(armed) and mirroring is True and have and host_party is not None and mirror == list(host_party)
    return ok, detail


def judge_guest_body(guest) -> tuple:
    """G9c on one read (PURE): the guest's controlled body is plain Zidane (98)."""
    p = sd._player(guest)
    return sd._int(p.get("model")) == BW.PLAIN_ZIDANE_MODEL, f"guest player.model {p.get('model')!r} body {p.get('body')!r}"


def judge_guest_dress(guest, want_model: int, models: dict) -> tuple:
    """G9c on one read of an s140+ guest (PURE): its controlled body wears the phase's section-8 model -- `player.model`
    and its texture stem (`body`, off the install: ``models``) -- and `netsync.dress.self` says why: 'dressed', from 'host'
    (the wire, never the selftest's 'bench'), want_model that model."""
    p = sd._player(guest)
    me = cb.path(guest, "netsync.dress.self")
    me = me if isinstance(me, dict) else {}
    facts = models.get(int(want_model)) or {}
    if not facts.get("body"):
        return False, f"{_NR}: no install oracle for model {want_model}"
    ok = (sd._int(p.get("model")) == int(want_model) and p.get("body") == facts["body"] and me.get("why") == "dressed"
          and me.get("from") == "host" and sd._int(me.get("want_model")) == int(want_model))
    return ok, (f"guest player.model {p.get('model')!r} body {p.get('body')!r}; self why {me.get('why')!r} from "
                f"{me.get('from')!r} want_model {me.get('want_model')!r} (want {want_model}, body {facts['body']!r})")


def judge_guest_bodies(reads, wants=None, models=None) -> tuple:
    """G9c over the run (PURE): :func:`judge_guest_body` at EVERY phase read (``reads``: (label, guest state) pairs, one per
    phase judged); [s140] with ``wants`` (one section-8 model per read) :func:`judge_guest_dress` instead; "not reached"
    with none."""
    reads = list(reads)
    if not reads:
        return False, f"{_NR}: no phase read the guest"
    if wants is not None and len(list(wants)) != len(reads):
        return False, f"{_NR}: {len(reads)} phase reads but {len(list(wants))} section-8 dresses"
    bad, parts = [], []
    for i, (label, st) in enumerate(reads):
        ok, why = judge_guest_body(st) if wants is None else judge_guest_dress(st, list(wants)[i], models or {})
        parts.append(f"{label}: {why}")
        if not ok:
            bad.append(label)
    return not bad, "; ".join(parts) + ((f" -- NOT 98 at {bad}" if wants is None else f" -- WRONG at {bad}") if bad else "")


def last_ghost_model(samples: list, guest_slots: int):
    """The host ghost's `model` on the LAST publish carrying ``guest_slots`` with `session.ghost` true (None: none)."""
    for s in reversed(samples or []):
        if cb.path(s, "netsync.battle.host.guest_slots") == int(guest_slots) and cb.path(s, "netsync.session.ghost") is True:
            return sd._int(cb.path(s, "netsync.dress.ghost.model"))
    return None


def judge_teardown(steps) -> tuple:
    """G9t (PURE): at each live step (``steps``: (label, the guest's state BEFORE its re-load, the previous phase's dress
    model, the host ghost's model on its last publish of the new GuestSlots)), the guest's live body is STILL the previous
    dress and the host shows it as it is (its ghost model == that wire body); "not reached" with no step."""
    steps = list(steps)
    if not steps:
        return False, f"{_NR}: no live GuestSlots step ran"
    bad, parts = [], []
    for label, st, prev, ghost in steps:
        p = sd._player(st)
        wire = sd._int(p.get("model"))
        ok = prev is not None and wire == int(prev) and ghost == wire
        parts.append(f"{label}: guest still {wire!r} (want the previous dress {prev}), host ghost {ghost!r} (want as is)")
        if not ok:
            bad.append(label)
    return not bad, "; ".join(parts) + (f" -- BROKEN at {bad}" if bad else "")


def rewarp_guest(guest, want_model: int, timeout: float = None, *, fresh_load: bool = False) -> tuple:
    """[s140] Re-load the guest's field (a warp to FIELD at entrance 0) and wait until it wears ``want_model`` with
    `netsync.dress.self.why` 'dressed' -- (ok, why). [s141] ``fresh_load``: ALSO wait for `self.attach_cold` (s140's
    per-process count of AttachDress at a load's SetModel) to grow past its value before the warp -- the witness that a
    re-load in the SAME dress happened (the dress alone cannot tell it: it is worn before and after)."""
    timeout = REWARP_S if timeout is None else timeout
    cold0 = sd.self_count(guest.state, "attach_cold") if fresh_load else None
    try:
        guest.warp(FIELD, entrance=0)
    except Exception as err:                               # noqa: BLE001 - a refused re-load reads in G9c's detail
        return False, f"the guest's re-load of {FIELD} raised {type(err).__name__}: {str(err)[:160]}"
    deadline = time.time() + timeout
    st = guest.state
    while True:
        cold = sd.self_count(st, "attach_cold")
        if (sd._int(sd._player(st).get("model")) == int(want_model) and cb.path(st, "netsync.dress.self.why") == "dressed"
                and (not fresh_load or (cold0 is not None and cold is not None and cold > cold0))):
            return True, ""
        if time.time() >= deadline:
            return False, (f"the guest re-loaded {FIELD} but did not wear {want_model} within {timeout:g}s"
                           + (f" (attach_cold {cold0!r} -> {cold!r}: want it grown)" if fresh_load else ""))
        time.sleep(0.5)
        st = guest.state


def want_host_ghost(host_party, wire_model: int, wire_anim: int, guest_slots: int = HOST_GUEST_SLOTS) -> dict:
    """(PURE) What THE HOST'S TRANSPORT SITE makes its ghost of the guest wear and play: HostDress (the s139 rule for the
    host's GhostAs and ``guest_slots`` over its party; moogleWhenEmpty on the host) behind GhostGuard on the guest's wire
    body, the anim GhostAnim over the guest's loco byte (its sender classifies its own anim on its own model)."""
    m, rig = BW.resolve_dress_rule(HOST_GHOST_AS, int(guest_slots), BW.moogle_when_empty("host", False),
                                   BW.live_slot_chars(host_party))
    dress = BW.ghost_guard(m, wire_model)
    rig = rig if dress else -1
    loco = BW.classify_loco(wire_model, wire_anim)
    return {"model": dress or wire_model, "rig": rig, "anim": BW.ghost_anim(dress, rig, wire_model, loco, wire_anim)}


def _host_pick(samples: list, guest_slots: int, hold: int):
    """The LAST host publish whose ghost tuple held ``hold``+ publishes on FieldHUD with `session.ghost` true AND the
    phase's GuestSlots published (`netsync.battle.host.guest_slots`: the step landed on that very publish); None when
    none."""
    pick, run, prev = None, 0, object()
    for s in samples:
        key = sd._ghost_tuple(s)
        run = run + 1 if key is not None and key == prev else 1
        prev = key
        if (run >= hold and sd._raw(s).get("ui_state") == "FieldHUD" and cb.path(s, "netsync.session.ghost") is True
                and cb.path(s, "netsync.battle.host.guest_slots") == int(guest_slots)):
            pick = s
    return pick


def judge_host_ghost(samples: list, guest, host_party, models: dict, clips: dict, *, guest_slots: int = HOST_GUEST_SLOTS,
                     hold: int = 2, visibility: bool = False, tree=None, garnet_hair=0, want_dress=None) -> tuple:
    """G9d / G9e / G9f (PURE): on :func:`_host_pick` (the phase's GuestSlots published), the ghost wears
    :func:`want_host_ghost` for the guest's own model and anim at ``guest_slots`` -- its model and rig, the GEO and texture
    stem the INSTALL gives that model (``models``), the clip NAME of the twin's anim (playing, where it lives in the worn
    folder) -- and `ghost.mode` reads 'ini:' + the host's GhostAs; with ``visibility`` (G9e) ALSO the rest mask on that
    publish (coop_self_dress.rest_mask_verdict over ``tree``, the prefab, with ``garnet_hair`` and the publish's own
    scenario counter). An engine without `ghost.mode` (s138) is red, its detail still naming what the ghost wears (a
    spectator's plain Zidane is the old DLL's behavioural red). [s140] ``want_dress`` (an s140+ guest: the phase's
    section-8 model): the guest's wire body must BE that dress, so the twin's want equals it -- a guest that never re-armed
    is red on its stale body, never a pass."""
    if not samples:
        return False, "no host publishes"
    gp = sd._player(guest)
    wire, anim = sd._int(gp.get("model")), sd._int(gp.get("anim"))
    if wire is None or anim is None or host_party is None:
        return False, f"{_NR}: the guest's model / anim ({wire}, {anim}) or the host's party ({host_party}) unread"
    gh_last = cb.path(samples[-1], "netsync.dress.ghost")
    absent = not isinstance(gh_last, dict) or "mode" not in gh_last
    pre = "netsync.dress.ghost.mode ABSENT on the host -- an engine before s139; " if absent else ""
    pick = _host_pick(samples, guest_slots, hold)
    if pick is None:
        last = samples[-1]
        return False, (f"{pre}no host publish with the ghost held {hold}+ on FieldHUD, session.ghost true and GuestSlots "
                       f"{guest_slots} published (last: guest_slots {cb.path(last, 'netsync.battle.host.guest_slots')!r}, "
                       f"ui {sd._raw(last).get('ui_state')!r})")
    gh = cb.path(pick, "netsync.dress.ghost")
    want = want_host_ghost(host_party, wire, anim, guest_slots)
    facts = models.get(want["model"]) or {}
    if not facts.get("geo") or not facts.get("body"):
        return False, f"{_NR}: no install oracle for model {want['model']}"
    want_clip = clips.get(want["anim"])
    judged_play = want_clip is not None and BW.folder_of(want_clip) == facts["geo"]
    want_mode = BW.DRESS_MODE_INI + HOST_GHOST_AS
    detail = (f"GuestSlots {guest_slots}: host ghost {cb.pick(gh, 'model', 'rig', 'geo', 'body', 'clip', 'playing', 'mode')} "
              f"vs the twin's {BW.rig_name(want['rig']) or 'undressed'}: model {want['model']} rig {want['rig']} geo "
              f"{facts['geo']} body {facts['body']!r} clip {want_clip!r} mode {want_mode!r} (the guest's wire {wire}/{anim}, "
              f"the host's party {host_party})")
    worn = (sd._int(gh.get("model")) == want["model"] and sd._int(gh.get("rig")) == want["rig"]
            and gh.get("geo") == facts["geo"] and gh.get("body") == facts["body"] and want_clip is not None
            and gh.get("clip") == want_clip and (not judged_play or gh.get("playing") is True))
    if absent:
        return False, pre + detail
    if want_dress is not None and want["model"] != int(want_dress):
        return False, (f"the guest's wire body {wire} is not this phase's section-8 dress {want_dress} (an s140 guest that "
                       f"did not re-arm): {detail}")
    ok = worn and gh.get("mode") == want_mode
    if not visibility:
        return ok, detail
    if want["model"] != GARNET_PREFAB:
        return False, (f"{_NR}: the rest mask's body is Garnet ({GARNET_PREFAB}), but GuestSlots {guest_slots} dresses "
                       f"model {want['model']} over the host's party {host_party} ({detail})")
    v_ok, v_why = sd.rest_mask_verdict(gh, sd._int(sd._raw(pick).get("scenario")), tree, garnet_hair)
    nr = f"{_NR}: "
    return ok and v_ok, (nr if v_why.startswith(nr) else "") + f"VISIBILITY {v_why.removeprefix(nr)}; WORN {detail}"


def polish_expect(models, ops, doc, pc, mcf=None, nfloors: int = 0) -> tuple:
    """(PURE over the census and the field's own reads) [s141] G9s / G9w / G9l's oracle for each section-8 model in
    ``models`` -- ({model: {"name", "model", "rig", "steps": {steps, steps_dropped, steps_passed} or None, "light": {floor:
    {"s141": {row, rgb}, "off": {row, rgb}}} or None}}, {what: why}). ``ops`` field 250's player footstep ops in script
    order (coop_self_dress.eb_footsteps over the `.eb` the guest loads; None: no steps oracle); ``doc`` the install census
    (polish.json): each rig's walk / run ids, footfall pairs and step sound off its `b_steps` row -- the ids stock
    REGISTERS footsteps on and the modal RunModelCode(16) frames, -1 / -1 for the moogle -- Zidane's the SOURCE pair;
    ``pc`` the census module, whose own twins replay it (expected_steps: MapFootstep on the DRESSED body, then stock
    FF9Snd's table) and light it (light_color, the source row 98 with the polish on / off) over ``mcf`` (the field's
    MapConfigData; None: no light oracle) on every walkmesh floor 0..``nfloors``-1 and 255 (none: the default light).
    Cross-check, each disagreement a named problem: the census's rig row against battlewire's (pairs, step sound)."""
    out, problems = {}, {}
    zc = sd._census_rig(doc, "zidane")
    zid = None
    if zc is not None:
        zid = {"walk": int(zc["walk"]["id"]), "run": int(zc["run"]["id"]),
               "walk_step_a": int(zc["census"]["walk_pair"][0]), "walk_step_b": int(zc["census"]["walk_pair"][1]),
               "run_step_a": int(zc["census"]["run_pair"][0]), "run_step_b": int(zc["census"]["run_pair"][1])}
    else:
        problems["census zidane"] = "no census row for the source rig (zidane)"
    for m in dict.fromkeys(int(x) for x in models):
        rig = BW.rig_for_model(m)
        name = pc.RIG_NAMES[rig] if 0 <= rig < len(pc.RIG_NAMES) else None
        c = sd._census_rig(doc, name) if name else None
        if c is None:
            problems[f"census {m}"] = f"no census row for model {m} (rig {rig}, {name!r})"
            continue
        cen = c["census"]
        r = {"name": name, "model": m, "walk": int(c["walk"]["id"]), "run": int(c["run"]["id"]),
             "walk_step_a": int(cen["walk_pair"][0]), "walk_step_b": int(cen["walk_pair"][1]),
             "run_step_a": int(cen["run_pair"][0]), "run_step_b": int(cen["run_pair"][1]),
             "step_sound": int(cen["step_sound"])}
        tw = BW.rig_row(rig)
        diff = [f"{k} {tw[k]} vs {r[k]}" for k in ("walk_step_a", "walk_step_b", "run_step_a", "run_step_b", "step_sound")
                if tw is not None and tw[k] != r[k]]
        if diff:
            problems[f"twin {name}"] = "the twin's rig row disagrees with the census: " + ", ".join(diff)
        steps = None
        if ops is not None and zid is not None:
            got = pc.expected_steps(r, [tuple(o) for o in ops], polish=True, dressed=True, zidane=zid)
            steps = {k: got[k] for k in ("steps", "steps_dropped", "steps_passed")}
            if got["faults"]:
                problems[f"faults {name}"] = f"the replay throws in stock: {got['faults'][:2]}"
        light = None
        if mcf is not None:
            light = {f: {k: {kk: pc.light_color(mcf, m, f, SOURCE_MODEL, pol)[kk] for kk in ("row", "rgb")}
                         for k, pol in (("s141", True), ("off", False))} for f in list(range(int(nfloors))) + [255]}
        out[m] = {"name": name, "model": m, "rig": rig, "steps": steps, "light": light}
    return out, problems


def _polish_ro(want: dict) -> dict:
    """coop_self_dress's `ro` (the row's asked-for body) for one phase's oracle: its name and model."""
    return {"name": want["name"], "model": want["model"]}


def judge_polish_steps(st, want) -> tuple:
    """S141-G9s on one phase (PURE): coop_self_dress.judge_f_steps on the guest's publish ``st`` (its fresh load, settled)
    against ``want`` (:func:`polish_expect`'s row for the phase's section-8 model) -- the body pinned first (player.model
    the dress, `self.rig` its rig, else "not reached"), `steps` (anim, frame) in table order == the replay's, no duplicate
    key, steps_dropped / steps_passed one load's, and -- when the oracle's keys share one sound -- every key's
    sndEffectID[0] that sound (Vivi's and Garnet's 919: the step_sound-0 rigs keep the source's Arg4)."""
    if not want or want.get("steps") is None:
        return False, f"{_NR}: no steps oracle for this phase's dress"
    sounds = {r[2] for r in want["steps"]["steps"]}
    return sd.judge_f_steps(st, want["steps"], _polish_ro(want), rig=want["rig"],
                            sound=sounds.pop() if len(sounds) == 1 else None)


def judge_walk_silent(walk: dict, ro: dict, *, rig: int) -> tuple:
    """(PURE) A DROP rig's walk (the moogle: every footstep op dropped at the load, its table empty): coop_self_dress
    .judge_f_fired's premises (no take-over, the bracket read, the body asked for, F_MIN_MOVE_TICKS+ field ticks moved --
    else "not reached") and then SILENCE: `steps_fired` +0 AND `steps_fired_player` +0 across the walk (nothing is
    registered on the dressed body's clip, and the 98 keys it dropped never reach it)."""
    if walk.get("left"):
        return False, f"{_NR}: the walk's hold was TAKEN OVER ({walk.get('why')})"
    before, after = walk.get("before"), walk.get("after")
    if before is None or after is None:
        return False, f"{_NR}: the walk did not run ({walk.get('why')})"
    pin = sd.f_dress_pin(before, ro, rig)
    if pin:
        return False, f"{_NR}: the body is not the one asked for: {pin}"
    ticks = sd.walk_ticks(walk.get("samples") or [])
    moved = f"the walk moved {ticks} field ticks ({walk.get('dir')!r})"
    if ticks < sd.F_MIN_MOVE_TICKS:
        return False, f"{_NR}: {moved} -- want {sd.F_MIN_MOVE_TICKS}+ (silence on so short a walk proves nothing)"
    if sd._polish(after) is None:
        return False, f"{sd._f_absent(after, 'steps_fired')}; {moved}"
    d, o = sd.count_delta(before, after, "steps_fired"), sd.count_delta(before, after, "steps_fired_player")
    ok = d == 0 and o == 0
    return ok, (("" if ok else "WRONG: a drop rig fired a footfall -- ")
                + f"steps_fired +{d}, steps_fired_player +{o} across the walk (want +0 / +0: silent); {moved}")


def judge_polish_walk(walk: dict, want) -> tuple:
    """S141-G9w on one phase (PURE): the guest's walk (``walk``: coop_self_dress._f_walk's bracket) keyed by the phase's
    oracle -- a rig whose replay registers keys (Vivi, Garnet) fires its own footfalls (coop_self_dress.judge_f_fired:
    `steps_fired` +F_FIRED_MIN or more, `steps_fired_player` +0); a rig whose replay registers none (the moogle) walks
    SILENT (:func:`judge_walk_silent`)."""
    if not want or want.get("steps") is None:
        return False, f"{_NR}: no steps oracle for this phase's dress"
    ro = _polish_ro(want)
    if want["steps"]["steps"]:
        return sd.judge_f_fired(walk, ro, rig=want["rig"], key="steps_fired", other="steps_fired_player")
    return judge_walk_silent(walk, ro, rig=want["rig"])


def judge_polish_light(st, want, floors_at=None) -> tuple:
    """S141-G9l on one phase (PURE): coop_self_dress.judge_f4 on the guest's publish ``st`` -- the body pinned, `light_row`
    == the source row 98 and `light_rgb` == its census tint on the engine's `light_floor`, the kit walkmesh's floors under
    the publish's x / z (``floors_at``: (x, z) -> floors; None unread -- a red with both shown) beside it."""
    if not want or want.get("light") is None:
        return False, f"{_NR}: no light oracle (field {FIELD}'s MapConfigData unread)"
    floors = sd._f_floors({"floors_at": floors_at}, st)
    return sd.judge_f4(st, want["light"], _polish_ro(want), rig=want["rig"], floors=floors, src=SOURCE_MODEL)


def judge_phases(parts) -> tuple:
    """(PURE) One polish row over the run's phases (``parts``: (label, (ok, why)) per phase, a blocked phase's "not
    reached" among them): green when every phase is; "not reached" with none, or when every red phase reads "not reached"
    (a row that judged nothing proves nothing); else red naming the phases."""
    parts = list(parts)
    if not parts:
        return False, f"{_NR}: no phase judged the guest's polish"
    bad = [label for label, (ok, _w) in parts if not ok]
    nr = bool(bad) and all(str(w).startswith(_NR) for _label, (ok, w) in parts if not ok)
    detail = "; ".join(f"{label}: {why}" for label, (_ok, why) in parts) + (f" -- RED at {bad}" if bad else "")
    return not bad, (f"{_NR}: " if nr else "") + detail


def calibration(stage, failed, unreached=()) -> tuple:
    """(PURE) COOP_CALIBRATE=1's verdict: exactly OLD_PREDICTED[stage] red (no row for that stage: no calibration), and no
    predicted red reading "not reached" (``unreached``: a red that proves nothing -- UNPROVEN)."""
    pred = OLD_PREDICTED.get(stage)
    if pred is None:
        return False, f"no calibration for a host at dress stage {stage!r}: calibrate on the s138 DLL"
    missing = sorted(set(pred) - set(failed))
    extra = sorted(set(failed) - set(pred))
    unproven = sorted(set(pred) & set(unreached))
    return not missing and not extra and not unproven, (
        f"predicted reds that stayed GREEN: {missing or 'none'}; unpredicted reds: {extra or 'none'}; UNPROVEN (read "
        f"'not reached'): {unproven or 'none'} (host dress stage s{stage})")


# ================================================================================================ the run
def _oracle(game: Path, models, prefabs=()) -> tuple:
    """({model: facts}, {anim id: clip name}, {model: prefab tree}, {what: why}) for G9d-f -- every expected model read off
    the install NOW (read_model) and the prefabs walked (coop_self_dress.prefab_tree), both READ-ONLY, plus the kit's copy
    of the open-source AnimationDB. A part that cannot be read is named and its judge reads "not reached"."""
    sd._kit()
    from ff9mapkit._animdb_all import ANIMATIONS
    facts, trees, problems = {}, {}, {}
    for m in sorted({int(m) for m in models}):
        try:
            f = sd.model_facts(game, m)
        except Exception as err:                           # noqa: BLE001 - an unread model reads "not reached"
            f, problems[f"model {m}"] = {}, f"read_model raised {type(err).__name__}: {str(err)[:160]}"
        facts[m] = f if f.get("geo") and f.get("body") else {}
    for m in prefabs:
        try:
            tree = sd.prefab_tree(game, int(m))
        except Exception as err:                           # noqa: BLE001 - a prefab that cannot be walked is a named problem
            problems[f"prefab {m}"] = f"the prefab walk raised {type(err).__name__}: {str(err)[:160]}"
            continue
        if tree.get("renderers"):
            trees[int(m)] = tree
        else:
            problems[f"prefab {m}"] = f"{tree.get('geo')}: no renderer found"
    return facts, dict(ANIMATIONS), trees, problems


def _polish_oracle(game: Path, models, regs=None) -> tuple:
    """[s141] (:func:`polish_expect`'s {model: oracle}, the kit walkmesh's (x, z) -> floors lookup or None, {what: why}) --
    field 250's player footstep ops off the `.eb` the guest's root loads (coop_self_dress.field_eb + eb_footsteps), its
    MapConfigData (polish_census.load_mcf) and stock walkmesh (the kit's), all READ-ONLY off the install NOW, and the
    census JSON. A part that cannot be read is named and its judge reads "not reached"; the kit cache missing leaves the
    install half out (a read that would WRITE into the install)."""
    sd._kit()
    pc = sd._polish_census()
    from ff9mapkit import extract as X
    game, problems = Path(game), {}
    install_ok = not sd.kit_cache_missing(game)
    ops = None
    try:
        data, src = sd.field_eb(game, FIELD, reg_name=(regs or {}).get(FIELD), install_ok=install_ok)
        if data is None:
            problems["ops"] = src
        else:
            fs = sd.eb_footsteps(data)
            ops = [tuple(o) for o in fs["load"]]
            if fs["problems"]:
                problems["ops eb"] = f"{src}: {fs['problems']}"
            if tuple(ops) != BW.FIELD250_STEPS:
                problems["twin ops"] = f"{src}: field {FIELD}'s ops {ops} vs battlewire.FIELD250_STEPS"
    except Exception as err:                               # noqa: BLE001 - an unread part reads "not reached"
        problems["ops"] = f"the .eb read raised {type(err).__name__}: {str(err)[:200]}"
    mcf, floors_at, nfloors = None, None, 0
    try:
        if not install_ok:
            raise RuntimeError(f"the kit cache {sd.KIT_CACHE_FILES} is missing from the install (the mapconfig and "
                               f"walkmesh reads would WRITE it -- run any ff9mapkit read once, by hand)")
        mcf = pc.load_mcf(FIELD, game)
        if mcf is None:
            raise RuntimeError(f"field {FIELD} has no MapConfigData")
        wm = X.stock_walkmesh(FIELD, game=game)
        nfloors, floors_at = len(wm.floors), wm.floors_at
    except Exception as err:                               # noqa: BLE001
        mcf = None
        problems["light"] = f"{type(err).__name__}: {str(err)[:240]}"
    try:
        got, more = polish_expect(models, ops, sd.polish_census_doc(), pc, mcf, nfloors)
    except Exception as err:                               # noqa: BLE001
        got, more = {}, {"census": f"{type(err).__name__}: {str(err)[:200]}"}
    return got, floors_at, dict(problems, **more)


def walk_guest(guest) -> dict:
    """[s141] G9w's walk on the GUEST's own body: coop_self_dress._f_walk (harness input -- THE UNATTENDED LAW: nobody at the
    keyboard --, four alternating holds sized at the measured render rate, each publish watched, its before / after
    bracket). A walk that raises reads "not reached" in G9w's detail (no bracket)."""
    try:
        return sd._f_walk(guest, FIELD)
    except Exception as err:                               # noqa: BLE001 - a refused hold is the row's "not reached"
        return {"dir": None, "samples": [], "left": False, "before": None, "after": None,
                "why": f"the walk raised {type(err).__name__}: {str(err)[:160]}"}


def run_duo(d) -> None:
    calibrate = cb.CALIBRATE
    strict, d.strict = d.strict, False                     # every G9 row is recorded (a calibration needs them all)
    failed, unreached = [], []

    def check(cid, ok, detail):
        if not ok:
            failed.append(cid)
            if str(detail).startswith(_NR):
                unreached.append(cid)
        d.check(ok, f"{cid}: {CATALOG[cid]}", detail, cid=cid)

    try:
        time.sleep(SETTLE_S)
        host, guest = d.host, d.guest
        host_party = _party(host.state)
        stage = dress_stage(host.state)
        gstage = dress_stage(guest.state)
        selfdress = gstage is not None and gstage >= 140      # [s140] the guest dresses itself off section 8
        polish = gstage is not None and gstage >= 141         # [s141] ...and polishes the dress (steps, its light)
        d.note(f"G9: host dress stage s{stage}, party {host_party}; guest stage s{gstage}"
               + (" (it dresses itself: each step re-loads its field)" if selfdress else "")
               + (" (its polish judged: G9s / G9w / G9l)" if polish else ""))
        # G9b first: the guest's old readers stepped past section 8 since the pairing (it needs no phase)
        armed = bool(d.wait_line("guest", "armed", 1.0))
        deadline = time.time() + MIRROR_S
        st = guest.state
        while time.time() < deadline and cb.path(st, "netsync.dress.mirror_party") != host_party:
            time.sleep(0.5)
            st = guest.state
        check("S139-G9b", *judge_guest_mirror(armed, st, host_party))
        # the offline oracle for every phase's expected dress (the guest's wire body as it is now) and Garnet's prefab
        wire0 = sd._int(sd._player(guest.state).get("model")) or BW.PLAIN_ZIDANE_MODEL
        want_models = [want_host_ghost(host_party, wire0, 0, s)["model"] for _c, s, _v in PHASES] if host_party else []
        dresses = phase_dress_models(host_party, [s for _c, s, _v in PHASES]) if host_party else []
        want_models += [m for m in dresses if m]           # [s140] what the guest wears at each phase
        models, clips, trees, problems = _oracle(Path(host.game_path), want_models, (GARNET_PREFAB,))
        if problems:
            d.note(f"G9 oracle problems (their judges read 'not reached'): {problems}")
        hair = (cb.ini_value(host, "Graphics", "GarnetHair") or "").strip()     # the HOST root's ini, READ-ONLY
        garnet_hair = int(hair) if hair.lstrip("-").isdigit() else 0
        poracle, floors_at = {}, None                      # [s141] the polish rows' oracle, read off the GUEST's root
        if polish:
            try:
                regs = guest.registered_fields()[0]
            except Exception:                              # noqa: BLE001 - no registrations: the stock .eb is read
                regs = {}
            poracle, floors_at, pprob = _polish_oracle(Path(guest.game_path), [m for m in dresses if m], regs)
            if pprob:
                d.note(f"G9 [s141] polish oracle problems (their judges read 'not reached'): {pprob}")
        psteps, pwalk, plight = [], [], []                 # [s141] (label, verdict) per phase
        reads, stepped, blocked = [], [], None
        wants, teardown, prev_dress = [], [], None         # [s140] each judged phase's section-8 dress; the steps' reads
        for i, (cid, slots, vis) in enumerate(PHASES):
            if blocked is not None:
                check(cid, False, f"{_NR}: {blocked}")
                if polish:
                    for rows in (psteps, pwalk, plight):
                        rows.append((f"GuestSlots {slots}", (False, f"{_NR}: {blocked}")))
                continue
            if stepped:                                    # the first phase is the pairing's own GuestSlots
                echo = d.set_netsync("host", {"GuestSlots": slots}, timeout=CONFIG_S,
                                     pred=lambda m, s=slots: cfg_guest_slots(m) == s)
                if not echo:
                    blocked = f"the host never echoed its live GuestSlots {slots} step within {CONFIG_S:g}s"
                    check(cid, False, f"{_NR}: {blocked}")
                    if polish:
                        for rows in (psteps, pwalk, plight):
                            rows.append((f"GuestSlots {slots}", (False, f"{_NR}: {blocked}")))
                    continue
                time.sleep(GHOST_SETTLE_S)
                if selfdress and dresses:                  # [s140] the teardown law, then the re-arm at a field load
                    hs = cb.hold_for(host, HOLD_S)
                    teardown.append((f"GuestSlots {slots}", guest.state, prev_dress, last_ghost_model(hs, slots)))
                    ok_w, why_w = rewarp_guest(guest, dresses[i])
                    if not ok_w:
                        d.note(f"G9 [s140]: {why_w}")
                    time.sleep(GHOST_SETTLE_S)
            elif polish and dresses:                       # [s141] the first phase on a KNOWN fresh load too: entrance 0
                ok_w, why_w = rewarp_guest(guest, dresses[i], fresh_load=True)     # (the pairing's spot is wherever
                if not ok_w:                                                      # `warp 250 -1` left the guest)
                    d.note(f"G9 [s141]: {why_w}")
                time.sleep(GHOST_SETTLE_S)
            stepped.append(slots)
            want_dress = dresses[i] if (selfdress and dresses) else None
            samples = cb.hold_for(host, HOLD_S)
            gst = guest.state
            reads.append((f"GuestSlots {slots}", gst))
            wants.append(want_dress)
            check(cid, *judge_host_ghost(samples, gst, host_party, models, clips, guest_slots=slots, visibility=vis,
                                         tree=trees.get(GARNET_PREFAB), garnet_hair=garnet_hair, want_dress=want_dress))
            prev_dress = want_dress
            if polish:                                     # [s141] on this load's settled publish, then a guest walk
                label, pw = f"GuestSlots {slots}", poracle.get(int(dresses[i])) if dresses else None
                psteps.append((label, judge_polish_steps(gst, pw)))
                plight.append((label, judge_polish_light(gst, pw, floors_at)))
                pwalk.append((label, judge_polish_walk(walk_guest(guest), pw)))
        check("S139-G9c", *judge_guest_bodies(reads, wants if selfdress else None, models))
        if selfdress:
            check("S140-G9t", *judge_teardown(teardown))
        if polish:
            check("S141-G9s", *judge_phases(psteps))
            check("S141-G9w", *judge_phases(pwalk))
            check("S141-G9l", *judge_phases(plight))
        # G9a LAST: the tap now holds every phase the run stepped
        try:
            _h, records, torn = CP.read_tape(d.run_dir / "relay.f9tape")
            check("S139-G9a", *judge_tape(records, host_party, stepped))
            if torn:
                d.note(f"the tap's tail is torn ({torn} B: the relay still writes) -- the read frames are whole")
        except (OSError, CP.TapeError) as err:
            check("S139-G9a", False, f"{_NR}: the relay tap does not read ({err})")
        if calibrate:
            ok, why = calibration(stage, failed, unreached)
            d.check(ok, "S139-G9-CAL: CALIBRATION -- exactly OLD_PREDICTED red on the s138 DLL", why, cid="S139-G9-CAL")
    finally:
        d.strict = strict
