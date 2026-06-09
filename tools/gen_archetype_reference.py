#!/usr/bin/env python3
"""Generate ff9mapkit/docs/ARCHETYPES.md -- the human-readable archetype reference.

For every named archetype: its primary name + aliases (from archetypes.py, insertion order = primary
first), the GEO model it places, a one-line ROLE (curated below, from the in-game gallery loop), and
WHERE it appears in FF9 (real fields, from the model_field_usage index). Re-run after naming new
archetypes:  py tools/gen_archetype_reference.py

Locations are a snapshot from the user's own install (model_field_usage scans p0data field scripts);
the doc holds only field ids + manifest location NAMES (the same provenance-clean reference metadata as
reference/field-manifest.tsv), never game bytes.
"""
import os
import sys
from collections import OrderedDict
from pathlib import Path

KIT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "ff9mapkit"))
sys.path.insert(0, KIT)
from ff9mapkit import archetypes as AR
from ff9mapkit import catalog as C
from ff9mapkit import prop_archetypes as PPA

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import model_field_usage as _mfu          # model id -> [field locations]

OUT = Path(KIT) / "docs" / "ARCHETYPES.md"

# token -> one-line role (curated from the gallery identification loop). Covers every named archetype.
ROLE = {
    # -- playable cast --
    "ZID": "Zidane Tribal -- keeps the cloned player's model + animations",
    "VIV": "Vivi Ornitier, the black mage",
    "GRN": "Princess Garnet / Dagger",
    "STN": "Adelbert Steiner",
    "FRJ": "Freya Crescent",
    "KUI": "Quina Quen",
    "EIK": "Eiko Carol",
    "SLM": "Amarant Coral",
    # -- main-character alt-forms --
    "ZDN": "Zidane's own field model, placed as an NPC (vs the cloned-player `zidane`)",
    "STD": "Steiner carrying Princess Garnet (Evil Forest)",
    "ZDD": "Zidane carrying Princess Garnet",
    # -- townsfolk & workers --
    "APF": "a generic adult townswoman",
    "APM": "a generic adult townsman",
    "HUM": "a generic adult man",
    "HEK": "a commoner / alleyway local (JP heikin = average)",
    "BAR": "a tavern bartender",
    "COK": "a cook",
    "WRK": "a worker / laborer (e.g. Dante the Alexandria signmaker)",
    "CSM": "a Lindblum townsman",
    "CLM": "a Cleyran maiden",
    "TMF": "an Alexandria townswoman (e.g. Hippaul's mother)",
    "TMM": "an Alexandria townsman / the inn keeper (\"Fish Man\")",
    "GUD": "an Alexandria tour guide",
    "ORC": "the Treno auction-house auctioneer",
    "OSC": "an Alexandria Castle scholar",
    "TCK": "the play's ticketmaster (TiCKet)",
    "CSA": "a Lindblum engineer (e.g. Zebolt)",
    # -- children & elders --
    "TBY": "a little boy -- the Alexandria kid who plays tag (Tag BoY)",
    "TGR": "a little girl -- chases the tag boy (Tag GiRl)",
    "KAC": "an Alexandria child (e.g. Hippaul)",
    "DAC": "a Dali boy",
    "DAF": "a Dali girl",
    "BUC": "a Burmecian child",
    "BBA": "an old woman / granny (JP baba)",
    "JJY": "an old man / grandpa (JP jijii)",
    # -- nobility --
    "G16": "a Treno / Lindblum nobleman (gentleman)",
    "G17": "a noblewoman",
    "G18": "a nobleman (variant)",
    "G19": "Queen Stella, a named Treno noble",
    "G20": "an aristocrat (nobleman variant)",
    "TRF": "a noble's servant (e.g. Queen Stella's, in Treno)",
    # -- soldiers & guards --
    "CSO": "an armed Lindblum guard / soldier",
    "OFF": "an Alexandrian soldier (female)",
    "RAS": "a Burmecian soldier (Gizamaluke's bell guards)",
    "HTH": "a bandit / thief (JP heikin thief)",
    # -- clergy & oracles --
    "NAN": "an Esto Gaza bishop",
    "CLD": "a Cleyran high priest (JP daikanshu)",
    "FLS": "a Cleyran Sand Oracle (priestess)",
    "DOK": "a dwarven priest (JP okashira = chief)",
    # -- mages --
    "BMG": "a black mage",
    "RMF": "a Red Mage (female)",
    "RMM": "a Red Mage (male)",
    # -- theater & rogues --
    "STR": "Lowell, the famous theater star (STaR)",
    "HUF": "a Lowell fan-club member (a woman)",
    "BND": "the Prima Vista's band conductor (BaND)",
    "RTC": "Puck, the Burmecian boy-thief (JP \"Rat Child\")",
    # -- regional & racial types --
    "BUF": "a Burmecian woman",
    "FUK": "the King of Burmecia (dev joke: FUkkatsu)",
    "DOC": "a Conde Petie dwarf (\"Rally-ho!\")",
    "DOF": "a dwarf woman",
    "DOM": "a dwarf man",
    "DAL": "a Dali townsman",
    "DAW": "a Dali townswoman / worker",
    # -- animals & creatures --
    "CAT": "a cat",
    "DOG": "a dog",
    "CCB": "a small bird (pigeon-ish)",
    "FRM": "the catchable marsh frog",
    "TAD": "a tadpole (Qu's Marsh)",
    "BRI": "an Oglop, the little bug-creature (JP burimushi)",
    "CHO": "a chocobo",
    "CHC": "a chocobo chick",
    "CHD": "the Fat Chocobo (JP Choco Debu)",
    "MOG": "a moogle, the iconic messenger critter",
    # -- SUB group: the named story cast --
    "BAK": "Baku, Tantalus' boss",
    "BLN": "Blank, Tantalus thief (Zidane's friend)",
    "MRC": "Marcus, Tantalus thief",
    "CNA": "Cinna, Tantalus thief",
    "RBY": "Ruby, Tantalus' actress",
    "ZNR": "Zenero, a Tantalus Nero-family member (tentative)",
    "BRN": "Queen Brahne of Alexandria",
    "BTX": "General Beatrix of Alexandria",
    "KJA": "Kuja, the antagonist",
    "ZON": "Zorn, Brahne's jester (paired with Thorn)",
    "SBW": "Lani, the bounty hunter (JP \"Scarlet Bounty Woman\")",
    "SSB": "a Knight of Pluto -- a male Alexandrian soldier (e.g. Haagen, Weimar)",
    "GRL": "Garland of Terra",
    "CID": "Regent Cid Fabool IX of Lindblum",
    "FLT": "Sir Fratley, Burmecian Dragon Knight (JP Furattorei)",
    "TOT": "Doctor Tot, the Treno scholar",
    "BW1": "Black Waltz No. 1",
    "BW3": "Black Waltz No. 3",
    "CDW": "Hilda, Cid's wife",
    "KUT": "Quale, Quina's master (Qu's Marsh)",
    "KUW": "Quan, Vivi's grandfather",
    "MOM": "the woman in Garnet's Memoria recollection (likely her birth mother)",
    "NTC": "a genome -- the roaming Terra one (normal stand/walk)",
    "NTA": "a Bran Bal genome (posed idle)",
    "NTB": "a Bran Bal genome (posed idle)",
    "NTD": "a Bran Bal genome (posed idle)",
}

