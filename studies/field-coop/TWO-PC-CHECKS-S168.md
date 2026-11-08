# FF9 Co-op: laptop update package (<DATE>, s168 with s167)

<!-- Packaging (delete this comment when done). Replace every placeholder before zipping; none may remain: <DATE>, <YYYYMMDD>,
<S168_SHA16>, <S168_SHA256>, <S168_BENCH_SUMMARY>, <S167_SNAPSHOT_TS>.
HASHES.txt needs eight lines: the six "<sha256> *dlls/<arch>/<name>" lines plus "<sha256> *dlls-s167/x64/Assembly-CSharp.dll" and
"<sha256> *dlls-s167/x86/Assembly-CSharp.dll" (lowercase hex, forward slashes), or check-s168.ps1 skips them and part 0 fails.
<S167_SNAPSHOT_TS> is the timestamp of the backups/ set whose Assembly-CSharp sha256 is 12be3220520813a6..., taken before the
FIRST s168-family deploy (the W1a/b pin included), so it may not be the "revert with" timestamp the final s168 build prints.
Always a timestamp, never a label. If no such set exists, delete that sentence under "Going back to s167 or s166". -->

This session tests two things at once, both on the s168 engine (s168 contains s167 unchanged):

- **Part A, s167: the guest walks the world map.** Benched on one PC on 2026-11-06, never yet run on two PCs.
- **Part B, s168: the guest's main menu, view only.** New.

The desktop hosts and the laptop is the guest. The order: step 0 (install and check both machines, about 20 minutes), Part A
with the guest's main menu never opened (about 20 minutes), Part B (about an hour), and the version check last (about 15
minutes). About two hours in all; the optional steps add more. A video of the guest's screen helps most.

**Engine in this package:** `Assembly-CSharp.dll` `<S168_SHA16>...` (both arches; sha256 `<S168_SHA256>`). `HASHES.txt` lists
eight DLL files: the six in `dlls` and the two s167 `Assembly-CSharp.dll` in `dlls-s167` (the check reads all eight). Only
`Assembly-CSharp.dll` changed; `Memoria.Prime.dll` and `UnityEngine.UI.dll` are the same files as in the s167
package, included so the set is complete. The desktop already runs this build. The package holds s168 and everything before it
(s167 unchanged inside it), so it replaces the s167 package and every earlier one.

**The s167 engine is in the package too:** `dlls-s167\x64` and `dlls-s167\x86` hold the s167 `Assembly-CSharp.dll`
(`12be3220520813a6...`). It is for the version check at the end and for telling an s167 fault from an s168 one. Do not copy it
unless a step says so.

**The three mod folders.** s168 changes no mod folder. `FF9CustomMap-world`, `FF9CustomMap-schema` and `FF9CustomMap-msgs` are
in the package, listed file by file with their SHA256s in `FOLDERS-MANIFEST.txt`. If nothing was promoted to the desktop's
overworld since the s167 package, they are the same 2,950 files (2,779, 25 and 146). The laptop already has them, so it copies
one again only if step 0 says it differs. As before, they are the desktop's folders minus its tool backups (`*.bak-*`) and empty
`.lock` files, which the game never reads.

**The version rule.** The co-op wire stays at version 15, so an s168 game still pairs with an s167 or an s166 one. **With s167
the walk still works; only the guest's menu is off.** With s166 the pair plays s166's world map (the guest frozen), as before.
The menu needs BOTH machines on s168. With an older partner, an s168 guest's Menu press gives the buzz and, for 4 seconds:

> FF9 co-op: Your partner's co-op build is older: the shared menu stays closed.

s167's words for an s166 partner stay as they were: *"Your partner's co-op build is older: you'll follow them as before."* (on
the guest), *"Your partner's co-op build is older: they'll follow you as before."* (on the host).

**New in the package:** `check-s168.ps1`, a read-only check that compares a machine with this package (step 0); the
`dlls-s167` folder (its two files are listed in `HASHES.txt` too); and, as in s167, `DATA-WORLD-HASHES.txt` and
`FOLDERS-MANIFEST.txt`.

## What's new (s167: the guest walks)

