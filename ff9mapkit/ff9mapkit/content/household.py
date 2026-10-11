"""``[household]`` -- the sims life sim as ONE declarative block.

THE PRODUCTIZATION of the Manor arc (``studies/sims/PLAN.md`` rungs 1-6, all in-game proven on benches
30430-30435): ``studies/sims/sims_bench2.py``'s hand-rolled generator, expressed as a single TOML table with
the tuned Manor values as DEFAULTS. A bare ``[household]`` is the rung-4 household; ``[household.job]`` adds
the job / skill / gil economy (rung 6) and ``[household.shop]`` adds buy mode.

What it generates (everything downstream sees plain proven blocks -- the ``[siege]`` / ``[[ferry]]`` pattern):

  * the sim ``[[npc]]`` + its home marker; one prop + use-spot marker per need;
  * the ``[behavior]`` header: the five-need table, the day clock, one metabolism drift per need, the night
    tiring drift, the all-nighter drain, the ONE HUD strip;
  * the sim's tree, TIERED: all-nighter wake / FAINT (per need: revive, down, fall) / job (finish, work, study,
    go) / FINISH (need met -> the task retires) / USE (posed holds that raise the need) / GO (walk to the
    object) / URGE (night bedtime, then one row per need, then the workday) / idle emotes / amble home;
  * the steward's ``[[choice]]`` menus: one per object (an order row hides while that task is pending), the
    household ledger (wages, work, study) and the moogle catalogue (buy mode).

ORDERS QUEUE by construction: a directive raises the same public flag an urge does, so she finishes the object
she is at, then walks to the next flagged one in tier order. A need at 0 FAINTS her (frozen collapse, the need
creeping back), never kills her.

The block is the vocabulary; the proven-in-game numbers are the defaults. Everything tunable is a plain key.
Defaults place the objects in the Manor room (``examples/household``: x +-1220, z 257..-1931, FRONT = -z);
in any other room, give each need's ``pos`` / ``spot`` yourself (``tools/field_layout_probe.py`` first).

``[household]`` OWNS the field's ``[behavior]``; a field cannot carry both. Desugars at project load.
"""
from __future__ import annotations

import copy
import tomllib
from dataclasses import dataclass, replace

NEEDS = ("hunger", "thirst", "energy", "hygiene", "fun")
LABEL = {"hunger": "HUN", "thirst": "THR", "energy": "NRG", "hygiene": "HYG", "fun": "FUN"}
NEED_TABLE_ID, CLOCK_TABLE_ID = 1000, 1001       # pinned so the HUD expr: sources name them stably
JOB_TABLE_ID = 1003                              # [0] shift progress, [1] study progress (field-session)
SKILL_FLOOR, SKILL_CEIL = 6_000_000, 6_999_999   # the persistent-table id band (behaviortoml)
SHOP_REQUEST_DEFAULT = 14960                     # flags.SIEGE_REQUEST_BASE: the kit's standing request lane

_KEYS = {"sim", "label", "model", "home", "dialogue", "speed", "hour_ticks", "start_hour", "warmup",
         "urge_at", "full_at", "night_sleep_at", "night_tire_every", "faint_pose", "revive_at",
         "faint_regen", "nosleep_every", "tired_at", "merry_at", "beat", "need", "job", "shop"}
_NEED_KEYS = {"prop", "pos", "spot", "seed", "decay", "use", "pose", "verb", "prompt", "zone_half"}
_JOB_KEYS = {"prop", "desk", "desk_spot", "shift_len", "study_len", "skilled_at", "wage_lo", "wage_hi",
             "study_gain", "work_fun", "study_fun", "work_ready_at", "skill_table", "desk_prompt"}
_SHOP_KEYS = {"name", "label", "catalogue", "model", "pose", "price", "fun", "request_flag", "prompt",
              "park"}


class HouseholdError(ValueError):
    pass


@dataclass(frozen=True)
class NeedSpec:
    name: str
    prop: str
    pos: tuple
    spot: tuple
    seed: int
    decay: int                       # ticks per -1
    use: tuple                       # (by, every) while she is at the object
    pose: str | None                 # gesture NAME on the sim's own rig; None = stand at the spot
    verb: str
    prompt: str
    zone_half: tuple                 # the steward's press zone, centred on the object

    def zone(self) -> list:
        hw, hd = self.zone_half
        x, z = self.pos
        x0, z0, x1, z1 = x - hw, z - hd, x + hw, z + hd
        return [[x0, z0], [x1, z0], [x1, z1], [x0, z1]]


@dataclass(frozen=True)
class JobSpec:
    skill_table: int | None          # None -> 6,000,000 + the field id, resolved at desugar
    prop: str = "shelf"
    desk: tuple = (300, -1150)
    desk_spot: tuple = (80, -1150)
    shift_len: int = 60
    study_len: int = 40
    skilled_at: int = 50
    wage_lo: int = 60
    wage_hi: int = 150
    study_gain: tuple = (1, 15)      # skill +by every N ticks while studying
    work_fun: tuple = (-1, 40)
    study_fun: tuple = (-1, 25)
    work_ready_at: int = 50
    desk_prompt: str = "The Mognet desk and the household ledger."

    def zone(self) -> list:
        x, z = self.desk
        return [[x - 260, z - 240], [x + 260, z - 240], [x + 260, z + 240], [x - 260, z + 240]]