# thematic quick-pick nav (primary names). Validated against the live archetype set below.
THEMES = OrderedDict([
    ("Party (as NPCs)", ["zidane", "vivi", "garnet", "steiner", "freya", "quina", "eiko", "amarant"]),
    ("Townsfolk & workers", ["townswoman", "townsman", "human_male", "commoner", "alexandria_woman",
                             "innkeeper", "lindblum_man", "cleyran_woman", "worker", "cook", "bartender"]),
    ("Shops & services", ["bartender", "cook", "innkeeper", "auctioneer", "ticket_master",
                          "tour_guide", "scholar", "engineer"]),
    ("Children & elders", ["little_boy", "little_girl", "alexandria_child", "dali_boy", "dali_girl",
                           "burmecian_child", "chocobo_child", "granny", "grandpa"]),
    ("Nobility", ["gentleman", "noblewoman", "noble_man", "aristocrat", "queen_stella", "servant"]),
    ("Soldiers & clergy", ["guard", "alexandria_soldier", "burmecian_soldier", "bishop", "high_priest",
                           "sand_oracle", "dwarf_priest"]),
    ("Mages", ["black_mage", "red_mage_man", "red_mage_woman"]),
    ("Theater & rogues", ["lowell", "fan_club_member", "conductor", "puck", "bandit"]),
    ("Burmecia", ["burmecian_child", "burmecian_woman", "burmecian_soldier", "burmecian_king", "puck"]),
    ("Conde Petie (dwarves)", ["dwarf", "dwarf_woman", "dwarf_man", "dwarf_priest"]),
    ("Dali", ["dali_boy", "dali_girl", "dali_man", "dali_woman"]),
    ("Animals & creatures", ["cat", "dog", "bird", "frog", "tadpole", "oglop",
                             "chocobo", "chocobo_child", "fat_chocobo", "moogle"]),
    ("Story cast (named)", ["beatrix", "kuja", "garland", "brahne", "cid", "fratley", "doctor_tot",
                            "zorn", "lani", "baku", "blank", "marcus", "cinna", "ruby", "genome",
                            "quan", "quale", "hilda", "pluto_knight"]),
])

