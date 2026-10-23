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

## 3. On a world-map battle, the guest's monsters looked smaller — OPEN, not obvious

- Reported after the first sitting. No log covers it: the host's Memoria.log is still the 21:16 one, so the
  battle ran in a session whose log was not kept, and the guest's log is on the laptop.
- Enemy size is not fixed per model. Defaults are 4096 (`btl_init.cs:194/362`); an enemy's battle AI script can
  set its own size at load (`btl_scrp.cs` member 55: during PHASE_ENTER it becomes `geo_scale_default`).
- Ruled out:
  - **The guest skipping that script.** The diorama gates only member 37 (change next field) in `btl_scrp`; the
    load-time size write runs on the guest as on the host.
  - **The replay shrinking units.** `NetSyncDiorama.Replay.cs` snapshots `geo_scale_*` before a replayed action
    and restores the same values after, so it puts back what was there.
  - **A mod patch.** No BattlePatch line in the host's mod folders touches size or scale.
- Next discriminants, cheapest first: is the whole scene smaller (a camera difference) or only the monsters? Do
  field battles show it, or only world-map ones? Which enemies, and where on the world map? And the guest's
  `Memoria.log` from the laptop, archived before its next launch overwrites it.

## 2. The host followed its guest: a 250 <-> 350 ping-pong — a real co-op bug

- 21:02:31: the Workspace's "Apply play style" wrote `FollowHost=1` on the HOST (`followHost=1 role=host`).
- 21:09:10-21:10:16: the host logged `following the peer to field 250` / `350` every ~2.5 s. Both games chased
  each other until the host turned co-op off and on again, which re-ran `coop host` and that forces `FollowHost=0`.
- Root cause, both layers:
  - The engine's `FollowHostTick` (NetSyncClient.cs) gates on `_followHost` only, never on the role.
  - The kit knows this. `coop.py` says "FollowHost fires regardless of role" and forces 0 in `coop host`, but
    `CoopDoc.apply_playstyle` writes the checkbox's value with no role check. That makes a law with one
    enforcement site out of two.
