"""Plain-language display labels for FF9's ``boneNNN`` skeletons -- a purely COSMETIC alias layer.

FF9 names every bone ``boneNNN``, which is meaningless to a human scrubbing a rig in Blender. This
module derives anatomical guesses (``root``, ``chest``, ``L_upper_arm``, ``R_hand``, ``tail_01``) from
REST-POSE GEOMETRY -- no ML, the same directional reasoning a rigger uses by eye. Labels only ever
DECORATE display names (``bone012`` -> ``bone012_R_hand``); everything that actually binds -- animation
splice, clip write-back, FBX emission (the engine reads the trailing digits of the FBX bone name) --
keys on the raw bone NUMBER and never sees a label.

The anatomy conventions, pinned empirically against shipping data (2026-07-11):

  * FF9 model space is Y-DOWN: **up = -y** (a bone's height is ``-y``).
  * Characters face **-z** at rest: Zidane's tail runs +z, the chocobo's neck runs -z, the goblin's
    toes point -z, and the preview renderer's viewer sits at -z and sees faces.
  * **+x = the character's RIGHT.** 11 of the 12 party battle rigs put their ``WeaponBone``
    (BattleParameters.csv -- the battle weapon hand, right-handed cast) at the extreme +x bone, and
    Zidane's ``battle_model*`` overlay (the Orichalcum OFF-hand dagger, engine second-weapon
    ``Attachment == 6``) binds to his -x hand. (Freya's rig is the lone left-handed outlier.)

The structural grammar FF9 rigs follow (seen across MAIN/NPC/MON alike): a ``root`` at hip height
whose co-located child PIVOTS split the body -- one owns the upper body (spine -> chest -> arms +
neck -> head), one the lower (legs + tail). A zero-length centre pivot owning a one-sided subtree is
a JOINT ANCHOR: pivot->arm = shoulder, pivot->leg = hip, pivot->head = neck, pivot->tail = tail_base.

Derivation runs offline over the whole install (``tools/regen_bone_labels.py``): skeletons cluster
into FAMILIES by topology signature (bone count + parent edges -- the same signal that makes
cross-model clip reuse work), each member is labeled from its own rest pose, and the family VOTES so
one outlier rig can't corrupt a shared template. The result is baked into ``ff9mapkit._bonelabeldb``
(numeric topology + our own label strings only -- provenance-clean, no game bytes) keyed by
signature, plus sparse per-prefab overrides (e.g. Garnet's ``rubber_band`` scrunchie bone, labeled
from its MESH name). At export time :func:`labels_for` is a dict lookup; an unknown signature (a
from-scratch custom rig) falls back to the live heuristics, and anything unparseable stays UNLABELED
-- a wrong confident guess is worse than a raw ``boneNNN``.
"""
from __future__ import annotations

import re

from . import extract
from .fbx_skin import _mat_trs, _mat_mul

# Limb templates, proximal -> distal (Blender/Rigify segment vocabulary riggers already know).
_ARM_T = ("upper_arm", "forearm", "hand", "hand_end")
_LEG_T = ("thigh", "shin", "foot", "toe")

# SMR names that are NOT accessory names: the generic body parts (mesh0/1, battle-monster 0000_0 /
# 0_1 shapes) and the per-mode overlays. Anything else (long_hair, rubber_band) names an accessory.
_GENERIC_MESH = re.compile(r"(?:mesh\d+|\d+_\d+|battle_model.*|field_model.*)$", re.IGNORECASE)

# display-name round-trip: bone012_R_hand[.001] -> 12  (Blender may append a .NNN dedup suffix)
_LABELED = re.compile(r"bone(\d+)(?:_.*)?$")


# ---------------------------------------------------------------- naming round-trip helpers

def decorate(bone_name: str, labels: dict) -> str:
    """``bone012`` + {12: "R_hand"} -> ``bone012_R_hand`` (unchanged when unlabeled)."""
    n = extract._bone_num(bone_name)
    lab = labels.get(n) if n is not None else None
    return f"{bone_name}_{lab}" if lab else str(bone_name)


def bone_num_lenient(name) -> int | None:
    """A display/Blender bone-node name -> FF9 bone number: accepts raw ``bone012``, the labeled
    ``bone012_R_hand``, and either with a Blender ``.001`` dedup suffix. None for a foreign name."""
    nm = re.sub(r"\.\d+$", "", str(name or ""))
    m = _LABELED.fullmatch(nm)
    return int(m.group(1)) if m else None