- **The guest walks.** A following guest walks its own copy of the world map on foot, beside the host, with its own controls and
  camera, on 9002, 9010 and 9011 (the Disc 1 world maps with no vehicle; 9011 is the kit's world, with the Southern Ring). Each
  game draws the other player as a second figure. The guest never meets its own random battles while it walks. It still cannot
  save, and the host still leads: the guest rejoins the host at the host's next stop, wherever it has walked to.
- **It freezes, as in s166,** while the host rides (Choco, the boat), is in a world-map scene, a battle or a location, or the two
  world maps differ, and says why: *"Your partner is riding. You'll rejoin them at their next stop."*, *"Your partner is in a
  world-map scene. You'll rejoin them at their next stop."*, or one of the lines below. It walks again once the reason ends.
- **Entrances stay the host's.** Confirm at an entrance gives the stock buzz and, for 4 seconds:

  > FF9 co-op: Your partner leads the way. You'll join them at their next stop.

- **The minimap closes again** while the guest is frozen (Select, no buzz), and the s165 hint *"Your partner is on the world map:
  press Select for the minimap."* then stays quiet for the rest of that world-map visit.
- **The full map** opens for a walking guest on 9010 and 9011, with the host's orange dot on it. It closes by itself first if the
  host enters a location or a host world battle starts.
- **The two world maps are compared** at every world-map load (a "fingerprint"). If they differ, the guest stays frozen and both
  games say so: the guest *"Your world map differs from your partner's (<part>): you'll follow them as before."*, the host *"Your
  partner's world map differs from yours: they'll follow you as before."*. While the guest waits for the comparison it shows
  *"Checking your world map against your partner's..."*, and the host *"Your partner can't walk yet: they'll join you at your
  next stop."* can show for the same wait.
- **WorldTPS is compared.** If the two machines' `[Graphics] WorldTPS` differ, each log says so once. Keep them equal.
- **The ~ menu's Release stays.** Its hint now starts "Enter locations alone (until the next field load).".

## What's new (s168: the guest's main menu, view only)

- **The menu opens.** A guest that is following can press Menu on a field, or on the world map while on foot. The stock main
  menu opens over a copy of the host's party: the host's members, levels, HP/MP, equipment, abilities and AP, items in the host's
  order, key items and gil. While it is open, the top centre shows *"View only: your partner's game makes the changes."*
- **What you can open.** Items (with Key Items), Abilities, Equip, Status and the Folklore row (it reads Journal when the Journal
  is on). Order, Card and Config are greyed and buzz, and so is Party when that row shows. There is no Save row.
- **Changes are refused.** Anything that would change something plays that screen's stock buzz and changes nothing: equipping,
  removing, Optimize, switching a support ability, using an item or a field ability, Gysahl Greens. No line is drawn for these.
  The chip is the explanation.
- **Sorting is allowed.** Sorting items and reading key items work, but only on your copy, and they are forgotten when the menu
  closes.
- **Closing.** Cancel at the top closes the menu and puts your own party back at once. Nothing can be saved while the menu is
  open.
- **Forced closes.** The menu closes by itself, with a 4-second line, when the host:
  - leaves the field;
  - walks out to the world map, or into a location from it;
  - is on another world map than yours (your menu open on the world map);
  - starts a battle;
  - starts a conversation, chest, ATE or scene on your field;
  - goes to the title.

  It also closes this way when the session ends.
- **Refusals.** When the menu cannot open you hear the buzz and, in most cases, see a 4-second line that says why (no line with
  co-op off or while the reconnecting line is up; nothing at all with a window up).
- **Both machines need s168.** With an older partner there is no main menu, as before.
- **The host sees nothing new.** The host's line about the guest's menu comes with s169.

## What was proven, and where

- **s167**, on the desktop, on the s167 DLL (`12be3220...`), on 2026-11-06, never on two PCs: one game against a simulated host
  (the walk on 9011 and 9002, a short simulated stall, the entrance line and buzz, the minimap close and the quiet hint, the full
  map for a walker on 9010 and 9011, the words for the reasons the walk stops); two games on one PC (a 25-check run: the guest
  walked 26 u on 9011 and the host's figure of it matched its steps, the host pulled the guest in from 538 u away, a host world
  battle returned the guest at its own spot, the entrance buzz answered at four kinds of entrance); 38 more launches with the
  walk switched off reproduced s166. Never run: two machines' fingerprints compared, a real network cut while the guest walks,
  the ~ menu Release with the walk, the "Close the map" line, the hint on screen, the vehicle worlds and the quicksand.
- **s168** adds nothing to the walk itself: it widens the co-op build's version word and adds the menu data to every host frame
  (about 13 to 29 KB/s from host to guest). The engine's own offline checks of the menu, its seat and the walk all pass. On the
  desktop: <S168_BENCH_SUMMARY>. Never run on two PCs, and never against a real older partner: the steps below are the first.

Two bench checks stay red by design. Each needs a recording only you can make on this build: s167's of you walking the world
map as the host, and one more for s168's menu. Claude will ask for them separately.

## Install on the laptop (close FF9 and the Memoria launcher on both machines first)

Unzip the package anywhere outside the FF9 folder (for example the Desktop). It holds one folder,
`FF9Coop-laptop-update-<YYYYMMDD>-s168`. The desktop has the same folder on its own Desktop.

### Step 0: back up, copy, and check both machines (before any test)

1. **Back up the laptop.** Make a folder outside the FF9 folder (for example `Desktop\FF9-backup-before-s168`; it holds whatever
   the laptop runs now, s166 or s167) with two subfolders, `x64` and `x86` (the two arches' DLLs share their names), and copy:
   - `x64\FF9_Data\Managed\Assembly-CSharp.dll`, `Memoria.Prime.dll` and `UnityEngine.UI.dll` into its `x64` subfolder;
   - the same three from `x86\FF9_Data\Managed\` into its `x86` subfolder;
   - `FINAL FANTASY IX\Memoria.ini` (the one beside `Memoria.log`; ignore any `x64\Memoria.ini`) into the folder itself;
   - **new:** the save folder, `%USERPROFILE%\AppData\LocalLow\SquareEnix\FINAL FANTASY IX\Steam\EncryptedSavedData` (paste that
     into Explorer's address bar), whole, into the folder itself. On the desktop, copy its save folder (it holds save 351) to its
     Desktop too.

   Optional: to know which engine you backed up, run the check (item 4) once now on the laptop, with
   ` > check-laptop-before.txt` at the end: its engine line names it (its part-1 DIFFERS lines are expected before item 2).
2. **The DLLs:** copy the three files from the package's `dlls\x64\` into `FINAL FANTASY IX\x64\FF9_Data\Managed\`, and the
   three from `dlls\x86\` into `FINAL FANTASY IX\x86\FF9_Data\Managed\`. Copy nothing from `dlls-s167` now.
3. **Leave the mod folders alone for now.** Do not copy `FF9CustomMap-world`, `-schema` or `-msgs` unless the check below says
   one of them differs.
4. **Run the check, on BOTH machines.** With FF9 closed, open PowerShell in the folder that holds `check-s168.ps1` (Windows'
   Extract All can nest it one folder deeper; in Explorer, right-click an empty spot in that folder and choose Open in
   Terminal) and run:

   ```
   powershell -NoProfile -ExecutionPolicy Bypass -File .\check-s168.ps1
   ```

   If FF9 is not in the default Steam folder, name it:

   ```
   powershell -NoProfile -ExecutionPolicy Bypass -File .\check-s168.ps1 -Game "D:\SteamLibrary\steamapps\common\FINAL FANTASY IX"
   ```

   It changes nothing. It prints `OK` or `DIFFERS` on each line, in five parts (0 the package itself, 1 the DLLs, 2 the mod
   folders, 3 the base world data, 4 the mod folder list and world-map files in other mod folders), and ends with either
   `ALL OK: this machine matches the s168 package.` or `N check(s) DIFFER: fix those lines before playing (see the README, step 0).`
   In part 1 a line names the engine the install holds now; on both machines it must read
   `engine in this install now: s168 (the package)`.
   **Both machines must end with ALL OK** (one exception: a lone part-3 `TransportControls.csv` line, below). Keep both
   outputs: select the window's text and copy it, or run the command again with ` > check-laptop.txt` (or
   ` > check-desktop.txt`) at the end. What to do for each kind of `DIFFERS` line:
   - **0. the package itself** (a line starting `package`, or a `HASHES.txt` line): the unzip or the copy damaged the package.
     Unzip it again; do not play until part 0 says OK. If the same line still says DIFFERS after a fresh unzip, the package
     itself is wrong: send the output to Claude.
   - **1. the DLLs** (`x64\Assembly-CSharp.dll` and the others): copy the DLLs from the package again (item 2). On the desktop,
     stop and ask Claude: its install is shared with Claude's benches, so a different DLL there means something changed it.
     If the engine line reads `s167 (the fallback)` or `s166 (the old engine)`, the copy did not land: copy again.
     `other <sha16>` means an unknown engine: stop and ask Claude. If the `x64 and x86 hold the same Assembly-CSharp.dll` line
     says DIFFERS, copy both folders again.
   - **2. a mod folder** (for example `DIFFERS  FF9CustomMap-world: 2779 files, 0 missing, 3 differ, 0 extra`, with up to three
     `e.g.` lines naming files): on the laptop, move that folder into your backup folder, then copy the package's folder into
     `FINAL FANTASY IX\`, beside `FF9CustomMap`. On the desktop, stop and ask Claude for a new package: its world changed after
     this one was made.
   - **3. the base world data** (`StreamingAssets/Data/World/Environment.txt`, `TransportControls.csv` or `WeatherColors.csv`):
     these are the game's own files (Memoria's patcher writes them; the check ignores line-ending differences). If
     `TransportControls.csv` is the only `DIFFERS` line, you may play: while part 4 says OK, both machines read the copy in
     `FF9CustomMap-world` instead. For the other two, stop and send both machines' outputs to Claude. Never overwrite game
     data to make the line pass.
   - **4. world-map files in another mod folder** (for example `DIFFERS  FF9CustomMap: 2 world-map file(s)`, with up to three
     `e.g.` lines naming them): a folder outside the package also carries world-map files, so that machine's world map differs
     from the other's. On the laptop, move those files into your backup folder, keeping their paths, and run the check again
     until the line says OK (the `e.g.` lines name at most three files, so the next run can name more); or send the output to
     Claude first. On the desktop, stop and ask Claude: a Claude session put them there. The first line of part 4 shows that
     machine's `[Mod] FolderNames`. The laptop's lists the same seven folders as the desktop's in another order: that is
     harmless while part 4 says OK. If a line `FF9CustomMap-world is listed in [Mod] FolderNames` (or `-schema`, `-msgs`) says
     DIFFERS, that folder is missing from the list: put it back in `[Mod] FolderNames` in `Memoria.ini` (compare with your
     backup copy) and run the check again.
5. **No overworld edits on the desktop until the session.** The World tab's promotes, and any Claude session working on the
   overworld, write `FF9CustomMap-world`, and a single changed byte keeps the guest frozen. If you do edit, run the check on the
   desktop again before playing. Do not open the Memoria launcher between the check and the session either: it rewrites the
   `[Mod]` lines.
6. **The rest of `Memoria.ini`, unchanged from s167** (s168 adds no setting; check them on the laptop):
   - the guest keeps `[Netsync] FollowHost = 1`;
   - both machines use the same `[Cheats] SpeedFactor`, `[Graphics] FieldTPS` and `[Graphics] WorldTPS`. The desktop runs
     `SpeedFactor = 3`, `FieldTPS = 30` and `WorldTPS = 28`; WorldTPS's default is 20, so check the laptop's;
   - both use the same language (the fingerprint compares it) and the same voice-acting setting;
   - both keep the same `[Interface] FadeDuration` (the desktop's is 40): the menu's forced closes take longer with a longer fade.
7. **Optional, for B20 only:** before the session, with co-op off on the laptop (`[Netsync] Enabled = 0`), load the laptop's
   main save, walk out onto the world map and save there with Alt+F5 into an EMPTY slot, never over the main save. Note which
   world map it is (the ~ menu's Go tab, Vehicle section, shows the world state). 9011 is best, but any world map works for
   B20. If a battle happened on the way, write down that save's gil and the lead's level too. Set `Enabled = 1` again after.
   From now on Continue opens that world map, so for the rest of step 0 and Part A the laptop always starts with Load and
   picks its main save, never Continue. (Continue is right again only after a pairing, as in B33.)

### Step 0, in the game: your own values, the pairing, the line-up

`Memoria.log` is in the FF9 folder itself, beside `Memoria.ini`: on the desktop
`C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX\Memoria.log`, on the laptop `FINAL FANTASY IX\Memoria.log` in
its own FF9 folder. Every start of the game rewrites it, so copy it aside before you start that game again.

1. **The guest's own values (the laptop alone, the desktop's FF9 still closed).** Start the laptop's game and load its own save
   (with Load, its main save, if you made item 7's world-map save). With no host online, its own menu opens as usual. Write down:
   - gil;
   - the lead's name, level and HP;
   - one item and its count.

   Close the menu, then quit the game (Alt+F4, Yes). Nothing is saved.
2. **The host.** Start the desktop's game, load save 351 (Dali, the morning after the inn rest), walk out onto world map 9011
   and stand still. (The host writes its own values down later, just before Part B.)
3. **The guest pairs.** Start the laptop's game and load its own save (again with Load, its main save, if you made item 7's
   save): it pairs on its own field as usual (last time field 250)
   and follows the host out. That is A1: go on there, and come back here for items 4 to 9 as you go.
4. **The save listing on the laptop.** Once the laptop's log shows
   `[NetSync] pairing autosave written on ... leaving co-op returns you here`, open a second PowerShell window on the laptop and
   run this (it only reads; it is safe with FF9 open):

   ```
   Get-ChildItem -LiteralPath "$env:USERPROFILE\AppData\LocalLow\SquareEnix\FINAL FANTASY IX\Steam\EncryptedSavedData" | Where-Object { $_.Name -like 'SavedData_*.dat' } | ForEach-Object { '{0}  {1}  {2:yyyy-MM-dd HH:mm:ss}  {3}' -f $_.Name, $_.Length, $_.LastWriteTime, (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash.Substring(0, 16) }
   ```

   Add ` > saves-1.txt` at the end to keep it. One line per save file: its name, size, time and the start of its hash. No save
   file should change after this point until the session ends (B16). If the log says
   `no pairing autosave this session ... leaving co-op reloads your last own autosave` instead, that is expected, not a fault:
   take the listing anyway.
5. **The wire line.** Once co-op is running (from the first field that loads with co-op on), each log shows:
   `[NetSync] own wire: this engine speaks wire 15 (caps 0x000B) on the relay -- the partner's engine must speak the same`
   `caps 0x0003` there means that machine still runs s167, `caps 0x0001` s166. Neither log should hold a line with
   `the partner's co-op build lacks my` (until the version check, where one is expected).
6. **The fingerprint lines.** Once both games stand on the same world map (after A1), each log holds a line like
   `[NetSync] world fingerprint: world map 9011 digest 0xXXXXXXXX -- language US, dispatcher 0x..., meshes 0x..., transport 0x..., environment 0x..., weather 0x... -- c2 over N override reads (N KB) -- N ms at the seam + N ms inside the engine's reads ([Mod] MergeScripts N, N mod folders: never hashed raw)`
   one per world-map load. Take the LAST line for that world map on each machine: the two `digest 0x...` values must be equal.
   If they are not, the six values after `--` say which part differs: `language` (the game's language), `dispatcher` (the world
   script), `meshes` (the world-map files the game read), `transport` (the travel-controls table), `environment`, `weather`.
   The guest's log also names it, once per visit:
   `[NetSync] world fingerprint: my world map W differs from the host's -- the PART (NAME: mine 0x..., the host's 0x...) -- the walk stays frozen ("Your world map differs from your partner's (PART): you'll follow them as before."); s165's follow-out is never gated by it (t N ms)`
   and the host's:
   `[NetSync] host world fingerprint: the partner's world map W differs from mine (my digest 0x..., the guest's 0x...) -- "Your partner's world map differs from yours: they'll follow you as before." (the guest's own line names the component) (t N ms)`
   For the language it reads `the language (mine US, the host's FR: the loaded language only)` (with the two languages). If the
   digests differ, stop the walking steps (the rest of s166's behaviour still works, and so does Part B on a field), and send
   both logs and both check outputs.
7. **Only if the guest stays on "Checking your world map against your partner's..."** for more than 10 seconds, its log says
   `[NetSync] world fingerprint: still checking after N ms on world map W -- my digest ..., the host's ... -- the walk stays frozen until both are ready (t N ms)`
   with the reason in the two middle parts. Send the log.
8. **WorldTPS.** If the two differ, each log shows, once:
   `[NetSync] client world speed differs: my [Graphics] WorldTPS is 20, the partner's 28 -- each walks its own copy at its own speed (keep WorldTPS equal on both machines) (t N ms)`
   (`host` instead of `client` on the desktop, the numbers swapped). Fix the laptop's `WorldTPS` before the next start.
9. **The mods line** (`[Initialization] Mods: ...` near the top of each log) lists the same seven folders on both machines
   (the desktop's ends with `FF9Coop`), in any order once part 4 of the check says OK.

## What to try (the desktop hosts, the laptop is the guest)

**The same route as in s166 and s167:** the desktop loads its save (351, Dali, the morning after the inn rest) and walks out onto
the world map (9011); the laptop loads its own save and pairs on its own field. A video of the guest's screen helps most, and of
the host's screen during A2, A7 and A8.

### The order at a glance

1. **Part A, on the world map:** A1 to A9 (A10 optional). **Never press the guest's Menu button in Part A.**
2. **The host walks into Dali** and writes down its values ("Before Part B").
3. **Part B on a field:** B1 to B7, B9 with B23, B8 with B24, B18 (optional), B15, B14, then B10 out onto the world map.
4. **Part B on the world map:** B26 with B30, B27, B22, B28, B29 (optional), B12, then B11 back into a location.
5. **Late steps, each one disturbs the session:** B13, B16, then the optional B21, B17 and B20.
6. **Optional, if there is time:** B32 and B33, then the extras that need other saves (A11 to A13, B31).
7. **The version check, last:** A14 with B19 (B25 optional).

Each step keeps its name: A for an s167 step (A1 is s167's step 1), B for an s168 step.

### How to read the lines below

- On screen, every co-op line starts with `FF9 co-op:`; a ` / ` inside a quoted screen line is a line break.
- In `Memoria.log`, each line follows the date, the time and `|M|`.
- Capital letters stand for numbers: F a field, W a world map, X and Z a position, E an entrance, N a count or milliseconds,
  0xNN a byte. In s168's lines, STATE is the screen the guest was on (`MainMenu`, `Item`, `Equip`, ...), WHY a refusal's short
  name, CAUSE a forced close's, MEMBER a character's name and COMP the part that differs.
- `(t N ms)` at the end is the engine's own clock.
- Lines not quoted here (s144 to s167, field co-op) print as before.
- **The guest's walk log (s167):** each time the guest starts or stops walking, its log says one of these:
  - `[NetSync] world walk FREE on world map W: the guest walks its own copy on foot (the host on foot on this world map; entering a location stays the host's)`
  - `[NetSync] world walk FROZEN (WHY) on world map W: WORDS -- travel input held` (it was walking, and stopped)
  - `[NetSync] world freeze ON (live) on world map W: travel input held -- the walk waits (WHY: WORDS)` (it is frozen when a
    world map starts, before it may walk)

  WHY is a short name, WORDS its explanation, for example `riding: the host is riding`, `host_scene: the host is in a
  world-map scene`, `host_not_world: the host is not on the live world map`, `transition: a world transition is in flight`,
  `not_live: the bee scene, an event world or a diorama` (the battle view), `checking: checking my world map against the
  partner's`, `fp_mismatch: the world maps differ`, `old_partner: the partner's co-op build is older (no world fingerprint)`.
  The words always name the reason.
- **s168's lines on screen:**
  - **The refusal line.** Top right, in the status box, for 4 s. It always starts `FF9 co-op: `. While it shows, it covers the
    status line below it; that line comes back when it ends.
  - **The forced-close line.** Top right, under the status box when that is up, for 4 s. It starts `FF9 co-op: menu closed -- `.
    Nothing else ends it early, so it can stay 2-3 s over the next field or a battle's start.
  - **The chip.** Top centre, while the menu is open: *"View only: your partner's game makes the changes."* (with no
    `FF9 co-op:` in front). If the conversation chip is up, the menu chip stacks below it.
  - **The buzz.** The stock refusal sound.
- **s168's lines in the guest's log:**
  - One line when the menu opens:
    `[NetSync] guest menu: seated the host's party from the host's latest state frame -- N member(s), N bag row(s), N key item(s), gil N; the session begins (view only)`
    where gil N is the host's gil.
  - One line when it closes:
    `[NetSync] guest menu: restored at the door (STATE -> FieldHUD) -- every family back by reference; the session ends`
    (`WorldHUD` on the world map).
  - **Every "seated" line must have exactly one "restored at" line after it.**
  - A refused press, logged once per place for each kind of refusal:
    `[NetSync] main menu (WHY) suppressed (following guest) on field F` (or `on world map W`). Two exceptions: an older partner
    writes the old line with no WHY, `[NetSync] main menu suppressed (following guest) on field F`, and `data_differs` adds the
    member and component,
    `[NetSync] main menu (data_differs) -- MEMBER, component COMP suppressed (following guest) on field F`.
  - A forced close, logged once, when it ends:
    `[NetSync] guest menu: forced close (CAUSE) from STATE done: the HUD's Show turned events back on after N ms (FieldHUD)`.
    CAUSE is one of `leave`, `out`, `rejoin`, `world`, `cut`, `ending`, `title`, `scene`.
  - **Red tells in the guest log at any time:** `(should never happen)`, `DROPPED without writing`, `ended by THE WATCHDOG`,
    `ended by its fault path`, any `guest menu: ... faulted`. On the host: `[NetSync] guest menu: section 12 dropped` or
    `section 12's build faulted`. If you see one, see "If something goes wrong".
- **Two rules for the whole session:**
  - **In Part A, never press the guest's Menu button.** On s168 it opens the guest's menu, and while that menu is open the
    guest's world is frozen and the host's figure of the guest stands mid-stride. Part A runs with s168's menu idle, so a fault
    there is s167's (or the extra traffic; see "If a step fails").
  - **In Part B, do not hold L3 or press F11 during a menu step.** With the menu open they do nothing (the key is swallowed).
    On the field or the world map, between a step's presses, they rejoin the host at once and spoil the step.

## Part A: the s167 steps (the guest walks; never open the guest's menu)

**A1. Pair and follow out (s167 step 1, as in s166).** The host loads its save, walks out onto the world map (9011) and stands
still. Then the guest loads its own save and pairs as usual, on its own field.
- **Guest screen:** as in s166: *"Following your partner out onto the world map..."*, a fade, and the world map, with the
  guest on the host's spot. Then, within a few seconds of the landing (the first world-map load of a game run is slow, about 6
  to 8 s), the guest can walk. *"Checking your world map against your partner's..."* may show briefly first.
- **Host screen:** as in s166: *"Your partner is following you out onto the world map..."*, then *"Your partner is loading
  the world map..."*, then the guest's figure on the host's spot. *"Your partner can't walk yet: they'll join you at your
  next stop."* may show briefly.
- **Guest log:** s166's step-1 lines (the pairing autosave, the follow-out's start, commit and landing, ARMED, the ghost's
  two lines), then `[NetSync] world fingerprint: world map 9011 digest 0x...` and
  `[NetSync] world walk FREE on world map 9011: the guest walks its own copy on foot (the host on foot on this world map; entering a location stays the host's)`
  (perhaps after one `world freeze ON (live) ... the walk waits (...)` line). The landing line still ends `-- frozen here
  until the rejoin`: an old wording, not a fault.
- **Host log:** s166's `host world: the partner is following` and `... is loading` lines.
- **Now do step 0 "in the game", items 4 to 9:** the save listing, the wire lines, and compare the fingerprint lines.
- **Red tells:** the guest cannot move after 15 s: read the reason on its screen and in its last `world walk FROZEN` or
  `world freeze ON` line, and send the log.

**A2. The guest walks (s167 step 2).** The guest walks around the host, then away from it, off the host's screen and back.
- **Guest screen:** the guest walks, runs and stops with its own controls, and its camera follows it. The host's figure stands
  or walks where the host is. While the guest walks, its line at the top right is s144's *"Your partner is on the world map. /
  You'll rejoin them at their next stop."* (or the s165 hint if its minimap is off).
- **Host screen:** the guest's figure walks where the guest walks, on the ground, playing the guest's own walk, run and stand.
- **Logs:** nothing new while walking.
- **Red tells:** the guest is pulled back to the host's spot; the guest's figure on the host stands still while the guest
  walks; a battle starts on the guest's game alone; a `world walk FROZEN` line while the host stands on foot on the same
  world map.

**A3. An entrance (s167 step 3).** The guest walks to an entrance on the world map (Dali's is the nearest stock one) and presses
Confirm there, then once more. If a Southern Ring entrance, the boat or the ferryman is within reach, try one of those too
(optional).
- **Guest screen:** at each press the stock buzz and, for 4 s, *"Your partner leads the way. You'll join them at their next
  stop."*. Nothing else: no fade, no load; the guest walks on.
- **Host screen:** nothing.
- **Guest log:** once per kind of entrance per visit (the buzz plays at every press):
  `[NetSync] an entrance press (location: reader entry 1, place N) -- the buzz and "Your partner leads the way. You'll join them at their next stop." suppressed (following guest) on world map 9011`
  (`kit_cell: reader entry 0`, `boat: reader entry 15, place 169` or `ferryman: reader entry 16, place 100` at the Southern
  Ring's; at the boat plate it may instead read `location: reader entry 1, place 69`, the same press read by another
  entry). The older line `[NetSync] world script button-poll (travel, vehicle, location) suppressed (following guest) on world map 9011`
  may come with it.
- **Red tells:** the guest goes in; no buzz; two buzzes for one press; no line on screen; the line stays much longer than 4 s.

**A4. The full map (a walking guest on 9010 or 9011; s167 step 4).** If the guest shows no minimap, it presses Select once to
bring it up. Then, with its minimap up, the guest presses Select.
- **Guest screen:** the full map opens, as in the stock game, with the host's dot on it (orange, under the guest's own arrow).
  Move the cursor over a place and press Confirm: nothing happens (on foot, as in the stock game). Press Select: the map
  closes to no minimap. The line at the top right now stays s144's (the "press Select" hint stays quiet; see A6). Press
  Select again: the minimap is back.
- **Then the map and the rejoin:** the guest opens its full map again and leaves it open. **Before the host goes in, it turns
  its own minimap off** (Select on the host until no map shows): that sets up A5. Then the host walks into a location (back
  into Dali, or any other).
- **Guest screen:** the full map closes by itself, then the guest follows the host into that field and lands with control.
- **Host screen:** nothing new.
- **Guest log:**
  - `[NetSync] world map: the full map opens for the walking guest on world map 9011 (decision 8: the partner's dot rides it, its location pick stays the host's; a rejoin, the host's world battle or the session's end closes it first)` (once per visit)
  - `[NetSync] world dot: minted 'ff9mk coop host dot (full map)' from the full map's player pointer (...) -- the dot at depth 27 under the arrow` (once per world-map load)
  - `[NetSync] world map: the full map closed for the rejoin to field F on world map 9011 -- WorldHUD's own Select close replayed (control back; no minimap until the next Select)`
  - a `world walk FROZEN (...)` line, then `[NetSync] world rejoin landed on field F after N ms`.
- **Red tells:** the map does not open (a buzz instead); no orange dot on it; the map stays open and the guest stays on the
  world map; after the landing the guest has no control.

**A5. Out again, and the pull from far away (s167 step 5).** On that field, the host walks out onto the world map. The guest
follows out as in A1. **The hint:** the guest lands with no minimap (the host turned its own off in A4), so its screen shows
*"Your partner is on the world map: press Select for the minimap."*. Leave it. Then the guest walks far away from the host,
off the host's screen, and the host walks into a location.
- **Guest screen:** the guest is pulled from where it stands into the host's field, as in A4.
- **Host screen:** nothing new.
- **Guest log:** a `world walk FROZEN (...)` line, then `[NetSync] world rejoin landed on field F after N ms`.
- **Red tells:** no hint at the landing (with no minimap showing); the guest stays on the world map; it lands somewhere other
  than the host's field.

**A6. The minimap while frozen, and the quiet hint (s167 step 6).** Out again (the host walks out, the guest follows; the hint
shows again, because this is a new visit). The guest presses Select once, so its minimap is up. Then the host calls Choco from
its ~ menu (the Go tab, as in s166) and rides for a while.
- **Guest screen:** while the host rides, the guest cannot walk, and its line reads *"Your partner is riding. You'll rejoin
  them at their next stop."*. Now the guest presses Select: the minimap closes at once, with no buzz (in s166 it could not
  close). Then the host gets off: the guest walks again, and its line reads s144's *"Your partner is on the world map. /
  You'll rejoin them at their next stop."*, not the "press Select" hint, for the rest of this visit (the battle in A7 keeps it
  quiet). Select still opens the minimap.
- **Host screen:** nothing new.
- **Guest log:**
  - `[NetSync] world walk FROZEN (riding) on world map 9011: the host is riding -- travel input held`
  - `[NetSync] world minimap closed by Select on world map 9011 (following guest, frozen): straight to no minimap -- no buzz, control untouched, Select opens it again; s165's minimap hint stays quiet for this world-map visit`
  - `[NetSync] world walk FREE on world map 9011: ...` once the host is on foot.
- **Red tells:** a buzz and the minimap staying open (s166's defect); the "press Select" hint back on screen in the same
  visit; Select no longer opening the minimap.

**A7. A host battle while the guest walks (s167 step 7).** The guest walks a little away from the host. The host walks until a
random battle starts.
- **Guest screen:** the host's figure disappears at the host's swirl, and the guest's game shows the host's battle, as in
  s145 (if the guest's full map was open, it closes first). After the battle the guest is back on the world map at ITS OWN
  spot, not the host's, and walks again once the host is back on foot. If the guest was busy when the battle started (the
  pause screen, the ~ menu, a fade), it sits the battle out on the world map, frozen, and walks again after it, as in s145.
  (New in s168: an open main menu closes instead, and the guest joins the battle. B12 checks that; here the menu stays shut.)
- **Host screen:** after the battle, *"Your partner is loading the world map..."* for a few seconds, then the guest's figure
  at the guest's own spot.
- **Guest log:**
  - `[NetSync] world walk FROZEN (host_not_world) on world map 9011: the host is not on the live world map -- travel input held`
    (the host's swirl takes it off the live world map before the guest's battle view starts; `(transition)` or `(not_live)`
    in the brackets instead is fine too)
  - after the return, a new `world fingerprint` line, then `[NetSync] world walk FREE on world map 9011: ...`, perhaps after
    one `[NetSync] world freeze ON (live) on world map 9011: travel input held -- the walk waits (...)` line (on the bench it
    read `host_not_world: the host is not on the live world map`, because the host was not back yet).
- **Red tells:** the guest returns at the host's spot; it cannot walk after both are back; it gets a battle of its own.
- **Note:** s168 reworked the code that builds the guest's view of a battle, so of all the Part A steps this one is the most
  exposed to s168. If it fails, it is the first to bisect (see "If a step fails").

**A8. A link cut while the guest walks (s167 step 8).** Both on the world map, the guest walking.
- **What to do:** as in s166: turn the laptop's network off for about 10 seconds while the guest keeps walking, then turn it
  back on. Keep the whole cut under 30 s: past 40 s the session ends and the guest's own save reloads. If the laptop's bridge
  window closed during the cut (it did once in s166), start it again as usual.
- **Guest screen:** the guest keeps walking through the whole cut. The host's figure stops and stands; after about 1 s the dot
  goes; at about 2 s *"the host's game went silent -- reconnecting (N s left) / the session waits for it; if it doesn't return,
  your own save reloads"*; at 5 s the figure goes. When the network is back the line clears, and the dot and the figure return
  where the host is.
- **Host screen:** the guest's figure stands where it was. At 5 s it goes, with *"Lost contact with your partner -- waiting
  for their game..."*. When the link is back, the line clears and the figure reappears where the guest has walked to.
- **Logs:** s166's step-7 lines on both machines (`lane gap`, `session: the host went silent`, `session: the host is back`,
  `lane gap over`, the host's `the partner is lost`). No `world walk FROZEN` line on the guest during the cut.
- **This is the first real cut while walking:** the bench only simulated a short stall.
- **Red tells:** the guest cannot walk during the cut; it is pulled to the host's spot; the session ends inside 40 s.

**A9. The ~ menu Release, the guest (s167 step 9).** Two parts, each ending with a rejoin.
- **a. The "Close the map" line.** Stay on the world map after A8, the guest on foot. The guest opens its ~ menu (tilde), the
  Go tab, and under "Co-op world map" presses *"Co-op: release world freeze (until the next field load)"* (it then reads
  *"Co-op: world freeze released (until the next field load)"*). The guest presses Select until its full map shows (from no
  minimap that is two presses: the first brings the minimap back) and leaves it open. Then the host walks into a location.
  - **Guest screen:** the map stays open, and the line reads *"Close the map to join your partner."*. The guest presses
    Select: the map closes, *"Rejoining your partner at field F..."*, and the guest follows the host in.
  - **Guest log:** `[NetSync] world freeze RELEASED (~ menu) on world map 9011 until the next field load: the guest walks, rides and enters locations on its own (an entry goes to the host's field when they stand on one; its own encounters stay suppressed)`,
    then `[NetSync] world rejoin landed on field F after N ms`.
  - **Red tells:** the map closes by itself (it should not for a released guest); no line; the guest never rejoins after
    closing the map.
- **b. Entering alone.** Out again: the host walks out of that location (the guest follows out), then stands still on the
  world map, on foot, until this part ends. The guest releases again, walks to an entrance (the one the host just came out
  of is nearest) and presses Confirm.
  - **Guest screen:** no buzz: the guest goes into that location on its own, while the host stays on the world map. Note what
    happens next: the guest should follow the host back out onto the world map shortly after it lands, as in A1.
  - **Host screen:** the host's lines as in A1 if the guest follows out.
  - **Guest log:** the RELEASED line, then the field's load, and s166's follow-out lines if it follows out.
  - **Red tells:** a buzz and the entrance line (the Release did not take); the guest stuck on the field.

**A10 (optional). The ferry, kit 9011 (s167 step 10).** The host takes the ferry voyage (talks to the ferryman) while the guest
walks nearby.
- **Guest screen:** during the voyage the guest is frozen with *"Your partner is in a world-map scene. You'll rejoin them at
  their next stop."*. Once the host lands across the water, the guest walks again, on its own shore. The boat and the
  ferryman answer it with the buzz and the entrance line. It rejoins the host at the host's next location.
- **Guest log:** `[NetSync] world walk FROZEN (host_scene) on world map 9011: the host is in a world-map scene -- travel input held`,
  then FREE.
- **Red tells:** the guest crosses the water alone; it stays frozen after the host lands.
- **Then:** the host takes the ferry back to the port it boarded from (or teleports back to Dali's shore with its ~ menu), so
  "Before Part B" starts in Dali; the guest rejoins at the host's next location.

A11 to A13 need other saves: they are near the end, under "Optional extras with other saves". A14 is the version check, last.

## Part B: the s168 steps (the guest's main menu)

From here on the guest may press Menu, but only where a step says so.

### Before Part B: the host's values

The host walks into Dali (the guest rejoins and lands with control). Then the host opens its own main menu and writes down:
- how many members the party shows;
- gil;
- the first five rows of Items, with their counts;
- the first three names in Key Items, in order;
- the lead's weapon, and one support ability that is on;
- the lead's level and HP/MP.

Then the host closes its menu. (These are taken here, not at the start, because A7's battle changed them.)

### On a field

**Before these steps:** the host is on a field in Dali and the guest has been pulled into the host's field and is following.
The guest stands with control, and no conversation window is up on either screen. After any landing, wait a second or two
before the first press (B24 tests the first second).

**B1. Open, look, close.**
- **Do:** The guest presses Menu once and looks, then presses Cancel once at the top. Next, press Menu twice quickly. With the
  menu open, press Menu once more.
- **Guest screen:**
  - The stock main menu opens over the host's party.
  - Gil is the host's gil, not the guest's own figure from step 0.
  - The chip is at the top centre, and no line shows top right.
  - Cancel: the chip goes, the guest stands on the field with control.
  - Two quick presses: one open, no buzz, no line. (At the normal fade the second press lands inside the opening menu and is
    dropped silently.)
  - Menu inside the open menu: nothing at all.
- **Host screen:** nothing new.
- **Guest log:** the seated line (as many members as the host's own menu shows, and the host's gil), then
  `restored at the door (MainMenu -> FieldHUD)`.
- **Host log:** nothing new.
- **If it is refused instead:**
  - *"FF9 co-op: The menu data did not arrive. Try again in a moment."* for more than 10 s: look in the host log for a
    `section 12` line and send both logs.
  - *"FF9 co-op: Your game data differs from your partner's (MEMBER)."*: the guest log names it,
    `main menu (data_differs) -- MEMBER, component COMP suppressed ...`. The desktop's own `FF9CustomMap` adds characters 12
    and 13 (Iviv and Steiniv, presets 20-21), which the laptop may lack; this matters only if one of them is in the host's
    party (save 351's party is stock). In this build that refuses the whole menu. Record it and send the logs. The rest of
    Part B cannot be seen this session.
- **Red tells:** the guest's own party or gil; no chip; a seated line with no restored line after Cancel; no control after
  Cancel.
- **Record:** the members and gil shown, the location name at the bottom of the menu, and roughly how long it took to open.

**B2. Browse every screen.**
- **Do:** Open each screen and Cancel back up each time:
  - Items (the list opens with the cursor on its first row; Cancel once for the bottom bar: Use, Arrange, Key), then Key (move
    right along the bar);
  - Abilities, for each member (the bottom bar Use / Equip moves left and right; Equip shows the support abilities);
  - Equip, for each member (the bottom bar Equip / Optimize / Off moves left and right): Equip, a slot, then scroll its
    candidate list but do not confirm;
  - Status, for each member;
  - the Folklore (or Journal) row.

  While the guest looks, the host opens its own Items and Key Items once.
- **Guest screen:**
  - Every screen works as in the stock game, over the host's data.
  - The first five Items rows and their counts match the host's.
  - Key Items are in the same order as on the host's screen.
  - The host's equipment, stats and AP show.
  - Equip's preview numbers move as you scroll candidates (they change only the copy).
  - The chip stays on every screen.
- **Logs:** only the seated and restored pair.
- **Red tells:**
  - a screen that will not open, shows empty rows or locks up;
  - an item order different from the host's;
  - the chip missing on a sub-screen.
- **Record:** whether Key Items are in the host's order; whether Status's trance bar matches the host's (it may differ: see
  Known limits).

**B3. Greyed rows and the save keys.**
- **Do:**
  - In the open menu, press Confirm on Order, Card and Config, and on Party if it shows.
  - Press Alt+F5, Alt+F9 and Alt+F2 once each.
  - Cancel out to the field and press Alt+F5 and Alt+F9 once more.
- **Guest screen:**
  - The greyed rows buzz and nothing opens.
  - There is no Save row.
  - Every Alt key, in the menu and on the field, buzzes and opens nothing.
- **Logs:** nothing new (these buzzes write no line).
- **Red tells:** a screen opens; a save or load screen appears.

**B4. Try to change things.** Do each one, Cancelling back to the top between them:
- **Do:**
  - **a.** Equip, a slot of the lead whose candidate list shows at least one real piece, that piece, Confirm. A list that holds
    only the empty row buzzes by itself and writes no E1 line: that is the stock game, not a refusal. If no slot of the lead
    lists a piece, use another member.
  - **b.** Equip, Remove (Off) on an equipped head, wrist, armor or accessory piece (not the weapon: the stock game never
    removes a weapon, so it buzzes there anyway and no E2 line is written).
  - **c.** Equip, Optimize.
  - **d.** Abilities, then Equip on the bottom bar (move right): the member's support abilities open, and the cursor should
    already sit on its first lit (white) one. Confirm there (on or off). If you know your Special button, press it on that lit
    support ability too. Special pressed on the Use / Equip bar itself jumps to the Equip screen: that is stock, not a refusal.
    A grey or blank row writes nothing and logs nothing, by design. Record where the cursor started.
  - **e.** Abilities, a field-usable ability (Dagger's Cure if she is in the party and has it), a target whose HP is not full
    if there is one, Confirm. Skip e if no member has a field ability. After Use the cursor starts on the list's first cell,
    which is blank while Dagger has learned no summon: that is stock Memoria (its default menu layout), and the host's own
    Abilities screen does the same. Move to Cure (white) before you Confirm; a Confirm on a blank cell buzzes and writes no A3
    line, by design. Check that Dagger's Cure is white on the guest's copy; the host compares with its own Abilities screen. A
    Cure that is grey on the guest but white on the host is a copy fault, not a refusal: take a screenshot of both and send the
    logs. Also compare her HP and MP numbers with the host's: different numbers are a red tell.
  - **f.** Items, a Potion, a target whose HP is not full, Confirm. If every member's HP is full, use any target: the stock
    game also refuses then, so judge by the Potion count and the guest log's `I1 confirm refused on Item` line.
- **Guest screen:**
  - Each Confirm buzzes and nothing changes: the slot keeps its piece; the ability keeps its mark and the magic stone count;
    the item count, the target's HP and the caster's MP stay the same.
  - You stay on the same screen. No line shows top right.
  - The stock game also buzzes when an item would do nothing, so judge by the numbers, not the sound.
- **Guest log:** once per kind of change per open, for example:
  `[NetSync] guest menu: E1 confirm refused on Equip -- view only: the seated copy is never written, the screen's own buzz (logged once per site per seat)`
  The kinds are E1 to E3 on `Equip`, A1 to A3 on `Ability` and I1 on `Item`. The bench has now seen every kind in a game except
  A3 (e's line): an A3 line on e would be the first anywhere. Write down which lines appeared.
- **Red tells:** anything changes after the buzz; the item is used up; no buzz.
- **Record:** for each of a to f, whether it buzzed, whether anything changed, and whether its `confirm refused` line appeared.

**B5. What you may change on the copy.**
- **Do:** Items, then Cancel once to the bottom bar, Arrange, Auto. Then Arrange again, the second choice (Manual): Confirm on one
  item, move to another, Confirm (the two swap). Then Key on the bottom bar: Confirm on a key item to open its description, and
  Cancel to close it. Cancel to the field, open the menu again, and look at Items and Key Items.
- **Guest screen:**
  - Auto may move nothing (the host's list may already be in sort order); the manual swap always moves two rows. After the
    reopen the list is back in the host's order.
  - A key item's "new" mark (if the host has one) goes when its description closes, and is back after the reopen. With no key
    items the Key list shows one empty row whose Confirm buzzes (stock).
- **Host screen:** its own Items order never changes. The host checks after.
- **Red tells:** the sort survives the reopen; the host's list is reordered.

**B6. Nothing changed: check both sides.**
- **Do:**
  - The host opens its own menu and compares with its notes from "Before Part B": gil, the five Items rows and counts, the
    lead's weapon and support ability, HP/MP.
  - The guest opens its menu once more.
  - The guest runs the save listing again (step 0, "in the game", item 4) and compares it with `saves-1.txt`.
- **What you should see:**
  - Every host value is the same.
  - The guest's menu shows the host's values, not the sorted or refused ones.
  - The save listing is the same, line for line.
  - The host's figure on the guest's screen, and the guest's own figure, look as they did before the menus.
- **Red tells:** any host value changed; a save file's time or hash changed; a figure changed model.

**B7. A stale view, and a reopen that refreshes it (both players in menus).**
- **Do:**
  - The guest opens Equip on the host's lead and stays there.
  - The host opens its own menu, swaps the lead's weapon for another and closes its menu.
  - The guest looks, Cancels to the field and opens Equip again.
  - The host then swaps the old weapon back.
- **Guest screen:** while its menu is open it keeps showing the old weapon, because the copy is taken once, at the open. After
  the reopen it shows the new weapon.
- **Host screen:** the swap works as in the stock game, with the guest's menu open at the same time. That is allowed on purpose.
- **Red tells:** the guest's open screen changes by itself; the reopen still shows the old weapon.

**B9. A host conversation on your field.**
- **Before:** both players on one field with an NPC. The guest's menu is open.
- **Do:** The host talks to the NPC. Optional: the host opens a chest, then uses an ATE if its screen offers one, with the
  guest's menu open each time.
- **Guest screen:** the menu closes, *"FF9 co-op: menu closed -- your partner's scene."*, then the conversation plays on the
  guest's screen as usual.
- **Guest log:** `forced close (scene) from STATE done: ...`. There must be no
  `[NetSync] talk relay: start N expired before my copy was free`.
- **Red tells:** the conversation does not play on the guest; the menu stays open; that expiry line.

**B23. During a host conversation** (right after B9, or at the host's next conversation).
- **Do:** While the host's conversation window is up on the guest's screen, the guest presses Menu.
- **Guest screen:** nothing at all: no buzz, no line. This is by design (Known limits). If you press between windows, you may
  hear the buzz with *"FF9 co-op: Try the menu again in a moment."* or *"FF9 co-op: Your partner is in a scene. Try again when
  it ends."* Record which.

**B8. The host leaves the field.**
- **Before:** the host stands by a door to another field (in Dali, for example the inn's door). The guest opens Equip and goes
  into a slot's candidate list.
- **Do:** The host walks through the door. Then repeat with the guest at the top menu.
- **Guest screen:**
  - Within about half a second the menu closes and the chip goes.
  - *"FF9 co-op: menu closed -- following your partner."* shows for about 4 s.
  - The guest follows as usual and lands with control.
  - At a sub-screen the field may brighten briefly before the follow fades it out (Known limits).
- **Host screen:** nothing new.
- **Guest log:**
  - `[NetSync] guest menu: restored at the door (Equip -> FieldHUD) -- every family back by reference; the session ends`
  - `[NetSync] guest menu: forced close (leave) from Equip done: the HUD's Show turned events back on after N ms (FieldHUD)`
  - the usual follow lines.

  In the repeat, `MainMenu` replaces `Equip`.
- **Red tells:**
  - the menu stays open after the host has gone;
  - the guest stays behind, or gets a black screen;
  - no close line;
  - `ended by THE WATCHDOG`;
  - no control after landing.
- **Record:** the ms in the close line; how long the line stayed; whether the field brightened before the fade. A screenshot or
  video of this step helps.

**B24. The first press after landing** (right after one of B8's landings). Within a second of a follow landing, a press may get
*"FF9 co-op: Try the menu again in a moment."* or *"FF9 co-op: Your partner is in a scene. Try again when it ends."* (the host
is still without control after its door); a second later it opens. A press in the very first instant after landing may do
nothing at all (no buzz, no line): the stock game drops a press while the HUD is still fading in. Press again.
- **Red tell:** refused for more than 5 s while the host stands still.

**B18 (optional, three tries). The door race.** The host walks through a door while the guest presses Menu at the same moment.
Any one of these is right on each try:
- the buzz with *"FF9 co-op: You're about to follow your partner."* or *"FF9 co-op: Try the menu again in a moment."*, then
  the follow;
- the buzz with *"FF9 co-op: Your partner is in a scene. Try again when it ends."*, then the follow. This is the likeliest
  one: a door turns the host's control off and fades for most of a second before it moves, and that is what the guest reads;
- the menu opens and closes at once with the following line, then the follow;
- nothing opens, and the follow happens.

The log may show any refusal whose words are one of those lines: `main menu (leaving)`, `main menu (host_elsewhere)`,
`main menu (host_busy)`, `main menu (busy)`, `main menu (control)`, `main menu (ui)` or `main menu (scene)`.
- **Red tells:** an open menu left behind on the old field; no follow; a field frozen after a refusal.
- **Note:** at the normal fade a hand-timed press rarely lands inside the fade, so this mostly shows the refusals at the press,
  most often `scene`.

**B15. The quit prompt holds a close.**
- **Before:** on a field by a door, the guest's menu open.
- **Do:** The guest presses Alt+F4 to bring up the quit prompt. The host walks through the door. Wait about 2 s, then the guest
  answers No (Cancel). Never Yes.
- **Guest screen:**
  - While the prompt is up, the menu stays under it and no close line shows.
  - After No: *"FF9 co-op: menu closed -- following your partner."* and the follow.
- **Guest log:** `forced close (leave) from MainMenu done: ... after N ms`, with N about the time you waited. No WATCHDOG line.
- **If Yes is pressed by mistake:** the laptop's game quits. Nothing is ever saved while the menu is open. Copy its
  `Memoria.log` aside first (`Memoria-laptop-B15.log`: it holds the session so far), then restart and pair again.
- **Battle version (run it on the world map, after B12; please do not skip it this session: the bench now raises the guest's
  quit prompt on a client, but only for a battle on a field, so this is the only world-map check of it):** the prompt is up over
  the open menu when the host's random battle starts. What you should see:
  - The host's battle runs without waiting for the guest while the prompt is up. After the guest's No, a short wait at the
    battle's first command is fine (the host holds for the late guest). Red tell: a `start hold ARMED` line in the host's log
    before the guest answered No.
  - The guest's menu stays until it answers No, then *"FF9 co-op: menu closed -- your partner's battle."*
  - The guest then joins late or sits the battle out. Record which.
- **Red tells:** the menu closes while the prompt is still up; no control after No.

**B14. A short link cut while the menu is open.**
- **Before:** the guest's menu is open on Status.
- **Do:**
  - Turn the laptop's network off for about 20 s. Keep the whole cut under 30 s. On a field the reconnecting line shows about
    5 to 7 s into the cut.
  - During the cut, browse and Cancel back to the top.
  - Close the menu and press Menu again once the reconnecting line is up.
  - Turn the network back on, wait for the line to clear, and press Menu.
- **Guest screen:**
  - The menu stays open through the cut and browsing works.
  - A press in the first 2 s of the cut, before the link counts as lost, may still open the menu from the host's last frame:
    not a fault. After that a press buzzes. *"FF9 co-op: Waiting for your partner's game: try the menu again in a moment."*
    may show briefly. Once the reconnecting line is up, that line stays instead: the refusal line never covers it.
  - Once the link is back, Menu opens.
- **Guest log:** A8's cut lines, then `[NetSync] main menu (link) suppressed (following guest) on field F` (or
  `on world map W`).
- **Red tells:** the menu closes during the cut (only the session's end may close it); it opens once the reconnecting line is
  up.

**B10. The host walks out to the world map.**
- **Before:** on the field with Dali's world-map exit. The guest's menu is open.
- **Do:** The host walks out.
- **Guest screen:** the menu stays open while the host's world map loads (a few seconds: the close waits until the host stands
  on the world map). Then *"FF9 co-op: menu closed -- following your partner."*, then the follow-out from s166 and s167:
  *"Following your partner out onto the world map..."*, then the walk.
- **Guest log:**
  - first `[NetSync] world follow-out: waits: the field HUD is not up -- field F, the host on world map 9011 (t N ms)`, logged
    as the close starts. That is expected: the follow-out waits for the menu to close. It appears at most once per host
    world-map visit, and other `world follow-out: waits:` lines may come with it;
  - then `[NetSync] guest menu: restored at the door (MainMenu -> FieldHUD) -- ...`;
  - then `forced close (out) from MainMenu done: ...`;
  - then the follow-out lines.
- **Red tells:** the menu still open 5 s after the host's own figure shows on the world map (on the host's screen); the guest
  stays on the field after the close line; a `waits: the field HUD is not up` line with no `forced close (out)` line after it.

### On the world map

**B26. A walking guest on 9011.**
- **Do:** Stop, press Menu, look at Items and Status, note the location name, then Cancel.
- **Guest screen:**
  - The menu opens over the host's party, with the chip.
  - After Cancel the minimap and s144's line are as before, and the guest walks again at once from the same spot.
- **Guest log:** the seated line, then `restored at the door (MainMenu -> WorldHUD)`.
- **Red tells:**
  - no walk after the close, or the guest is moved;
  - music, a scene, the minimap or the location name changes after the close (the world script's menu hook). Write down
    exactly what changed.

**B30. The host's view** (with B26: open the guest's menu again right after walking).
- **Do:** While the guest's world menu is open (it was walking when it opened), the host looks at the guest's figure.
- **What you should see:** it stands frozen mid-stride (Known limits). Take a screenshot. On a field the guest's figure stands
  still too.
- **Then:** the guest Cancels.

**B27. The host in its own menu.**
- **Do:** The host keeps its own main menu open while the guest presses Menu.
- **What you should see:** the design expects the menu to open. If instead you get the buzz and *"FF9 co-op: Your partner is in
  a scene. Try again when it ends."* (log: `main menu (scene)`), record it. That is a known open question with a later fix.
- **Record:** the guest's walk state while the host's menu is open (does the guest still walk, or freeze?).
- **Then:** the guest Cancels and the host closes its menu.

**B22. The full map.**
- **Do:** A walking guest presses Select until the full map shows, then presses Menu.
- **Guest screen:** the buzz and *"FF9 co-op: Try the menu again in a moment."* for 4 s, in place of s144's line, which then
  returns. Close the map, and Menu opens.
- **Guest log:** `[NetSync] main menu (control) suppressed (following guest) on world map 9011`. The open full map turns the
  guest's own control off, and the control check comes before the full-map check. `main menu (world_busy)` would also be fine.
- **Note:** the stock game is silent here. Whether it should buzz is your call.

**B28. A frozen guest.**
- **Do:** The host calls Choco from its ~ menu and rides. The guest, showing *"Your partner is riding. You'll rejoin them at
  their next stop."*, presses Menu, browses and Cancels.
- **What you should see:** the menu opens; after Cancel the guest is still frozen with the riding line.
- **If instead** you get the buzz and *"FF9 co-op: Your partner is in a scene. Try again when it ends."* (log
  `main menu (scene)`), record it: it is an open question (whether a riding host counts as "in a scene"), not a fault.
- **Red tells:** a refusal with any other line; the guest walks while the host still rides.
- **Then:** the host gets off Choco and stands on foot before the next step (B29's ferry and B12's random battle need it on
  foot).

**B29 (optional). The ferry.**
- **Do (a):** During the host's voyage, the guest presses Menu.
  - **What you should see:** the buzz and *"FF9 co-op: Your partner is in a scene. Try again when it ends."*
- **Do (b):** The guest opens its menu first, then the host starts the voyage.
  - **What you should see:** the build has no close for a world-map scene, so expect the menu to stay open until you Cancel,
    then the guest frozen with s167's scene line.
- **Record:** what actually happened in (b).
- **Then:** if the host crossed, it takes the ferry back before B12; B11 needs Dali's shore.

**B12. A host battle.**
- **Before:** on the world map, the guest's menu open on Items.
- **Do:** The host walks until a random battle starts. Optional: the same on a field that has encounters.
- **Guest screen:**
  - *"FF9 co-op: menu closed -- your partner's battle."* (it may show over the battle's first seconds).
  - Then the guest's view of the host's battle, as in A7.
  - Afterwards, back at its own spot on the world map.
- **Host screen:** the battle starts with the guest on board, with no sign of a late join.
- **Guest log:** first `[NetSync] guest menu: restored at the door (Item -> WorldHUD) -- ...`, then
  `forced close (cut) from Item done: ...` on the world map. In the optional field version: `restored at the door (Item ->
  FieldHUD)`, then `diorama BOOT`, then `forced close (cut) from Item ended at a clear point after N ms (a scene load)`. Both are
  right; `ended: the scene changed` cannot appear here. Then the battle lines as before.
- **Red tells:**
  - the menu stays open;
  - the guest sits the battle out frozen, or joins it late;
  - the guest gets a battle of its own.
- **Note:** for about 2 s after the host's battle ends, a guest Menu press is refused with *"FF9 co-op: Your partner is in a
  battle."* (log `main menu (host_battle)`): the battle stays live for 2 s. Not a fault: press again.

(B15's battle version goes here: please do not skip it.)

**B11. The host enters a location from the world map.**
- **Before:** both players on 9011, the guest on foot with its menu open on Items.
- **Do:** The host walks into Dali.
- **Guest screen:** *"FF9 co-op: menu closed -- following your partner."*, then the rejoin, landing with control.
- **Guest log:**
  - one or more `[NetSync] world rejoin to field F waits: ...` lines while the menu closes, the first reading
    `waits: the world HUD is not up` (expected: the rejoin waits for the close)
  - `[NetSync] guest menu: restored at the door (Item -> WorldHUD) -- ...`
  - `forced close (rejoin) from Item done: ... (WorldHUD)`
  - `[NetSync] world rejoin landed on field F after N ms`
- **Red tells:** the guest stays on the world map.

A video of the guest's screen across B8 to B13 helps most.

### Late steps (each one disturbs the session)

The host walks back out onto 9011 (the guest follows out).

**B13. The host goes to the title.**
- **Before:** on the world map 9011, the guest's menu open.
- **Do:**
  - The host presses Pause, then F8 (the desktop has `[Control] SoftReset = 1`), which takes it to the title. The host loses any
    progress it has not saved (do not save over 351 during the session).
  - Once the guest's menu has closed, the guest presses Menu.
  - The host loads save 351 again.
- **Guest screen:**
  - *"FF9 co-op: menu closed -- your partner is at the title screen."* under the s144 line *"FF9 co-op: Your partner is at the
    title screen."*, which stays after it.
  - The press: the buzz and *"FF9 co-op: Try the menu again in a moment."*
  - When the host's save loads, the guest rejoins the host's field.
- **Guest log:** `forced close (title) from MainMenu done: ...` and
  `[NetSync] main menu (host_busy) suppressed (following guest) on world map 9011`.
- **Red tells:** the menu stays open while the host is at the title; the guest's own autosave loads.
- **Record:** if the log says `(world)` or `(leave)` instead of `(title)`, note it.

Then the host walks out onto 9011 again (the guest follows out).

**B16. Co-op switched off while the menu is open (the session ends).**
- **Before:** on the world map 9011, the guest's menu open.
- **Do:** On the laptop, alt-tab out. In `FINAL FANTASY IX\Memoria.ini`, under `[Netsync]`, change `Enabled = 1` to
  `Enabled = 0` and save. Return to the game with Alt+Tab or a click on the window's title bar (a click inside the picture
  presses a menu row); the change is read within about 2 s.
- **Guest screen:**
  - *"FF9 co-op: menu closed -- the co-op session is ending."* (it shows even with co-op off).
  - The menu closes, then the guest's own autosave loads: its pairing spot (where step 0's pairing autosave line said it was
    written; last time field 250). If step 0 saw `no pairing autosave this session`, its last own autosave loads instead.
  - Its own menu then shows its own party, and gil and level as noted in step 0.
  - Order, Card and Config are not greyed, and there is no chip.
- **Guest log, in this order:**
  - `[NetSync] config change applied live (disabled)`
  - `[NetSync] guest menu: restored at the door (MainMenu -> WorldHUD) -- every family back by reference; the session ends`
  - `forced close (ending) from MainMenu ...`, which reads either `done: ...` or
    `ended at a clear point ... (the exit ramp's fire)`
  - `[NetSync] session ended -> reloading own autosave (Continue)`
- **Must not appear:** `exit ramp: ... never returned control in 10s`, or `(should never happen)`.
- **Record:** the guest's own values after the load (they should match step 0).
- **To resume:** set `Enabled = 1`, save, and the guest pairs and follows again. Once the pairing autosave line shows, take a
  new save listing (`saves-2.txt`). From here, compare with the newest listing.

**B21 (optional, after B16's resume, on the world map). Riding.**
- **Do:**
  - On 9011, on the guest's ~ menu Go tab, use "Co-op world map": *"Co-op: release world freeze (until the next field load)"*.
  - Then in Vehicle, choose "Chocobo — plains", close the ~ menu (tilde) and press Menu.
  - Open the ~ menu again, choose "On foot", close it and press Menu again; when the menu opens, Cancel.
- **Guest screen:** on the chocobo, the buzz and *"FF9 co-op: The menu opens on foot."*; on foot, the menu opens. (If you hear
  the buzz with *"Try the menu again in a moment."*, the ~ menu was still open: close it and press again.)
- **Guest log:** `main menu (riding) ... on world map 9011`.
- The release lasts until the next field load: let the host walk into a location and back out before the next step.

**B17 (optional). A long cut.** With the guest's menu open, turn the network off for more than 40 s.
- **Guest screen:** the menu stays open until the session ends, then closes with *"FF9 co-op: menu closed -- the co-op session
  is ending."*, and the guest's own autosave loads.
- Then turn the network on; the guest pairs again. Take a new save listing.

**B20 (optional). Before following.** This needs the laptop's world-map save from step 0, item 7.
- **Do:** In the session, with the host standing on 9011: copy the laptop's `Memoria.log` aside
  (`Memoria-laptop-before-B20.log`), quit the laptop's game (Alt+F4, Yes), start it again and Load the world-map save from
  step 0 item 7 (not Continue); it pairs there. Then, once the host's figure shows on the laptop's screen, the guest presses Menu
  (a press before the pairing has finished opens the guest's own menu by design: wait for the host's figure). Once the pairing
  autosave line shows, take a new save listing. From here the guest's own autosave is on that world map, and its own values are that save's.
- **Guest screen:**
  - The buzz and *"FF9 co-op: You'll get the menu once you've followed your partner into a location."* for 4 s, covering
    s167's walk line, which then comes back.
  - After the host enters a location and the guest rejoins, Menu opens.
- **Guest log:** `[NetSync] main menu (not_mirroring) suppressed (following guest) on world map W` (W = that save's world map).
- **Red tell:** after the host's figure showed, the guest's own menu opens, with its own party and gil. That would be s38's old hole back, and it is what this
  step checks.

### Optional: routes the bench could not reach

**B32 (optional). The quit prompt left up when the session ends (on a field).**
- **Before:** both on a field, the guest following.
- **Do:**
  - Open the menu and press Alt+F4.
  - Alt-tab out, set `Enabled = 0` in Memoria.ini and save. Return to the game with Alt+Tab (or a click on the window's title
    bar), never a click inside the picture: a click there can press the prompt's Yes or No.
  - Touch nothing for about 15 s.
- **What you should see:**
  - Within about 10 s the prompt goes by itself and the guest's own autosave loads.
  - After that load: no prompt, and control works.
  - No close line shows; this is by design.
- **Guest log:**
  - `[NetSync] exit ramp: the field never returned control in 10s -- reloading the guest's own save anyway (fail-safe)`
  - `forced close (ending) from MainMenu ended at a clear point after N ms (the exit ramp's fire (the quit prompt held the close))`
  - `[NetSync] guest menu: restored at the exit ramp's fire (the quit prompt held the close) (before reloading own autosave) -- every family back by reference; the session ends`
  - `[NetSync] session ended -> reloading own autosave (Continue)`

  It must not show `(should never happen)`. No bench has shown these lines yet: treat what you see as a first read and send the
  log either way.
- **Recovery, if the prompt survives the load:** pressing its Cancel would leave the field frozen. Instead press Alt+F4, then
  Yes, copy its `Memoria.log` aside (`Memoria-laptop-B32.log`: it holds the session so far), and restart. Nothing was saved.
- **Where to run it:** on a field. The world-map version of the fail-safe line wrongly says "event world map".
- **To resume:** set `Enabled = 1` and save; the guest pairs again. Once the pairing autosave line shows, take a new save
  listing.

**B33 (optional, last of Part B). Kill the guest's game while the menu is open.**
- **Do:**
  - Run the save listing (` > saves-before-kill.txt`).
  - Open the menu, then run `taskkill /F /IM FF9.exe` in a terminal on the laptop. (Task Manager's Processes tab sends a close
    request, which brings up the quit prompt instead.)
  - Before starting anything, run the save listing again (` > saves-after-kill.txt`).
  - Close the desktop's game too.
  - Copy both `Memoria.log` files aside now, before starting either game again: `Memoria-laptop.log` and
    `Memoria-desktop.log` (the whole session so far).
  - Restart the laptop's game, Continue, and open its menu.
- **What you should see:**
  - `saves-before-kill.txt` and `saves-after-kill.txt` are the same, line for line: no save file was written while the menu
    was open. (Continue itself may write the autosave, so do not compare a listing taken after it.)
  - After Continue: its own party, and gil and level as noted in step 0 (or as noted for the world-map save, if B20 was run).

### Skipped, and why

- **The load route (Alt+F9 while the menu is open).** A following guest never reaches it: Alt+F9 meets the older co-op load
  gate first and buzzes (B3). Only the one-PC bench can hold the menu open without following.
- **A host battle the guest cannot show.** It needs a battle scene the laptop lacks, and nothing on this route starts one. The
  world-map version has no route at all.
- **The press-in-the-fade ramp legs.** They need a laptop FadeDuration above 2 s and an ini save that lands inside one fade.
  Nothing shows on screen either way (co-op is off, so no line), so the result would be log only.
- **The guest's own soft reset and the Role edit.** Both were benched on one PC. On two PCs they only end the session the long
  way, or make the laptop host.
- **A frozen guest at the rejoin.** No easy route: Choco does not enter towns.
- **The kit HUD-strip field.** It is not on this route.

## Optional extras with other saves (A11 to A13, B31)

Each needs a different save; the host's progress since its last save is lost when it loads one. Skip any that are not easy.
On these the guest may press Menu (Part A's rule was for A1 to A10).

**A11. World map 9002 (s167 step 11)** (needs a save whose world map is 9002; both figures are Dagger there). As A1 to A3, with
one difference: on 9002 a walking guest's Select goes straight from the minimap to no minimap (no full map). Its minimap on 9002
has never been seen in game: say what shows.

**A12. A vehicle world (s167 step 12)** (needs a later-disc save on a world map with Choco, a ship or an airship: 9000, 9003,
9005, 9007, 9008 or 9009). The guest follows out and stays frozen there the whole time, as in s166: no walking, only the dot.
Check that Select on its minimap closes it (no buzz), that a Confirm at an entrance does nothing (no buzz, no line: the buzz is
for 9002, 9010 and 9011 only), and that both logs show a `world fingerprint` line for that world map with equal digests. If
the host flies the airship, try the minimap close during the flight too. (s168: the follow-out lands the guest on foot and it
stays frozen on foot, so Menu opens the main menu over the host's party, as on 9011; Cancel and note it. While the host rides,
the buzz and *"FF9 co-op: Your partner is in a scene. Try again when it ends."* may come instead (B28's open question): record
which. Only a guest riding by itself after a ~ menu Release gets the buzz and *"FF9 co-op: The menu opens on foot."*.)

**A13. The quicksand (s167 step 13)** (skip unless it is easy: world maps 9003 or 9009, later discs). It tests only a guest that
loaded its own save ON the world map, standing on a quicksand pit, and paired there; a guest that followed the host out is
already covered. During a link cut of a few seconds that guest presses Confirm on the pit: nothing should happen on its side,
and no battle starts on the guest alone. Its log may say
`[NetSync] scripted world battle (..., scene 144) suppressed (following guest) on world map W`.
(s168: that guest is not following yet, so its Menu gives the buzz and *"FF9 co-op: You'll get the menu once you've followed
your partner into a location."*; s167 opened the guest's own party's menu there.)

**B31 (optional, needs a save whose world map is 9010).** Repeat B26 and B22 on 9010, and note anything on the world that
changes after a close.

## The version check (last): the laptop on s167

A14 (s167's step 14) and B19 (s168), in one run: an s167 laptop still pairs with the s168 desktop and still walks, and the
guest's menu stays off for that pair.

1. **The host** loads 351 if needed, walks out onto world map 9011 and stands still, on foot.
2. **On the laptop, close FF9** and copy its `Memoria.log` aside (`Memoria-laptop.log`, or `Memoria-laptop-extras.log` if B33
   already saved the session log under that name).
   Copy `dlls-s167\x64\Assembly-CSharp.dll` into `x64\FF9_Data\Managed\` and `dlls-s167\x86\Assembly-CSharp.dll` into
   `x86\FF9_Data\Managed\`. Leave the other two DLLs: they are the same in both builds.
3. **Run the check on the laptop.** The engine line must read `engine in this install now: s167 (the fallback)`. Part 1 says
   DIFFERS for exactly two lines, `x64\Assembly-CSharp.dll` and `x86\Assembly-CSharp.dll`; the
   `x64 and x86 hold the same Assembly-CSharp.dll` line must say OK. The run prints
   `2 check(s) DIFFER: fix those lines before playing (see the README, step 0).` followed by a two-line
   `NOTE: this install runs the s167 engine (the fallback), ...`. That is expected here. Any other DIFFERS line still needs
   fixing. Keep this output: run the command again with ` > check-laptop-s167.txt` at the end.
4. **Start the laptop's game,** load its own save (with Load, its main save, not Continue), pair, and follow out. The guest
   walks a little, then presses Menu on the world map. Then the host walks into Dali, the guest rejoins, and presses Menu once
   on the field.
   - **Both pair** (the wire is still 15). The laptop's wire line shows `caps 0x0003`.
   - **The laptop walks** as in A1 and A2, and the two fingerprint digests are equal.
   - **The laptop's Menu:** the buzz only. Nothing opens; no line on screen.
   - **Laptop log,** once per place: `[NetSync] main menu suppressed (following guest) on world map 9011`, then
     `[NetSync] main menu suppressed (following guest) on field F`. No `lacks my` line on the laptop (nothing of its own is
     switched off).
   - **Host screen:** nothing new.
   - **Host log,** once:
     `[NetSync] host the partner's co-op build lacks my guest menu (its caps 0x0003, mine 0x000B) -- off for this pair: the older behaviour (t N ms)`
   - **Red tells:** the two do not pair; the laptop does NOT walk; the laptop's menu opens; the host shows *"Your partner's
     co-op build is older: they'll follow you as before."*. That last one means the laptop really runs s166: its wire line
     would read `caps 0x0001`, and the host's log would name both features,
     `[NetSync] host the partner's co-op build lacks my world fingerprint, guest menu (its caps 0x0001, mine 0x000B) -- off for this pair: the older behaviour (t N ms)`,
     plus s167's `host world: the partner's walk -- older (...)` line.
5. **Put s168 back on the laptop:** close its FF9, copy its `Memoria.log` aside again (`Memoria-laptop-skew.log`: it holds this
   step), copy the package's `dlls\x64\Assembly-CSharp.dll` into `x64\FF9_Data\Managed\` and `dlls\x86\Assembly-CSharp.dll`
   into `x86\FF9_Data\Managed\`, and run the check again: `ALL OK`, with the engine line `s168 (the package)`.

**B25 (optional): the desktop on s167, the laptop on s168.** The only way to see the guest's older-build line on screen.
- **Do:**
  - Close FF9 on the desktop and copy its `Memoria.log` aside (`Memoria-desktop.log`, or `Memoria-desktop-extras.log` if B33
    already saved one under that name). Copy the desktop's package folder's `dlls-s167\x64\Assembly-CSharp.dll` and
    `dlls-s167\x86\Assembly-CSharp.dll` into the desktop's `x64\FF9_Data\Managed\` and `x86\FF9_Data\Managed\`, and run the
    check on the desktop with ` > check-desktop-s167.txt` at the end (engine `s167 (the fallback)`, `2 check(s) DIFFER` and the
    NOTE: expected).
  - Start the desktop's game, load 351; pair, and the guest presses Menu on a field.
- **Guest screen:** the buzz and *"FF9 co-op: Your partner's co-op build is older: the shared menu stays closed."* for 4 s.
  The walk still works on the world map.
- **Guest log, once:**
  `[NetSync] client the partner's co-op build lacks my guest menu (its caps 0x0003, mine 0x000B) -- off for this pair: the older behaviour (t N ms)`,
  then `[NetSync] main menu suppressed (following guest) on field F`.
- **Then restore s168 on the desktop:** close FF9 on both machines, copy each `Memoria.log` aside (`Memoria-desktop-b25.log`,
  `Memoria-laptop-b25.log`), copy the package's `dlls\x64\` and `dlls\x86\` `Assembly-CSharp.dll` back on the desktop, and run
  the check until it says ALL OK, with the engine line `s168 (the package)`.

## If a step fails: s167 or s168?

s167 is the walk, the entrance refusal, the full map, the minimap close, the rejoin, the world battle, the link cut, the
fingerprint and the Release. s168 adds only the guest's main menu (the Menu press, the copy, the refusals, the forced closes,
the chip), plus the menu data riding every host frame. The wire is 15 for both.

1. **Name the step and note the clock time.** Was the guest's menu ever opened since that game started?
2. **A walk, fingerprint, entrance, full map, minimap, rejoin, link cut or Release fault with the menu never opened** is s167's,
   or the extra traffic's. Check both logs: are the `world fingerprint` digests equal, and what does the last
   `world walk FROZEN (WHY)` line say? Redo the step once.
3. **If the menu was opened or closed just before the failure,** or the failing line contains `guest menu`, `menu closed` or
   `main menu (`, treat it as s168's.
4. **To separate them, redo the step with no menu on either machine.** If it still fails, it is s167's (or an install or
   line-up problem: run the check again). If it passes, it is s168's.
5. **Run the check again on both machines** (it only reads) and confirm both wire lines show `caps 0x000B`. `0x0003` means that
   machine runs s167 and the guest's menu is off; `0x0001` means s166 and the walk is off too.
6. **Rolling both machines back to s167 is the only sure test.** Do it only for a fault that blocks the rest of the session, or
   when a step below fails with the menu never opened:
   - **A7** (the host battle): s168 reworked the code that builds the guest's battle view. The most likely of all.
   - **A1, A2, A5, A8**, or `lane gap` / `lane hang` lines outside a load: the menu data adds about 13 to 29 KB/s from host to
     guest.
   - **A8** (the link cut): the cut's screen lines and the session-end code gained s168 checks that do nothing with the menu
     shut.
   - **A4, A5, A9** (a rejoin or a follow-out): the least likely.

   **How:** close FF9 on BOTH machines and copy both logs aside (add `-s168` to their names). On each machine copy the package's
   `dlls-s167\x64\Assembly-CSharp.dll` and `dlls-s167\x86\Assembly-CSharp.dll` into the matching `FF9_Data\Managed\` folders,
   and run the check: the engine line must read `s167 (the fallback)` on both, with `2 check(s) DIFFER` and the NOTE (expected).
   Start both, pair, and redo only the failing Part A step (s167 has no guest menu, so Part B cannot run there). Copy both
   logs aside (`-s167bisect`). If it fails on s167 too, it is s167's; if it passes there, it is s168's. Then put s168 back on
   both (the package's `dlls\` files) and run the check until both say ALL OK with `s168 (the package)`. Claude can narrow an
   A7 fault further on its own bench; nothing more is needed from you.
7. **What to note for each failure:** the step; which screen was up (the field or world HUD, the menu and which sub-screen,
   the full map, the minimap); the host's state (field, world, riding, a scene, a battle, its own menu open); the exact line on
   screen; the clock time; whether the link stalled (`lane gap` lines are harmless around a load); the digest lines; and
   whether control came back after a Cancel or a follow. Then send both logs and both check outputs.
8. **Not faults (do not report these):** `lane hang: the partner's frames arrive but repeat (its game is not updating)` for 1 to
   3 s around a load; the follow-out landing line ending `-- frozen here until the rejoin`; the first world-map load of a game
   run taking 6 to 8 s; the guest's battle starting about 0.8 s after the host's; the host's lines during its own load showing
   late or not at all; Order, Card and Config greyed in the guest's menu.

## The look (your call)

**The walk (s167):**
1. Does the guest's walk feel like the stock game's (speed, turning, the camera)?
2. On the host, does the guest's figure keep up with the guest, without sliding or jumping?
3. When the guest is far from the host, is it clear where the host is (the dot, the figure)?
4. When the walk stops (the host rides, a scene, a battle), is it clear why?

**The entrance (s167):**
1. The stock buzz at each press: right, or too harsh?
2. The line's 4 s: too short, too long?

**The minimap and the full map (s167):**
1. The minimap close while frozen: does it feel natural?
2. The quiet hint: after you close the minimap, should the "press Select" hint stay quiet for the visit (as built), or come
   back?
3. The full-map dot: orange, under your own arrow. Is it easy to find? Right size?

**The guest's menu (s168):**
1. **The chip.** Placement, wording, and whether it is readable over every screen. Is it clear the party is the host's?
2. **The two lines.** The refusal line top right, and the close line under the status box. Is 4 s right for each?
3. **No line for refused changes.** A refused change has only the buzz and the chip. Enough?
4. **Buzzes the stock game does not make.** The full map (B22) and riding (B21) now buzz. Should they stay silent, as in the
   stock game?
5. **The status line hidden for 4 s.** The refusal line covers the world status line for its 4 s. This was a coordinator call
   you may reverse.
6. **Config and Card greyed.** Another coordinator call you may reverse.
7. **Battles.** Should every host battle close the menu?
8. **The ferry.** Should a host world-map scene close the menu? It does not today.
9. **The close line lingering.** It can stay over the next field or a battle's start.
10. **The brighten before a follow.** After a close at a sub-screen the field brightens before the follow fades it out.
11. **The overlay text over the menu.** Is the co-op text readable over the stock menu?
12. **The host's figure of the guest** standing mid-stride while the guest's world menu is open (B30): does it look wrong?

## The words (your call)

Change any of them. These are the designs' proposals.

**s167's (none answered yet):**
- the guest, at an entrance (with the buzz, 4 s): "Your partner leads the way. You'll join them at their next stop."
- the guest, paired while itself on the world map: "You'll walk once you've followed your partner into a location."
- the guest, waiting for the comparison: "Checking your world map against your partner's..."
- the guest, the world maps differ: "Your world map differs from your partner's (<part>): you'll follow them as before." The
  parts are named "language", "world script", "world map meshes", "travel controls", "world environment" and "weather colors".
- the guest, an s166 host: "Your partner's co-op build is older: you'll follow them as before."
- the guest, released, with its full map open while the host moves on: "Close the map to join your partner."
- the host, the world maps differ: "Your partner's world map differs from yours: they'll follow you as before."
- the host, the guest cannot walk yet: "Your partner can't walk yet: they'll join you at your next stop."
- the host, an s166 guest: "Your partner's co-op build is older: they'll follow you as before."
- **Not reworded yet:** while the guest walks, its line still reads s144's "Your partner is on the world map. / You'll rejoin
  them at their next stop.". Keep it, or say something about walking?
- The ~ menu's Release hint: "Enter locations alone (until the next field load). While you follow, you walk beside your partner
  on foot where the world map allows it and rejoin them at their next stop (F11 / held L3 rejoins at once); entering a location
  stays theirs. This hands the world map back to you until the next field load: walk, ride and enter a location (an entry takes
  you to your partner's field when they stand on one)."

**s168's.** Each line on screen starts "FF9 co-op: ".

Refusals:

| Reason | Words |
|---|---|
| not following yet | "You'll get the menu once you've followed your partner into a location." |
| older build | "Your partner's co-op build is older: the shared menu stays closed." |
| link | "Waiting for your partner's game: try the menu again in a moment." |
| no data | "The menu data did not arrive. Try again in a moment." |
| data differs | "Your game data differs from your partner's (<member>)." |
| host in battle | "Your partner is in a battle." |
| host busy, busy, interface, world busy, control | "Try the menu again in a moment." |
| scene | "Your partner is in a scene. Try again when it ends." |
| leaving, move, host elsewhere | "You're about to follow your partner." |
| riding | "The menu opens on foot." |
| fault | "The menu couldn't open." |
| session ending | "The co-op session is ending." |

Closes: "menu closed -- " followed by one of:
- "following your partner."
- "your partner's battle."
- "your partner's scene."
- "the co-op session is ending."
- "your partner is at the title screen."

Chip: "View only: your partner's game makes the changes."

The s166 words (the host's following, loading and scene lines, "Lost contact", the version mismatch) and s165's are still yours
to change too: they were not answered either.

## Known limits

### New in s168

- **View only, copied once.** The copy is taken at the open. Host changes show only after Cancel and reopen.
- **Lost at close.** The sort and the read marks.
- **Story displays.** Displays that depend on the story (the trance bar, chocobo bytes) show the guest's own last field-load
  copy.
- **Windows take the press.** With a window up (a conversation, a kit HUD strip), Menu does nothing, silently. A refusal at the
  moment the menu would open (after the press itself passed) can still cost a window the press closed.
- **The quit prompt holds a close** until answered, and the battle start then does not wait for the guest.
- **Content differences.** A content difference refuses the whole menu.
- **The ~ menu.** Its Heal, Give Item and Give Gil act on the copy, and the change is lost at close.
- **The host's figure of the guest** stands mid-stride while the guest's world menu is open.
- **The host in its own world menu** may refuse the guest's world open (B27).
- **A partner build that drops the feature.** If the partner stops supporting the menu while it is open, it stays open as a
  view; the next open is refused with the older-build words.
- **Bandwidth.** The menu data costs about 13-29 KB/s host to guest for the whole session, menu open or not.
- **One switch for all closes.** There is no in-game switch for one close trigger.
- **Lines with co-op off.** A refusal after co-op is turned off draws no line.
- **A world-map scene does not close the menu** (B29): only a host scene on your own field does.
- **Right after a host battle.** For about 2 s after the host's battle ends, the menu is refused with "Your partner is in a
  battle." (B12).

### New in s167 (carried)

- **The same world map, byte for byte.** Any difference in the world files on the two machines keeps the guest frozen for the
  whole session, with the words naming the part: an overworld edit after the package was made, a stray world file in another
  mod folder, or an older Memoria patcher on one machine. Step 0 checks for all three. The game names a difference but cannot
  heal it.
- **Where:** walking only on 9002, 9010 and 9011. On the other free-roam world maps (later discs, with Choco or a ship) the guest
  stays frozen with only the dot, as in s166. The full map opens only on 9010 and 9011. 9002 is still barely tested.
- **The ferry:** after the host's ferry voyage on 9011, the guest walks only on its own shore; it rejoins at the host's next
  location.
- **A host scene freezes the guest** for its length, and so does a moogle save (the host's full map does not). The s167 sheet
  said the host's main menu freezes it too; that is now in doubt, and B27 shows which.
- **A long link cut:** the guest keeps walking for up to 40 s; then the session ends and the guest's own save reloads. An open
  guest menu stays open as a view through the cut and closes when the session ends.
- **The pause screen:** if the session ends while the guest is paused on its full map, its own save can load with the full map
  still up: Select closes it. And while the pause screen or a fade is up, a guest's open full map cannot close by itself, so
  *"Close the map to join your partner."* can show even when the guest is not released; the map closes once the pause or fade
  ends.
- **A battle the guest cannot show:** if the host's world battle is one the laptop cannot load, the guest's full map closes for
  a battle that never starts on its side. It cannot open again until the host's battle ends; then Select opens it as usual.
  The guest's main menu also closes for such a battle. Nothing else is affected.
- **Entrances that warp on touch:** the entrance refusal answers a Confirm press. An entrance on 9002, 9010 or 9011 that warps
  without a press would take a walking guest in alone. None exists on either machine today, and the kit now warns when one is
  made.
- **The quiet hint is per visit:** after a minimap close it stays quiet through a battle and the ~ menu's world reload, and comes
  back after the next location.
- **WorldTPS** is compared, not synced: unequal values make the two walk at different speeds.
- **In a link stall,** a few older guards (the script's menus, the party menu, NPC talk) still lift for a guest that paired while
  itself on the world map; the walk, the entrances, world battles and the main menu stay guarded. Its Menu key is refused with
  *"You'll get the menu once you've followed your partner into a location."*. A ~ menu Release also ends if the link stalls.
- **A walking guest's last word on screen** is s144's "on the world map ... next stop" line (see The words).

### Still true from s166

- **Install:** both machines must run the same DLL and the same world-map folders, and a rollback rolls back both. Each machine
  keeps its own `FF9CustomMap` (first in the folder order); the desktop's also changes battle and character data, which this
  test does not line up, so a battle's numbers can differ between the two machines. The guest's menu checks the host's party
  against the laptop's own data: a member the laptop lacks gives *"Your game data differs from your partner's (<member>)."*
  (B1).
- **Looks:** two identical figures, with no tint or dress yet. The host's figure hides while the host rides; the dot follows.
- **In a link stall:** the dot goes at 1 s and the figure at 5 s.
- **The host's lines during its own load** can show late, briefly or not at all; they are informational only.
- **A guest that leaves for good,** on the relay or a bridge: the host keeps "Lost contact with your partner -- waiting for
  their game..." on every later world-map visit until the title, a config change or a new session.
- **The mismatch words linger** up to 15 s after an older partner quits.
- **A guest that paired or Continued on the world map** is not pulled out and does not walk (*"You'll walk once you've followed
  your partner into a location."*) until the host's next stop, and its Menu gives the buzz and *"You'll get the menu once
  you've followed your partner into a location."* (s167 opened its own menu there).
- **Unchanged from s165:** a host on the kit's new world (9013) reads as 9011 to the follow-out; do not take an entrance on 9013
  (reached only through the ~ menu): its three bench fields, 30950 to 30952, are registered on neither machine, so an entrance
  there leads to a black screen. After a host Gysahl press on 9010 or 9011, later follow-outs wait. A host that changes world
  map without a field, or walks back out while the guest's rejoin waited, leaves the guest behind until its next stop.
- **A follow-out lost halfway** (another world map loads instead, or a field loads while the link is down) can leave the host's
  world position in the guest's own story. If the guest ever arrives somewhere unexpected after a link drop during a follow-out,
  say so.
- **Log lines that are not faults:** a 1 to 3 s `lane hang: the partner's frames arrive but repeat (its game is not updating)`
  line pair around a load; the follow-out's landing line ending `-- frozen here until the rejoin` (the guest walks anyway).

## If something goes wrong (saves and stuck screens)

- **Nothing is saved while the guest's menu is open.** The only two save events in the session are expected:
  - the pairing autosave at pairing;
  - the session-end reload of the guest's own autosave, which returns it to its pairing spot with its own party (a load, not a
    save).
- **Alarm lines in the guest log.** If you see `(should never happen)`, `DROPPED without writing`, `WATCHDOG`, `fault path` or
  `faulted`:
  1. Stop the Part B steps.
  2. Quit the laptop's game (Alt+F4, Yes) and copy its `Memoria.log` aside as `Memoria-laptop-alarm.log` before anything
     else: the next start rewrites it.
  3. Restart the laptop's game. Never save over the main slot.
  4. Send `Memoria-laptop-alarm.log`.
- **The guest's game crashes or is killed with the menu open.** Copy its `Memoria.log` aside first
  (`Memoria-laptop-crash.log`), then restart and Continue: it loads the guest's own autosave or the pairing autosave. If the
  world looks wrong (the host's party, or a different place), do NOT save. Quit the game (Alt+F4, Yes) and copy its
  `Memoria.log` aside (`Memoria-laptop-after-crash.log`). With FF9 closed, rename
  `%USERPROFILE%\AppData\LocalLow\SquareEnix\FINAL FANTASY IX\Steam\EncryptedSavedData` to `EncryptedSavedData-after-fault`
  (keep it for Claude), then copy the backup's `EncryptedSavedData` folder back in its place, whole. Report it.
- **A menu that will not close, or no control after a close.** Wait 10 s. Answer or cancel any quit prompt. Press Cancel. If
  still stuck, the host walks to a new place so the guest is pulled by a follow. Last resort: Alt+F4 then Yes, or
  `taskkill /F /IM FF9.exe`; copy its `Memoria.log` aside (`Memoria-laptop-stuck.log`) before starting it again; Continue then
  loads the guest's own autosave. Note the exact state: which screen, the host on a field or the world map, any prompt up.
- **Do not use the guest's ~ menu Heal, Give Item or Give Gil** while its menu is open: they act on the copy and are lost.
- **Do not change in-game settings on the guest** during the session: they revert when the session ends.
- **The host's changes are real.** Swap B7's weapon back. Do not save over 351 during the session.
- **DLL changes.** On the laptop, change DLLs only from the package or the step-0 backup. On the desktop, only from the package
  folder or through `restore_memoria_dll.py`, always with FF9 closed, and run the check after each change.

## What to send back

- Both `Memoria.log` files (`FINAL FANTASY IX\Memoria.log` on each machine), named `Memoria-desktop.log` and
  `Memoria-laptop.log`. Copy each one before starting that game again; add `-skew`, `-s168`, `-s167bisect`, `-b25`,
  `-before-B20`, `-B15`, `-B32`, `-alarm`, `-crash`, `-after-crash` or `-stuck` for the runs named above. If B33 was run, name
  each machine's later log `-extras` (`Memoria-desktop-extras.log`, `Memoria-laptop-extras.log`). Do not trim them.
- Both machines' `check-s168.ps1` output (`check-desktop.txt`, `check-laptop.txt`), `check-laptop-s167.txt` from the version
  check, `check-desktop-s167.txt` if B25 ran, and `check-laptop-before.txt` if step 0 took it.
- Every save listing (`saves-1.txt`, `saves-2.txt`, ...).
- The guest's own values from step 0, and again after B16.
- The session's rough times (the two machines' clocks differ by about 2 s).
- Which input each machine used (keyboard or pad).
- A result for each step, A and B.
- Your answers on the look and the words.
- The videos (the guest's screen for A1 to A9 and B8 to B13; the host's for A2, A7 and A8) and the screenshots: B8, B30, the
  menu's root with the chip and the greyed rows, one screen each of Status, Equip, Abilities and Items, any refusal line and
  any close line.
- If a mods or fingerprint line differs: each machine's `Memoria.ini` `[Mod]`, `[Netsync]`, `[Cheats]` and `[Graphics]` lines.

## Going back to s167 or s166

Do it on both machines, with FF9 closed:
- **To s167:** each machine copies the package's `dlls-s167\x64\Assembly-CSharp.dll` and `dlls-s167\x86\Assembly-CSharp.dll`
  into the matching `FF9_Data\Managed\` folders and runs the check (engine line `s167 (the fallback)`, `2 check(s) DIFFER` and
  the NOTE). The desktop may instead run `py tools/restore_memoria_dll.py <S167_SNAPSHOT_TS>` in `C:\gd\Dream-World-IX`. That
  tool prints no sha, so run the check after it: the engine line must read `s167 (the fallback)`.
- **To s166:** the laptop puts back the six DLLs from its step-0 backup if that backup is s166 (`check-laptop-before.txt`
  names it, if step 0 took it), or else from the backup it made in the s167 package's step 0 (that README's example name was
  `Desktop\FF9-backup-s166`), each arch from its own subfolder, and keeps `Memoria.ini` and the three world folders as they
  are. The desktop runs
  `py tools/restore_memoria_dll.py 20261106-031939` (s166, `b24e0123`) in `C:\gd\Dream-World-IX`. Then each runs the check:
  the engine line reads `s166 (the old engine)`, and the two `Assembly-CSharp.dll` lines in part 1 say DIFFERS
  (`2 check(s) DIFFER`, no NOTE). That is expected after this rollback.

Still open from s166, no test needed: is the FF9Coop mod folder (it reroutes the chocobo-dive return to field `1953`, listed
last in `[Mod] FolderNames`) still wanted?

## Results
