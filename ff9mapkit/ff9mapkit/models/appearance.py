"""Static census of FF9's engine per-model APPEARANCE logic, so the kit can warn a modder when a model they
export / import / mint is scenario-gated -- the rule the Garnet scrunchie taught us, generalized.

THE RULE: the engine's per-model appearance logic is keyed on the GEO **name** (not the numeric id). So an
**OVERRIDE** (re-import at the real id -> same name) PRESERVES all of it for free; a **MINT** (new id >=6000
-> a novel name) BYPASSES it (the model shows its plain default). And a story-evolved character is *several*
GEO ids, not one -- editing one form leaves the others stock.

Transcribed from Memoria's ``ModelFactory.cs`` (``garnetShortHairTable`` ~792-806, the ``{F3,F4,F5}_ZDN``
per-form texture reassign ~75-91). Pure/offline -- no install needed; only the name matters.
"""
from __future__ import annotations

import re
from typing import NamedTuple

from .._modeldb import MODELS

# The engine hides ``long_hair`` (ScenarioCounter >= 10300) or ``short_hair`` (early game) by child NAME, for
# exactly this name-set (ModelFactory.garnetShortHairTable). The single riskiest override in the game.
GARNET_HAIR_SWAP = frozenset({
    "GEO_MAIN_F0_GRN", "GEO_MAIN_F1_GRN",
    "GEO_MAIN_B0_002", "GEO_MAIN_B0_003", "GEO_MAIN_B0_004", "GEO_MAIN_B0_005",
    "GEO_MON_B3_149", "GEO_MON_B3_169",
    "GEO_MAIN_B0_024", "GEO_MAIN_B0_025", "GEO_MAIN_B0_026", "GEO_MAIN_B0_027",
})

# Zidane alt-costume field forms whose ``_MainTex`` the engine rebuilds per-form from disc (name-keyed).
ZDN_TEXTURE_REASSIGN = frozenset({"GEO_MAIN_F3_ZDN", "GEO_MAIN_F4_ZDN", "GEO_MAIN_F5_ZDN"})

# Child-mesh names the engine keys on -- these must survive a round-trip unchanged (the kit preserves them).
RESERVED_MESH_NAMES = ("long_hair", "short_hair", "field_model", "battle_model")


def _canon(token) -> "str | None":
    """A GEO name or numeric id -> the canonical GEO name (offline; via MODELS only). None if unknown."""
    tok = str(token).strip()
    if tok.isdigit():
        return MODELS.get(int(tok))
    return tok.upper()


def _build_field_forms() -> dict:
    """char token -> sorted GEO names of its GEO_MAIN_F*_<CHAR> field forms (the story-evolved id set)."""
    out: dict = {}
    for name in MODELS.values():
        m = re.fullmatch(r"GEO_MAIN_F\d+_([A-Z]{2,})", name)
        if m:
            out.setdefault(m.group(1), set()).add(name)
    return {c: sorted(v) for c, v in out.items()}


_FIELD_FORMS = _build_field_forms()


def character_forms(geo_name) -> list:
    """The other GEO_MAIN_F*_<CHAR> forms of this character (the story-evolved set). [] if not a MAIN field
    model. E.g. GEO_MAIN_F0_GRN -> all of Garnet's F-forms; the engine/.eb loads a different one per beat."""
    name = _canon(geo_name)
    m = re.fullmatch(r"GEO_MAIN_F\d+_([A-Z]{2,})", name or "")
    return list(_FIELD_FORMS.get(m.group(1), [])) if m else []


def is_scenario_gated(geo_name) -> bool:
    """True if this exact model has name-keyed engine appearance logic (hair-swap or the ZDN texture reassign)."""
    name = _canon(geo_name)
    return name in GARNET_HAIR_SWAP or name in ZDN_TEXTURE_REASSIGN