@dataclass(frozen=True)
class ShopSpec:
    name: str = "toy"                # the pooled npc; its pool is "<name>s"
    label: str = "A toy airship"
    catalogue: tuple = (-500, -1650)
    model: str = "GEO_ACC_F0_TSM"
    pose: int = 1105                 # a raw clip id: a preset prop has no gesture table
    price: int = 50
    fun: tuple = (3, 6)              # playing with it: fun +by every N ticks (the puppet is +2 / 10)
    request_flag: int = SHOP_REQUEST_DEFAULT
    prompt: str = "The moogle catalogue. (SELECT opens it anywhere.)"
    park: tuple = (-1050, -1780)     # dormant placeholder: a pooled unit appears where it is BOUGHT

    def pool(self) -> str:
        return f"{self.name}s"


@dataclass(frozen=True)
class HouseholdSpec:
    sim: str = "bilba"
    label: str = "Bilba"
    model: str = "GEO_MAIN_F0_VIV"
    home: tuple = (-200, -700)
    dialogue: str = "...The soup is still worried. So am I, a little."
    speed: int = 25
    hour_ticks: int = 150            # ticks per in-game hour (5 s): a day is 2 minutes
    start_hour: int = 6              # the clock reads 06:00 at entry; night = 18:00-06:00
    warmup: int = 30
    urge_at: int = 40
    full_at: int = 95
    night_sleep_at: int = 70         # at night, energy this low already sends her to bed
    night_tire_every: int = 40
    faint_pose: str = "hiza_1"       # the collapse, frozen at its last frame
    revive_at: int = 25
    faint_regen: int = 10            # +1 every N ticks while down
    nosleep_every: int = 5           # "stay up all night": energy -1 every N ticks
    tired_at: int = 55               # idle emotes on the beat: a yawn when energy is at/under this
    merry_at: int = 80               # ...and a laugh when fun is at/over this
    beat: int = 75                   # the idle-emote alternator (frames on, frames off)
    needs: tuple = ()
    job: JobSpec | None = None
    shop: ShopSpec | None = None


# the tuned Manor values (studies/sims/sims_bench2.py), per need
_DEFAULTS = {
    "hunger":  dict(prop="pot", pos=(600, -250), spot=(600, -520), seed=80, decay=45, use=(2, 8),
                    pose="dine_1", verb="eat something", prompt="The soup pot.", zone_half=(260, 240)),
    "thirst":  dict(prop="cup", pos=(-950, -1100), spot=(-720, -1100), seed=70, decay=40, use=(3, 8),
                    pose=None, verb="have a drink", prompt="A cup of water.", zone_half=(260, 240)),
    "energy":  dict(prop="tent", pos=(-850, -150), spot=(-850, -500), seed=75, decay=55, use=(1, 6),
                    pose="sleeping", verb="take a nap", prompt="The tent.", zone_half=(320, 240)),
    "hygiene": dict(prop="cask", pos=(950, -1050), spot=(720, -1050), seed=85, decay=60, use=(2, 8),
                    pose=None, verb="wash up", prompt="The wash barrel.", zone_half=(260, 240)),
    "fun":     dict(prop="dagger_doll", pos=(100, -150), spot=(100, -420), seed=60, decay=45, use=(2, 10),
                    pose="laugh", verb="play a while", prompt="The puppet.", zone_half=(260, 240)),
}


# ------------------------------------------------------------------------------------------------ parsing
def _point(v, ctx: str) -> tuple:
    if not (isinstance(v, (list, tuple)) and len(v) == 2 and all(isinstance(c, (int, float))
                                                                  and not isinstance(c, bool) for c in v)):
        raise HouseholdError(f"{ctx}: must be an [x, z] point")
    return (int(v[0]), int(v[1]))


def _pair(v, ctx: str, lo_by=None) -> tuple:
    if not (isinstance(v, (list, tuple)) and len(v) == 2 and all(isinstance(c, int) and not isinstance(c, bool)
                                                                  for c in v)):
        raise HouseholdError(f"{ctx}: must be [by, every] (two integers)")
    if v[1] < 1:
        raise HouseholdError(f"{ctx}: `every` (the second number) must be >= 1")
    return (int(v[0]), int(v[1]))


def _int(d: dict, key: str, default: int, ctx: str, lo: int, hi: int) -> int:
    v = d.get(key, default)
    if isinstance(v, bool) or not isinstance(v, int) or not lo <= v <= hi:
        raise HouseholdError(f"{ctx}: {key} must be an integer {lo}..{hi}")
    return v


def _str(d: dict, key: str, default: str, ctx: str) -> str:
    v = d.get(key, default)
    if not isinstance(v, str) or not v.strip():
        raise HouseholdError(f"{ctx}: {key} must be a non-empty string")
    return v


def _unknown(d: dict, allowed: set, ctx: str) -> None:
    extra = set(d) - allowed
    if extra:
        raise HouseholdError(f"{ctx}: unknown key(s) {sorted(extra)}")


