"""FF9 item id <-> name, baked from Memoria's open-source ``RegularItem`` enum (Memoria.Data) -- NOT
game data (it's the same id table Memoria publishes in source; see docs/PROVENANCE.md). Used by
:mod:`ff9mapkit.items` so authors can write ``give_item = ["Potion", 1]`` instead of memorizing 236.

Regenerate from a Memoria checkout by transcribing
``Memoria/Assembly-CSharp/Memoria/Data/Battle/RegularItem.cs``.
"""

from __future__ import annotations

# id -> canonical PascalCase name (weapons 0-87, armor/add-ons 88-223, gems 224-235, items 236-254).
ITEMS = {
    0: "Hammer", 1: "Dagger", 2: "MageMasher", 3: "MythrilDagger", 4: "Gladius", 5: "ZorlinShape",
    6: "Orichalcon", 7: "ButterflySword", 8: "TheOgre", 9: "Exploda", 10: "RuneTooth",
    11: "AngelBless", 12: "Sargatanas", 13: "Masamune", 14: "TheTower", 15: "UltimaWeapon",
    16: "Broadsword", 17: "IronSword", 18: "MythrilSword", 19: "BloodSword", 20: "IceBrand",
    21: "CoralSword", 22: "DiamondSword", 23: "FlameSaber", 24: "RuneBlade", 25: "Defender",
    26: "SaveTheQueen", 27: "UltimaSword", 28: "Excalibur", 29: "Ragnarok", 30: "ExcaliburII",
    31: "Javelin", 32: "MythrilSpear", 33: "Partisan", 34: "IceLance", 35: "Trident",
    36: "HeavyLance", 37: "Obelisk", 38: "HolyLance", 39: "KainLance", 40: "DragonHair",
    41: "CatClaws", 42: "PoisonKnuckles", 43: "MythrilClaws", 44: "ScissorFangs", 45: "DragonClaws",
    46: "TigerFangs", 47: "Avenger", 48: "KaiserKnuckles", 49: "DuelClaws", 50: "RuneClaws",
    51: "AirRacket", 52: "MultinaRacket", 53: "MagicRacket", 54: "MythrilRacket", 55: "PriestRacket",
    56: "TigerRacket", 57: "Rod", 58: "MythrilRod", 59: "StardustRod", 60: "HealingRod",
    61: "AsuraRod", 62: "WizardRod", 63: "WhaleWhisker", 64: "GolemFlute", 65: "LamiaFlute",
    66: "FairyFlute", 67: "Hamelin", 68: "SirenFlute", 69: "AngelFlute", 70: "MageStaff",
    71: "FlameStaff", 72: "IceStaff", 73: "LightningStaff", 74: "OakStaff", 75: "CypressPile",
    76: "OctagonRod", 77: "HighMageStaff", 78: "MaceOfZeus", 79: "Fork", 80: "NeedleFork",
    81: "MythrilFork", 82: "SilverFork", 83: "BistroFork", 84: "GastroFork", 85: "Pinwheel",
    86: "RisingSun", 87: "WingEdge", 88: "Wrist", 89: "LeatherWrist", 90: "GlassArmlet",
    91: "BoneWrist", 92: "MythrilArmlet", 93: "MagicArmlet", 94: "ChimeraArmlet", 95: "EgoistArmlet",
    96: "NKaiArmlet", 97: "JadeArmlet", 98: "ThiefGloves", 99: "DragonWrist", 100: "PowerWrist",
    101: "Bracer", 102: "BronzeGloves", 103: "SilverGloves", 104: "MythrilGloves",
    105: "ThunderGloves", 106: "DiamondGloves", 107: "VenetiaShield", 108: "DefenseGloves",
    109: "GenjiGloves", 110: "AegisGloves", 111: "Gauntlets", 112: "LeatherHat", 113: "StrawHat",
    114: "FeatherHat", 115: "SteepledHat", 116: "Headgear", 117: "MagusHat", 118: "Bandana",
    119: "MageHat", 120: "LamiaTiara", 121: "RitualHat", 122: "TwistHeadband", 123: "MantraBand",
    124: "DarkHat", 125: "GreenBeret", 126: "BlackHood", 127: "RedHat", 128: "GoldenHairpin",
    129: "Coronet", 130: "FlashHat", 131: "AdamanHat", 132: "ThiefHat", 133: "HolyMiter",
    134: "GoldenSkullcap", 135: "Circlet", 136: "RubberHelm", 137: "BronzeHelm", 138: "IronHelm",
    139: "Barbut", 140: "MythrilHelm", 141: "GoldHelm", 142: "CrossHelm", 143: "DiamondHelm",
    144: "PlatinumHelm", 145: "KaiserHelm", 146: "GenjiHelmet", 147: "GrandHelm", 148: "AlohaTshirt",
    149: "LeatherShirt", 150: "SilkShirt", 151: "LeatherPlate", 152: "BronzeVest", 153: "ChainPlate",
    154: "MythrilVest", 155: "AdamanVest", 156: "MagicianCloak", 157: "SurvivalVest",
    158: "Brigandine", 159: "JudoUniform", 160: "PowerVest", 161: "GaiaGear", 162: "DemonVest",
    163: "MinervaPlate", 164: "NinjaGear", 165: "DarkGear", 166: "RubberSuit", 167: "BraveSuit",
    168: "CottonRobe", 169: "SilkRobe", 170: "MagicianRobe", 171: "GluttonRobe", 172: "WhiteRobe",
    173: "BlackRobe", 174: "LightRobe", 175: "RobeOfLords", 176: "TinArmor", 177: "BronzeArmor",
    178: "LinenCuirass", 179: "ChainMail", 180: "MythrilArmor", 181: "PlateMail", 182: "GoldArmor",
    183: "ShieldArmor", 184: "DemonMail", 185: "DiamondArmor", 186: "PlatinaArmor",
    187: "CarabiniMail", 188: "DragonMail", 189: "GenjiArmor", 190: "Maximillian", 191: "GrandArmor",
    192: "DesertBoots", 193: "MagicianShoes", 194: "GerminasBoots", 195: "Sandals",
    196: "FeatherBoots", 197: "BattleBoots", 198: "RunningShoes", 199: "Anklet", 200: "PowerBelt",
    201: "BlackBelt", 202: "GlassBuckle", 203: "MadainRing", 204: "RosettaRing", 205: "ReflectRing",
    206: "CoralRing", 207: "PromistRing", 208: "RebirthRing", 209: "ProtectRing", 210: "PumicePiece",
    211: "Pumice", 212: "YellowScarf", 213: "GoldChoker", 214: "FairyEarrings", 215: "AngelEarrings",
    216: "PearlRouge", 217: "PearlArmlet", 218: "Cachusha", 219: "Barette", 220: "Extension",
    221: "Ribbon", 222: "MaidenPrayer", 223: "AncientAroma", 224: "Garnet", 225: "Amethyst",
    226: "Aquamarine", 227: "Diamond", 228: "Emerald", 229: "Moonstone", 230: "Ruby", 231: "Peridot",
    232: "Sapphire", 233: "Opal", 234: "Topaz", 235: "LapisLazuli", 236: "Potion", 237: "HiPotion",
    238: "Ether", 239: "Elixir", 240: "PhoenixDown", 241: "EchoScreen", 242: "Soft", 243: "Antidote",
    244: "EyeDrops", 245: "MagicTag", 246: "Vaccine", 247: "Remedy", 248: "Annoyntment",
    249: "PhoenixPinion", 250: "DarkMatter", 251: "GysahlGreens", 252: "DeadPepper", 253: "Tent",
    254: "Ore", 255: "NoItem",
}
