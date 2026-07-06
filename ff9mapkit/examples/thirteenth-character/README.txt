THE 13th PLAYABLE CHARACTER — in-game proof recipe
==================================================

What this proves: a genuine NEW engine CharacterId (id 12) — a party member ALONGSIDE all 12 canon
characters — authored purely as data (CSV rows + a DictionaryPatch name + field bytecode), ZERO DLL.
"Iviv" borrows Vivi's battle model / Black-Magic kit / mage stats (a truly custom MODEL is the separate
custom-models pillar), but is its OWN roster slot with its OWN name and stats.

The whole character is one block in iviv.field.toml:

    [[playable]]
    name = "Iviv"
    borrow = "vivi"
    recruit = true
    stats = { magic = 40 }

DEPLOY
------
From the repo root:

    py tools/deploy_field.py ff9mapkit/examples/thirteenth-character/iviv.field.toml

(That sandboxes the field into your test slot — default 4003 — and copies the id-12 BaseStats.csv +
CharacterParameters.csv + CommandSets.csv and the CharacterDefaultName lines into your live mod folder,
all reversibly.)

TEST (the order matters)
------------------------
1. RELAUNCH FF9. The new CharacterParameters/BaseStats rows and the CharacterDefaultName directive load
   at STARTUP / New-Game init — F6 "Reload field" will NOT pick them up (it only re-reads the field's
   .eb/.mes/scene/walkmesh). deploy_field prints a "RELAUNCH to apply" reminder for exactly this.
2. NEW GAME. The engine builds the party with id-12 present (FF9Play_Init allocates a PLAYER for every
   loaded CharacterParameters row, so shipping an Id=12 row is what brings Iviv into existence).
3. F6 -> "Warp to field" -> your test slot (4003). Main_Init runs B_PARTYADD(12) on load -> Iviv joins.

VERIFY (the three proofs)
-------------------------
A. APPEARS  — open the party menu. Iviv is its OWN member (Vivi's look, the name "Iviv", Magic 40).
              Open Equip/Status/Ability on Iviv — all should render.
B. FIGHTS   — walk around; this room has random battles (Evil Forest, weak). Iviv fights in the ATB
              line with its own name + commands.
C. SAVES    — step on the save point (the "!" bubble), Save, then reload that save from the title.
              Iviv must still be in the party (it persists via Memoria's MemoriaExtraData block).

DO NOT open the in-game name-entry / rename screen for Iviv — that engine screen has a hardcoded < 12
reseed that would overwrite Zidane's name (a documented caveat; the name comes from the DictionaryPatch,
so there is no reason to open it). In FIELDS the engine renders only the party LEADER, so Iviv shows in
the MENU and BATTLE, not as a walking follower — that is expected, not a bug.

If any step fails, capture a few seconds of video of the failing step and report it — that is the fastest
way to pinpoint a coordinate/UI issue.

REVERT
------
    py tools/scroll_out/revert_deploy.py        (latest deploy)   — or the per-id revert_deploy_<id>.py
