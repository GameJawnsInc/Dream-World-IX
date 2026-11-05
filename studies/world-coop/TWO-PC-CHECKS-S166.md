# FF9 Co-op: laptop update package (2026-11-04, s166)

**Engine in this package:** `Assembly-CSharp.dll` `b24e0123ac93960c...` (both arches). `HASHES.txt` lists the six DLLs. Only
`Assembly-CSharp.dll` changed; `Memoria.Prime.dll` and `UnityEngine.UI.dll` are the same files as before, included so the set is
complete. The desktop already runs this build. The package holds s166 (round A) and everything before it, so it replaces the
s165 package and every earlier one.

**Both machines MUST run this DLL.** s166 moves the co-op wire from version 14 to 15, so an s166 game and an s165 (or older)
game never pair. The s166 game says so on screen:

> FF9 co-op: Your partner's co-op version doesn't match yours: update both games.

and its log says, once: `[NetSync] the partner's engine speaks wire 14, this one speaks 15 -- update both machines`. The older
game has no words for it: it keeps its ordinary connecting or waiting line and never pairs. If you ever roll back, roll back
both machines together.

**Three mod folders come with it** (s165 finding 3): `FF9CustomMap-world` (44,031,200 bytes in 2,779 files; Explorer shows about 42 MB), `FF9CustomMap-schema` and `FF9CustomMap-msgs`,
copied from the desktop's install, so both machines load the same world map. Step 0 lines the two installs up and checks them.
`FOLDERS-MANIFEST.txt` lists every file of the three folders with its SHA256. They are the desktop's folders minus its tool
backups (`*.bak-*`) and empty `.lock` files, which the game never reads.

## What's new (s166 round A: you see each other on the world map; the guest is still frozen)

- **You see each other, both ways.** On the guest, the host is a second figure (the ghost) that walks where the host walks.
  On the host, the frozen guest is a second figure standing where the guest landed. Each figure is the same world model as
  your own walker (Zidane on the Disc 1 map the Dali save uses; Dagger on 9002), on the ground, with its own shadow, playing
  its player's own walk, run and stand, a little behind (about a tenth of a second, plus the link). A figure hides while its player is in a
  battle, a load, a world-map scene, on another world map or riding (a figure on a mount comes in a later round), and comes back
  when that ends. Ghosts exist only on the three Disc 1 free-roam world maps (9002, 9010, 9011); on the others the guest keeps
  only the dot.
- **Pairing while the host already stands on the world map pulls the guest out** (s165 finding 1). Last time the guest waited on
  its field until the host's next stop. Now a guest that pairs on its own field writes its pairing autosave, then follows the
  host out like any follow-out, and its game takes on the host's story at the landing (so from then on its saves are refused, as
  for any following guest). A guest that pairs or Continues while itself on the world map is unchanged: it has no field to
  follow from, so it stays frozen until the host's next stop.
- **The dot follows a riding host** (s165 finding 2). What the code does: the dot's position and facing now come from the live
  data every s166 host frame carries about the actor the host controls (its walker on foot, the mount while it rides), whenever
  that frame says the host stands on a live world map. Only when a host frame carries no world position (the host loading or in
  battle) does the dot fall back to s165's source, the host's save record, which the world scripts stop updating during a ride. When the dot shows, where it pins, its tint and size are all s165's: it still draws ABOVE your arrow at
  80% (s165 finding 4).
- **The host now sees how the guest is doing.** While a following guest follows out, loads its world map, or plays a world-map
  scene, the host's screen says so: "Your partner is following you out onto the world map...", "Your partner is loading the
  world map...", "Your partner's game is in a world-map scene.". If nothing arrives from the guest for 5 s: "Lost contact with
  your partner -- waiting for their game...". These show only on the host's own world map, never on a field. The host's log
  also records every link gap of a second or more (the first 20 per link). Until now the host saw almost nothing on the world
  map.
- **Lost contact on the guest too.** If the host's game stops updating for 5 s while its frames still arrive (a hung host game),
  the guest hides the host's figure and shows the same "Lost contact" line. A plain network cut shows the old session line
  instead ("the host's game went silent -- reconnecting"), which comes first.