# named characters -> archetype, for a quick index
NAMED = ["zidane", "vivi", "garnet", "steiner", "freya", "quina", "eiko", "amarant",
         "puck", "lowell", "dante", "hippaul", "zebolt", "stella", "fish_man", "hippauls_mom"]


def _clean(s: str) -> str:
    return s.encode("ascii", "ignore").decode().strip()


def group_archetypes():
    """[(token, geo_name|None, [primary, *aliases], mid|None)] in archetypes.py insertion order,
    one row per model (aliases folded in). zidane (cloned player, no model) leads."""
    groups = OrderedDict()

    def add(key, mid, token, geo, name):
        g = groups.setdefault(key, {"mid": mid, "token": token, "geo": geo, "names": []})
        g["names"].append(name)

    # vivi/zidane live outside ARCHETYPES (they're byte-golden character presets)
    vmid = C.resolve_model("GEO_MAIN_F0_VIV")
    add("zidane", None, "ZID", None, "zidane")
    add(vmid, vmid, C.model(vmid).token, C.model(vmid).name, "vivi")
    for name, spec in AR.ARCHETYPES.items():
        mid = C.resolve_model(spec["model"])
        m = C.model(mid)
        add(mid, mid, m.token, m.name, name)
    return [(g["token"], g["geo"], g["names"], g["mid"]) for g in groups.values()]


def where(mid):
    if mid is None:
        return "(spawns as the player)"
    rows, total = _mfu.usage(mid, limit=8)
    seen, examples = set(), []
    for _fid, nm in rows:
        nm = _clean(nm)
        if nm and nm not in seen:
            seen.add(nm)
            examples.append(nm)
        if len(examples) == 3:
            break
    if not total:
        return "(not placed by any field script)"
    return f"{'; '.join(examples)} -- {total} field" + ("s" if total != 1 else "")