def from_raw(h: dict) -> HouseholdSpec:
    ctx = "[household]"
    if not isinstance(h, dict):
        raise HouseholdError(f"{ctx}: must be a table")
    _unknown(h, _KEYS, ctx)
    sim = _str(h, "sim", "bilba", ctx)
    if not sim.replace("_", "").isalnum():
        raise HouseholdError(f"{ctx}: sim is the npc's name -- letters, digits, underscores")
    base = HouseholdSpec()
    kw = dict(
        sim=sim,
        label=_str(h, "label", sim.capitalize(), ctx),
        model=_str(h, "model", base.model, ctx),
        home=_point(h.get("home", base.home), f"{ctx} home"),
        dialogue=_str(h, "dialogue", base.dialogue, ctx),
        speed=_int(h, "speed", base.speed, ctx, 1, 255),
        hour_ticks=_int(h, "hour_ticks", base.hour_ticks, ctx, 10, 3000),
        start_hour=_int(h, "start_hour", base.start_hour, ctx, 0, 23),
        warmup=_int(h, "warmup", base.warmup, ctx, 0, 600),
        urge_at=_int(h, "urge_at", base.urge_at, ctx, 1, 99),
        full_at=_int(h, "full_at", base.full_at, ctx, 2, 100),
        night_sleep_at=_int(h, "night_sleep_at", base.night_sleep_at, ctx, 1, 100),
        night_tire_every=_int(h, "night_tire_every", base.night_tire_every, ctx, 1, 3000),
        faint_pose=_str(h, "faint_pose", base.faint_pose, ctx),
        revive_at=_int(h, "revive_at", base.revive_at, ctx, 1, 99),
        faint_regen=_int(h, "faint_regen", base.faint_regen, ctx, 1, 3000),
        nosleep_every=_int(h, "nosleep_every", base.nosleep_every, ctx, 1, 3000),
        tired_at=_int(h, "tired_at", base.tired_at, ctx, 0, 100),
        merry_at=_int(h, "merry_at", base.merry_at, ctx, 0, 100),
        beat=_int(h, "beat", base.beat, ctx, 10, 3000),
    )
    if kw["urge_at"] >= kw["full_at"]:
        raise HouseholdError(f"{ctx}: urge_at ({kw['urge_at']}) must be below full_at ({kw['full_at']}) -- "
                             f"a need she starts serving at the urge line must be able to END at the full line")
    if kw["revive_at"] <= 0:
        raise HouseholdError(f"{ctx}: revive_at must be > 0 (a faint ends when the need creeps back to it)")

    nraw = h.get("need", {}) or {}
    if not isinstance(nraw, dict):
        raise HouseholdError(f"{ctx}: [household.need.<name>] is a table of tables")
    bad = set(nraw) - set(NEEDS)
    if bad:
        raise HouseholdError(f"[household.need]: unknown need(s) {sorted(bad)} -- the five needs are "
                             f"{', '.join(NEEDS)}")
    needs = []
    for n in NEEDS:
        nctx = f"[household.need.{n}]"
        row = nraw.get(n, {}) or {}
        _unknown(row, _NEED_KEYS, nctx)
        d = dict(_DEFAULTS[n])
        pose = row.get("pose", d["pose"])
        if pose is not None and (not isinstance(pose, str) or not pose.strip()):
            raise HouseholdError(f"{nctx}: pose is a gesture NAME on the sim's own model (or omit it to stand)")
        zh = row.get("zone_half", d["zone_half"])
        if not (isinstance(zh, (list, tuple)) and len(zh) == 2 and all(isinstance(c, int) and c > 0 for c in zh)):
            raise HouseholdError(f"{nctx}: zone_half must be [half_width, half_depth], positive integers")
        needs.append(NeedSpec(
            name=n, prop=_str(row, "prop", d["prop"], nctx),
            pos=_point(row.get("pos", d["pos"]), f"{nctx} pos"),
            spot=_point(row.get("spot", d["spot"]), f"{nctx} spot"),
            seed=_int(row, "seed", d["seed"], nctx, 0, 100),
            decay=_int(row, "decay", d["decay"], nctx, 1, 100000),
            use=_pair(row.get("use", d["use"]), f"{nctx} use"),
            pose=pose, verb=_str(row, "verb", d["verb"], nctx), prompt=_str(row, "prompt", d["prompt"], nctx),
            zone_half=(int(zh[0]), int(zh[1]))))
    kw["needs"] = tuple(needs)

    job = h.get("job")
    if job is not None:
        jctx = "[household.job]"
        if not isinstance(job, dict):
            raise HouseholdError(f"{jctx}: must be a table")
        _unknown(job, _JOB_KEYS, jctx)
        jd = JobSpec(skill_table=None)
        st = job.get("skill_table")
        if st is not None and (isinstance(st, bool) or not isinstance(st, int)
                               or not SKILL_FLOOR <= st <= SKILL_CEIL):
            raise HouseholdError(f"{jctx}: skill_table is a PERSISTENT table id in {SKILL_FLOOR}..{SKILL_CEIL} "
                                 f"-- it survives the save, so keep it stable and unique to this field")
        spec_job = JobSpec(
            skill_table=st, prop=_str(job, "prop", jd.prop, jctx),
            desk=_point(job.get("desk", jd.desk), f"{jctx} desk"),
            desk_spot=_point(job.get("desk_spot", jd.desk_spot), f"{jctx} desk_spot"),
            shift_len=_int(job, "shift_len", jd.shift_len, jctx, 1, 1000),
            study_len=_int(job, "study_len", jd.study_len, jctx, 1, 1000),
            skilled_at=_int(job, "skilled_at", jd.skilled_at, jctx, 1, 100),
            wage_lo=_int(job, "wage_lo", jd.wage_lo, jctx, 1, 99999),
            wage_hi=_int(job, "wage_hi", jd.wage_hi, jctx, 1, 99999),
            study_gain=_pair(job.get("study_gain", jd.study_gain), f"{jctx} study_gain"),
            work_fun=_pair(job.get("work_fun", jd.work_fun), f"{jctx} work_fun"),
            study_fun=_pair(job.get("study_fun", jd.study_fun), f"{jctx} study_fun"),
            work_ready_at=_int(job, "work_ready_at", jd.work_ready_at, jctx, 0, 100),
            desk_prompt=_str(job, "desk_prompt", jd.desk_prompt, jctx))
        if spec_job.wage_lo == spec_job.wage_hi:
            raise HouseholdError(f"{jctx}: wage_lo and wage_hi must differ (two ledger rows, told apart by "
                                 f"their gil)")
        kw["job"] = spec_job

    shop = h.get("shop")
    if shop is not None:
        sctx = "[household.shop]"
        if not isinstance(shop, dict):
            raise HouseholdError(f"{sctx}: must be a table")
        if kw.get("job") is None:
            raise HouseholdError(f"{sctx}: buy mode needs [household.job] -- the purse it spends is the gil "
                                 f"the job earns, and the HUD strip shows it")
        _unknown(shop, _SHOP_KEYS, sctx)
        sd = ShopSpec()
        pose = shop.get("pose", sd.pose)
        if isinstance(pose, bool) or not isinstance(pose, int) or not 0 <= pose <= 65535:
            raise HouseholdError(f"{sctx}: pose is a raw clip id 0..65535 (a preset prop has no gesture names)")
        name = _str(shop, "name", sd.name, sctx)
        if not name.replace("_", "").isalnum():
            raise HouseholdError(f"{sctx}: name is the pooled npc's name -- letters, digits, underscores")
        kw["shop"] = ShopSpec(
            name=name, label=_str(shop, "label", sd.label, sctx),
            catalogue=_point(shop.get("catalogue", sd.catalogue), f"{sctx} catalogue"),
            model=_str(shop, "model", sd.model, sctx), pose=pose,
            price=_int(shop, "price", sd.price, sctx, 1, 99999),
            fun=_pair(shop.get("fun", sd.fun), f"{sctx} fun"),
            request_flag=_int(shop, "request_flag", sd.request_flag, sctx, 0, 16143),
            prompt=_str(shop, "prompt", sd.prompt, sctx),
            park=_point(shop.get("park", sd.park), f"{sctx} park"))
    return HouseholdSpec(**kw)


