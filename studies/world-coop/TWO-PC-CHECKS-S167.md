# FF9 Co-op: laptop update package (2026-11-06, s167)

**Engine in this package:** `Assembly-CSharp.dll` `12be3220520813a6...` (both arches). `HASHES.txt` lists the six DLLs. Only
`Assembly-CSharp.dll` changed; `Memoria.Prime.dll` and `UnityEngine.UI.dll` are the same files as in the s166 package, included
so the set is complete. The desktop already runs this build. The package holds s167 and everything before it, so it replaces
the s166 package and every earlier one.

**The three mod folders are unchanged.** `FF9CustomMap-world` (2,779 files), `FF9CustomMap-schema` (25) and `FF9CustomMap-msgs`
(146) are byte for byte the s166 package's: the same 2,950 files with the same SHA256s, listed in `FOLDERS-MANIFEST.txt`. The
laptop already has them from s166, so it copies them again only if step 0 says one differs. As before, they are the desktop's
folders minus its tool backups (`*.bak-*`) and empty `.lock` files, which the game never reads.

**The version rule.** The co-op wire stays at version 15, so an s167 game still pairs with an s166 one. Nobody walks then: the
pair plays s166's world map (the guest frozen, as before), and the s167 side says so:

> FF9 co-op: Your partner's co-op build is older: you'll follow them as before.

(on an s167 guest), or *"Your partner's co-op build is older: they'll follow you as before."* (on an s167 host). The walk needs
BOTH machines on s167 AND the same world map on both, checked byte for byte (step 0).

**New in the package:** `check-s167.ps1`, a read-only check that compares a machine with this package (step 0), and
`DATA-WORLD-HASHES.txt`, the hashes of three base-game world files it compares too.

## What's new (s167: the guest walks)

- **The guest walks.** A following guest now walks its own copy of the world map on foot, beside the host, with its own
  controls and camera. Each game draws the other player as a second figure, as in s166. This works on three world maps, 9002,
  9010 and 9011 (the Disc 1 ones with no vehicle; 9011 is the kit's world, with the Southern Ring). The guest never meets its
  own random battles while it walks. It still cannot save, and the host still leads: the guest rejoins the host at the host's
  next stop, wherever it has walked to.
- **The guest stops walking (it freezes, as in s166) while** the host rides (Choco, the boat), the host is in a world-map
  scene, the host is in a battle or a location, or the two world maps differ. It shows why: *"Your partner is riding. You'll
  rejoin them at their next stop."*, *"Your partner is in a world-map scene. You'll rejoin them at their next stop."*, or one of
  the lines below. It walks again on its own once the reason ends.
- **Entrances stay the host's.** When the guest presses Confirm at an entrance (a stock location, one of the Southern Ring's
  entrances, the boat, the ferryman), it hears the stock buzz and sees, for 4 seconds:

  > FF9 co-op: Your partner leads the way. You'll join them at their next stop.

  Nothing else happens: no fade, no load. The same buzz and line answer a frozen guest on those three world maps.
- **The minimap closes again** (s166 finding 1). While the guest is frozen, Select on its minimap now closes it, with no buzz,
  and Select opens it again. Then the s165 hint, *"Your partner is on the world map: press Select for the minimap."*, stays quiet
  for the rest of that world-map visit. A visit starts when the world map loads from a field or the title; a world battle and
  the ~ menu's world reload keep the same visit, so the hint stays quiet after them and comes back after the next location.
- **The full map, for a walking guest on 9010 and 9011.** Select on the minimap opens the full map, as in the stock game, with
  the host's orange dot on it. On foot, Confirm on a place does nothing, as in the stock game. If the host enters a location, or
  a host world battle starts, while the guest's full map is open, the map closes by itself first. On 9002, and whenever the
  guest is frozen, Select still goes straight from the minimap to no minimap.