# ---------------------------------------------------------------- topology signature

def signature(bones: list) -> str:
    """A skeleton's topology signature: every ``num>parentNum`` edge in bone-number order (root
    parent = -1). Two rigs share a signature iff a bone number means the same joint slot in both --
    the family key the label DB is baked under."""
    rows = []
    for b in bones:
        n = extract._bone_num(b["name"])
        if n is None:
            continue
        p = extract._bone_num(b.get("parent")) if b.get("parent") else None
        rows.append((n, -1 if p is None else p))
    rows.sort()
    return ",".join(f"{n}>{p}" for n, p in rows)


def rest_world(bones: list) -> dict:
    """{boneNum: (x, y, z)} rest-pose world positions (the model-space frame read_model returns)."""
    by_name = {b["name"]: b for b in bones}
    cache: dict = {}

    def world(nm):
        if nm in cache:
            return cache[nm]
        b = by_name[nm]
        loc = _mat_trs(b["pos"], b["rot"], b["scale"])
        p = b.get("parent")
        cache[nm] = loc if not p or p not in by_name else _mat_mul(world(p), loc)
        return cache[nm]

    out = {}
    for b in bones:
        n = extract._bone_num(b["name"])
        if n is None:
            continue
        M = world(b["name"])
        out[n] = (M[0][3], M[1][3], M[2][3])
    return out


# ---------------------------------------------------------------- single-rig heuristics