# ------------------------------------------------------------------------------------------------ emission
def _vec(table_id: int, i: int) -> str:
    return f"const({table_id}) const({i}) B_VECTOR"


def _pt(p) -> str:
    return f"[{p[0]}, {p[1]}]"


def _need_index(n: str) -> int:
    return NEEDS.index(n)


def _mood_expr() -> str:
    """MOOD = the average of the five needs (B_LMAX/B_LMIN are party selectors, not min/max -- the trap)."""
    cells = [_vec(NEED_TABLE_ID, i) for i in range(len(NEEDS))]
    return '"expr:' + cells[0] + "".join(f" {c} B_PLUS" for c in cells[1:]) + f' const({len(NEEDS)}) B_DIV"'


def _hud(s: HouseholdSpec) -> str:
    vals = ", ".join(f'"expr:{_vec(NEED_TABLE_ID, i)}"' for i in range(len(NEEDS)))
    need_txt = " ".join(f"{LABEL[n]} [NUMB={i}]" for i, n in enumerate(NEEDS))
    hour = f"expr:{_vec(CLOCK_TABLE_ID, 0)} const({s.start_hour}) B_PLUS const(24) B_REM"
    if s.job is not None:
        return f"""[[behavior.hud]]                    # ONE strip: 5 needs, the hour, SKILL, GIL -- all 8 gMesValue slots
window = 6
text = "[MPOS=10,48]{need_txt}\\nSKILL [NUMB=6]  [NUMB=5]:00  GIL [NUMB=7]{"  SELECT: shop" if s.shop else ""}"
values = [{vals},
          "{hour}",
          "expr:const4({s.job.skill_table}) const(0) B_VECTOR",
          "gil"]
digits = [3, 3, 3, 3, 3, 2, 3, 5]
"""
    day = f"expr:{_vec(CLOCK_TABLE_ID, 0)} const({s.start_hour}) B_PLUS const(24) B_DIV const(1) B_PLUS"
    return f"""[[behavior.hud]]                    # ONE strip: gMesValue[8] is global, a second strip overwrites this one's slots
window = 6
text = "[MPOS=10,48]HUN [NUMB=0] THR [NUMB=1] NRG [NUMB=2] HYG [NUMB=3] FUN [NUMB=4]\\nDAY [NUMB=5]  [NUMB=6]:00  MOOD [NUMB=7]"
values = [{vals},
          "{day}",
          "{hour}",
          {_mood_expr()}]
digits = [3, 3, 3, 3, 3, 2, 2, 3]
"""