- **The two world maps are compared.** At every world-map load each game logs a "fingerprint" of its world map: the language,
  the world script, every world-map file the game read, and three base-game world tables (travel controls, environment,
  weather). If the two differ, the guest stays frozen for that world map and both games say so: the guest *"Your world map
  differs from your partner's (<part>): you'll follow them as before."*, the host *"Your partner's world map differs from yours:
  they'll follow you as before."*. While the guest's game waits for the comparison it shows *"Checking your world map against
  your partner's..."*, and on the host *"Your partner can't walk yet: they'll join you at your next stop."* can show for the
  same wait.
- **WorldTPS is compared.** If the two machines' `[Graphics] WorldTPS` differ, each log says so once. Nothing changes in the
  game (each player walks its own copy at its own speed), but keep them equal.
- **The ~ menu's Release stays.** Its hint now starts "Enter locations alone (until the next field load).": the walk already
  gives the guest its feet, and the Release adds entering locations on its own.

**What was proven, and where.** Everything ran on the desktop, on this exact DLL, on 2026-11-06, never on two PCs:
- One game against a simulated host: the guest walked on 9011 and on 9002; it kept walking through a short simulated stall;
  the entrance line and buzz; the minimap close and the quiet hint; the full map for a walker on 9010 and 9011; the words
  for the reasons the walk stops (a guest paired on the world map, a fingerprint mismatch, and others).
- Two games on one PC (a 25-check run): the guest walked 26 u on 9011 and the host's figure of it matched its steps; the host
  entered a location and pulled the guest in from 538 u away; a host world battle pulled the guest into the battle view and
  returned it at its own spot; the entrance buzz answered at a stock location, a Southern Ring entrance, the boat plate and the
  ferryman. The fingerprint costs about 2.4 ms plus 30.7 ms per world-map load (626 files read, 13.1 MB).
- 38 more launches with the walk switched off reproduced s166 and everything before it.
- Never run: two machines' fingerprints compared (this session is the first time two installs meet), a real network cut while
  the guest walks, the ~ menu Release with the walk, the "Close the map" line, the hint on screen, the vehicle worlds and the
  quicksand. Those are in the steps below.

One bench check stays red by design, as in s166: it needs a recording of you walking the world map as the host on this build,
which only you can make. Claude will ask for it separately.

## Install on the laptop (close FF9 and the Memoria launcher on both machines first)

Unzip the package anywhere outside the FF9 folder (for example the Desktop). It holds one folder,
`FF9Coop-laptop-update-20261106-s167`. The desktop has the same folder on its own Desktop.

### Step 0: back up, copy, and check both machines (before any test)

