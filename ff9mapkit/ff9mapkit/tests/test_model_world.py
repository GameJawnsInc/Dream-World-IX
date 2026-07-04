"""Offline tests for OVERWORLD model reskin routing + discovery (no install needed).

An overworld actor's model is a world-form GEO (``GEO_SUB_W0_*``, group ``SUB`` -> type 5). The engine loads
it via the SAME ``ModelFactory.CreateModel`` disc-probe as a field model (``EventEngine`` ``gMode == 3``) and
attaches its clips via the disc-probed ``AnimationFactory`` (the ``SetStand/Walk/Run`` opcodes aren't
gMode-gated) -> a reskin (loose FBX) AND an ``.anim`` edit are BOTH DLL-free, so the field-model pipeline
handles world models unchanged (proven offline: ``model-gltf``/``model-import`` round-trips ``GEO_SUB_W0_001``
to ``Models/5/310/310.fbx``). These guard the type routing (-> ``Models/5/``) + the clip-vocabulary role hint.
"""
from ff9mapkit import catalog as C
from ff9mapkit.models import extract, mint, gltf


class _FakeType:
    def __init__(self, name): self.name = name


class _FakeObj:
    def __init__(self, name): self.type = _FakeType(name)


class _FakeEnv:
    """A stand-in for the p0data5 UnityPy env: only ``.container`` (path -> obj) is read by the anim selector,
    so we can replay a model's real on-disc anim keys offline (labels come from the baked catalog, no install)."""
    def __init__(self, geo_id, keys):
        self.container = {f"assets/resources/animations/{geo_id}/{k}.anim": _FakeObj("AnimationClip") for k in keys}


def test_world_sub_model_routes_to_type_5():
    # a GEO_SUB_W0_* model resolves to type 5 -> the deploy lands at Models/5/{id}/ (what CreateModel probes)
    name, mid, type_int = extract.resolve_geo("GEO_SUB_W0_001")
    assert name == "GEO_SUB_W0_001" and type_int == 5 and mid == 310
    assert mint.type_int_of_name("GEO_SUB_W0_002") == 5     # the mint path agrees on the type


def test_world_character_is_authoritative():
    # transcribed from WMAnimationBank.cs -- the engine NAMES these six by their clip fields.
    assert C.world_character("GEO_SUB_W0_001") == "Zidane"        # ZidaneIdleClip = ANH_SUB_W0_001_STAND
    assert C.world_character(310) == "Zidane"                     # by id too (310 == GEO_SUB_W0_001)
    assert C.world_character("GEO_SUB_W0_002") == "Dagger (Garnet)"
    assert C.world_character("GEO_SUB_W0_003") == "Chocobo"
    assert C.world_character("GEO_SUB_W0_008") == "Blue Narciss"
    assert C.world_character("GEO_SUB_W0_011") == ""             # an unnamed chibi -> never fabricated
    assert C.world_character("GEO_MAIN_F0_VIV") == ""            # a field model isn't a world actor


def test_world_role_from_clip_vocabulary():
    # a RIDER (Zidane) carries the chocobo's _CHO/takeoff mount clips but is a WALKER, not a vehicle/chocobo --
    # the plain on-foot run/walk must win (the bug the user caught: W0_001 is Zidane, not the chocobo).
    assert C.world_role("GEO_SUB_W0_001") == "walker"      # Zidane (has plain run + _CHO ride clips)
    assert C.world_role("GEO_SUB_W0_002") == "walker"      # Garnet
    assert C.world_role("GEO_SUB_W0_003") == "chocobo"     # only _CHO clips, no on-foot walk
    assert C.world_role("GEO_SUB_W0_008") == "vehicle"     # takeoff -> airship / ship, no on-foot walk
    assert C.world_role("GEO_MAIN_F0_VIV") == ""           # a FIELD model is not a world actor
    assert C.world_role(999999999) == ""                   # unknown id -> empty, never raises


def test_auto_anim_selection_prefers_on_foot_with_friendly_labels():
    # Zidane's REAL on-disc anim keys (p0data5 animations/310/); the chocobo-RIDING clips have the LOWEST ids,
    # so naive disc-order surfaced those with numeric names -> the model imported straddling an absent chocobo.
    keys = [1143, 1144, 1418, 4716, 4717, 4719, 4722, 4723, 4726, 4728, 8143, 8145, 8147, 8149, 8152, 8154]
    sel = gltf._select_anim_keys("GEO_SUB_W0_001", 310, "auto", _FakeEnv(310, keys))
    labels = [lbl for lbl, _ in sel]
    assert all(not lbl.isdigit() for lbl in labels), labels          # friendly action labels, not raw ids
    assert {"idle1", "stand", "run"} <= set(labels)                  # on-foot clips chosen over lower-id riding
    assert labels[0] == "stand"                                      # NEUTRAL rest first (not idle1 -- a yawn)
    assert labels.index("stand") < labels.index("idle1")             # fidget clips don't lead
    # a raw-id / list request still works and stays numeric-addressable
    one = gltf._select_anim_keys("GEO_SUB_W0_001", 310, "4722", _FakeEnv(310, keys))
    assert one == [("4722", 4722)]


def test_world_form_models_are_all_sub_group():
    world = [m for m in C.all_models() if m.form == "W0"]
    assert len(world) >= 20 and all(m.group == "SUB" and m.kind == "sub-character" for m in world)
    # every world model gets a non-empty role hint OR is a low-clip prop -- the hint never raises
    assert all(isinstance(C.world_role(m.id), str) for m in world)