def label_skeleton(bones: list, smr_bones=None, group: str | None = None) -> dict:
    """{boneNum: label} for ONE rig from its rest pose. ``smr_bones`` = [(mesh_name, iterable of
    bone nums)] for the mesh-name accessory pass; ``group`` = the GEO group token ('main', 'npc',
    'mon', 'sub', 'acc', 'wep') -- prop groups (acc/wep) are never anatomy, so they get no labels.
    Returns {} whenever the rig doesn't parse into the limb grammar (prefer unlabeled over wrong)."""
    if group in ("acc", "wep"):
        return {}
    nums, par, kids = [], {}, {}
    for b in bones:
        n = extract._bone_num(b["name"])
        if n is None:
            continue
        p = extract._bone_num(b.get("parent")) if b.get("parent") else None
        nums.append(n)
        par[n] = p
        kids.setdefault(p, []).append(n)
    roots = sorted(kids.get(None, []))
    if len(nums) < 5 or not roots:
        return {}
    root = roots[0]
    W = rest_world(bones)

    def x(n):
        return W[n][0]

    def h(n):
        return -W[n][1]           # up = -y

    def z(n):
        return W[n][2]

    span = max(max(c[i] for c in W.values()) - min(c[i] for c in W.values()) for i in range(3))
    if span <= 0:
        return {}
    eps = 0.04 * span
    minh_all = min(h(n) for n in nums)

    def subtree(n):
        out, stack = [], [n]
        while stack:
            c = stack.pop()
            out.append(c)
            stack.extend(kids.get(c, []))
        return out

    def main_path(n):
        """Longest chain from n down the tree (ties -> lower bone numbers)."""
        best = [n]
        for c in sorted(kids.get(n, [])):
            p = [n] + main_path(c)
            if len(p) > len(best):
                best = p
        return best

    centre = {n for n in nums if abs(x(n)) <= eps}

    # --- sided chains: a lateral bone whose parent is centre starts a limb-ish subtree ---
    starts = [n for n in nums
              if par[n] is not None and n not in centre and par[n] in centre]
    chains = []          # {start, sub, mp, side, attach, kind}
    for s in sorted(starts):
        sub = subtree(s)
        mean_x = sum(x(n) for n in sub) / len(sub)
        if abs(mean_x) <= eps / 2:
            continue                                   # mixed-side subtree -- not a limb
        mp = main_path(s)
        end = mp[-1]
        is_leg = h(s) <= h(root) + eps and min(h(n) for n in sub) <= minh_all + 0.30 * span
        pure_lateral = (len(mp) <= 2 and
                        abs(x(end) - x(s)) > 3 * max(abs(h(end) - h(s)), abs(z(end) - z(s)), 1e-9))
        is_wing = (not is_leg) and (z(end) - z(s) > 0.10 * span or pure_lateral)
        kind = "leg" if is_leg else ("wing" if is_wing else
                                     ("upper" if h(s) > h(root) + eps else "flap"))
        chains.append({"start": s, "sub": sub, "mp": mp, "side": "R" if mean_x > 0 else "L",
                       "attach": par[s], "kind": kind})

    if not any(c["kind"] in ("leg", "upper", "wing") for c in chains):
        return {}                                       # no limbs at all -> not a creature we can read

    # --- chest = the centre attach STATION carrying the longest 'upper' chain (arms live there;
    #     shorter upper chains attached higher are head parts: ears, tusks). FF9 rigs park several
    #     CO-LOCATED sibling pivots at one girdle (Zidane: chest + neck + R-clavicle all at one
    #     spot under the upper pivot), so the station -- position, not tree edge -- is the unit. ---
    def station(n):
        """Attach-point identity: co-located pivots share a station (position quantized by eps)."""
        return (round(x(n) / eps) if eps else 0, round(h(n) / eps) if eps else 0,
                round(z(n) / eps) if eps else 0)

    uppers = [c for c in chains if c["kind"] == "upper"]
    chest = None
    chest_st = None
    if uppers:
        best = max(uppers, key=lambda c: (len(c["mp"]), -c["start"]))
        chest = best["attach"]
        chest_st = station(chest)
        for c in uppers:
            if station(c["attach"]) != chest_st:
                c["kind"] = "head_part" if h(c["attach"]) > h(chest) + eps else "flap"
            else:
                c["kind"] = "arm"
    else:
        wings = [c for c in chains if c["kind"] == "wing"]
        if wings:
            # wings-only rig (chocobo): the wing girdle is the chest station; the chest is the
            # station bone whose subtree climbs highest (it owns the neck)
            chest_st = station(wings[0]["attach"])
            cands = [n for n in centre if station(n) == chest_st]
            if cands:
                chest = max(cands, key=lambda n: max(h(m) for m in subtree(n)))

    labels: dict = {root: "root"}

    # --- centre torso path: hips/pelvis below, spine -> chest above, then neck -> head -> crest ---
    leg_starts = {c["start"] for c in chains if c["kind"] == "leg"}

    def owns_legs(n):
        sub = set(subtree(n))
        owned = [s for s in leg_starts if s in sub]
        sides = {("R" if x(s) > 0 else "L") for s in owned}
        tail_here = any(t in sub for t in nums
                        if t in centre and par.get(t) in sub and z(t) - z(par[t]) > 0.08 * span)
        return len(owned) >= 2 or (len(sides) >= 2) or (len(owned) >= 1 and tail_here)

    lower_hubs = [n for n in centre if n != root and h(n) <= h(root) + eps and owns_legs(n)]
    # hips = the hub nearest the root (tree depth), deeper multi-sided hubs = pelvis
    def depth(n):
        d = 0
        while par.get(n) is not None:
            n = par[n]
            d += 1
        return d

    for i, n in enumerate(sorted(lower_hubs, key=depth)):
        labels[n] = "hips" if i == 0 else ("pelvis" if i == 1 else f"pelvis_{i - 1:02d}")

    if chest is not None:
        labels.setdefault(chest, "chest")
        # spine = centre path root -> chest (exclusive)
        path, n = [], chest
        while par.get(n) is not None and par[n] != root:
            n = par[n]
            if n in centre and n not in labels:
                path.append(n)
        for i, n in enumerate(reversed(path)):
            labels[n] = "spine" if i == 0 else f"spine_{i:02d}"

        arm_bones: set = set()
        for c in chains:
            if c["kind"] == "arm":
                arm_bones.update(c["sub"])

        def sided_anchor(n):
            """A centre pivot whose whole subtree is sided (a limb/ear/tusk anchor) -- the head
            walk must not descend into these, and they stay unlabeled here (pivot pass names them)."""
            sub = [m for m in subtree(n) if m != n]
            return bool(sub) and all(m not in centre for m in sub)

        # neck root: the centre bone AT the chest station (Zidane's 007, co-located sibling of the
        # chest) owning the tallest arm-free subtree; a rig without one climbs from the chest itself.
        cands = [nb for nb in centre
                 if nb not in labels and station(nb) == chest_st
                 and not (set(subtree(nb)) & arm_bones) and not sided_anchor(nb)
                 and any(m in centre for m in subtree(nb) if m != nb)]
        cur = max(cands, key=lambda nb: max(h(m) for m in subtree(nb))) if cands else chest
        head_path = [cur] if cur != chest else []
        guard = 0
        while guard < 96:
            guard += 1
            rises = [c for c in kids.get(cur, [])
                     if c in centre and c not in labels and c not in head_path
                     and h(c) >= h(cur) - eps and not sided_anchor(c)
                     # a climb that mostly veers BACKWARD (+z) is a crest/hat riding the head, not
                     # more neck -- forward veer is normal (a chocobo's neck slopes toward -z)
                     and not (z(c) - z(cur) > 0.75 * max(h(c) - h(cur), eps))]
            if not rises:
                break
            cur = max(rises, key=lambda c: (len(subtree(c)), -c))
            head_path.append(cur)
        if head_path:
            # head sits after the LARGEST single rise; before = neck, after = crest (pompom stalks)
            hs = [h(chest)] + [h(n) for n in head_path]
            head_i = max(range(len(head_path)), key=lambda i: hs[i + 1] - hs[i])
            for i, n in enumerate(head_path):
                if i < head_i:
                    labels[n] = "neck" if i == 0 else f"neck_{i:02d}"
                elif i == head_i:
                    labels[n] = "head"
                else:
                    labels[n] = f"crest_{i - head_i:02d}"
            # co-located siblings of the head (Vivi's triple pivot) ride along as head_NN
            hn = head_path[head_i]
            sibs = [c for c in kids.get(par.get(hn), []) if c != hn and c in centre
                    and c not in labels and station(c) == station(hn)]
            for i, c in enumerate(sorted(sibs)):
                labels[c] = f"head_{i + 1:02d}"
            # crest mop-up: unlabeled centre bones hanging off the head cluster (Vivi's hat tip,
            # a topknot) -- rising or veering, they're head ornaments
            crest_i = len(head_path) - 1 - head_i
            head_set = set(head_path[head_i:]) | set(sibs)
            for n in sorted(nums):
                if n in labels or n not in centre or sided_anchor(n):
                    continue
                p = par.get(n)
                seen_head = False
                while p is not None:
                    if p in head_set:
                        seen_head = True
                        break
                    if p in labels and labels[p] not in ("head",) \
                            and not str(labels[p]).startswith(("head_", "crest_", "neck")):
                        break
                    p = par.get(p)
                if seen_head:
                    crest_i += 1
                    labels[n] = f"crest_{crest_i:02d}"
                    head_set.add(n)

    # --- tails: centre chains veering +z (behind) off the lower body. A pivot whose subtree
    #     carries a LIMB chain is a limb anchor (Mu's hind-hip pivots sit far behind the root),
    #     never a tail bone. ---
    chain_starts = {c["start"] for c in chains}
    tail_i = 0
    for n in sorted(nums):
        if n in centre and n not in labels and par.get(n) is not None \
                and par[n] in centre and z(n) - z(par[n]) > 0.08 * span \
                and h(par[n]) <= h(root) + 2 * eps \
                and not (set(subtree(n)) & chain_starts):
            for m in main_path(n):
                if m in centre and m not in labels:
                    tail_i += 1
                    labels[m] = f"tail_{tail_i:02d}"

    # --- sided chains -> limb templates ---
    def label_chain(c, template, base=None):
        side = c["side"]
        mp = c["mp"]
        if base is not None:                            # fixed stem + running index (wings, flaps)
            for i, n in enumerate(mp):
                labels.setdefault(n, f"{side}_{base}_{i + 1:02d}")
        else:
            # template = core joints + one optional distal end (toe / hand_end, only on long
            # chains). A short chain keeps the proximal slots + the core's distal end: a 2-bone
            # leg is thigh+foot (not thigh+shin, and not a toe with no foot).
            core, end = template[:-1], template[-1]
            if len(mp) <= len(core):
                slots = list(core[:max(len(mp) - 1, 0)]) + [core[-1]]
            else:
                slots = list(core) + [end]
            for i, n in enumerate(mp):
                lab = slots[i] if i < len(slots) else f"{slots[-1]}_{i - len(slots) + 1:02d}"
                labels.setdefault(n, f"{side}_{lab}")
        # off-main branches: number from the branch parent's label
        for n in sorted(c["sub"]):
            if n in labels:
                continue
            p, i = par.get(n), 1
            stem = labels.get(p)
            while stem is None and p is not None:
                p = par.get(p)
                stem = labels.get(p)
            stem = stem or f"{side}_limb"
            cand = f"{stem}_{i:02d}"
            while cand in labels.values():
                i += 1
                cand = f"{stem}_{i:02d}"
            labels[n] = cand

    legs = sorted((c for c in chains if c["kind"] == "leg"),
                  key=lambda c: (z(c["start"]), c["start"]))
    n_leg_rows = len({round(z(c["start"]) / max(eps, 1e-9)) for c in legs})
    leg_row = {}
    for c in legs:
        row = round(z(c["start"]) / max(eps, 1e-9))
        leg_row.setdefault(row, len(leg_row))
    for c in legs:
        row = leg_row[round(z(c["start"]) / max(eps, 1e-9))]
        if n_leg_rows <= 1:
            c["pivot_base"] = "hip"
            label_chain(c, _LEG_T)
        elif n_leg_rows == 2:
            pre = "front_" if row == 0 else "hind_"
            c["pivot_base"] = pre + "hip"
            label_chain(c, tuple(pre + t for t in _LEG_T))
        else:
            c["pivot_base"] = f"leg{row + 1}_base"
            label_chain(c, _LEG_T, base=f"leg{row + 1}")

    for c in chains:
        if c["kind"] == "arm":
            label_chain(c, _ARM_T)
        elif c["kind"] == "wing":
            label_chain(c, (), base="wing")
        elif c["kind"] == "head_part":
            end = c["mp"][-1]
            if len(c["mp"]) <= 2 and z(end) - z(c["start"]) > -0.05 * span:
                label_chain(c, (), base="ear")
            elif z(end) - z(c["start"]) < -0.05 * span:
                label_chain(c, (), base="jaw")
            else:
                label_chain(c, (), base="head")
        elif c["kind"] == "flap":
            label_chain(c, (), base="flap")

    # --- centre pivots that anchor exactly one labeled sided chain = joint anchors ---
    _PIVOT = {"leg": "hip", "arm": "shoulder", "wing": "wing_base"}
    for c in chains:
        base = c.get("pivot_base") or _PIVOT.get(c["kind"])
        if not base:
            continue
        p = c["attach"]
        if p in centre and p not in labels and p != root:
            sub = [m for m in subtree(p) if m != p]
            if sub and all(m in c["sub"] for m in sub):
                labels[p] = f"{c['side']}_{base}"
    # tail pivot: a centre bone owning only tail-labeled bones
    for n in centre:
        if n in labels or n == root:
            continue
        sub = [m for m in subtree(n) if m != n]
        if sub and all(str(labels.get(m, "")).startswith("tail") for m in sub):
            labels[n] = "tail_base"

    # --- mesh-name accessories override anatomy: a bone referenced ONLY by named accessory
    #     meshes is that accessory (Garnet's rubber_band), not a body part ---
    if smr_bones:
        refs: dict = {}
        for name, bset in smr_bones:
            for n in set(bset):
                refs.setdefault(n, []).append(str(name or ""))
        acc_counts: dict = {}
        for name, bset in smr_bones:
            acc_counts[str(name or "")] = len(set(bset))
        used: dict = {}
        for n in sorted(refs):
            names = refs[n]
            if not names or any(_GENERIC_MESH.fullmatch(nm or "") for nm in names):
                continue
            best = min(names, key=lambda nm: acc_counts.get(nm, 1 << 30))
            stem = re.sub(r"[^A-Za-z0-9]+", "_", best).strip("_").lower() or "acc"
            used[stem] = used.get(stem, 0) + 1
            labels[n] = stem if used[stem] == 1 else f"{stem}_{used[stem]:02d}"

    # --- uniqueness: Blender-facing names read better unique; number any residual duplicates ---
    seen: dict = {}
    for n in sorted(labels):
        lab = labels[n]
        if lab in seen:
            seen[lab] += 1
            labels[n] = f"{lab}_x{seen[lab]}"
        else:
            seen[lab] = 0
    return labels