1. **Back up the laptop.** Make a folder outside the FF9 folder (for example `Desktop\FF9-backup-s166`) with two subfolders,
   `x64` and `x86` (the two arches' DLLs share their names), and copy:
   - `x64\FF9_Data\Managed\Assembly-CSharp.dll`, `Memoria.Prime.dll` and `UnityEngine.UI.dll` into its `x64` subfolder;
   - the same three from `x86\FF9_Data\Managed\` into its `x86` subfolder;
   - `FINAL FANTASY IX\Memoria.ini` (the one beside `Memoria.log`; ignore any `x64\Memoria.ini`) into the folder itself.
2. **The DLLs:** copy the three files from the package's `dlls\x64\` into `FINAL FANTASY IX\x64\FF9_Data\Managed\`, and the
   three from `dlls\x86\` into `FINAL FANTASY IX\x86\FF9_Data\Managed\`.
3. **Leave the mod folders alone for now.** Do not copy `FF9CustomMap-world`, `-schema` or `-msgs` unless the check below says
   one of them differs.
4. **Run the check, on BOTH machines.** With FF9 closed, open PowerShell in the package folder (in Explorer, right-click an
   empty spot in the folder and choose Open in Terminal) and run:

   ```
   powershell -NoProfile -ExecutionPolicy Bypass -File .\check-s167.ps1
   ```

   If FF9 is not in the default Steam folder, name it:

   ```
   powershell -NoProfile -ExecutionPolicy Bypass -File .\check-s167.ps1 -Game "D:\SteamLibrary\steamapps\common\FINAL FANTASY IX"
   ```

   It changes nothing. It prints `OK` or `DIFFERS` on each line, in four parts, and ends with either
   `ALL OK: this machine matches the s167 package.` or `N check(s) DIFFER: fix those lines before playing (see the README, step 0).`
   **Both machines must end with ALL OK.** Keep both outputs: select the window's text and copy it, or run the command again
   with ` > check-laptop.txt` (or ` > check-desktop.txt`) at the end. What to do for each kind of `DIFFERS` line:
   - **1. the DLLs** (`x64\Assembly-CSharp.dll` and the others): copy the DLLs from the package again (item 2). On the desktop,
     stop and ask Claude: its install is shared with Claude's benches, so a different DLL there means something changed it.
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
     harmless while part 4 says OK.
5. **No overworld edits on the desktop until the session.** The World tab's promotes, and any Claude session working on the
   overworld, write `FF9CustomMap-world`, and a single changed byte keeps the guest frozen. If you do edit, run the check on the
   desktop again before playing.
6. **The rest of `Memoria.ini`, unchanged from s166** (check them on the laptop):
   - the guest keeps `[Netsync] FollowHost = 1`;
   - both machines use the same `[Cheats] SpeedFactor`, `[Graphics] FieldTPS` and `[Graphics] WorldTPS`. The desktop runs
     `SpeedFactor = 3`, `FieldTPS = 30` and `WorldTPS = 28`; WorldTPS's default is 20, so check the laptop's;
   - both use the same language (the fingerprint compares it) and the same voice-acting setting.

### Step 0, in the game: the line-up

`Memoria.log` is in the FF9 folder itself, beside `Memoria.ini`: on the desktop
`C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX\Memoria.log`, on the laptop `FINAL FANTASY IX\Memoria.log` in
its own FF9 folder. Every start of the game rewrites it.

1. **The wire line.** Once co-op is running (from the first field that loads with co-op on), each log shows:
   `[NetSync] own wire: this engine speaks wire 15 (caps 0x0003) on the relay -- the partner's engine must speak the same`
   `caps 0x0001` there means that machine still runs s166.
2. **The fingerprint lines.** Once both games stand on the same world map (after step 1 below), each log holds a line like
   `[NetSync] world fingerprint: world map 9011 digest 0xXXXXXXXX -- language US, dispatcher 0x..., meshes 0x..., transport 0x..., environment 0x..., weather 0x... -- c2 over N override reads (N KB) -- N ms at the seam + N ms inside the engine's reads ([Mod] MergeScripts N, N mod folders: never hashed raw)`
   one per world-map load. Take the LAST line for that world map on each machine: the two `digest 0x...` values must be equal.
   If they are not, the six values after `--` say which part differs: `language` (the game's language), `dispatcher` (the world
   script), `meshes` (the world-map files the game read), `transport` (the travel-controls table), `environment`, `weather`.
   The guest's log also names it, once per visit:
   `[NetSync] world fingerprint: my world map W differs from the host's -- the PART (NAME: mine 0x..., the host's 0x...) -- the walk stays frozen ("Your world map differs from your partner's (PART): you'll follow them as before."); s165's follow-out is never gated by it (t N ms)`
   and the host's:
   `[NetSync] host world fingerprint: the partner's world map W differs from mine (my digest 0x..., the guest's 0x...) -- "Your partner's world map differs from yours: they'll follow you as before." (the guest's own line names the component) (t N ms)`
   For the language it reads `the language (mine US, the host's FR: the loaded language only)` (with the two languages). If the
   digests differ, stop the walking steps (the rest of s166's behaviour still works), and send both logs and both check
   outputs.
3. **Only if the guest stays on "Checking your world map against your partner's..."** for more than 10 seconds, its log says
   `[NetSync] world fingerprint: still checking after N ms on world map W -- my digest ..., the host's ... -- the walk stays frozen until both are ready (t N ms)`
   with the reason in the two middle parts. Send the log.
4. **WorldTPS.** If the two differ, each log shows, once:
   `[NetSync] client world speed differs: my [Graphics] WorldTPS is 20, the partner's 28 -- each walks its own copy at its own speed (keep WorldTPS equal on both machines) (t N ms)`
   (`host` instead of `client` on the desktop, the numbers swapped). Fix the laptop's `WorldTPS` before the next start.
5. **The mods line** (`[Initialization] Mods: ...` near the top of each log) lists the same seven folders on both machines, in
   any order once part 4 of the check says OK.

## What to try (the desktop hosts, the laptop is the guest)

**The same route as in s166 works:** the desktop loads its save (351, Dali, the morning after the inn rest) and walks out onto
the world map (9011); the laptop loads its own save and pairs on its field (last time field 250). A video of the guest's screen
helps most, and of the host's screen during steps 2, 7 and 8. Steps 1 to 9 are the core (about 20 minutes); the extras after
them are optional.

**How to read the lines below:**
- On screen, every co-op line starts with `FF9 co-op:`; a ` / ` inside a quoted screen line is a line break.
- In `Memoria.log`, each line follows the date, the time and `|M|`.
- Capital letters stand for numbers: F a field, W a world map, X and Z a position, E an entrance, N a count or milliseconds,
  0xNN a byte.
- `(t N ms)` at the end is the engine's own clock.
- Lines not quoted here (s144 to s166, field co-op) print as before.
- **The guest's walk log:** each time the guest starts or stops walking, its log says one of these:
  - `[NetSync] world walk FREE on world map W: the guest walks its own copy on foot (the host on foot on this world map; entering a location stays the host's)`
  - `[NetSync] world walk FROZEN (WHY) on world map W: WORDS -- travel input held` (it was walking, and stopped)
  - `[NetSync] world freeze ON (live) on world map W: travel input held -- the walk waits (WHY: WORDS)` (it is frozen when a
    world map starts, before it may walk)

  WHY is a short name, WORDS its explanation, for example `riding: the host is riding`, `host_scene: the host is in a
  world-map scene`, `host_not_world: the host is not on the live world map`, `transition: a world transition is in flight`,
  `not_live: the bee scene, an event world or a diorama` (the battle view), `checking: checking my world map against the
  partner's`, `fp_mismatch: the world maps differ`, `old_partner: the partner's co-op build is older (no world fingerprint)`.
  The words always name the reason.

1. **Pair and follow out (as in s166).** The host loads its save, walks out onto the world map (9011) and stands still. Then the
   guest loads its own save and pairs as usual, on its own field.
   - **Guest screen:** as in s166: *"Following your partner out onto the world map..."*, a fade, and the world map, with the
     guest on the host's spot. Then, new: within a few seconds of the landing (the first world-map load of a game run is slow,
     about 6 to 8 s, as in s166), the guest can walk. *"Checking your world map against your partner's..."* may show briefly
     first.
   - **Host screen:** as in s166: *"Your partner is following you out onto the world map..."*, then *"Your partner is loading
     the world map..."*, then the guest's figure on the host's spot. *"Your partner can't walk yet: they'll join you at your
     next stop."* may show briefly.
   - **Guest log:** s166's step-1 lines (the pairing autosave, the follow-out's start, commit and landing, ARMED, the ghost's
     two lines), then `[NetSync] world fingerprint: world map 9011 digest 0x...` and
     `[NetSync] world walk FREE on world map 9011: the guest walks its own copy on foot (the host on foot on this world map; entering a location stays the host's)`
     (perhaps after one `world freeze ON (live) ... the walk waits (...)` line). The landing line still ends `-- frozen here
     until the rejoin`: an old wording, not a fault.
   - **Host log:** s166's `host world: the partner is following` and `... is loading` lines.
   - **Now compare the fingerprint lines** (step 0, "in the game", item 2).
   - **Red tells:** the guest cannot move after 15 s: read the reason on its screen and in its last `world walk FROZEN` or
     `world freeze ON` line, and send the log.