def _failure_tiers(s: HouseholdSpec) -> str:
    """Above everything: the all-nighter wakes her, and a need at 0 FAINTS her. Per need, in order: revive
    (down, and the need has crept back to revive_at -> get up) / down (the frozen collapse, the need creeping
    back) / fall (the need hit 0 -> raise the fainted flag; an energy faint ends the all-nighter)."""
    out = ["""  [[behavior.unit.branch]]           # the all-nighter: up out of bed, now
  when = [{ flag = "nosleep" }, { flag = "t_energy" }]
  do = { hold_ground = true }
  clear_flags = ["t_energy"]
"""]
    for i, n in enumerate(NEEDS):
        extra = '\n  clear_flags = ["nosleep"]' if n == "energy" else ""
        out.append(f"""  [[behavior.unit.branch]]           # FAINT {n}: back on her feet
  when = [{{ flag = "f_{n}" }}, {{ table_ge = ["need", {i}, {s.revive_at}] }}]
  do = {{ hold_ground = true }}
  clear_flags = ["f_{n}"]

  [[behavior.unit.branch]]           # FAINT {n}: down, frozen, the need creeping back
  when = [{{ flag = "f_{n}" }}]
  do = {{ hold_ground = true, anim = "{s.faint_pose}", freeze = true }}
  adjust = {{ table = "need", index = {i}, by = 1, clamp = [0, 100], every = {s.faint_regen} }}

  [[behavior.unit.branch]]           # FAINT {n}: the need hit 0 -- she drops where she stands
  when = [{{ table_le = ["need", {i}, 0] }}]
  do = {{ hold_ground = true }}
  raise_flags = ["f_{n}"]{extra}
""")
    return "\n".join(out)


def _job_tiers(s: HouseholdSpec) -> str:
    """Work and study: finish -> use -> go, as one block below the failure tiers and above the needs' finish
    tier -- a NEED's urge still wins when it fires first (the urge tier runs only with no task flagged), but a
    task in progress is finished before a new need is served. A shift ends by raising the payday flag its skill
    earns; the progress cell resets (a -1000 adjust clamped at 0)."""
    j = s.job
    f = _need_index("fun")
    reset0 = '{ table = "job", index = 0, by = -1000, clamp = [0, 1000] }'
    reset1 = '{ table = "job", index = 1, by = -1000, clamp = [0, 1000] }'
    return f"""  [[behavior.unit.branch]]           # WORK done, skilled: the higher wage
  when = [{{ flag = "t_work" }}, {{ table_ge = ["job", 0, {j.shift_len}] }}, {{ table_ge = ["skill", 0, {j.skilled_at}] }}]
  do = {{ hold_ground = true }}
  clear_flags = ["t_work"]
  raise_flags = ["worked", "pay_hi"]
  adjust = {reset0}

  [[behavior.unit.branch]]           # WORK done: the starting wage
  when = [{{ flag = "t_work" }}, {{ table_ge = ["job", 0, {j.shift_len}] }}]
  do = {{ hold_ground = true }}
  clear_flags = ["t_work"]
  raise_flags = ["worked", "pay_lo"]
  adjust = {reset0}

  [[behavior.unit.branch]]           # STUDY done
  when = [{{ flag = "t_study" }}, {{ table_ge = ["job", 1, {j.study_len}] }}]
  do = {{ hold_ground = true }}
  clear_flags = ["t_study"]
  adjust = {reset1}

  [[behavior.unit.branch]]           # at the desk: sorting the mail (costs fun)
  when = [{{ flag = "t_work" }}, {{ near_point = ["desk_spot", 160] }}]
  do = {{ hold = "desk_spot" }}
  adjust = [{{ table = "job", index = 0, by = 1, clamp = [0, 1000], every = 10 }},
            {{ table = "need", index = {f}, by = {j.work_fun[0]}, clamp = [0, 100], every = {j.work_fun[1]} }}]

  [[behavior.unit.branch]]           # at the desk: studying (skill climbs, fun drains)
  when = [{{ flag = "t_study" }}, {{ near_point = ["desk_spot", 160] }}]
  do = {{ hold = "desk_spot" }}
  adjust = [{{ table = "job", index = 1, by = 1, clamp = [0, 1000], every = 10 }},
            {{ table = "skill", index = 0, by = {j.study_gain[0]}, clamp = [0, 100], every = {j.study_gain[1]} }},
            {{ table = "need", index = {f}, by = {j.study_fun[0]}, clamp = [0, 100], every = {j.study_fun[1]} }}]

  [[behavior.unit.branch]]           # off to work
  when = [{{ flag = "t_work" }}]
  do = {{ walk_to = "desk_spot", speed = 40 }}

  [[behavior.unit.branch]]           # off to study
  when = [{{ flag = "t_study" }}]
  do = {{ walk_to = "desk_spot", speed = 40 }}
"""


