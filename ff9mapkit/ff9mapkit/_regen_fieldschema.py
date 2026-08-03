"""Regenerate ``_fieldschema.py`` -- the HARVESTED field.toml key schema.

Runs the REAL pipeline (load -> validate -> lint -> build-to-tempdir) over the bundled examples
(plus targeted stubs grafted onto a vivi-hut copy) with the raw tree wrapped in the recording dict
(:mod:`ff9mapkit.fieldschema`), and emits every key the consumers PROBED, per normalized path.
Probes are not usage: one ``[[npc]]`` in the corpus harvests the whole npc vocabulary the code
asks about, present or not. Enforcement is stricter than vocabulary: a path is enforced only if it
occurred in a corpus item whose FULL pipeline completed, so a section whose consumers never all
ran is recorded but never enforced against a user.

The editor form specs are merged in as seeds: the editor WRITES those keys, so they are legal by
construction even where the build never reads them (documentation-only keys like ``[field]
title``) -- and seeding keeps the two curated surfaces from ever disagreeing.

Run from the kit root:  ``py -m ff9mapkit._regen_fieldschema``  (``--check`` re-harvests and exits
nonzero on drift instead of writing). In a fresh worktree the extract cache is empty and
BG-borrow examples cannot build; point ``$FF9MAPKIT_DATA`` at a checkout whose cache is populated,
or accept the demotion (the sanity gate refuses an emit that lost core coverage, so a crippled run
cannot silently ship a crippled schema).
"""

from __future__ import annotations

import argparse
import shutil
import sys
import tempfile
import tomllib
from pathlib import Path

from . import fieldschema

_DEST = Path(__file__).resolve().parent / "_fieldschema.py"
_EXAMPLES = Path(__file__).resolve().parents[1] / "examples"

# Sections the bundled examples don't author, grafted (data-only, offline-buildable) onto a copy of
# vivi-hut so their consumers run end-to-end and the paths reach ENFORCED. Each stub must only ADD
# sections vivi-hut lacks (a repeated [table] is a TOML parse error; a repeated [[array]] is fine).
# Grouped so one stub failing to build demotes only its own sections. Coordinates sit inside
# vivi-hut's walkmesh quad (x -1400..1400, z -2400..-800); placement WARNINGS don't demote.
_STUBS: "list[tuple[str, str]]" = [
    ("content", """
[dialogue]
wrap = 26

[[flag]]
name = "stub_chest"
index = 8790

[[flag]]
name = "stub_seen"
index = 8791

[[marker]]
name = "stub_mark"
pos = [-600, -1500]

[[prop]]
name = "stub_barrel"
prop = "barrel"
pos = [900, -2100]
face = 64

[[chest]]
pos = [-900, -2100]
gil = 150
flag = "stub_chest"
face = 128

[[npc]]
name = "Asker"
preset = "vivi"
pos = [600, -1200]

[[choice]]
npc = "Asker"
prompt = "A stub question?"
options = [
  { text = "Yes", reply = "Good.", set_flag = ["stub_seen", 1] },
  { text = "No", reply = "Fine." },
]
"""),
    ("ferry", """
[[npc]]
name = "Purser"
preset = "vivi"
pos = [-600, -1200]

[[ferry]]
npc = "Purser"
prompt = "Where shall we sail?"
decline = "Stay ashore."
decline_reply = "Very well."

[[ferry.destination]]
name = "Ashvale"
arrive = [60.0, -1168.0]
arrive_face = 192
reply = "Casting off."
"""),
    ("behavior", """
[[marker]]
name = "post"
pos = [-600, -1500]

[[marker]]
name = "ring"
pos = [-600, -1500]
path = [[-600, -1500], [-200, -1500], [-200, -1100], [-600, -1100]]
closed = true

[[marker]]
name = "lane"
pos = [600, -1500]
path = [[600, -1500], [200, -1800], [-200, -2000]]

[[npc]]
name = "guard"
preset = "vivi"
pos = [0, -1000]
dialogue = "Halt!"

[[npc]]
name = "beast"
preset = "vivi"
pos = [500, -1900]
dialogue = "Grr."

[behavior]
warmup = 30
public_flags = ["go"]

[[behavior.alternators]]
name = "shift"
frames = 300

[[behavior.unit]]
npc = "guard"
hp = 5
speed = 40
branch = [
  { when = [ { hp_le = 0 } ], do = { die = true } },
  { when = [ { flag = "alarm" }, { active = "beast" }, { near = ["beast", 300] } ], do = { swing_at = "beast", damage = 2 } },
  { when = [ { any_near = [["beast"], 700] } ], do = { chase = "beast", standoff = 180, speed = 65 }, raise_flags = ["alarm"] },
  { when = [ { flag = "shift" } ], do = { patrol = "ring" } },
  { do = { hold = "post" } },
]

[[behavior.unit]]
npc = "beast"
hp = 3
branch = [
  { when = [ { hp_le = 0 } ], do = { die = true } },
  { when = [ { flag = "go" }, { near_point = ["post", 250] } ], do = { announce_npc = "beast" }, once = "gloat" },
  { when = [ { flag = "go" } ], do = { march = "lane", arrive_r = 200 } },
  { do = { wander = [500, -1900], radius = 300, every = 90, speed = 30 } },
]
"""),
    ("sps", """
[[sps]]
id = 5001
template = "fire"
pos = [0, -1200]
"""),
    # The CONDUCTOR (a CAST cutscene, actors = [...]): the bundled examples only author narration
    # cutscenes, so without this stub group_parallel/_validate_conductor never run and the whole
    # conductor step vocabulary (with_prev, speed, follow, ...) is invisible to the harvest -- lint
    # then false-positives on an in-game-proven key.
    ("conductor", """
[[npc]]
name = "Stagehand"
preset = "vivi"
pos = [-500, -1300]

[[npc]]
name = "Runner"
preset = "vivi"
pos = [500, -1300]

[cutscene]
actors = ["Stagehand", "Runner", "player"]
once = true
flag = 8794
steps = [
  { actor = "Stagehand", say = "Places, everyone!", speaker = "[HAND]" },
  { actor = "Runner", teleport = [900, -2200] },
  { actor = "Stagehand", walk = [-700, -1600] },
  { actor = "Runner", walk = [700, -1600], with_prev = true },
  { actor = "player", turn = 128, with_prev = true },
  { wait = 20 },
  { actor = "Stagehand", animation = "glad" },
  { actor = "Runner", turn = 0, with_prev = true },
  { actor = "Stagehand", face_player = true },
  { set_flag = [8794, 1] },
]
"""),
]

