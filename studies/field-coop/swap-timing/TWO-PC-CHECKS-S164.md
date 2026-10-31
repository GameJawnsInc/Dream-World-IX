> The README of the s164 laptop update package, built 2026-10-30 as `Desktop\FF9Coop-laptop-update-20261030-s164` (+ `.zip`); its README.md is this file from line 4.
> The two-PC checks are under **What to try**. The final bench's numbers: `memoria-patches/README.md`'s s164 row.

# FF9 Co-op: laptop update package (2026-10-30, s164)

**Engine in this package:** `Assembly-CSharp.dll` `29f351aaacd3f3d8…` (both arches). `HASHES.txt` lists the six DLLs.
The desktop is already on this build, and **both machines must run it**: the host's game keeps its exit on the wire
longer and marks its landing, and the guest's game does the rest. It contains one new round, s164 (field-swap timing),
and includes everything from the s163 package and earlier ones, so it replaces them. Only `Assembly-CSharp.dll`
changed; the other two DLLs are the same files, included so the set is complete.

## What's new (s164: the guest lands right behind the host)

- **Doors and gateways: the guest lands about 0.43 s after the host, not about 0.93 s.** The guest's screen fades with
  the stock 12-tick wipe and its game loads as soon as the screen is black, instead of on a fixed 0.9 s timer. When
  the guest plays at 3x, its screen no longer sits black for about 0.6 s after the fade.
