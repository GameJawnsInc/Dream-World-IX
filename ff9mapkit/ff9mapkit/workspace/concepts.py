"""Concept cards -- plain-language, newcomer-voiced explanations of the domain vocabulary.

Every intimidating word the Workspace shows (journey, fork, walkmesh, gEventGlobal, gateway, deploy, …)
should be answerable *in place*. This module is the single source of truth: a small registry of
:class:`Concept` cards, condensed from the canonical ``docs/GLOSSARY.md`` into a sentence or two a
non-modder understands, with the engine/technical term deferred to a muted aside.

PySide6-FREE (pure data + a resolver), like :mod:`..editor.theme` / :mod:`..editor.forms` -- so it's
unit-testable headless and consumable by any surface: the Ctrl-K palette (a "What is X?" row), a
What's-This popup, an Inspector "About this…" section, and a "?" badge on a jargon form label.
"""

from __future__ import annotations

from dataclasses import dataclass, field as _dc_field


@dataclass(frozen=True)
class Concept:
    """One concept card. ``plain`` is the newcomer explanation (no unexplained jargon); ``engine_term`` is
    the technical name/aside shown muted underneath; ``aliases`` are extra lowercase match keys."""

    term: str                       # canonical key (lowercase, the primary lookup)
    title: str                      # display title
    plain: str                      # 1-3 plain-language sentences
    engine_term: str = ""           # the technical aside ("the technical name is …")
    aliases: tuple = _dc_field(default_factory=tuple)

    def html(self, muted_hex: str) -> str:
        """The card body as rich text: the plain explanation, then the engine-term aside in ``muted_hex``."""
        body = self.plain
        if self.engine_term:
            body += f'<br><span style="color:{muted_hex};">Under the hood: {self.engine_term}</span>'
        return body