def _behavior_text(s: HouseholdSpec) -> str:
    out = []
    e = _need_index("energy")
    flags = [f"t_{n}" for n in NEEDS] + ["nosleep"]
    if s.job:
        flags += ["t_work", "t_study", "pay_lo", "pay_hi"]
    seeds = ", ".join(str(n.seed) for n in s.needs)
    out.append(f"""# ---------------------------------------------------------------- the behavior
[behavior]
warmup = {s.warmup}
public_flags = [{", ".join(f'"{f}"' for f in flags)}]
alternators = [{{ name = "night", frames = {12 * s.hour_ticks} }}, {{ name = "beat", frames = {s.beat} }}]


[[behavior.table]]
name = "need"                       # {", ".join(f"{i}={n}" for i, n in enumerate(NEEDS))} (0..100, 100 = met)
values = [{seeds}]
id = {NEED_TABLE_ID}

[[behavior.table]]
name = "clock"                      # [0] = hours since entry (the day starts at {s.start_hour:02d}:00)
values = [0]
id = {CLOCK_TABLE_ID}""")
    if s.job:
        out.append(f"""
[[behavior.table]]
name = "skill"                      # [0] = the sim's job skill, 0..100 -- PERSISTENT: survives the day
values = [0]
id = {s.job.skill_table}
persist = true

[[behavior.table]]
name = "job"                        # [0] = shift progress, [1] = study progress
values = [0, 0]
id = {JOB_TABLE_ID}
""")
    if s.job and s.shop:
        out.append(f"""[[behavior.pool]]                   # BUY MODE: {s.shop.label}, at the steward's feet, for real gil
name = "{s.shop.pool()}"
price = {s.shop.price}
button = true
request_flag = {s.shop.request_flag}
""")
    out.append(f"""
[[behavior.drift]]                  # THE CLOCK
table = "clock"
index = 0
by = 1
clamp = [0, 1000000]
every = {s.hour_ticks}
""")
    for i, n in enumerate(s.needs):
        out.append(f"""[[behavior.drift]]                  # metabolism: {n.name}
table = "need"
index = {i}
by = -1
clamp = [0, 100]
every = {n.decay}
""")
    out.append(f"""[[behavior.drift]]                  # night tires her faster
table = "need"
index = {e}
by = -1
clamp = [0, 100]
every = {s.night_tire_every}
flag = "night"

[[behavior.drift]]                  # an all-nighter drains her fast
table = "need"
index = {e}
by = -1
clamp = [0, 100]
every = {s.nosleep_every}
flag = "nosleep"

{_hud(s).rstrip(chr(10))}
# (no "(day)/(night)" word: a [TEXT=] in a HUD strip is resolved ONCE at window open -- the engine's constant-tag
#  pass runs before the variable snapshot -- so it freezes at the open pass's sentinel row and renders "")

[[behavior.unit]]
npc = "{s.sim}"
speed = {s.speed}
""")
    out.append(_failure_tiers(s))
    if s.job:
        out.append(_job_tiers(s))
    # ---- tier 1: finish
    for i, n in enumerate(s.needs):
        out.append(f"""  [[behavior.unit.branch]]           # finish: {n.name} is met -> the task retires
  when = [{{ flag = "t_{n.name}" }}, {{ table_ge = ["need", {i}, {s.full_at}] }}]
  do = {{ hold = "{n.name}_spot" }}
  clear_flags = ["t_{n.name}"]
""")
    # ---- tier 2: use
    for i, n in enumerate(s.needs):
        if n.name == "fun" and s.shop:
            sh = s.shop
            out.append(f"""  [[behavior.unit.branch]]           # use: FUN with the {sh.name} (bought) -- faster than the puppet
  when = [{{ flag = "t_fun" }}, {{ active = "{sh.name}" }}, {{ near = ["{sh.name}", 240] }}]
  do = {{ hold_ground = true, anim = "laugh" }}
  adjust = {{ table = "need", index = {i}, by = {sh.fun[0]}, clamp = [0, 100], every = {sh.fun[1]} }}
""")
        by, every = n.use
        do = (f'{{ hold_ground = true, anim = "{n.pose}" }}' if n.pose else f'{{ hold = "{n.name}_spot" }}')
        out.append(f"""  [[behavior.unit.branch]]           # use: at the {n.name} object, the meter climbs
  when = [{{ flag = "t_{n.name}" }}, {{ near_point = ["{n.name}_spot", 160] }}]
  do = {do}
  adjust = {{ table = "need", index = {i}, by = {by}, clamp = [0, 100], every = {every} }}
""")
    # ---- tier 3: go
    for n in s.needs:
        if n.name == "fun" and s.shop:
            out.append(f"""  [[behavior.unit.branch]]           # go: to the {s.shop.name}, if she owns one
  when = [{{ flag = "t_fun" }}, {{ active = "{s.shop.name}" }}]
  do = {{ chase = "{s.shop.name}", standoff = 160, speed = 40 }}
""")
        out.append(f"""  [[behavior.unit.branch]]           # go: a {n.name} task is waiting
  when = [{{ flag = "t_{n.name}" }}]
  do = {{ walk_to = "{n.name}_spot", speed = 40 }}
""")
    # ---- tier 4: urges (only reached when no task is flagged), most pressing first
    new_day = '\n  clear_flags = ["worked"]            # bedtime: tomorrow is a new workday' if s.job else ""
    out.append(f"""  [[behavior.unit.branch]]           # urge: night, and tired enough to turn in
  when = [{{ flag = "night" }}, {{ table_le = ["need", {e}, {s.night_sleep_at}] }}, {{ not_flag = "nosleep" }}]
  do = {{ walk_to = "energy_spot", speed = 40 }}
  raise_flags = ["t_energy"]{new_day}
""")
    for n in ("hunger", "thirst", "energy", "hygiene", "fun"):
        i = _need_index(n)
        guard = ', { not_flag = "nosleep" }' if n == "energy" else ""
        out.append(f"""  [[behavior.unit.branch]]           # urge: {n} has run low
  when = [{{ table_le = ["need", {i}, {s.urge_at}] }}{guard}]
  do = {{ walk_to = "{n}_spot", speed = 40 }}
  raise_flags = ["t_{n}"]
""")
    if s.job:
        out.append(f"""  [[behavior.unit.branch]]           # a WORKDAY: by day, rested, not yet worked today -> to the desk
  when = [{{ not_flag = "night" }}, {{ not_flag = "worked" }}, {{ table_ge = ["need", {e}, {s.job.work_ready_at}] }}]
  do = {{ walk_to = "desk_spot", speed = 40 }}
  raise_flags = ["t_work"]
""")
    out.append(f"""  [[behavior.unit.branch]]           # idle emote: tired -> a yawn on the beat
  when = [{{ flag = "beat" }}, {{ table_le = ["need", {e}, {s.tired_at}] }}]
  do = {{ hold_ground = true, anim = "yawn" }}

  [[behavior.unit.branch]]           # idle emote: merry -> a laugh on the beat
  when = [{{ flag = "beat" }}, {{ table_ge = ["need", {_need_index("fun")}, {s.merry_at}] }}]
  do = {{ hold_ground = true, anim = "laugh" }}
""")
    out.append("""  # idle: amble round home
  [[behavior.unit.branch]]
  do = { wander = "home", radius = 200, every = 120, speed = 25 }
""")
    if s.job and s.shop:
        out.append(f"""
[[behavior.unit]]
npc = "{s.shop.name}"
pooled = true
pool = "{s.shop.pool()}"

  [[behavior.unit.branch]]
  do = {{ hold_post = true }}          # it stays where the steward bought it
""")
    return "\n".join(out)