def main():
    rows = group_archetypes()
    # split playable cast (GEO_MAIN) / story cast (GEO_SUB) / generic NPC types (GEO_NPC)
    CAST = {"ZID", "VIV", "GRN", "STN", "FRJ", "KUI", "EIK", "SLM", "ZDN", "STD", "ZDD"}
    is_sub = lambda r: bool(r[1]) and "_SUB_" in r[1]
    cast = [r for r in rows if r[0] in CAST]
    story = sorted((r for r in rows if is_sub(r)), key=lambda r: r[2][0])
    npcs = sorted((r for r in rows if r[0] not in CAST and not is_sub(r)), key=lambda r: r[2][0])

    # validate THEMES / NAMED reference only real archetypes
    allnames = set(AR.names())
    for theme, ns in THEMES.items():
        bad = [n for n in ns if n not in allnames]
        assert not bad, f"THEMES[{theme!r}] has unknown names: {bad}"
    assert all(n in allnames for n in NAMED), [n for n in NAMED if n not in allnames]

    L = []
    L.append("# FF9 NPC archetype reference\n")
    L.append("> Generated by `tools/gen_archetype_reference.py` -- do not hand-edit. "
             "Regenerate after naming new archetypes.\n")
    L.append("Every entry below places a working field NPC with **one word**:\n")
    L.append("```toml\n[[npc]]\nname = \"Vivi\"\narchetype = \"black_mage\"   # model + animations auto-resolve\n"
             "pos = [120, 150]\ndialogue = \"...\"\n```\n")
    L.append("`archetype` (alias: `preset`) maps a friendly name to a GEO model whose five movement "
             "gestures (stand / walk / run / turn-left / turn-right) auto-resolve from the catalog -- "
             "no `anims` needed. Prefer a name here; for any model not curated, place it directly with "
             "`model = \"GEO_NPC_F0_XXX\"` (browse `ff9mapkit models`). The set below is **complete**: "
             "every field-NPC model with a full gesture set is named, plus the named **story cast** "
             "(the `SUB` models -- Beatrix, Kuja, the Tantalus crew, ...).\n")
    L.append(f"**{len(AR.names())} names** covering **{len(rows)} models**. "
             "\"Appears in\" lists a few real fields that place the model (snapshot from this install).\n")

    # quick-pick nav
    L.append("## Browse by theme\n")
    for theme, ns in THEMES.items():
        L.append(f"- **{theme}:** " + ", ".join(f"`{n}`" for n in ns))
    L.append("")

    # playable cast
    L.append("## Playable cast\n")
    L.append("Place a party member as a field NPC. (`zidane` keeps the cloned player; the rest resolve "
             "their own model + auto-anims.)\n")
    L.append("| Archetype | Aliases | Model | Role |")
    L.append("|---|---|---|---|")
    castorder = {t: i for i, t in enumerate(["ZID", "VIV", "GRN", "STN", "FRJ", "KUI", "EIK", "SLM",
                                             "ZDN", "ZDD", "STD"])}
    for token, geo, names, _mid in sorted(cast, key=lambda r: castorder.get(r[0], 99)):
        primary, aliases = names[0], names[1:]
        model = geo or "(cloned player)"
        L.append(f"| `{primary}` | {', '.join(f'`{a}`' for a in aliases) or '--'} | `{model}` "
                 f"| {ROLE.get(token, '')} |")
    L.append("")

    # npc types
    L.append("## NPC types\n")
    L.append("| Archetype | Aliases | Model | Role | Appears in |")
    L.append("|---|---|---|---|---|")
    for token, geo, names, mid in npcs:
        primary, aliases = names[0], names[1:]
        L.append(f"| `{primary}` | {', '.join(f'`{a}`' for a in aliases) or '--'} | `{geo}` "
                 f"| {ROLE.get(token, '')} | {where(mid)} |")
    L.append("")

    # story cast (SUB group)
    L.append("## Story cast\n")
    L.append("The named characters (the `SUB` models) -- place a specific story figure; same "
             "model->anim auto-resolve as an NPC. (Black Waltz No. 2 and Trance Kuja are special boss "
             "models with no standard idle/walk, so they're not archetypes -- place by raw model id.)\n")
    L.append("| Archetype | Aliases | Model | Role | Appears in |")
    L.append("|---|---|---|---|---|")
    for token, geo, names, mid in story:
        primary, aliases = names[0], names[1:]
        L.append(f"| `{primary}` | {', '.join(f'`{a}`' for a in aliases) or '--'} | `{geo}` "
                 f"| {ROLE.get(token, '')} | {where(mid)} |")
    L.append("")

    # props (set dressing)
    L.append("## Props (set dressing)\n")
    L.append("Static set pieces placed with `[[prop]] prop = \"chest\"` (or `model = \"GEO_ACC_F0_...\"` "
             "+ `pose`). NOT characters -- no head-tracking; each holds its canonical pose (baked from "
             f"shipping fields). {len(PPA.names())} names.\n")
    L.append("| Prop | Aliases | Model | Appears in |")
    L.append("|---|---|---|---|")
    pgroups = OrderedDict()
    for nm, spec in PPA.PROP_ARCHETYPES.items():
        pgroups.setdefault(C.resolve_model(spec["model"]), []).append(nm)
    for mid, pnames in pgroups.items():
        L.append(f"| `{pnames[0]}` | {', '.join(f'`{a}`' for a in pnames[1:]) or '--'} "
                 f"| `{C.model(mid).name}` | {where(mid)} |")
    L.append("")

    # creatures (bestiary)
    L.append("## Creatures (bestiary)\n")
    cgroups = OrderedDict()
    for nm, spec in AR.CREATURES.items():
        cgroups.setdefault(C.resolve_model(spec["model"]), []).append(nm)
    L.append("Battle MONSTERS placed as field objects with `[[npc]] archetype = \"zaghnol\"`. "
             f"{len(cgroups)} `GEO_MON` models verified IN-GAME to render + animate as field objects (the "
             "arena gallery). Most also appear in shipping field scripts (the **Appears in** column); a few "
             "are battle bosses the kit can still place. Token decodes + JP origins in the source.\n")
    L.append("| Creature | Aliases | Model | Appears in |")
    L.append("|---|---|---|---|")
    for mid, cnames in cgroups.items():
        L.append(f"| `{cnames[0]}` | {', '.join(f'`{a}`' for a in cnames[1:]) or '--'} "
                 f"| `{C.model(mid).name}` | {where(mid)} |")
    L.append("")

    # named-character index
    L.append("## Named characters\n")
    L.append("Several archetypes carry a specific character's name as an alias (the model is reused "
             "across many NPCs, so the role is the generic one):\n")
    for n in NAMED:
        mid = AR.resolve(n)[0]
        geo = C.model(mid).name if mid is not None else "(cloned player)"
        L.append(f"- `{n}` -> `{geo}`")
    L.append("")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(L), encoding="utf-8")
    print(f"wrote {OUT}  ({len(AR.names())} names, {len(rows)} models)")


if __name__ == "__main__":
    main()