2. **The guest walks.** The guest walks around the host, then away from it, off the host's screen and back.
   - **Guest screen:** the guest walks, runs and stops with its own controls, and its camera follows it. The host's figure stands
     or walks where the host is. While the guest walks, its line at the top right is s144's *"Your partner is on the world map. /
     You'll rejoin them at their next stop."* (or the s165 hint if its minimap is off).
   - **Host screen:** the guest's figure walks where the guest walks, on the ground, playing the guest's own walk, run and stand.
   - **Logs:** nothing new while walking.
   - **Red tells:** the guest is pulled back to the host's spot; the guest's figure on the host stands still while the guest
     walks; a battle starts on the guest's game alone; a `world walk FROZEN` line while the host stands on foot on the same
     world map.
3. **An entrance.** The guest walks to an entrance on the world map (Dali's is the nearest stock one) and presses Confirm there,
   then once more. If a Southern Ring entrance, the boat or the ferryman is within reach, try one of those too (optional).
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
4. **The full map (a walking guest on 9010 or 9011).** If the guest shows no minimap, it presses Select once to bring it up.
   Then, with its minimap up, the guest presses Select.
   - **Guest screen:** the full map opens, as in the stock game, with the host's dot on it (orange, under the guest's own arrow).
     Move the cursor over a place and press Confirm: nothing happens (on foot, as in the stock game). Press Select: the map
     closes to no minimap. The line at the top right now stays s144's (the "press Select" hint stays quiet; see step 6). Press
     Select again: the minimap is back.
   - **Then the map and the rejoin:** the guest opens its full map again and leaves it open. **Before the host goes in, it turns
     its own minimap off** (Select on the host until no map shows): that sets up step 5. Then the host walks into a location
     (back into Dali, or any other).
   - **Guest screen:** the full map closes by itself, then the guest follows the host into that field and lands with control.
   - **Host screen:** nothing new.
   - **Guest log:**
     - `[NetSync] world map: the full map opens for the walking guest on world map 9011 (decision 8: the partner's dot rides it, its location pick stays the host's; a rejoin, the host's world battle or the session's end closes it first)` (once per visit)
     - `[NetSync] world dot: minted 'ff9mk coop host dot (full map)' from the full map's player pointer (...) -- the dot at depth 27 under the arrow` (once per world-map load)
     - `[NetSync] world map: the full map closed for the rejoin to field F on world map 9011 -- WorldHUD's own Select close replayed (control back; no minimap until the next Select)`
     - a `world walk FROZEN (...)` line, then `[NetSync] world rejoin landed on field F after N ms`.
   - **Red tells:** the map does not open (a buzz instead); no orange dot on it; the map stays open and the guest stays on the
     world map; after the landing the guest has no control.
