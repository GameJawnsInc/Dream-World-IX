# FF9 Co-op: laptop update package (2026-11-02, s165)

**Engine in this package:** `Assembly-CSharp.dll` `e364ca8d732f8cda…` (both arches). `HASHES.txt` lists the six DLLs.
The desktop is already on this build. **Install it on the laptop too.** The guest's game does all of s165's work, so the
laptop must run it whenever it is the guest. The host side only adds two log lines. The package contains one new round,
s165 (the world-map follow-out), and everything from the s164 package and earlier, so it replaces them. Only
`Assembly-CSharp.dll` changed; the other two DLLs are the same files, included so the set is complete.

## What's new (s165: the guest follows the host out onto the world map)

- **Walking out onto the world map, the guest comes too.** Until now a guest left on a field stayed there when the host
  walked out onto the world map, and only caught up at the host's next location. Now, once the host has stood on the world
  map for about a second, the guest's screen fades and its game loads the same world map. It lands **where the host is
  standing** (not at the exit's usual arrival point), on foot, and **frozen** there, as before s165: the host drives, and
  the guest follows the host into its next location.
- **A dot for your partner on the guest's minimap.** An orange marker, a little larger than your own arrow, drawn under it,
  pointing the way the host faces. It moves as the host walks, in small steps (about 7 updates a second). When the host is
  outside the minimap's window it is pinned to the window's edge and dimmed. It hides when the host leaves the world map
  or goes to another world map, and when the host's game stops sending. While the host calls, mounts or boards something it
  holds its last position; what it does while the host rides has not been looked at yet.
- **When the guest waits instead:** if the host is riding (Choco, the boat, an airship) or is in a world-map scene, the guest
  stays on its field with a line, and follows the host into its next location as before.
- **The guest cannot save while it follows the host.** The save screen plays the stock buzz and saves nothing (the log
  says `save refused while following your partner`). The host saves as usual.
- **Chocobo dive (world 9012):** a guest frozen there no longer gets stuck; it follows the host into its next location.

All of this was proven on the desktop: the guest following a recorded host over the real link (it landed exactly on the
host's spot, 1183 units from the usual arrival point), and two games on one PC. Your two-PC session is the first real
network test, and the dot's look is yours to judge.

## Install on the laptop (close FF9 first)

1. **DLLs:** copy the three files from `dlls\x64\` into `FINAL FANTASY IX\x64\FF9_Data\Managed\`, and the three from
   `dlls\x86\` into `FINAL FANTASY IX\x86\FF9_Data\Managed\`. Back up the files you replace.
2. **Check the copy:** in a terminal on the laptop:
   `certutil -hashfile "<FF9 folder>\x64\FF9_Data\Managed\Assembly-CSharp.dll" SHA256`
   should start `e364ca8d`.
3. **Memoria.ini:** nothing new. The guest keeps `[Netsync] FollowHost = 1`, as before. Keep the same `[Cheats]
   SpeedFactor` and `[Graphics] FieldTPS` on both machines.
4. **Nothing else:** no mod-folder files. Both machines need the same world map (same mod folders), as before.
5. Use the same language and the same voice-acting setting on both machines.

## What to try (the desktop hosts, the laptop is the guest; the guest presses nothing unless a step says so)

**Any save with the world map open works.** Last session's save (351, Dali, the morning after the inn rest) does: the host
walks out of Dali onto the world map. Pair the guest on the field first, as usual.

**On the guest, press nothing while it lands on the world map, and do not open the ~ menu on the guest while it is on the
world map.** While the guest's control is off (its first moments after the landing, or the ~ menu open with "Disable
control"), a Confirm press reaches the Southern Ring's own entrances (the kit's 6601, 6602 and 6603 cells) unchecked: if
the guest stands on one, it walks in by itself and its screen can stay black. The fix is designed for the next round.

1. **The follow-out.** The host walks out of a field onto the world map and stands still for a few seconds.
   - **Guest screen:** about a second after the host arrives, the line *"Following your partner out onto the world map..."*,
     a short fade to black, the world map loads, and the guest stands on the host's spot, frozen (its controls do nothing).
   - **Host screen:** nothing new.
   - **Guest log:** `world follow-out: start -- field F follows the host out onto world map W (the host on foot at x X, z Z,
     ...)`, then `world follow-out: commit -- ...` and `world follow-out: landed on world map W -- the host's latest frame at
     x X, z Z, ... -- frozen here until the rejoin`. **Host log:** `host: world-map exit from field F to world W` and
     `host: on world map W (b6) at world frame N, blocks ready yes|no`.
   - **Red tells:** the guest lands at the exit's usual arrival point while the host stood somewhere else; the guest lands
     on a different world map; the guest can walk; the guest's screen stays black; a second load right after the first.
2. **Walking on: the dot.** Once the guest has landed, the host walks around for a while, then far away.
   - If the guest's minimap is off, the guest sees *"Your partner is on the world map: press Select for the minimap."*:
     press Select once on the guest.
   - **The look (your call):** the dot is warm orange, 1.25 times the size of the guest's own arrow, drawn under it, and
     points the way the host faces. Right after the landing it sits on the guest's own arrow, so only its orange rim shows.
     As the host walks it should track the host's real position. When the host leaves the minimap's window it pins to the
     window's edge, dimmed to 60%.
   - **Tell me:** is the tint right, is the size right, and at the edge do you want it pinned and dimmed, or hidden?
3. **Into a location.** The host walks into a location on the world map (back into Dali, or any other).
   - **Guest:** the dot disappears, the guest follows the host into that field (the s144 rejoin), and lands with control.
4. **Leaving again while the host is far off.** Back on a field, both paired, the host walks out onto the world map and
   keeps walking. The guest lands where the host stood when the guest's world map finished loading (a second or two
   behind the host), not at the exit point: the dot then shows how far ahead the host is.
5. **Saving on the guest (optional).** While frozen on the world map, press **Alt+F5** on the guest (Memoria's save
   shortcut: a following guest's main menu stays closed, as before), then pick a slot.
   - **Guest:** the stock buzz, back to the file list; nothing is saved. **Guest log:** `save refused while following your
     partner (...)`. The host can save as usual.
6. **Riding (optional, only if Choco is available in your save).** On a field, the host calls or rides Choco out onto the
   world map, or rides once out. **Guest:** it stays on its field with *"Your partner is riding. You'll rejoin them at their
   next stop."* and follows the host into its next location. If the guest is already on the world map when the host
   mounts, note what the dot does while the host rides.

## The words (your call)

Change any of them; they are the proposals from the design:

- leaving: "Following your partner out onto the world map..."
- the host rides: "Your partner is riding. You'll rejoin them at their next stop."
- an event world: "Your partner is in a world-map scene. You'll rejoin them at their next stop."
- a world not on this install: "Your partner's world map isn't on this install."
- the minimap off: "Your partner is on the world map: press Select for the minimap."

## What to send back

Both `Memoria.log` files (`FINAL FANTASY IX\Memoria.log` on each machine), the session's rough times, and your answers on
the dot's look and the words. A video of the guest's screen during step 1 and step 2 helps most.

Also open, no test needed: is the FF9Coop mod folder (it reroutes the chocobo-dive return to field `1953`, listed last in
`[Mod] FolderNames`) still wanted?

## Results: the owner's two-PC session (2026-11-02, 13:19-13:27)

The desktop hosted, the laptop was the guest, both on `e364ca8d`. Sources: the laptop's `Memoria.log` (sent as
`Memoria-laptop.log`) and the desktop's own. The guest paired on its field 250; the host then entered Dali (359), warped to
350 with the ~ menu, walked out onto world 9011, rode Choco (called from the ~ menu), entered field 1856, warped back to 350
and walked out again.

| Step | Result |
|---|---|
| Field follows before the test (250 -> 359 -> 350) | Green: both follows faded and landed, the dialogue lock and step-out as before. |
| 1 The follow-out | Green, twice. The guest landed on the host's spot (drift 0 u the first time), frozen. The host showed its two s165 lines and nothing else. |
| 2 The dot | Green on foot. **Gap:** while the host rode Choco, the dot and its facing stood still until the host got off. The look questions (tint, size, the edge) are still open. |
| 3 Into a location | Green: the host entered 1856 from 9011, and the guest rejoined 375 ms later. |
| 4 Leaving while the host walks on | Green, as designed: the guest landed where the host stood when the guest's world map finished loading (857 ms after the start), 18.3 u behind the host by then, not at the exit. |
| 5 Saving on the guest | Not run. The main menu is refused, as expected (`main menu suppressed (following guest)`); Alt+F5 was not tried. |
| 6 Riding | Not run: Choco is not unlocked in this save. |

The link had one outage, 203 ms at 13:24:01, which recovered inside the grace; it was otherwise clean for about 8 minutes.

**Findings:**

1. **A guest that pairs while the host is already on the world map waits on its field.** The log line is `world follow-out:
   waits: not mirroring the host's story yet (the pairing window: the s144 wait stands)`. That is the design (S165 decision 1,
   THE PAIRING-WINDOW LAW), but the law's reason, a pairing autosave that may still be pending, did not hold: the guest wrote
   its pairing autosave at the moment it paired (13:19:10). The owner expected the guest to be pulled out. The fix is small:
   the term becomes "the pairing autosave has not resolved", and the world landing arms the mirror. `LandWorldOut` already
   applies the host's whole story; it never arms only because a guest that follows out was always mirroring already.
   -> The owner folded it into s166 (2026-11-02): `S166-DESIGN.md` decision 26, round A's second piece.
2. **The dot holds while the host rides.** s165's dot reads the host's save-anchor record (section 0, `gEventGlobal` 64-72),
   and the world scripts stop writing it while the host rides: the same freeze `S166-DESIGN.md` decision 4 names for a
   Gysahl press and the kit voyage. s166's world trailer carries the host's live walker position
   (`w_moveActorPtr.RealPosition`) instead, but decision 12 kept the dot on section 0. -> open item 14.
3. **The laptop runs without `FF9CustomMap-world`, `-schema` and `-msgs`.** Its mods line reads `'FF9CustomMap'
   'MoguriVideo' 'MoguriMain' 'FF9Coop'`, while the desktop's lists all seven folders. The two machines therefore do not have
   the same world map: the desktop loads its Disc 1 terrain overrides from `-world`, and the laptop has none. This did not show
   in s165, because the guest stands frozen wherever the host stands. It matters from s166 on, when the ghosts would stand on
   different ground, and in s167, when the guest walks a different map. The next package must carry `FF9CustomMap-world`
   (73 MB), or the owner copies it across.
4. **This checklist described the dot wrongly.** It draws ABOVE the guest's own arrow at 80% opacity, not under it. The
   minimap's depths leave no free slot under the arrow, so this is the design's fallback, and it happens every time.