# --- the registry (condensed from docs/GLOSSARY.md; keep the two in step) -------------------------
_CARDS = [
    Concept("field", "Field",
            "One explorable screen in the game — a room, a corridor, a town square — that you walk around on, "
            "drawn over a fixed painted background. It's the smallest thing you can build and the best place "
            "to start.",
            "FF9 ships ~674 of them; a custom field uses an id of 4000 or higher.",
            ("fields", "room", "screen")),
    Concept("walkmesh", "Walkmesh",
            "The invisible floor that decides where your character can stand and how far forward or back they "
            "are (which controls what they pass in front of or behind). It isn't the picture you see — it's "
            "the surface underneath it.",
            "shipped as a .bgi file; authored from camera math, confirmed in-game.",
            ("walk mesh", "floor", "collision")),
    Concept("gateway", "Gateway",
            "A spot the player walks into that sends them to another screen — a door, a staircase, or the edge "
            "of the screen.",
            "a region trigger; the walk-out direction comes from the order of its corner points.",
            ("gateways", "door", "exit", "warp")),
    Concept("encounter", "Encounter",
            "A random battle on a field. You choose how often it happens and which battle background and music "
            "it uses.",
            "pure field-script data — it works on the stock engine.",
            ("encounters", "random battle")),
    Concept("campaign", "Campaign",
            "Several fields forked together into one mod, with the doors between them hooked up so you can walk "
            "from one screen to the next.",
            "built with import-chain; a campaign chains fields.",
            ("campaigns",)),
    Concept("journey", "Journey",
            "A whole playable adventure — one or more campaigns strung together, chosen from a World Hub, with "
            "a starting point and story state set up for you.",
            "a journey chains campaigns; a campaign chains fields.",
            ("journeys", "arc")),
    Concept("fork", "Fork",
            "Taking one of the game's real screens and copying it onto a new id so you can study it, retarget "
            "it, or build on it — the original is never touched. This is the usual way to start a project.",
            "ff9mapkit import; everything is read from your own install, never shipped with the tool.",
            ("forks", "forking", "forked", "import")),
    Concept("verbatim", "Verbatim fork",
            "The most faithful fork: it ships the real screen's entire original script and text, changing only "
            "where its doors lead. The screen keeps all of its own real behaviour — story gating, NPCs, cutscenes.",
            "the truest fork mode; implies --native.",
            ("verbatim fork",)),
    Concept("script-entries", "Entries, tags & routines",
            "A screen's script is a cast list. Each ENTRY is one actor slot — the screen itself (entry 0), "
            "the player, every NPC and object, plus invisible helpers with no model at all. An entry's "
            "numbered TAGS are the moments the engine calls it: 0 runs once at setup, 1 runs every frame, "
            "2 fires on contact, 3 fires when you press the action button there, 10 runs after a battle — "
            "other numbers are the script's own helpers, called from other routines. One entry + one tag = "
            "one ROUTINE, a single little function. Some routines pick one path from many with a switch: "
            "each CASE is one path, chosen by a value — a story beat, your menu answer's row, or a script "
            "variable — and 'default' runs when nothing matches.",
            "the .eb entry table + per-entry function tags; a [[logic_edit]]/[[logic_add]] addresses a "
            "routine as entry + tag, and switch_case retargets one case.",
            ("entry", "entries", "tag", "tags", "routine", "routines", "case", "cases", "switch",
             "switches", "script entry", "function tag")),
    Concept("native", "Native fork",
            "Ships the real background and a matching floor with no in-between files, drawn through the engine's "
            "seamless path. Handles screens the simpler 'borrow' can't.",
            "--native.",
            ("native fork", "native scene")),
    Concept("editable", "Editable fork",
            "Forks a screen into a form you can repaint — the art is split into editable layers, one per depth. "
            "Use it when you want to change the room, not just reproduce it.",
            "--editable; a re-authorable custom scene.",
            ("editable fork", "editable scene", "re-authorable")),
    Concept("bg-borrow", "BG-borrow",
            "The quickest way to give your field a background: point it at a real screen's art, so the game "
            "draws that room while running your script. You ship no pictures of your own.",
            "vs a custom scene, which ships its own background PNGs + camera + walkmesh.",
            ("bg borrow", "borrow bg", "borrow", "borrow background")),
    Concept("paint-roundtrip", "Painting a room's art",
            "Compose gives every room stand-in art — a checkerboard wall and floor — so the dungeon is "
            "walkable before you've painted anything. 'Paint art…' writes see-through guide pictures beside "
            "the room: its own camera view, the floor outline, and a marker for everything placed there, "
            "with a legend saying how tall each thing should be. Trace over those in any image editor, then "
            "save your painting over the two stand-in files — art/back.png and art/floor.png, same "
            "filenames, same size. A recompose recognises a painted file and keeps it; only untouched "
            "stand-ins get repainted.",
            "ff9mapkit paint-template projects the solved camera + walkmesh + content markers; the composer "
            "fingerprints its own placeholder PNGs (sha256), so a file that no longer matches is yours and "
            "is preserved.",
            ("paint template", "paint-template", "paint art", "paint round-trip", "placeholder art",
             "checkerboard", "trace-over")),
    Concept("story-flag", "Story flag",
            "A yes/no marker the game remembers — 'chest opened', 'talked to the king', 'saw the intro'. Use a "
            "saved (Global) one so it sticks across saves and screen reloads; a Map flag is wiped whenever the "
            "screen reloads.",
            "gEventGlobal — a save-backed memory block; pick indices in the safe band so you don't collide "
            "with the base game.",
            ("story flags", "flag", "geventglobal", "geventglobal[", "glob flag", "map flag", "glob", "flags")),
    Concept("scenario", "Scenario (story progress)",
            "The game's single 'how far along the story am I' number. Fields and scenes can check it to change "
            "what happens at different points in the story.",
            "the ScenarioCounter, stored inside gEventGlobal.",
            ("scenariocounter", "scenario counter", "story progress", "beat")),
    Concept("deploy", "Deploy",
            "Building your project and copying it into the game so you can play it. It goes into a safe test "
            "slot and backs up first, so it's reversible.",
            "writes into the mod folder; press F9 here, then ~ (tilde) in-game to reload the field.",
            ("deploys", "deployed", "deploying", "f9")),
    Concept("f6", "debug menu (~)",
            "An in-game menu you open with the tilde key (~) to test your work — reload the current screen, warp to any field, "
            "set story flags, give items, change the time. It ships in the engine bundle as a real tool.",
            "context-adaptive tabs: Go / Cheats / Flags / Time, on field, battle and overworld. (Was F6; "
            "remapped to ~ because stock Memoria uses F6 as a cheat hotkey.)",
            ("f6 menu", "debug menu", "tilde", "~", "backquote")),
    Concept("memoria", "Memoria (the engine)",
            "The open-source engine layer this toolkit works with — the Steam release of FF9 uses it. Fields you "
            "build from scratch run on the stock engine; forked fields need the dwix-custom-memoria engine bundle.",
            "novel fields = stock Memoria; forked fields = the bundled s23–s33 fork-gate patches.",
            ("engine", "dll")),
    Concept("eb", "Event script (.eb)",
            "A field's program — the code that runs it: what NPCs do, the dialogue, the doors, cutscenes, and "
            "battles. The toolkit writes it for you; you never touch a third-party editor.",
            ".eb bytecode, authored directly in Python.",
            (".eb", "event script", "bytecode", "script")),
    Concept("mes", "Text block (.mes)",
            "A field's block of dialogue lines. Each line has an id the script points at. The toolkit writes it "
            "and the game merges it over the base text.",
            "the mesID picks which text block — leave it empty to derive it from the field id (and register "
            "it automatically). A REAL block would overwrite that location's own dialogue.",
            (".mes", "mesid", "text block", "textid", "message file")),
    Concept("fbg", "FBG name",
            "The internal name of a real field's background scene, like alxt_map016 or grgr. You can look a "
            "field up by its FBG name (or a piece of it) when forking.",
            "the background-scene resource name.",
            ("fbg name", "field name")),
    Concept("field-toml", "field.toml vs scene.toml",
            "field.toml is the logic of a field — its id, dialogue, doors, and events — and it's yours to edit. "
            "scene.toml is the optional spatial half (camera, floor, positions) that Blender owns. The build "
            "merges the two, so re-exporting from Blender never clobbers your script.",
            "merged at build time by entity name; a field.toml with no scene sibling builds fine.",
            ("field.toml", "scene.toml", "scene toml", "field toml")),
    Concept("world-hub", "World Hub",
            "A menu screen a New Game can land on that lists your installed journeys and warps the player into "
            "the one they pick, setting up its story state.",
            "generated with gen-hub.",
            ("world hub", "hub")),
    Concept("overworld", "Overworld (world map)",
            "The big walkable world map between towns. The kit's world-* commands reshape its land, coastlines, "
            "encounters, and entrances.",
            "some overworld features need the dwix-custom-memoria engine bundle (the s34 overworld override).",
            ("world map", "worldmap")),
    Concept("prop", "Prop",
            "A piece of set dressing on a field — a chest, tent, barrel, or sign. A model in a fixed pose with "
            "no behaviour of its own.",
            "authored via [[prop]].",
            ("props",)),
    Concept("savepoint", "Save point",
            "A spot on a field that opens the save menu (with an optional moogle). Saving on your field and "
            "reloading back into it works.",
            "authored via [[savepoint]]; Menu(4,0) + a region.",
            ("save point", "save points")),
    Concept("ate", "ATE (Active Time Event)",
            "FF9's optional 'Press SELECT' side-scenes. Most of an ATE lives in the field's own script, so a "
            "faithful fork brings it along.",
            "field-.eb data: a GetChoose + jump table.",
            ("ates", "active time event")),
    Concept("bbg", "Battle background (BBG)",
            "The 3D scene a battle plays out in. You can reskin one, rebuild its geometry, or make a new one — "
            "no engine changes needed.",
            "BBG_B###; tuned alongside the fight and camera.",
            ("battle background", "battle backgrounds")),
]

CONCEPTS = {c.term: c for c in _CARDS}

# a flat lookup of every key/alias -> canonical term, for cheap resolution
_INDEX = {}
for _c in _CARDS:
    _INDEX[_c.term] = _c.term
    for _a in _c.aliases:
        _INDEX.setdefault(_a.lower(), _c.term)


def all_concepts():
    """The cards in registry (roughly newcomer-first) order."""
    return list(_CARDS)


def get(term):
    """The :class:`Concept` for a canonical ``term`` (or ``None``)."""
    return CONCEPTS.get(term)


def resolve(query):
    """Best-effort resolve a free-text ``query`` to a :class:`Concept`: exact term/alias first, then a
    substring match against a term/alias/title. ``None`` if nothing plausible. Case-insensitive."""
    if not query:
        return None
    q = str(query).strip().lower()
    if q in _INDEX:
        return CONCEPTS[_INDEX[q]]
    # substring: the query contains a key, or a key contains the query (>=3 chars to avoid noise)
    for key, term in _INDEX.items():
        if len(key) >= 3 and (key in q or (len(q) >= 3 and q in key)):
            return CONCEPTS[term]
    for c in _CARDS:
        if len(q) >= 3 and q in c.title.lower():
            return c
    return None