5. **Out again, and the pull from far away.** On that field, the host walks out onto the world map. The guest follows out as in
   step 1. **The hint:** the guest lands with no minimap (the host turned its own off in step 4), so its screen shows
   *"Your partner is on the world map: press Select for the minimap."*. Leave it. Then the guest walks far away from the host,
   off the host's screen, and the host walks into a location.
   - **Guest screen:** the guest is pulled from where it stands into the host's field, as in step 4.
   - **Host screen:** nothing new.
   - **Guest log:** a `world walk FROZEN (...)` line, then `[NetSync] world rejoin landed on field F after N ms`.
   - **Red tells:** no hint at the landing (with no minimap showing); the guest stays on the world map; it lands somewhere other
     than the host's field.
6. **The minimap while frozen, and the quiet hint.** Out again (the host walks out, the guest follows; the hint shows again,
   because this is a new visit). The guest presses Select once, so its minimap is up. Then the host calls Choco from its ~ menu
   (the Go tab, as in s166) and rides for a while.
   - **Guest screen:** while the host rides, the guest cannot walk, and its line reads *"Your partner is riding. You'll rejoin
     them at their next stop."*. Now the guest presses Select: the minimap closes at once, with no buzz (last session it could
     not close). Then the host gets off: the guest walks again, and its line reads s144's *"Your partner is on the world map. /
     You'll rejoin them at their next stop."*, not the "press Select" hint, for the rest of this visit (a battle in step 7 keeps
     it quiet). Select still opens the minimap.
   - **Host screen:** nothing new.
   - **Guest log:**
     - `[NetSync] world walk FROZEN (riding) on world map 9011: the host is riding -- travel input held`
     - `[NetSync] world minimap closed by Select on world map 9011 (following guest, frozen): straight to no minimap -- no buzz, control untouched, Select opens it again; s165's minimap hint stays quiet for this world-map visit`
     - `[NetSync] world walk FREE on world map 9011: ...` once the host is on foot.
   - **Red tells:** a buzz and the minimap staying open (s166's defect); the "press Select" hint back on screen in the same
     visit; Select no longer opening the minimap.
7. **A host battle while the guest walks.** The guest walks a little away from the host. The host walks until a random battle
   starts.
   - **Guest screen:** the host's figure disappears at the host's swirl, and the guest's game shows the host's battle, as in
     s145 (if the guest's full map was open, it closes first). After the battle the guest is back on the world map at ITS OWN
     spot, not the host's, and walks again once the host is back on foot. If the guest was busy when the battle started (a menu,
     a fade), it sits the battle out on the world map, frozen, and walks again after it, as in s145.
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
8. **A link cut while the guest walks.** Both on the world map, the guest walking.
   - **What to do:** as in s166: turn the laptop's network off for about 10 seconds while the guest keeps walking, then turn it
     back on. Keep the whole cut under 30 s: past 40 s the session ends and the guest's own save reloads.
   - **Guest screen:** the guest keeps walking through the whole cut. The host's figure stops and stands; after about 1 s the dot
     goes; at about 2 s *"the host's game went silent -- reconnecting (N s left) / the session waits for it; if it doesn't return,
     your own save reloads"*; at 5 s the figure goes. When the network is back the line clears, and the dot and the figure return
     where the host is.
   - **Host screen:** the guest's figure stands where it was. At 5 s it goes, with *"Lost contact with your partner -- waiting
     for their game..."*. When the link is back, the line clears and the figure reappears where the guest has walked to.
   - **Logs:** s166's step-7 lines on both machines (`lane gap`, `session: the host went silent`, `session: the host is back`,
     `lane gap over`, the host's `the partner is lost`). New: no `world walk FROZEN` line on the guest during the cut.
   - **This is the first real cut while walking:** the bench only simulated a short stall.
   - **Red tells:** the guest cannot walk during the cut; it is pulled to the host's spot; the session ends inside 40 s.
9. **The ~ menu Release (the guest).** Two parts, each ending with a rejoin.
   - **a. The "Close the map" line.** Stay on the world map after step 8, the guest on foot. The guest opens its ~ menu
     (tilde), the Go tab, and under "Co-op world map" presses *"Co-op: release world freeze (until the next field load)"* (it
     then reads *"Co-op: world freeze released (until the next field load)"*). The guest presses Select until its full map
     shows (from no minimap that is two presses: the first brings the minimap back) and leaves it open. Then the host walks
     into a location.
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
       happens next: the guest should follow the host back out onto the world map shortly after it lands, as in step 1.
     - **Host screen:** the host's lines as in step 1 if the guest follows out.
     - **Guest log:** the RELEASED line, then the field's load, and s166's follow-out lines if it follows out.
     - **Red tells:** a buzz and the entrance line (the Release did not take); the guest stuck on the field.

**Optional extras (each needs nothing more than above unless it says so):**

10. **The ferry (kit 9011).** The host takes the ferry voyage (talks to the ferryman) while the guest walks nearby.
    - **Guest screen:** during the voyage the guest is frozen with *"Your partner is in a world-map scene. You'll rejoin them at
      their next stop."*. Once the host lands across the water, the guest walks again, on its own shore. The boat and the
      ferryman answer it with the buzz and the entrance line. It rejoins the host at the host's next location.
    - **Guest log:** `[NetSync] world walk FROZEN (host_scene) on world map 9011: the host is in a world-map scene -- travel input held`,
      then FREE.
    - **Red tells:** the guest crosses the water alone; it stays frozen after the host lands.
11. **World map 9002** (needs a save whose world map is 9002; both figures are Dagger there). As steps 1 to 3, with one
    difference: on 9002 a walking guest's Select goes straight from the minimap to no minimap (no full map). Its minimap on 9002
    has never been seen in game: say what shows.
12. **A vehicle world** (needs a later-disc save on a world map with Choco, a ship or an airship: 9000, 9003, 9005, 9007, 9008 or
    9009). The guest follows out and stays frozen there the whole time, as in s166: no walking, only the dot. Check that Select
    on its minimap closes it (no buzz), that a Confirm at an entrance does nothing (no buzz, no line: the buzz is for 9002, 9010
    and 9011 only), and that both logs show a `world fingerprint` line for that world map with equal digests. If the host flies
    the airship, try the minimap close during the flight too.
13. **The quicksand** (skip unless it is easy: world maps 9003 or 9009, later discs). It tests only a guest that loaded its
    own save ON the world map, standing on a quicksand pit, and paired there; a guest that followed the host out is already
    covered. During a link cut of a few seconds that guest presses Confirm on the pit: nothing should happen on its side, and
    no battle starts on the guest alone. Its log may say
    `[NetSync] scripted world battle (..., scene 144) suppressed (following guest) on world map W`.
14. **The version check (last).** On the laptop, close FF9 and copy its `Memoria.log` aside first. Put back the s166
    `Assembly-CSharp.dll` from the step-0 backup (its `x64` copy into `x64\FF9_Data\Managed\` and its `x86` copy into
    `x86\FF9_Data\Managed\`), start the game, pair, and follow out.
    - **Both pair** (the wire is still 15). The laptop (s166) behaves as last session: frozen on the world map, and its minimap
      cannot close (s166's defect).
    - **Host (desktop) screen**, while the guest stands on the same world map: *"Your partner's co-op build is older: they'll
      follow you as before."*.
    - **Host log**, once: `[NetSync] host the partner's co-op build lacks my world fingerprint (its caps 0x0001, mine 0x0003) -- off for this pair: the older behaviour (t N ms)`
      and once the line shows:
      `[NetSync] host world: the partner's walk -- older ("Your partner's co-op build is older: they'll follow you as before.") -- the guest's state 0xNN, why 0xNN, caps 0x0001 (t N ms)`
    - **Then put s167 back** on the laptop: close its FF9 (copy its `Memoria.log` aside again: it holds this step), copy the
      package's `dlls\x64\Assembly-CSharp.dll` into `x64\FF9_Data\Managed\` and `dlls\x86\Assembly-CSharp.dll` into
      `x86\FF9_Data\Managed\`, and run the check again: ALL OK.
    - **Red tells:** the two do not pair; the laptop walks.

## The look (your call)

**The walk:**
1. Does the guest's walk feel like the stock game's (speed, turning, the camera)?
2. On the host, does the guest's figure keep up with the guest, without sliding or jumping?
3. When the guest is far from the host, is it clear where the host is (the dot, the figure)?
4. When the walk stops (the host rides, a scene, a battle), is it clear why?

**The entrance:**
1. The stock buzz at each press: right, or too harsh?
2. The line's 4 s: too short, too long?

**The minimap and the full map:**
1. The minimap close while frozen: does it feel natural?
2. The quiet hint: after you close the minimap, should the "press Select" hint stay quiet for the visit (as built), or come
   back?
3. The full-map dot: orange, under your own arrow. Is it easy to find? Right size?

## The words (your call)

Change any of them. These are the design's proposals:

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

The s166 words (the host's following, loading and scene lines, "Lost contact", the version mismatch) and s165's are still yours
to change too: they were not answered last session.

## Known limits (s167)

**New in s167:**
- **The same world map, byte for byte.** Any difference in the world files on the two machines keeps the guest frozen for the
  whole session, with the words naming the part: an overworld edit after the package was made, a stray world file in another
  mod folder, or an older Memoria patcher on one machine. Step 0 checks for all three. The game names a difference but cannot
  heal it.
- **Where:** walking only on 9002, 9010 and 9011. On the other free-roam world maps (later discs, with Choco or a ship) the guest
  stays frozen with only the dot, as in s166. The full map opens only on 9010 and 9011. 9002 is still barely tested.
- **The ferry:** after the host's ferry voyage on 9011, the guest walks only on its own shore; it rejoins at the host's next
  location.
- **A host scene freezes the guest** for its length, and so does the host's main menu or a moogle save (the host's full map does
  not).
- **A long link cut:** the guest keeps walking for up to 40 s; then the session ends and the guest's own save reloads.
- **The pause screen:** if the session ends while the guest is paused on its full map, its own save can load with the full map
  still up: Select closes it. And while the pause screen or a fade is up, a guest's open full map cannot close by itself, so
  *"Close the map to join your partner."* can show even when the guest is not released; the map closes once the pause or fade
  ends.
- **A battle the guest cannot show:** if the host's world battle is one the laptop cannot load, the guest's full map closes for
  a battle that never starts on its side. It cannot open again until the host's battle ends; then Select opens it as usual.
  Nothing else is affected.
- **Entrances that warp on touch:** the entrance refusal answers a Confirm press. An entrance on 9002, 9010 or 9011 that warps
  without a press would take a walking guest in alone. None exists on either machine today, and the kit now warns when one is
  made.
- **The quiet hint is per visit:** after a minimap close it stays quiet through a battle and the ~ menu's world reload, and comes
  back after the next location.
- **WorldTPS** is compared, not synced: unequal values make the two walk at different speeds.
- **In a link stall,** a few older guards (some menus) still lift for a guest that paired while itself on the world map; the
  walk, the entrances and world battles stay guarded. A ~ menu Release also ends if the link stalls.
- **A walking guest's last word on screen** is s144's "on the world map ... next stop" line (see The words).

**Still true from s166:**
- **Install:** both machines must run the same DLL and the same world-map folders, and a rollback rolls back both. Each machine
  keeps its own `FF9CustomMap` (first in the folder order); the desktop's also changes battle and character data, which this
  test does not line up, so a battle's numbers can differ between the two machines.
- **Looks:** two identical figures, with no tint or dress yet. The host's figure hides while the host rides; the dot follows.
- **In a link stall:** the dot goes at 1 s and the figure at 5 s.
- **The host's lines during its own load** can show late, briefly or not at all; they are informational only.
- **A guest that leaves for good,** on the relay or a bridge: the host keeps "Lost contact with your partner -- waiting for
  their game..." on every later world-map visit until the title, a config change or a new session.
- **The mismatch words linger** up to 15 s after an older partner quits.
- **A guest that paired or Continued on the world map** is not pulled out and does not walk (*"You'll walk once you've followed
  your partner into a location."*) until the host's next stop. (s167 closes its link-stall gap.)
- **Unchanged from s165:** a host on the kit's new world (9013) reads as 9011 to the follow-out; do not take an entrance on 9013
  (reached only through the ~ menu): its three bench fields, 30950 to 30952, are registered on neither machine, so an entrance
  there leads to a black screen. After a host Gysahl press on 9010 or 9011, later follow-outs wait. A host that changes world
  map without a field, or walks back out while the guest's rejoin waited, leaves the guest behind until its next stop.
- **A follow-out lost halfway** (another world map loads instead, or a field loads while the link is down) can leave the host's
  world position in the guest's own story. If the guest ever arrives somewhere unexpected after a link drop during a follow-out,
  say so.
- **Log lines that are not faults:** a 1 to 3 s `lane hang: the partner's frames arrive but repeat (its game is not updating)`
  line pair around a load; the follow-out's landing line ending `-- frozen here until the rejoin` (the guest walks anyway).

## What to send back

- Both `Memoria.log` files (`FINAL FANTASY IX\Memoria.log` on each machine). Copy each one before starting that game again.
- Both machines' `check-s167.ps1` output.
- The session's rough times.
- Your answers on the look and the words.
- The videos.

If you need to go back to s166, do it on both machines:
- the laptop puts back the six DLLs from its step-0 backup (each arch from its own subfolder), and keeps `Memoria.ini` and the
  three world folders as they are (s166 ran with them too);
- the desktop runs `py tools/restore_memoria_dll.py 20261106-031939` (s166, `b24e0123`), with FF9 closed, in
  `C:\gd\Dream-World-IX`.

Still open from s166, no test needed: is the FF9Coop mod folder (it reroutes the chocobo-dive return to field `1953`, listed
last in `[Mod] FolderNames`) still wanted?

## Results
