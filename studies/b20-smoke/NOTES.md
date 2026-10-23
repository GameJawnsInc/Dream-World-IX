# b20 two-PC smoke test — notes

The engine under test is the b20 bundle `dwix-custom-memoria-1.0.0b20.zip` (sha `0d46b956eedd2ee8`). It was
installed on the host PC on 2026-10-22, and its files byte-match the zip. The host's logs from the first sitting
are in `logs/`.

## 1. Black screen after the host quit to title and loaded another save — NOT a co-op or engine bug

- What happened: the host quit to title at 21:15:24 and the guest showed "The Host is away", as designed. The host
  then loaded a different save and got a black screen, with the menu's location still reading field 312's.
- Cause: `output_log.txt` shows `KeyNotFoundException` in `HonoluluFieldMain.HonoAwake`. Its first line is
  `eventIDToMESID[fldMapNo]`, a stock Memoria lookup, which throws when the save's field id is not registered on
  this install. No `Map:` line follows in Memoria.log, so the field never started. The menu location is
  `fldLocNo`, which is assigned on that same line, so it still held 312's value.
- The save file's field id is the Int16 at offset 9 of each decrypted `SavedData_ww.dat` block. It reads 312 in
  the 21:15 autosave. Slots whose field is not registered by any folder in `FolderNames`:
  slot 2 saves 1-5 (6099, 6133, 6167, 6007, 6094: old journey forks), slot 3 saves 1-2 (4005),
  slot 4 saves 1-4 (7202, 30102), and slot 5 save 2 (7202). The autosave (312), slot 1 (1425, 1865),
  slot 3 save 3 and slot 5 save 1 are real fields and load.
- Stock Memoria behaves the same for any save made on a mod field that has since been removed.

## 3. The guest's spiders were half size — ROOT CAUSE FOUND; the fix needs an engine round (kept for b20)

- Owner: only the monsters (not the camera), Carve Spiders outside Dali, the only fight of the sitting. The
  guest's log (`logs/guest-memoria-20261022-2117.log`) puts it at 21:13:51 on **field 450 (Dali/Field)**, not the
  world map: `diorama BOOT scene=245 pattern=4`. Scene 245 is `BSC_WM_0104`, a world-map formation (Python + Carve
  Spider) that field 450 reuses.
- Enemy size is not fixed per model. It defaults to 4096 (`btl_init.cs:194/362`), and the scene's battle AI script
  resizes its enemies: each type's Main (tag 1) loops until `B_SYSVAR[40] & 8` (`btl_load_status` LOAD_INITNPC,
  set at `btl_init.cs:96`), then writes member 55. **Carve Spider -> 8192 (2x), Python -> 5120.** Their Reaction
  functions also resize them (2560/5120, 4096/8192).
- **The guest never runs battle scripts at all.** The diorama boots with `FF9StateSystem.Battle.isDebug` on, and
  every `EventEngine.ServiceEvents()` call in a battle is gated `!isDebug` (`battle.cs:73/178`,
  `HonoluluBattleMain.cs:744`). So the guest's spiders stay at 4096: half the host's.
- The earlier "ruled out" was wrong about the first item: the size write does not run on the guest. The other two
  hold (the replay restores snapshot values; no mod patch touches size).
- Class, not one scene: any enemy whose AI script sets its own size, at load or in a Reaction, is wrong on the
  guest. The wire carries no `geo_scale`, so no guest-side switch can fix it.
- Fix shape (an engine round, its own patch): the host ships each enemy's `geo_scale_x/y/z` in its battle frames,
  and the guest applies it with `geo.geoScaleSetXYZ` when it differs (the Replay snapshot must then restore the
  wire value, not a stale pre-replay one). That is a wire change, so a protocol bump, a rebuilt bundle and a
  two-PC retest.

## 2. The host followed its guest: a 250 <-> 350 ping-pong — a real co-op bug

- 21:02:31: the Workspace's "Apply play style" wrote `FollowHost=1` on the HOST (`followHost=1 role=host`).
- 21:09:10-21:10:16: the host logged `following the peer to field 250` / `350` every ~2.5 s. Both games chased
  each other until the host turned co-op off and on again, which re-ran `coop host` and that forces `FollowHost=0`.
- Root cause, both layers:
  - The engine's `FollowHostTick` (NetSyncClient.cs) gates on `_followHost` only, never on the role.
  - The kit knows this. `coop.py` says "FollowHost fires regardless of role" and forces 0 in `coop host`, but
    `CoopDoc.apply_playstyle` writes the checkbox's value with no role check. That makes a law with one
    enforcement site out of two.