def _world_text(s: HouseholdSpec) -> str:
    """The sim npc, its props and markers -- everything that is not behavior or a menu."""
    out = [f"""[[npc]]
name = "{s.sim}"
model = "{s.model}"
pos = [{s.home[0]}, {s.home[1]}]
dialogue = {_q(s.dialogue)}

[[marker]]
name = "home"
pos = [{s.home[0]}, {s.home[1]}]
"""]
    if s.job:
        j = s.job
        out.append(f"""
[[prop]]
prop = "{j.prop}"
pos = [{j.desk[0]}, {j.desk[1]}]
""")
        if s.shop:
            out.append(f"""[[prop]]
prop = "save_point"                 # the moogle + its book: the catalogue, somewhere you can SEE
pos = [{s.shop.catalogue[0]}, {s.shop.catalogue[1]}]
""")
        out.append(f"""[[marker]]
name = "desk_spot"
pos = [{j.desk_spot[0]}, {j.desk_spot[1]}]
""")
        if s.shop:
            sh = s.shop
            out.append(f"""[[npc]]
name = "{sh.name}"
model = "{sh.model}"
anims = {{ stand = {sh.pose}, walk = {sh.pose}, run = {sh.pose}, left = {sh.pose}, right = {sh.pose} }}
pos = [{sh.park[0]}, {sh.park[1]}]                 # dormant placeholder: a pooled unit appears where it is BOUGHT
""")
    for n in s.needs:
        out.append(f"""
[[prop]]
prop = "{n.prop}"
pos = [{n.pos[0]}, {n.pos[1]}]

[[marker]]
name = "{n.name}_spot"
pos = [{n.spot[0]}, {n.spot[1]}]
""")
    return "\n".join(out)


def _q(text: str) -> str:
    """A TOML basic string."""
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'


def blocks(spec: HouseholdSpec) -> dict:
    """The generated blocks WITHOUT the menus (their flag indices come from a dry allocation of these):
    ``{"npc": [...], "prop": [...], "marker": [...], "behavior": {...}}``."""
    return tomllib.loads(_world_text(spec) + "\n" + _behavior_text(spec))


# ------------------------------------------------------------------------------------------------ the menus
def _opt(text: str, **kw) -> dict:
    return {"text": text, **kw}


def choices(spec: HouseholdSpec, flags: dict) -> list:
    """The steward's menus. ``flags`` maps a published flag NAME to its resolved blackboard index. An order
    row sets the SAME public flag an urge raises and hides while that task is pending; no reply page (a
    reply only delays the walk: the order lands when the reply CLOSES)."""
    out = []
    for n in spec.needs:
        t = f"t_{n.name}"
        opts = [_opt(f"{spec.label}, {n.verb}.", set_flag=[flags[t], 1], requires_flag_clear=flags[t])]
        if n.name == "energy":
            opts.append(_opt(f"{spec.label}, stay up all night!", set_flag=[flags["nosleep"], 1],
                             requires_flag_clear=flags["nosleep"]))
        opts.append(_opt("Never mind."))
        out.append({"zone": n.zone(), "bubble": True, "instant": True, "prompt": n.prompt, "options": opts})
    j = spec.job
    if j:
        out.append({"zone": j.zone(), "bubble": True, "instant": True, "prompt": j.desk_prompt, "options": [
            _opt(f"Collect {spec.label}'s wages ({j.wage_hi} gil).", gil=j.wage_hi,
                 set_flag=[flags["pay_hi"], 0], requires_flag=flags["pay_hi"]),
            _opt(f"Collect {spec.label}'s wages ({j.wage_lo} gil).", gil=j.wage_lo,
                 set_flag=[flags["pay_lo"], 0], requires_flag=flags["pay_lo"]),
            _opt(f"{spec.label}, go to work.", set_flag=[flags["t_work"], 1],
                 requires_flag_clear=flags["t_work"]),
            _opt(f"{spec.label}, study.", set_flag=[flags["t_study"], 1], requires_flag_clear=flags["t_study"]),
            _opt("Never mind.")]})
        sh = spec.shop
        if sh:
            cx, cz = sh.catalogue
            out.append({"zone": [[cx - 260, cz - 240], [cx + 260, cz - 240], [cx + 260, cz + 240],
                                 [cx - 260, cz + 240]],
                        "bubble": True, "instant": True, "prompt": sh.prompt, "options": [
                _opt(f"{sh.label} ({sh.price} gil).", set_flag=[sh.request_flag, 1],
                     requires_flag=flags[f"pool.{sh.pool()}.hireable"]),
                _opt("Not now.")]})
    return out