# ---------------------------------------------------------------- light skeleton read (regen-time)

def read_skeleton(token: str, game=None, bundle=None) -> dict:
    """Bones + per-SMR bone-number lists for a model's shipping prefab -- NO mesh/texture decode,
    so a whole-install sweep is seconds, not minutes. Returns {geo, geo_id, prefab_geo, prefab_id,
    prefab_tint, bones, smrs=[(mesh_name, [bone nums])]}. Raises like :func:`extract.read_model`
    for unshipped ids."""
    geo, gid, tint, pgeo, pgid, ptint, b, root_pid = extract._open_prefab(token, game, bundle)
    bones: list = []
    bone_pid_to_name: dict = {}
    smr_pids: list = []

    def walk(tr_pid, tr_tt, parent_name):
        if not tr_tt:
            return
        go_pid = extract._pid(tr_tt.get("m_GameObject", {}))
        go_tt = b.tt(go_pid)
        name = go_tt.get("m_Name") if go_tt else None
        is_bone = bool(name and re.fullmatch(r"bone\d+", str(name)))
        if is_bone:
            bones.append({"name": name, "parent": parent_name,
                          "pos": extract._vec3(tr_tt.get("m_LocalPosition")),
                          "rot": extract._quat(tr_tt.get("m_LocalRotation", {})),
                          "scale": extract._vec3(tr_tt.get("m_LocalScale"), (1.0, 1.0, 1.0))})
            bone_pid_to_name[tr_pid] = name
        if go_tt:
            for tn, pid in b.components(go_tt):
                if tn == "SkinnedMeshRenderer":
                    smr_pids.append((name, pid))
        child_parent = name if is_bone else parent_name
        for ch in tr_tt.get("m_Children", []):
            cpid = extract._pid(ch)
            walk(cpid, b.tt(cpid), child_parent)

    root_tpid, root_ttr = b.transform_of(b.tt(root_pid))
    walk(root_tpid, root_ttr, None)
    smrs = []
    for go_name, smr_pid in smr_pids:
        smr = b.tt(smr_pid) or {}
        nums = []
        for bp in smr.get("m_Bones", []):
            n = extract._bone_num(bone_pid_to_name.get(extract._pid(bp)))
            if n is not None:
                nums.append(n)
        smrs.append((go_name, nums))
    return {"geo": geo, "geo_id": gid, "prefab_geo": pgeo, "prefab_id": pgid,
            "prefab_tint": ptint, "bones": bones, "smrs": smrs, "bundle": b}