# Standalone stub projects (whole tomls, no vivi-hut base) -- for paths a vivi-hut graft can't
# reach because the base already owns the section. The auto-frame stub ships NO walkmesh, so
# resolve_walkmesh takes the [camera.frame] auto path (vivi-hut's quad short-circuits it).
_STANDALONE_STUBS: "list[tuple[str, str]]" = [
    ("autoframe", """
[field]
id = 31999
name = "AUTOFRAME"
area = 11

[camera]
pitch = 48
distance = 4500
fov = 42.2

[camera.frame]
back = 205
front = 432

[player]
spawn = [0, -1350]

[[gateway]]
to = "worldmap"
region_key = 62
arrive = [60.0, -1168.0]
arrive_face = 192
zone = [[-1100, -2400], [1100, -2400], [1100, -1750], [-1100, -1750]]
"""),
]

# The emit is refused unless these paths came out enforced -- a run whose corpus could not build
# (empty extract cache, missing install) must fail loudly, not ship a schema with checking off.
# This is the won ground: every path here HAS built end-to-end from the examples + stubs, so a
# regen that loses one has lost corpus coverage, not gained flexibility.
_REQUIRED_ENFORCED = {"", "field", "camera", "walkmesh", "layers", "player", "npc", "gateway",
                      "event", "chest", "prop", "marker", "flag", "choice", "choice.options",
                      "cutscene", "cutscene.steps", "dialogue", "encounter", "music", "party",
                      "startup", "ferry", "ferry.destination", "behavior", "behavior.unit"}


def _corpus(extra=()) -> list[Path]:
    items = sorted(_EXAMPLES.rglob("*.field.toml"))
    for e in extra:
        p = Path(e)
        items += sorted(p.rglob("*.field.toml")) if p.is_dir() else [p]
    return items


def _stub_items(tmp: Path) -> list[Path]:
    src = _EXAMPLES / "vivi-hut"
    out = []
    for name, extra_toml in _STUBS:
        d = tmp / f"stub-{name}"
        shutil.copytree(src, d)
        f = d / "hut_int.field.toml"
        f.write_text(f.read_text(encoding="utf-8") + "\n" + extra_toml, encoding="utf-8")
        out.append(f)
    for name, toml_text in _STANDALONE_STUBS:
        d = tmp / f"stub-{name}"
        d.mkdir()
        f = d / f"{name}.field.toml"
        f.write_text(toml_text, encoding="utf-8")
        out.append(f)
    return out