- **Scripted exits: one load when the host's exit reaches the guest first.** In earlier sessions 2 of the 5 scripted
  Dali exits bounced, both the inn rest from 351 to 352: the guest's game reloaded the room it was leaving before
  following (about 1.5 s, and the room shown twice). When the host's exit has already reached the guest's game as its
  own copy of the scene gets to the exit, that exit now loads the host's field once. When the guest's copy gets to the
  exit first (the second session's bounce), it still reloads the room once and then follows: not fixed in this round.
  And when the guest's copy has already started its own fade to black, the follow carries that fade on instead of
  restarting it from a bright screen, so the flash at its start is gone. A fade to white still flashes, as before.
- **Finding 11 (the innkeeper's first line in "Cat's Eye" on 351).** The guest's game no longer closes a line by itself
  while the host's control is off on the same field: it holds the line until the host's own line closes it.
- **The guest arrives in the host's story as it was when the host left,** not a later one, when it lands within about
  2.5 s of the host (the normal case).
- **A guest a second behind still follows the host's exit** instead of falling back to the slower follow.
- **Quiet arrivals:** landing sooner does not make the guest step out early where both players stand still with no
  line; the step-out still comes about when it did on s163.
- **The log** stamps each field change to the millisecond and writes one summary line per change
  (`[NetSync] swap #N to field F (from S) closed by ...`), so a slow landing can be read from the log alone.

All of this was proven with two games on the desktop. Your two-PC session is the first real link: it checks the
landing gap over a network and the host-landing timing the quiet-arrival rule reads.

## Install on the laptop (close FF9 first)

1. **DLLs:** copy the three files from `dlls\x64\` into `FINAL FANTASY IX\x64\FF9_Data\Managed\`, and the three from
   `dlls\x86\` into `FINAL FANTASY IX\x86\FF9_Data\Managed\`. Back up the files you replace.
2. **Check the copy:** in a terminal on the laptop:
   `certutil -hashfile "<FF9 folder>\x64\FF9_Data\Managed\Assembly-CSharp.dll" SHA256`
   should start `29f351aa`.
3. **Memoria.ini:** nothing new. Keep s163's match: the same `[Cheats] SpeedFactor` and `[Graphics] FieldTPS` on both
   machines (the desktop has `SpeedFactor = 3` and `FieldTPS = 30`). Checks 3 and 4 use the laptop's own booster (F1),
   which needs `[Cheats] Enabled = 1` and `SpeedMode = 1` in the laptop's Memoria.ini, as last session.
4. **Nothing else:** no mod-folder files.
5. Use the same language and the same voice-acting setting on both machines.

## What to try (the guest follows the host and presses nothing unless a step says so)

**Which save (host only):** load the same save you started last session from (it loads on 351, the morning after the
inn rest), never a save made after it. Check 2 replays the rest: the host goes to 359 (Dali's arrival scene), which runs
straight into the innkeeper's desk scene on 351 and the rest, and the trip through 359 also makes Dali's ATEs available
again, "Cat's Eye" included. **Pair the guest before the host goes to 359**, so both games play these scenes from their
first line: a guest that joins partway through the desk scene starts it again from its first line and leaves by the
follow, so check 2 shows nothing (last session the guest joined during the desk scene and waited on line 129 for 24 s).

1. **Doors and gateways, both at 1x.** Walk the host through a few ordinary doors and screen edges in Dali.
   - **Guest screen:** a short fade to black (about half as long as before), and the guest's game arrives about half a
     second after the host's. **Host screen:** the guest's ghost shows up about half a second after you arrive.
   - **Guest log, per door:** `follow fade: to field N -- fast: the screen reads visible (sub); fading to black in 12
     ticks; ...`, then `follow fade: field N due after ~400 ms / 12 ticks -- the screen reads black, one dialogue pass
     later`, and later the summary `swap #K to field N (from M) closed by ...: via the follow; ... commit +3xx-4xx, landed
     +6xx-8xx ...`.
   - **Read the START line to tell the paths apart, not the due line.** Two starts keep the old timing on purpose: `--
     today's timing: field F has a backlog (<reason>)` followed by `due after ~900 ms / 27 ticks -- today's 0.9 s
     timer`, and a `fast:` start whose due line reads `today's 0.9 s timer: a backlog rose mid-fade (<reason>)`. Both
     mean the guest's game was still behind the host's dialogue at the door: a line still up here, a host line not open
     here yet, or a relayed host key not played here yet. The last two can happen with no line on the guest's screen,
     for example right after the host closes a line. Note the reason when you see it.
   - **Red tells:** a `fast:` start whose due line reads `the 0.9 s fallback: the fade never read black (...)`, or the
     plain `today's 0.9 s timer` with no `: <reason>` after it (after a `fast:` start only a fault gives that; after a
     `today's timing` start it is normal); or a start line `today's rule (...)` other than `my own warp is in flight`
     (that one only follows the guest's own ~ warp or reload).
   - **Known from the desktop, not a red:** on a scripted exit (not a door) a `fast:` start can end in `the 0.9 s fallback:
     the fade never read black (heading, darkest channel 2xx)` with the screen all but black and no reload: 5 of 78 desktop
     follows out of 359 did. Note it if you see it.
2. **The inn rest (351 -> 352) and the night scene, both at 1x.** With the guest paired, the host warps to 359: **~**,
   the **Go** tab, **Warp to field** 359 with Entrance and Scenario left blank (blank keeps this save's story; do not
   type 0 and do not use **Reset all flags + reload**), then **Go**. On 359 a box reading `Error Env Play() Slot=0`
   opens first on both screens: it is the stock script's own line, not a fault, so page it like any line. 359's scene
   then runs into the innkeeper's desk scene on 351, and the desk scene ends in the rest: one fade from 351 into 352's
   night scene. The host only pages the lines (in this save the innkeeper gives no rest when spoken to: he dozes, then
   says your friends aren't back yet).
   - **Guest screen:** the scene's own fade runs straight on to black with no pop back to a bright screen first, then
     one load into 352.
   - **Guest log:** `follow fade: to field 352 -- fast: the screen reads heading (sub) (N ticks left); joining its own
     fade (no re-init); ...` (or `reads black`), then `own Field(352) passes on field 351 -- the host's announced field
     (...); my follow's fade becomes this commit (one load)`. With more than 12 ticks left the start reads `hurrying it
     to black in 12 ticks from where it is (no flash)` instead, and the pass line ends `(committed); my follow already
     committed to it`: also fine, still one load.
   - **Known, not this round's red:** if the guest's copy reaches the exit before the host's exit reaches the guest,
     the guest sees 351 load again before it follows (about 1.5 s). The log reads `bounced to a reload of 351 (not the
     host's field: the host's lane reads field 351)`, and that change's summary line shows `own +0` with `seen` later.
     On the desktop this happened only when the host waited about 2.5 s on each line. Note it if you see it.
   - **Also known, not a red:** on the way in, 359's scripted exit into the desk scene can bounce the same way: the
     guest sees 359 load again, then follows. The log reads `own Field(351) on field 359 -- bounced to a reload of 359
     (not the host's field: the host's lane reads field 0)`; 29 of 72 desktop exits from 359 did. Note it if you see it.
   - **Red tell:** a 351 bounce on the rest exit AFTER the guest saw the host's exit. Read it from that change's
     summary line, `swap #K to field 352 (from 351) closed by ...`: it ends `after its first edge (seen); follows N,
     bounces 1, ...` (the known case above ends `after its first edge (own)`). Also red: a 351 bounce that reads
     `bounced to a reload of 351 (not the host's field: the host's lane reads field 0)`.
   - **The night scene on 352 is the quiet arrival:** both players stand still with no line for several seconds. If the
     guest is dressed as Steiner (as last time), its Steiner stands in Zidane's place after it lands, then the Zidane
     stand-in takes over for the scene, as on s163: expected, not a red. How long depends on the first guard line
     below: about 2.5-3 s with `reached me X ms after mine` (2.7-2.9 s on the desktop), and less, about 2.5 s minus X,
     with `the host landed X ms before me` (1.9-2.5 s on the desktop). **Guest log:** first
     `arrival guard: field 352 -- the host landed X ms before me (intent nonce K); ...` or `-- the host's landing
     reached me X ms after mine (...)` (either is fine; which one shows on a real link is what this session measures),
     then `arrival guard: held the dwell on field 352 -- the base is 15xx ms, its guarded dwell ... ms (s158 would
     step out here)` (usually 1500), then `arrival guard: field 352 -- held the dwell OUT ... ms (it stepped out at base
     ... ms)`. If the guest lands more than about 1 s after the host (after a bounce, say), none of these three
     `arrival guard:` lines prints for 352 and the step-out comes as on s163: that is fine.
3. **Doors with the guest at 3x.** The GUEST turns its own booster on (F1 on the laptop); the host stays at 1x. Walk a
   few doors. Stay inside the village: do not go out to the Dali field (450), and do not watch "Dagger Tries" before
   check 4. Either one starts Dali's countdown, which takes "Cat's Eye" off the ATE menu a few doors later.
   **Guest screen:** a quick fade, then the new field with no black pause after it. **Guest log:** `due after ~150 ms /
   13 ticks` (12-17 ticks). Keep the guest's booster on for check 4.
4. **"Cat's Eye" on 351 (Finding 11), the guest at 3x, the host at 1x.** This needs the guest's copy AHEAD of the
   host, which is how Finding 11 happened: the HOST's booster is off, the GUEST's is on (from check 3). The host presses
   Select on 350 and picks "Cat's Eye". It is on 350's ATE menu once the host has walked out of the inn (351 -> 350)
   since the rest; if it is still missing then, check 4 cannot run in this run.
   - **Guest screen on 351:** Innkeeper Hal's lines (text 113 on) show and advance only as the host pages them; none
     closes by itself before the host reaches it.
   - **Guest log:** `dialogue orphan: win 7 text 113 held -- the host's control is off on my field`, then `the control
     hold ends after ... ms (a host event claims it)`, then `win 7 text 113 closed (host seq N)`.
   - **Red tell:** a 113-117 line closed on the guest before the host closed it. In the guest log that reads
     `dialogue orphan: win 7 text 11x auto-closed (host idle ...)`, usually after `... is not on the host's screen
     ... -- closing it at reading pace`. If both games ran at the same speed, the guest's copy lands just behind the
     host's and neither a `held` nor an `auto-closed` line prints: that is not a red, the check was simply not
     reached. Afterwards the guest turns its booster off.

Already confirmed, no need to repeat: s159-s163 (the Steiner step-out, chests, the ATE menu/pick/title/own jump/cancel,
"no 2 Vivis", the 3x speed mirror).

## During the session

- If the guest gets left behind: press **F11**, or hold **L3** for about a second (not mid-climb). If you are ever stuck
  partway up a ladder, press **~** and click **Reload field** on the **Go** tab.
- Any `[NetSync] field swap fault` line in either log is a red, whatever the check: note what you were doing.
- Keep both `Memoria.log` files after the session (each is in its machine's FF9 folder, next to `Memoria.ini`). Each
  launch overwrites it, so copy it out before you relaunch either game.