def resolve_flags(raw: dict) -> dict:
    """The blackboard flag indices the menus need -- every ``public_flags`` name (``t_hunger`` ...) and each
    pool's ``hireable`` gate (``pool.<name>.hireable``) -- WITHOUT compiling: allocation is deterministic from
    the FieldBehavior constructor alone (the allocation contract), so a throwaway build on a route-stripped
    copy resolves them (the ``siege.resolve_hireable`` pattern)."""
    from . import behaviortoml as BT
    work = copy.deepcopy(raw)
    txids = {(ui, bi): 900 + 10 * ui + bi for ui, bi, _ in BT.announce_lines(work)}
    txids.update({("hud", hi): 890 + hi for hi, _h in BT.hud_lines(work)})
    fb = BT.build(work, npc_slots=BT.placeholder_slots(work),
                  npc_txids_by_name={n.get("name"): 0 for n in work.get("npc", []) or []},
                  behavior_txids=txids)
    out = {str(pf): fb.public_flag(str(pf)) for pf in (work.get("behavior", {}).get("public_flags") or [])}
    for pool, flag in fb.pool_hireable.items():
        out[f"pool.{pool}.hireable"] = int(flag)
    return out


def _resolve_skill_table(spec: HouseholdSpec, raw: dict) -> HouseholdSpec:
    """A job with no ``skill_table`` takes 6,000,000 + the field id: persistent ids are SAVE identity, and the
    field id is the one number already unique to this field."""
    if spec.job is None or spec.job.skill_table is not None:
        return spec
    try:
        fid = int((raw.get("field") or {}).get("id"))
    except (TypeError, ValueError):
        raise HouseholdError("[household.job]: no skill_table and no [field] id to derive one from -- set "
                             f"skill_table to a persistent id in {SKILL_FLOOR}..{SKILL_CEIL}")
    if not 0 <= fid <= SKILL_CEIL - SKILL_FLOOR:
        raise HouseholdError(f"[household.job]: field id {fid} is out of range for a derived skill_table")
    return replace(spec, job=replace(spec.job, skill_table=SKILL_FLOOR + fid))


def desugar(raw: dict) -> None:
    """Expand ``[household]`` into the proven blocks, in place. Malformed input is left for
    :func:`ff9mapkit.build.validate` to report (the ferry / siege pattern); a field already carrying
    ``[behavior]`` is also left untouched (validate refuses the combination -- ``[household]`` owns the
    behavior table)."""
    h = raw.get("household")
    if h is None:
        return
    if raw.get("behavior") or raw.get("siege"):
        raw["_household_conflict"] = True         # validate() reports; nothing emitted
        return
    try:
        spec = _resolve_skill_table(from_raw(h), raw)
    except HouseholdError:
        return                                    # validate() re-parses and reports
    gen = blocks(spec)
    for key in ("npc", "prop", "marker"):
        raw.setdefault(key, [])
        raw[key] += gen.get(key, [])
    raw["behavior"] = gen["behavior"]
    try:
        flags = resolve_flags(raw)
    except Exception as e:                        # a generated-raw bug must not crash load
        raw["_household_error"] = f"flag resolution failed: {e}"
        return
    raw.setdefault("choice", [])
    raw["choice"] += choices(spec, flags)


def problems(raw: dict) -> list:
    """What :func:`ff9mapkit.build.validate` reports for the block the author WROTE (the desugared
    ``[behavior]`` / ``[[npc]]`` / ``[[choice]]`` rows then get the full downstream validation for free)."""
    if raw.get("household") is None:
        return []
    out = []
    if raw.get("_household_conflict"):
        out.append("[household] owns the field's [behavior] table -- remove the hand-written [behavior] (or "
                   "[siege]); drop to raw [behavior] authoring for anything the block cannot express")
    else:
        try:
            _resolve_skill_table(from_raw(raw["household"]), raw)
        except HouseholdError as e:
            out.append(str(e))
    if raw.get("_household_error"):
        out.append(f"[household]: {raw['_household_error']}")
    if "verbatim_eb" in raw:
        out.append("[household] is not supported on a verbatim fork -- it synthesizes the field's whole "
                   "behavior layer")
    return out
