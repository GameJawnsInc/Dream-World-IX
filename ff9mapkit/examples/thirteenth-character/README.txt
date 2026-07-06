THE 13th PLAYABLE CHARACTER — in-game proof recipe
==================================================

What this proves: a genuine NEW engine CharacterId (id 12) — a party member ALONGSIDE all 12 canon
characters — authored purely as data (CSV rows + a DictionaryPatch name + a minted model + field
bytecode), ZERO DLL. "Iviv" is its OWN roster slot with its OWN name, stats, and — with
custom_battle_model = true — its OWN independent battle model.

The whole character is one block in iviv.field.toml:

    [[playable]]
    name = "Iviv"
    borrow = "vivi"             # clone Vivi's stats / command kit as the starting point
    recruit = true              # join the party at field load
    custom_battle_model = true  # mint an INDEPENDENT, editable copy of Vivi's battle model, bound to Iviv
    custom_battle_anims = true  # ALSO give that model its OWN independent, editable battle ANIMSET
    stats = { magic = 40 }

custom_battle_model mints Vivi's battle model as a NEW GEO (id 6100, GEO_MAIN_B0_M100) at
Models/2/6100/, gives Iviv its own CharacterSerialNumber (19) + BattleParameters row using that GEO,
and reuses Vivi's battle animations (they bind by bone name). So Iviv starts looking like Vivi but is a
SEPARATE model — reshape/recolor Models/2/6100/6100.fbx in Blender (ff9mapkit model-gltf 6100 -> edit ->
model-import) to make it truly yours, and Vivi (id 5415) is never touched.

custom_battle_anims goes one step further: the 34 battle motions (idle / attack / cast / hit / ...) are
attached BY NAME, and a name's own token decides which folder its clip loads from — so simply reusing
Vivi's names would share Vivi's clips (editing them would change Vivi too). With this flag the kit ships
faithful copies of Vivi's 34 clips under Iviv's OWN model — Animations/6100/<key>.anim — and registers
them (3DModelAnimation lines) + re-points Iviv's BattleParameters row to the new names. They play
identically to Vivi UNTIL you edit them; editing any Animations/6100/*.anim (or the Blender clip loop)
changes only Iviv. Vivi's own Animations/5415/ is never written. (Trance animations stay shared in v1.)

    Proving a UNIQUE pose (after the deploy + a battle works): edit one shipped clip in the LIVE mod, e.g.
    <game>\FF9CustomMap\StreamingAssets\Assets\Resources\Animations\6100\<key>.anim — exaggerate a bone's
    rotation in the JSON — then RELAUNCH and fight. Iviv's motion differs; Vivi's is unchanged. (A
    first-class "edit in Blender, deploy to Iviv" retarget loop is the next increment.)

DEPLOY
------
From the repo root:

    py tools/deploy_field.py ff9mapkit/examples/thirteenth-character/iviv.field.toml

(That sandboxes the field into your test slot — default 4003 — and copies the id-12 BaseStats.csv +
CharacterParameters.csv + CommandSets.csv + BattleParameters.csv, the CharacterDefaultName lines, the
minted Models/2/6100/ FBX, and — with custom_battle_anims — the Animations/6100/ clips + their
3DModelAnimation lines, all reversibly. The 3DModel/3DModelAnimation registrations are read at LAUNCH,
so the animset needs a relaunch to take effect, same as the model itself.)

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