- **The Southern Ring's entrances are closed to a frozen guest** (s165's Confirm warning). Last time, a Confirm on the guest while
  its control was off (its first moments after the landing, or the ~ menu's "Disable control") could walk it alone into the
  kit's 6601, 6602 or 6603, with a black screen. Now, on every world map, while the guest follows the host, those entrance
  cells, 9011's boat and 9011's ferryman ignore the guest's Confirm, Cancel, Select, menu and face buttons while its control is
  off; when it ignores a press, the log says so (once per entrance per world-map load). Stock entrances are untouched. With
  `FF9CustomMap-world` the laptop's world map now carries these entrances as the desktop's does.
- **What has not changed:** the guest is still frozen on the world map. The host drives and the guest rejoins at the host's next
  stop; walking on its own copy is the next round (s167). The guest still cannot save while it follows. The host has no dot for
  the guest (it sees the guest's figure). Field co-op is unchanged.

**What was proven, and where.** All of it ran on the desktop, never on two PCs; everything but the entrance close ran on
2026-11-04 on this exact DLL:
- Two games on one PC: the host's ghost of the frozen guest stood within 2 u of the guest; the guest's ghost tracked the host's
  walk sample by sample; the dot followed a host on Choco within 8 u; both ghosts came back after a world battle; both hid before
  the rejoin; the host showed "following" through the guest's whole follow-out, then "loading" (the bench held the guest's
  start until the host's own world map was live; play has no such hold, see Known limits).
- A real guest against a recorded host: the pull landed 0.0 u from the host's spot, and the guest's game took on the host's
  story once, at the landing. A recorded older (wire 14) host never paired, and the mismatch words showed. A recorded host
  whose game stopped updating while its frames kept arriving (a hung game, not a network cut) had its ghost held through
  2.3 s, and in a 6 s run hidden at 5 s with "Lost contact", as designed.
- Link gaps ran only for 1.5 s: a gap in a recorded guest's frames gave a real host its gap lines with the figure held, and
  the guest's side ran against a simulated host inside the guest's own game.
- The entrance close was benched on one PC when it was built, on that build; this build's bench did not repeat it.
- Not benched at all: a network cut of 5 s or more on either machine (so the host's own 5 s "Lost contact" has never shown),
  and the ~ menu's "Disable control" on the guest (no bench tool can hold that menu).

One bench check stays red by design: it needs a recording of you walking the world map as the host, which only you can make.
Your two-PC session is the first real network test, and every question about the look is yours.

## Install on the laptop (close FF9 and the Memoria launcher on both machines first)

### Step 0: line the two machines up, and check them (before any test)

1. **Back up the laptop.** Make a folder outside the FF9 folder (for example `Desktop\FF9-backup-s165`) with two
   subfolders, `x64` and `x86` (the two arches' DLLs share their names), and copy:
   - `x64\FF9_Data\Managed\Assembly-CSharp.dll`, `Memoria.Prime.dll` and `UnityEngine.UI.dll` into its `x64` subfolder;
   - the same three from `x86\FF9_Data\Managed\` into its `x86` subfolder;
   - `FINAL FANTASY IX\Memoria.ini` (the one beside `Memoria.log`; ignore any `x64\Memoria.ini`) into the folder itself.

   If the laptop already has a folder named `FF9CustomMap-world`, `FF9CustomMap-schema` or `FF9CustomMap-msgs` (it had none in
   s165), move it into the backup too.
2. **The DLLs:** copy the three files from `dlls\x64\` into `FINAL FANTASY IX\x64\FF9_Data\Managed\`, and the three from
   `dlls\x86\` into `FINAL FANTASY IX\x86\FF9_Data\Managed\`.
3. **The hash, on BOTH machines.** The desktop's install is shared with Claude's benches, so check it rather than assume it.
   In a terminal on each machine:
   `certutil -hashfile "<FF9 folder>\x64\FF9_Data\Managed\Assembly-CSharp.dll" SHA256`
   and the same with `x86`. All four must start `b24e0123`. If the desktop's does not, stop and ask Claude before testing.
4. **The mod folders:** copy the package's `FF9CustomMap-world`, `FF9CustomMap-schema` and `FF9CustomMap-msgs` into the laptop's
   `FINAL FANTASY IX\` folder, beside `FF9CustomMap`. Keep the laptop's own `FF9CustomMap`, `MoguriMain`, `MoguriVideo` and
   `FF9Coop`: they are not in this package. `FF9CustomMap-world` is the desktop's whole overworld folder: the Disc 1 terrain
   edits and the Southern Ring. It also carries the desktop's New Game start (its own copy of field 70, the game's opening):
   unless the laptop's own `FF9CustomMap` replaces that field too, a New Game on the laptop now starts where the desktop's does.

   **Check the copy, on BOTH machines** (the desktop's world folders change with Claude's work, so check that they still match
   this package). In PowerShell, with `<FF9 folder>` your `FINAL FANTASY IX` folder:

   ```
   foreach ($f in 'FF9CustomMap-world','FF9CustomMap-schema','FF9CustomMap-msgs') { "$f " + (Get-ChildItem -Recurse -File -Force "<FF9 folder>\$f" | Where-Object { $_.Name -notlike '*.bak-*' -and $_.Name -notlike '*.lock' }).Count }
   ```

   Both machines must print `FF9CustomMap-world 2779`, `FF9CustomMap-schema 25` and `FF9CustomMap-msgs 146`. If the laptop's
   differ, copy the folders again; if the desktop's differ, its world changed after this package was made: ask Claude for a
   new one. `FOLDERS-MANIFEST.txt` holds every file's SHA256 if a file-by-file check is ever needed.
5. **Memoria.ini `[Mod]`:** in Notepad, open `FINAL FANTASY IX\Memoria.ini` (beside `Memoria.log`; ignore any
   `x64\Memoria.ini`) and set the laptop's two lines to exactly the desktop's:

   ```
   FolderNames = "FF9CustomMap", "FF9CustomMap-world", "MoguriMain", "MoguriVideo", "FF9CustomMap-schema", "FF9CustomMap-msgs", "FF9Coop"
   Priorities = "FF9CustomMap", "FF9CustomMap-world", "MoguriMain", "MoguriVideo", "FF9CustomMap-schema", "FF9CustomMap-msgs", "FF9Coop"
   ```

   - In s165 the laptop's log read `'FF9CustomMap' 'MoguriVideo' 'MoguriMain' 'FF9Coop'`: three folders were missing, and
     MoguriMain and MoguriVideo were the other way round. The order matters, because an earlier folder wins.
   - The Memoria launcher rewrites both lines, and it adds a folder it has not seen before at the END of both. So edit with the
     launcher closed and keep the two lines identical. If you open the launcher, check the lines again afterwards.
6. **The rest of the same `Memoria.ini`, as before:**
   - the guest keeps `[Netsync] FollowHost = 1`;
   - both machines use the same `[Cheats] SpeedFactor` and `[Graphics] FieldTPS`, and now also the same `[Graphics] WorldTPS`
     (s166 sends WorldTPS to the partner but does nothing with it yet). The desktop runs `SpeedFactor = 3`, `FieldTPS = 30`
     and `WorldTPS = 28`; WorldTPS's default is 20, so check the laptop's;
   - both use the same language and the same voice-acting setting.
7. **Compare the mods line.** Start both games (the title is enough). In each machine's `FINAL FANTASY IX\Memoria.log`, near the
   top, find the line with `[Initialization] Mods:`. On both it must read, after the date and `|M|`:
   `[Initialization] Mods: 'FF9CustomMap' 'FF9CustomMap-world' 'MoguriMain' 'MoguriVideo' 'FF9CustomMap-schema' 'FF9CustomMap-msgs' 'FF9Coop' `
   It must list the same folders in the same order on both machines. If it does not, fix Memoria.ini and start again. Once the
   laptop has loaded a world map, its log should also show lines like the desktop's
   `[WorldMeshOverride] loaded 'WorldMap/Disc1/0_1/r16/Block[0][16] Object' from FF9CustomMap-world/FF9_Data/WorldMap/Disc1/0_1/r16/Block[0][16] Object.ff9mesh`:
   the laptop now loads the desktop's terrain.
8. **The wire line.** Once co-op is running (from the first field that loads with co-op on), each log shows:
   `[NetSync] own wire: this engine speaks wire 15 (caps 0x0001) on the relay -- the partner's engine must speak the same`
   On a direct LAN link it reads `on tcp (host)` or `on tcp (client)` instead of `on the relay`. A game whose log has no such
   line runs an older DLL.

## What to try (the desktop hosts, the laptop is the guest; the guest presses nothing unless a step says so)

**Any save with the world map open works.** Last session's save does (351, Dali, the morning after the inn rest). A video of the
guest's screen during steps 1 to 3 helps most, and of the host's screen during steps 1 and 7.

**How to read the lines below:**
- On screen, every co-op line starts with `FF9 co-op:`; a ` / ` inside a quoted screen line is a line break.
- In `Memoria.log`, each line follows the date, the time and `|M|`.
- Capital letters stand for numbers: F a field, W a world map, X and Z a position, E an entrance, N a count or milliseconds,
  0xNN a byte.
- `(t N ms)` at the end is the engine's own clock.
- Lines not quoted here (s144, s145, s165, field co-op) print as before.

1. **Pairing while the host stands on the world map (the pull; s165 finding 1).** The host loads the save, walks out onto the
   world map and stands still. Then the guest loads its own save and pairs as usual, on a field that is not the host's last field
   (last time: field 250).
   - **Guest screen:** for a second or so s144's line *"Your partner is on the world map. / You'll rejoin them at their next
     stop."*, then *"Following your partner out onto the world map..."*, a short fade to black, and the world map loads. The guest
     stands on the host's spot, frozen. The host's figure stands in the same place, so until the host moves you may see only
     one body.
   - **Host screen:** *"Your partner is following you out onto the world map..."*, then *"Your partner is loading the world
     map..."*, then nothing. The guest's figure (a second Zidane) appears where the guest landed: on the host's own spot if the
     host stood still.
   - **Guest log**, in this order (the `waits` line may not appear):
     - `[NetSync] pairing autosave written on field F (the pairing window): leaving co-op returns you here`
     - `[NetSync] world follow-out: waits: the host has not been live on the world map for 1200 ms yet -- field F, the host on world map W (t N ms)`
     - `[NetSync] world follow-out: start -- field F follows the host out onto world map W (the host on foot at x X, z Z, entrance E; live on the world map for N ms) (t N ms)`
     - `[NetSync] world follow-out: commit -- world map W from field F (SetNextMap, nextMode 3, attr 0x2; seeded from the start pin: x X, z Z, entrance E) N ms after its start (black) (t N ms)`
     - `[NetSync] state-mirror ARMED at world map W's landing -- this guest's fields now stage the HOST's story`
     - `[NetSync] world follow-out: landed on world map W -- the host's latest frame at x X, z Z, entrance E, N ms after its start -- frozen here until the rejoin (t N ms)`
     - `[NetSync] world freeze ON (live) on world map W: travel input held -- the host drives; the guest rejoins at their next stop`
     - `[NetSync] world ghost: minted 'ff9mk coop world ghost' under WorldMapRoot on map W (the shadow; hidden until wanted) (t N ms)`
     - `[NetSync] world ghost: body GEO_SUB_W0_001 (model 310, ratio 67, scale 0.004089) -- renderers 2, clips 18, stand ANH_SUB_W0_001_STAND, HonoBehaviours 0, minted in N ms (hidden until wanted) (t N ms)`
       (this is Zidane's body, on 9010 and 9011; Dagger's on 9002)
     - `[NetSync] world follow-out: drift N u at my blocks on world map W (the host at x X, z Z; me at x X, z Z) (t N ms)`
   - **Host log** (the two `world ghost` lines come once per world-map load, before or after these):
     - `[NetSync] host world: the partner is following ("Your partner is following you out onto the world map...") -- the guest's place transition, state 0xNN (t N ms)`
     - `[NetSync] host world: the partner's following state ended after N ms -- the guest's place P, state 0xNN (t N ms)`
     - `[NetSync] host world: the partner is loading ("Your partner is loading the world map...") -- the guest's place world_loading, state 0xNN (t N ms)`
     - `[NetSync] host world: the partner's loading state ended after N ms -- the guest's place world, state 0xNN (t N ms)`

     An end and the next start can share one line, joined by `; `
     (`... following state ended after N ms; the partner is loading ("...") -- ...`).
   - **Red tells:**
     - The guest stays on its field with the "next stop" line, and its log says
       `[NetSync] world follow-out: waits: not mirroring the host's story yet (the pairing window: the s144 wait stands) -- field F, the host on world map W (t N ms)`:
       that is s165's wait, which this DLL should never print (an s165 guest could not even pair with this host): send the log.
     - `... waits: your pairing autosave is still pending ...` never clears while the guest stands free (no menu, no dialogue).
     - `[NetSync] no pairing autosave this session: the mirror armed at world map W's landing first (...) -- leaving co-op reloads your last own autosave`
       This line is expected, not red, when the laptop writes no autosave there: autosave off, autosave only at moogles
       (`[SaveFile] AutoSaveOnlyAtMoogle`), a spot where the game itself does not autosave, or a place the laptop did not reach
       on its own. The bracket says which. Otherwise it is red.
     - Not red, but not the pull either: if the guest shows `[NetSync] state-mirror ARMED -- this guest's fields now stage the HOST's story`
       (no "at world map W's landing") before its follow-out, it took on the host's story at a field load instead: it went
       through a door, the host was still on a field when it paired, or it loaded its save while its co-op link was already up
       from an earlier load in the same game run. To see the pull, close the laptop's FF9, start it again, load the save once the
       host stands on the world map, and press nothing until the pull.
   - **Optional, saving:** press **Alt+F5** on the guest now. Expect the stock buzz and no save screen at all, because the shortcut
     itself is refused while the guest follows the host's story. Nothing is logged. This corrects s165's step 5, which expected
     the file list and a log line.
2. **Walking on: the ghosts, both ways.** The host walks around near the guest, stops, walks off well past the edge of the
   screen, comes back, and crosses a slope or hill if there is one nearby.
   - **Guest screen:** the host's figure walks where the host walks, on the ground, with a shadow, playing the host's own walk,
     run and stand. The guest itself does not move, and its camera stays on the guest, so the figure walks off-screen and back.
   - **Host screen:** the guest's figure stands, idle, where the guest landed, and stays there as the host walks away.
   - **Logs:** nothing new while walking: each figure logs only its mint.
   - **Red tells:**
     - On screen: a figure that faces backwards or sideways, floats or sinks, slides without stepping, freezes mid-stride
       while its player walks, or stands while its player walks. Also red: the guest moves.
     - `[NetSync] world ghost: ground mismatch -- the partner stands at y A where my ground is B (D u, beyond 1 u) at (X, Z) on map W, walkmesh id 0xNN -- the two worlds' content may differ; the body keeps the wire's y (said once per world visit) (t N ms)`
       The two world maps differ: check step 0's mods line again. The 1 u threshold is a guess, so a D of 1 or 2 u on a slope
       may be a false alarm; send it either way.
     - `[NetSync] world ghost: the body for model M cannot be minted (...) -- latched: no ghost body of that model this process`
     - `[NetSync] world ghost: minted 'ff9mk coop world ghost' under WorldMapRoot on map W (the NO shadow: its prefab is missing; hidden until wanted) (t N ms)`
     - `[NetSync] world ghost: the partner plays CLIP (anim N), which is not on BODY -- keeping the clip already playing`
3. **The dot, and the host riding (s165 finding 2).**
   - If the guest's minimap is off, the guest sees *"Your partner is on the world map: press Select for the minimap."*. Press
     Select once on the guest.
   - **On foot:** as in s165. The dot tracks the host, and pins to the window's edge, dimmed, when the host is outside it.
   - **Riding:** the host calls Choco from its ~ menu World tab (as last time), rides around for a while, then gets off.
     - **Guest screen:** the host's figure disappears while the host rides. The dot keeps moving and turning with the host.
       Once the host is on foot again, the figure reappears on the host: it jumps there, with no slide.
     - **Host screen:** nothing new. The guest's figure stays where it stood.
     - **Logs:** nothing new.
     - **Red tells:** the dot stands still while the host rides (s165's behaviour); a figure is drawn walking along under the
       mount.
4. **A host battle.** The host walks until a random battle starts.
   - **Guest screen:** the host's figure disappears as the host's battle swirl starts. Then the guest's game shows the host's
     battle, as in s145 (or, if it cannot, the guest waits on the world map). Once both are back on the world map, the host's
     figure is back on the host.
   - **Host screen:** after the battle, while the guest's world map reloads, *"Your partner is loading the world map..."* can show
     for a few seconds. Then the guest's figure is back where it stood.
   - **Logs:**
     - Both: after the return, a fresh `world ghost: minted ...` and `world ghost: body ...` pair (every world-map load builds
       a new body).
     - Host: `host world: the partner is loading (...)` and its `... ended after N ms ...` line.
     - Guest, if a host load lasts a second or more (normal):
       `[NetSync] client lane hang: the partner's game is loading (its frames repeat) for N ms (t N ms)` and
       `[NetSync] client lane hang over: the partner's game loaded after N ms (t N ms)`.
       The host may log the same with `host` for the guest's load.
   - **Red tells:** on the guest's screen, a figure standing frozen while the host is already in its battle; no figure after both
     are back and the host walks again.
5. **Into a location (the rejoin).** The host walks into a location on the world map (back into Dali, or any other).
   - **Guest screen:** the host's figure and the dot disappear the moment the host goes in. Then the guest follows the host into
     that field (the s144 rejoin) and lands with control.
   - **Host screen:** nothing new.
   - **Guest log:** `[NetSync] world rejoin landed on field F after N ms`.
   - **Red tells:** the host's figure still standing at the entrance after the host went in; the guest staying on the world map.
6. **Out again (the follow-out).** Back on that field with the guest paired, the host walks out onto the world map and stands
   still for a few seconds.
   - **Guest screen:** as in s165. About a second after the host arrives, *"Following your partner out onto the world map..."*,
     a fade, the world map, and the guest on the host's spot, frozen, with the host's figure.
   - **Host screen:** the two lines as in step 1, then the guest's figure.
   - **Logs:** the guest logs the same lines as in step 1, without the pairing autosave and ARMED lines (this guest already
     follows the host's story). The host logs step 1's lines, after its two s165 lines:
     `[NetSync] host: world-map exit from field F to world W (t N ms)` and
     `[NetSync] host: on world map W (b6) at world frame N, blocks ready yes|no (t N ms)`.
   - **Red tells:**
     - s165's: the guest lands at the exit's usual arrival point while the host stood somewhere else; it lands on a different
       world map; it can walk; its screen stays black; a second load comes right after the first.
     - The host's two lines can show late, briefly or not at all if the host's own world map was still loading when the guest
       started (see Known limits). Note what you see.
7. **A link drop.** Both stand on the world map, the guest frozen, both figures showing.
   - **What to do:** turn the laptop's network off (Wi-Fi off, or pull its cable) for about 10 seconds, then turn it back on.
     Reconnecting can add a few seconds; keep the whole cut under 30 s, because past the session's grace (40 s by default) the
     guest's own save reloads. If the guest's bridge window closed, start it again as usual.
   - **Guest screen:**
     - At once, the host's figure stops and stands.
     - After about 1 s, the dot goes.
     - At about 2 s, the session's line appears: *"the host's game went silent -- reconnecting (N s left) / the session waits for
       it; if it doesn't return, your own save reloads"*.
     - At 5 s, the figure goes.
     - When the network is back, the line clears and the dot and the figure return. The figure jumps to where the host is now.
   - **Host screen:** the guest's figure stands. At 5 s it goes, and *"Lost contact with your partner -- waiting for their
     game..."* shows. When the link is back, the line clears and the figure returns. (On a direct LAN link whose connection
     drops, the host shows its own connecting line, *"waiting for the other player to connect"*, instead.)
   - **Guest log:**
     - `[NetSync] client lane gap: no frame from the partner for N ms -- its ghost holds (t N ms)`
     - `[NetSync] session: the host went silent (the hop is up: a cut or a stall upstream) -- holding the session for up to 40 s, reconnecting (the story mirror stays armed, saving stays off); outages=N`
       (or `(the link is down)` in the first brackets)
     - `[NetSync] session: the host is back after N ms -- inside the 40 s grace, the session continues (no exit ramp; still mirroring); resumes=N`
     - `[NetSync] client lane gap over: the partner's frames are back after N ms (t N ms)`
   - **Host log:**
     - `[NetSync] host lane gap: no frame from the partner for N ms -- its ghost holds (t N ms)`
     - `[NetSync] host world: the partner is lost ("Lost contact with your partner -- waiting for their game...") -- the guest's place world, state 0xNN (t N ms)`
     - `[NetSync] host lane gap over: the partner's frames are back after N ms (t N ms)`
     - `[NetSync] host world: the partner's lost state ended after N ms -- the guest's place world, state 0xNN (t N ms)`
     - It may also log, just before the `partner is lost` line,
       `[NetSync] world line: lost contact -- the partner's game has not updated for N ms (its last frame N ms ago): "Lost contact with your partner -- waiting for their game..." (t N ms)`
       and at the end `[NetSync] world line: lost contact over after N ms (now none) (t N ms)`: the same event, seen by the
       figure's own 5 s clock.
   - **This is the first real cut:** the desktop's bench never cut a link for 5 s or more. Its 2.3 s and 6 s runs froze a
     recorded host whose frames kept arriving (a hung game), and its link gaps lasted 1.5 s. The host's own 5 s line has had no
     bench at all.
   - **Red tells:**
     - Through the whole cut the host shows nothing and logs no `host lane gap` line: the host is blind again, as on s165.
     - The host's figure keeps walking on the guest's screen during the cut.
     - "Lost contact" stays up after the link and the figure are back.
     - The guest's session ends (its own save reloads) inside 40 s.
8. **The version check (optional, last).** On the laptop, close FF9 and copy its `Memoria.log` aside first: it holds steps 1
   to 7, and every start of the game rewrites it. Then put back the s165 `Assembly-CSharp.dll` from your step-0 backup (its `x64`
   copy into `x64\FF9_Data\Managed\` and its `x86` copy into `x86\FF9_Data\Managed\`, so whichever one the launcher runs is
   s165), start the game and try to pair as usual.
   - **Host (desktop) screen:** *"Your partner's co-op version doesn't match yours: update both games."* Nothing pairs.
   - **Guest (laptop, s165) screen:** its usual line, waiting for the host's game; it never pairs and says nothing about versions.
   - **Host log:**
     - `[NetSync] the partner's engine speaks wire 14, this one speaks 15 -- update both machines`, once per game run.
     - On a direct LAN link, also
       `[NetSync] peer disconnected; awaiting reconnect (wire-version mismatch: the partner's engine speaks wire 14, this one speaks 15 -- update both machines' engine)`
       once (another reason in the brackets can show once too), then nothing while the laptop keeps redialling every 2 s. When
       the restored laptop connects again, one `[NetSync] tcp redial: N quiet cycle(s) since the last line -- each broke as already said`
       line counts those quiet tries, just before its `peer connected` line.
   - **Guest log:** nothing on the relay. On a direct LAN link, every couple of seconds a `[NetSync] connected to host ...` line,
     then usually `[NetSync] peer speaks a different wire version -- disconnecting` and
     `[NetSync] lost host; retrying (wire-version mismatch (update both machines' engine))` (another reason in the last
     brackets when the desktop hangs up first).
   - **Then put s166 back:** close the laptop's FF9 (copy its `Memoria.log` aside again: it holds this step), copy the
     package's `dlls\x64\Assembly-CSharp.dll` and `dlls\x86\Assembly-CSharp.dll` back to their folders, check both hashes
     again (`b24e0123`), and start the game. The desktop's words
     clear as soon as the laptop's first frame arrives; if the laptop just stays closed, they clear within 15 s.
   - **Red tells:** the two pair; the desktop shows no words.

## The look (your call)

The design could not settle these on the desktop. One desktop screenshot of Dagger on 9002 showed the figure upright, at the
walker's scale and on the ground. That is all that has been seen so far.

**The ghost:**
1. **Facing:** does the figure face the way it walks?
2. **Ground and shadow:** are its feet on the ground, on slopes and hills too? Does it have a shadow the size of your own
   walker's, under its feet?
3. **Animation:** does it walk in step with its movement (no sliding), and stand when its player stands? In a link drop it
   should switch to standing within about 0.3 s.
4. **Smoothness:** it trails its player by about a tenth of a second plus the link, with no smoothing buffer. Does it read
   smooth, floaty or jumpy?
5. **The hitch:** each world-map load builds the figure's body (50 to 70 ms on the desktop's bench). Do you notice a stutter as
   the world map appears, on either machine, the laptop especially?
6. **Two identical bodies:** are two Zidanes fine, or should the partner look different (a tint, or a dress such as a moogle
   partner as the world Mog)?

**The dot** (still open from s165):
1. Is the warm orange tint right?
2. Is the size right (1.25 times your arrow)?
3. At the window's edge, do you want it pinned and dimmed, or hidden?
4. New: does it follow a riding host well?
5. New: in a link drop it goes after about 1 s, before the figure (5 s). Is that fine?

## The words (your call)

Change any of them. These are the proposals from the design:

- the s166 machine, when the partner runs another engine: "Your partner's co-op version doesn't match yours: update both games."
- the host, nothing from the guest for 5 s; the guest, a host game that stops updating for 5 s: "Lost contact with your partner
  -- waiting for their game..."
- host, the guest follows out: "Your partner is following you out onto the world map..."
- host, the guest loads: "Your partner is loading the world map..."
- host, the guest in a scene: "Your partner's game is in a world-map scene."

s165's five lines are still yours to change too.

## Known limits (s166)

- **Install:** both machines must run the same DLL and the same world-map folders (`FF9CustomMap-world`, `-schema` and `-msgs`),
  and a rollback rolls back both. Nothing in the game checks the world content yet (s167 will name a difference); the only hint
  is the ghost's ground-mismatch log line. Each machine keeps its own `FF9CustomMap` (first in the folder order): the desktop's
  also changes battle and character data (its battle action, ability and character tables), which this test does not line
  up, as in s165's session, so a battle's numbers can differ between the two machines.
- **Where:** ghosts only on 9002, 9010 and 9011. On the other free-roam world maps (later discs, with Choco or a ship) the guest
  keeps only the dot, and on world-map scenes neither. 9002 has barely been tested: both bodies are Dagger there, and its minimap
  is unproven in game.
- **Riding:** the host's figure hides while the host rides; the dot follows.
- **Looks:** two identical figures, with no tint or dress yet.
- **In a link stall:** the dot goes at 1 s and the figure at 5 s.
- **The host's lines during its own load:** the guest starts its follow-out once the host has stood on the world map for 1.2 s,
  which can come before the host's own world map has finished loading. The host's lines can then show late, briefly or not at
  all. They are informational only.
- **A guest that leaves for good:** on the relay or a bridge, the host keeps "Lost contact with your partner -- waiting for their
  game..." on every later world-map visit until the title, a config change or a new session. Each of those world-map loads also
  has the short body-building hitch. A direct LAN link is unaffected.
- **The mismatch words linger:** they stay up to 15 s after an older partner quits.
- **Unchanged from s165:**
  - a host on the kit's new world (9013) reads as 9011 to the follow-out; do not take an entrance on 9013 (reached only through
    the ~ menu): its three bench fields, 30950 to 30952, are registered on neither machine, so an entrance there leads to a
    black screen;
  - after a host Gysahl press on 9010 or 9011, later follow-outs wait (the guest's log says `the host is calling Choco`);
  - a host that changes world map without a field, or walks back out while the guest's rejoin waited, leaves the guest behind
    until its next stop.
- **A guest that paired or Continued on the world map:** it is not pulled, and during a link stall the entrance close does not
  cover it (s167 closes that).
- **A follow-out lost halfway** (another world map loads instead, or a field loads while the link is down) can leave the host's
  world position in the guest's own story. No way to make this happen in play was found offline. If the guest ever arrives
  somewhere unexpected after a link drop during a follow-out, say so.
- **Log lines that are not faults:** a 1 to 3 s `lane hang: the partner's frames arrive but repeat (its game is not updating)`
  line pair around a load (a field follow, a world-map exit) is a known wording slip; it means loading. Each battle exit can also
  freeze the partner's frames for about 0.8 s, which logs nothing.

## What to send back

- Both `Memoria.log` files (`FINAL FANTASY IX\Memoria.log` on each machine). Copy each one before starting that game again.
- The session's rough times.
- Your answers on the look and the words.
- The videos.

If you need to go back to s165, do it on both machines:
- the laptop puts back the six DLLs from its step-0 backup (each arch from its own subfolder), and keeps the step-5 `[Mod]`
  lines and the three copied folders: the desktop ran s165 with them too, and they keep the two machines' mods lined up;
- the desktop runs `py tools/restore_memoria_dll.py 20261102-175107` (s165, `e364ca8d`), with FF9 closed, in
  `C:\gd\Dream-World-IX`.

Also still open, no test needed: is the FF9Coop mod folder (it reroutes the chocobo-dive return to field `1953`, listed last in
`[Mod] FolderNames`) still wanted?

## Results