def _run_item(path: Path, rec: fieldschema.Recorder) -> "tuple[bool, list[str]]":
    """One corpus item through the pipeline. True = the FULL pipeline completed (validate clean +
    build succeeded); lint always runs for its probes but its warnings don't demote the item --
    a warning doesn't stop a consumer from reading its keys."""
    from . import build, config
    notes: list[str] = []
    try:
        with fieldschema.harvesting(rec):
            proj = build.FieldProject.load(path)     # raw stays wrapped for the stages below
    except Exception as e:                        # noqa: BLE001 -- a bad item demotes, never aborts
        return False, [f"load failed: {type(e).__name__}: {e}"]
    try:
        problems = build.validate(proj)
    except Exception as e:                        # noqa: BLE001 -- e.g. a traversal '..' asset ref
        problems = [f"validate crashed: {type(e).__name__}: {e}"]
    build.lint_all(proj)                          # never raises (its own contract); run for the probes
    if problems:
        notes.append(f"validate: {len(problems)} problem(s): {problems[0]}")
        return False, notes
    with tempfile.TemporaryDirectory() as td:
        try:
            build.build_field(proj, config.ModLayout(Path(td)))
        except Exception as e:                    # noqa: BLE001 -- any failure just demotes the item
            notes.append(f"build failed: {type(e).__name__}: {e}")
            return False, notes
    return True, notes


def _occurring_paths(data: dict) -> set[str]:
    """Every normalized dict-node path in an authored tree (list-of-tables shares its key's path)."""
    out = {""}

    def walk(node: dict, path: str) -> None:
        for k, v in node.items():
            child = f"{path}.{k}" if path else k
            if isinstance(v, dict):
                out.add(child)
                walk(v, child)
            elif isinstance(v, list):
                for e in v:
                    if isinstance(e, dict):
                        out.add(child)
                        walk(e, child)

    walk(data, "")
    return out


def _seed_vocab() -> "dict[str, set[str]]":
    from .editor import forms
    spec_paths = {
        "field": forms.FIELD_SPEC, "npc": forms.NPC_SPEC, "gateway": forms.GATEWAY_SPEC,
        "event": forms.EVENT_SPEC, "chest": forms.CHEST_SPEC, "prop": forms.PROP_SPEC,
        "sps": forms.SPS_SPEC, "encounter": forms.ENCOUNTER_SPEC, "music": forms.MUSIC_SPEC,
        "party": forms.PARTY_SPEC, "playable": forms.PLAYABLE_SPEC, "startup": forms.STARTUP_SPEC,
        "cutscene": forms.CUTSCENE_SPEC, "marker": forms.MARKER_SPEC, "flag": forms.FLAG_SPEC,
        "choice": forms.CHOICE_SPEC, "choice.options": forms.CHOICE_OPTION_SPEC,
        "dialogue": forms.DIALOGUE_SPEC, "player": forms.PLAYER_SPEC,
    }
    seeds = {p: {f.key for f in spec} for p, spec in spec_paths.items()}
    seeds["cutscene.steps"] = set(forms.STEP_KIND) | {"actor"}
    # A walk/path step's DOCUMENTED `speed` (FORMAT.md "Optional speed = N") is read only AFTER
    # _resolve_conductor_steps/_resolve_move_steps rebuild the step dicts (`dict(s)` / `{**s}` copies
    # shed the recording wrapper), so no probe can ever harvest it. (`follow` is NOT seeded: the build
    # derives it internally in _resolve_move_steps -- authors write `walk = "@player"`.)
    seeds["cutscene.steps"].add("speed")
    # [scene] file is probed on the PRE-merge base (before the harvest seam) -- seed it explicitly.
    seeds[""] = {"scene"}
    seeds["scene"] = {"file"}
    # DOCUMENTED accepted-but-ignored back-compat keys (build.resolve_walkmesh's comment): older
    # projects and the Blender editable-fork export carry them, and the build reads NEITHER -- so no
    # probe can ever harvest them. Seeding is what keeps a legal legacy toml from false-positiving.
    seeds["walkmesh"] = {"frame", "character_offset"}
    # Keys consumed GENERICALLY (an items() filter against a key table) never probe, so they're
    # seeded from the code's OWN tables -- the same objects the consumers filter with, so the two
    # can't drift. A custom ability row's tuning overrides are actiondelta._CUSTOM_ACTION_OVERRIDES
    # (playable._parse_custom_ability: "everything else is an ACTION_FIELDS override"); a learn row
    # is "{ ability, ap }" (playable.parse_playable's own error text).
    from .battle import actiondelta
    for cmd in ("command1", "command2"):
        seeds.setdefault(f"playable.abilities.{cmd}.abilities", set()).update(
            actiondelta._CUSTOM_ACTION_OVERRIDES)
    seeds.setdefault("playable.abilities.learn", set()).update({"ability", "ap"})
    # The native-scene carry trio: written into a fork's [field] by `import --native`
    # (extract.py's toml emit) and consumed only on the native branch (build's bgs/atlas/mapconfig
    # ship + repaint-native's atlas_tile_size) -- a branch no offline corpus item can reach, since
    # native forks stage game-derived assets the repo can't carry.
    seeds.setdefault("field", set()).update({"atlas", "atlas_tile_size", "mapconfig"})
    return seeds