class Appearance(NamedTuple):
    """A model's story/scenario APPEARANCE profile (offline; name-keyed). All fields default to the plain
    look, so :data:`NO_APPEARANCE` is the "nothing special" singleton the catalog attaches to most models."""
    forms: tuple = ()               # the character's GEO_MAIN_F*_<CHAR> field forms (incl. this one); () if <=1
    scenario_gated: bool = False    # this exact model has name-keyed engine appearance logic
    gate_kind: str = ""             # "" | "hair-swap" | "texture-reassign"

    @property
    def story_evolved(self) -> bool:
        """True if the character has >1 field form the game swaps between across the story."""
        return len(self.forms) > 1

    @property
    def special(self) -> bool:
        """True if there's anything worth surfacing (story forms and/or a name-keyed engine gate)."""
        return self.story_evolved or self.scenario_gated


NO_APPEARANCE = Appearance()


def appearance_of(token) -> Appearance:
    """The APPEARANCE profile of a model (by GEO name or id). :data:`NO_APPEARANCE` (the singleton) for a
    plain / unknown model, so ``catalog.Model.appearance`` is cheap and identity-comparable for the common case."""
    name = _canon(token)
    if not name:
        return NO_APPEARANCE
    forms = tuple(character_forms(name))
    gate_kind = ("hair-swap" if name in GARNET_HAIR_SWAP else
                 "texture-reassign" if name in ZDN_TEXTURE_REASSIGN else "")
    if len(forms) <= 1 and not gate_kind:
        return NO_APPEARANCE
    return Appearance(forms if len(forms) > 1 else (), bool(gate_kind), gate_kind)


def appearance_notes(token, *, minted: bool = False) -> list:
    """Human-readable notes to print when exporting/importing/minting a model, encoding THE RULE. ``minted``
    True => the model is going to a NEW id (a novel name), so name-keyed engine logic will NOT fire."""
    name = _canon(token)
    if not name:
        return []
    notes: list = []

    # Alias models (a battle form / alt outfit / F1 variant with no own-id prefab): the geometry ships
    # in a DONOR prefab (extract.resolve_prefab -- offline, baked from ModelFactory's rename tables).
    try:
        from .extract import resolve_prefab
        pgeo, pgid, _pt = resolve_prefab(name)
    except Exception:   # noqa: BLE001 -- an unknown/unsupported name has no prefab note
        pgeo = name
    if pgeo != name:
        if minted:
            notes.append(f"geometry ships in donor prefab {pgeo} (id {pgid}) -- the mint copies that body "
                         f"(animations still come from THIS id's animset).")
        else:
            notes.append(f"SHARED PREFAB: this form's geometry ships in {pgeo} (id {pgid}) -- an override "
                         f"deploys to ITS folder and affects every form loading that prefab (field AND "
                         f"battle). Animations stay this id's own animset.")

    if name in GARNET_HAIR_SWAP:
        if minted:
            notes.append("MINT bypasses the engine hair-swap (it's name-keyed) -> BOTH long_hair AND short_hair "
                         "render at once. Ship the model in its final look (delete one hair mesh in Blender).")
        else:
            notes.append("engine HAIR-SWAP: it hides long_hair/short_hair by ScenarioCounter>=10300. Your "
                         "OVERRIDE preserves it -- keep BOTH child meshes named exactly 'long_hair'/'short_hair' "
                         "and verify in-game at ScenarioCounter <10300 AND >=10300. (A merged nested scrunchie "
                         "shows in every scene -- the documented late-game float.)")

    if name in ZDN_TEXTURE_REASSIGN:
        if minted:
            notes.append("MINT bypasses this form's per-form engine texture reassign (name-keyed).")
        else:
            notes.append("engine rebuilds this Zidane form's textures per-form from disc (name-keyed); your "
                         "OVERRIDE preserves it -- keep the Models/<type>/<id>/ texture layout.")

    forms = character_forms(name)
    if len(forms) > 1:
        others = [f for f in forms if f != name]
        if minted:
            notes.append(f"the source is a STORY-EVOLVED character ({len(forms)} field forms: "
                         f"{', '.join(forms)}); a mint is a single fixed look, decoupled from all of them.")
        else:
            notes.append(f"STORY-EVOLVED character: {len(forms)} field forms exist ({', '.join(forms)}). "
                         f"Editing THIS id doesn't touch the others -- the game loads a different id at other "
                         f"beats. Override each form you care about ({', '.join(others)}).")

    return notes