# ---------------------------------------------------------------- family vote (regen-time)

def vote_labels(member_labels: list) -> dict:
    """Family consensus: {boneNum: label} where a strict majority of members agree; disagreeing
    bones stay unlabeled (per-prefab overrides preserve each model's own divergent labels)."""
    if not member_labels:
        return {}
    counts: dict = {}
    for labs in member_labels:
        for n, lab in labs.items():
            counts.setdefault(n, {})
            counts[n][lab] = counts[n].get(lab, 0) + 1
    out = {}
    half = len(member_labels) / 2.0
    for n, c in counts.items():
        lab, k = max(c.items(), key=lambda kv: kv[1])
        if k > half:
            out[n] = lab
    return out


# ---------------------------------------------------------------- runtime lookup

def labels_for(bones: list, prefab_id=None, geo: str | None = None) -> dict:
    """The labels to DISPLAY for this skeleton: the baked family consensus for its topology
    signature, overlaid with the model's own baked per-prefab diffs; an unknown signature (custom
    rig) falls back to the live heuristics. Always safe to call -- returns {} when nothing is known."""
    try:
        from .._bonelabeldb import BONE_LABELS, PREFAB_LABELS
    except ImportError:                                  # DB not baked (source checkout mid-regen)
        BONE_LABELS, PREFAB_LABELS = {}, {}
    sig = signature(bones)
    base = BONE_LABELS.get(sig)
    if base is None:
        grp = None
        if geo:
            parts = str(geo).split("_")
            grp = parts[1].lower() if len(parts) > 1 else None
        try:
            base = label_skeleton(bones, group=grp)
        except Exception:
            base = {}
    out = dict(base or {})
    if prefab_id is not None:
        out.update(PREFAB_LABELS.get(int(prefab_id), {}))
    return out