def harvest(extra=()) -> "tuple[dict[str, set[str]], set[str], list[str]]":
    rec = fieldschema.Recorder()
    report: list[str] = []
    enforced: set[str] = set()
    with tempfile.TemporaryDirectory() as tmp:
        items = _corpus(extra) + _stub_items(Path(tmp))
        for f in items:
            ok, notes = _run_item(f, rec)
            tag = "ok      " if ok else "partial "
            label = f"{f.parent.name}/{f.name}"
            report.append(f"  [{tag}] {label}" + (f"  ({'; '.join(notes)})" if notes else ""))
            if ok:
                with f.open("rb") as fh:
                    enforced |= _occurring_paths(tomllib.load(fh))
    vocab = {p: set(keys) for p, keys in rec.probes.items()}
    for p, keys in _seed_vocab().items():
        vocab.setdefault(p, set()).update(keys)
    # never enforce a path whose vocabulary came out empty -- it would flag EVERY key there
    dropped = {p for p in enforced if not vocab.get(p)}
    enforced -= dropped
    for p in sorted(dropped):
        report.append(f"  [dropped] {p!r} occurred in the corpus but no consumer probed it")
    return vocab, enforced, report


_HEADER = '''"""AUTO-GENERATED by _regen_fieldschema.py -- DO NOT EDIT BY HAND.

The harvested field.toml key schema: ``VOCAB`` maps a normalized dotted path (a list-of-tables
shares its key's path) to every key the pipeline's consumers PROBED there while the bundled
examples ran end-to-end, merged with the editor form-spec seeds; ``ENFORCED`` is the subset of
paths where lint's unknown-key check is ON (the path occurred in a corpus item whose full offline
pipeline completed). See ff9mapkit/fieldschema.py; regenerate with
``py -m ff9mapkit._regen_fieldschema``.
"""

'''


def _emit(vocab: "dict[str, set[str]]", enforced: "set[str]") -> str:
    lines = [_HEADER + "VOCAB = {"]
    for p in sorted(vocab):
        keys = sorted(vocab[p])
        if not keys:
            continue
        body = ", ".join(repr(k) for k in keys)
        lines.append(f"    {p!r}: ({body},)," if len(keys) == 1 else f"    {p!r}: ({body}),")
    lines.append("}")
    lines.append("")
    lines.append("ENFORCED = frozenset({")
    for p in sorted(enforced):
        lines.append(f"    {p!r},")
    lines.append("})")
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true",
                    help="re-harvest and exit 2 if the shipped _fieldschema.py differs (write nothing)")
    ap.add_argument("--extra", nargs="*", default=(),
                    help="extra corpus files/dirs (rglob *.field.toml) beyond the bundled examples")
    ap.add_argument("--out", default=None, help=f"destination (default {_DEST})")
    args = ap.parse_args(argv)

    vocab, enforced, report = harvest(args.extra)
    print("corpus:")
    for line in report:
        print(line)
    vocab_only = sorted(p for p in vocab if p not in enforced)
    print(f"harvest: {len(vocab)} paths with vocabulary, {len(enforced)} enforced")
    if vocab_only:
        print("vocabulary-only (recorded, NOT enforced): " + ", ".join(repr(p) for p in vocab_only))

    missing = _REQUIRED_ENFORCED - enforced
    if missing:
        print(f"REFUSING to emit: core paths not enforced: {sorted(missing)} -- the corpus could not "
              f"build (empty extract cache? missing install?). Fix the corpus, don't ship a schema "
              f"with checking off.", file=sys.stderr)
        return 1

    text = _emit(vocab, enforced)
    dest = Path(args.out) if args.out else _DEST
    if args.check:
        current = dest.read_text(encoding="utf-8") if dest.is_file() else ""
        if current != text:
            print(f"DRIFT: {dest.name} does not match a fresh harvest -- regenerate it "
                  f"(py -m ff9mapkit._regen_fieldschema)", file=sys.stderr)
            return 2
        print(f"{dest.name} is fresh.")
        return 0
    from . import fsutil
    fsutil.atomic_write_text(dest, text, encoding="utf-8", newline="\n")
    print(f"wrote {dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
