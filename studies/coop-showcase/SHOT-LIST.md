# Co-op showcase video: recording-day shot list

For the 3-4 minute co-op showcase (beat sheet: cold open, proof shot, joining, walking and talking, the fight,
the cable pull, story montage, outro). PC 1 = the desktop, HOST. PC 2 = the laptop, GUEST. Shoot in the order
below (grouped by save); edit in beat-sheet order.

Grounded on master `94ad3d5c` (co-op through s144; protocol v14). Re-check this list once s145 lands and the
release bundle exists.

---

## 1. Once, before recording day

- [ ] **Same engine on both PCs: the b20 release bundle.** Not the dev DLL, so there is no work-in-progress, the
      Journal is off, and viewers get the same thing. Compare the hashes on both machines:
      `Get-FileHash "<game>\x64\FF9_Data\Managed\Assembly-CSharp.dll"`.
- [ ] **Same kit build on both PCs.** It writes the config and runs the bridge.
- [ ] **No engine rebuilds during the shoot.** Pause every agent session that could run `build_memoria.py`, which
      auto-deploys over the live install, or that deploys into the game folder. That includes s145 work.
- [ ] **Strip the dev mod folders on the desktop.** Back up `Memoria.ini` first. In the Memoria launcher's Mod
      Manager, turn off `FF9CustomMap`, `FF9CustomMap-world`, `FF9CustomMap-schema` and `FF9CustomMap-msgs`, and
      keep `FF9Coop`. Use the launcher, not a hand edit, so `Priorities` stays consistent. This removes the New
      Game override, so the stock opening plays. It also removes the custom overworld and the dev text.
      After launch, `Memoria.log`'s `[Initialization] Mods:` line must list only what you kept.
- [ ] **The same visual mods on both PCs** (Moguri on both, or on neither). Otherwise the two screens won't
      match side by side.
- [ ] **Desktop `Memoria.ini` changes for the shoot:**
      - `[SfxProbe] Enabled = 0`. It's on now and dumps summon data every frame.
      - `[Folklore] Enabled = 0`, for a stock main menu.
- [ ] **Swirl decision.** Do one rehearsal take each way and keep the one that looks better.
      - Off: `[Graphics] BattleSwirlFrames = 0` on both (Memoria's default, an instant cut).
      - Classic PSX swirl: `BattleSwirlFrames = 115` on both, plus `[Netsync] DioramaSwirlFrames = -1` on the
        guest. The guest plays the shorter of its own swirl and this key, so -1 means "use mine".
- [ ] **`[Battle] SFXRework = 1` on both** (the default). The guest's attack and spell replay needs it.
- [ ] **Same window mode and resolution on both** (borderless 1920×1080). Set OBS Game Capture on each PC, and
      record a mic track on each for the clap sync.
- [ ] **One controller per PC.** Nothing else plugged into the desktop: a stray pad has knocked a launch off the
      title screen before.

### Saves to make on the HOST (the guest can load any of its own)

| Save | Where | Party | Used for |
|---|---|---|---|
| **New Game** | stock opening (fields 50-69, Prima Vista) | Zidane + Blank / Marcus / Cinna | story montage, opening dialogue |
| **E1** | Evil Forest trail, field **250** (the Fang encounters from the R3 sittings) | check in the party menu | joining, walking, the fight, the cable pull |
| **E2** | the screen before the Nest, entering field **257** | 257 seats **[Blank, Zidane, Vivi, Steiner]** | cold open, boss montage |

The guest's own save is never touched. While paired, its story state mirrors the host's and saving is off.
When the session ends, it reloads its own autosave.

---

## 2. Co-op settings per PC

**Commands (relay mode, the transport the two-PC sittings proved).** Keep each console open: it runs the
bridge for the whole session.

```bash
# HOST (desktop, from the repo's ff9mapkit\ folder) -- prints the session code and copies it
py -m ff9mapkit coop host --guest-slots 3 --ghost-as auto --hang-dump
```
```bash
# GUEST (laptop)
ff9mapkit coop join ff9-XXXXXXXX --follow-host on --ghost-as off
```

LAN alternative (same network, no relay or bridge; it uses the direct-TCP transport):
`coop host --lan --guest-slots 3 --ghost-as auto` and `coop join --lan <desktop IP> --follow-host on --ghost-as off`.

Then run `coop show` on both and read it back.

| `[Netsync]` key | HOST | GUEST | Set by |
|---|---|---|---|
| `Enabled` | 1 | 1 | `coop` |
| `Role` | host | client | `coop` |
| `TargetField` | 0 (everywhere) | 0 | `coop`. Must be 0, or following breaks |
| `GuestSlots` | 4 (= position 3) | — | `--guest-slots 3` |
| `GhostAs` | `auto` | empty (off) | `--ghost-as`. Host only: the guest wears the host's pick |
| `FollowHost` | 0 (forced) | 1 | `--follow-host on` |
| `SelfDress` | — | 1 (default) | leave |
| `ActionReplay` | — | 1 (default) | leave |
| `GuestStockMenu` | — | 1 (default) | leave |
| `SessionGraceMs` | — | 40000 (default, the max) | leave |
| `AutoTeleport` | — | 0 (default) | leave |
| `DioramaSwirlFrames` | — | 0, or -1 for the swirl | hand edit (see section 1) |
| `StartHoldMs` | 8000 (default) | — | leave. The host's gauges wait for the guest's battle to load |
| `GuestWaitMs` | 30000 (default) | — | leave. Caps how long a guest turn freezes the gauges |

**`--guest-slots` is a party POSITION, and story scripts reorder the party.** Position 3 is Vivi at Plant
Brain, but may be someone else on field 250. The guest can never command the host's leader (Zidane); s143
moves that bit to the next member. To change it mid-session, run
`py -m ff9mapkit coop host --guest-slots N --no-bridge` in a second console. It takes effect within about 2
seconds, and the bridge keeps running.

---

## 3. The shots

Shoot order, grouped by save. "Edit beat" is where the shot lands in the video.

### Session A — Evil Forest (host loads E1, field 250)

| # | Edit beat | Setup | Action | Check before rolling | Cut at |
|---|---|---|---|---|---|
| A1 | Joining (0:25) | Host on 250 with `coop host` running; guest at its own save, not yet joined. | Guest runs `coop join`; it warps onto 250 dressed as its party member. Hold both screens 3 s on each console line. | The guest's body is the expected character, not Zidane and not a moogle (a moogle means its slot is empty). | The guest standing beside the host |
| A2 | Walking and talking (0:45) | Paired on 250. | Walk two or three trail screens; the guest follows through each change. Talk to an NPC or save moogle on your route; pages turn on both screens with the host's presses. | Avoid NPCs that quote gil, cards or frogs: on the guest those read its OWN save. | Last page closing |
| A3 | The fight (1:30), several takes | Paired, host walking 250 for a random encounter. | Fight to the victory fanfare. The guest picks a spell or attack from FF9's real menu each turn, then rewards play, and both land back where they stood. | First command phase: the guest shows "You: Vivi" and the host "Partner: Vivi (not Zidane)". If the name is wrong, fix `--guest-slots` before the next take. | Both back on the field |
| A4 | Cable pull (3:00) | A fresh random battle. | Between the guest's turns, not with its menu open, unplug the guest's network or switch off its Wi-Fi for about 15 s, then restore. The guest's screen holds; the host covers the guest's turn; the guest resumes the same fight. | Clock the cut and stay under 20 s, the drop length played on two PCs. Past 40 s the guest gives up and reloads its own autosave. | The guest's next action after it resumes |

### Session B — Plant Brain (host loads E2)

| # | Edit beat | Setup | Action | Check before rolling | Cut at |
|---|---|---|---|---|---|
| B1 | Cold open (0:00) + montage | `--guest-slots 3`, so the guest is Vivi. | The boss fight. Get a take where Vivi casts on Plant Brain and the spell lands on both screens. | "You: Vivi" / "Partner: Vivi (not Zidane)" on the first turn. | **The victory pose.** It's a scripted story battle, so the guest's post-battle lines can run ahead of the host's (known issue) |

### Session C — the opening (host: New Game)

| # | Edit beat | Setup | Action | Check before rolling | Cut at |
|---|---|---|---|---|---|
| C1 | Story montage (3:20) | Host New Game; the guest joins once the host is on field 50. | Opening dialogue playing in step on both screens. | Fields 50-57: the guest appears as a **moogle**, because its slot is empty at load (accepted; a cute beat). | Any clean line |
| C2 | Story montage | Same run, through the first battle (338). | A short clip of the Tantalus fight. | After battle 338, field 63 shows **two Cinnas**: the guest dressed as Cinna beside Cinna's NPC (accepted as built). Use it or avoid that framing. | The victory pose (scripted battle) |

### Any session

| # | Edit beat | Shot |
|---|---|---|
| P1 | Proof (0:15) | A phone shot of both monitors and both controllers in two people's hands, with a battle running. One continuous take, no cut. |
| P2 | Joining B-roll | The two console commands on screen, readable for about 3 s. Blur the session code. |

---

## 4. Every take

1. [ ] **OBS:** recording on BOTH PCs. Clap once where both mics hear it, for the sync.
2. [ ] **Consoles:** both bridge consoles alive and quiet, no SILENT lines. `coop show` is unchanged.
3. [ ] **Placement and dress:** the guest is on the host's field and dressed as planned.
4. [ ] **Clean screens:** no booster icons on either screen (speed, 9999 damage, no encounters), no `~` menu, no
      debug overlay.
5. [ ] **Turbo dialogue off:** a test line advances only on a press. If pages fly by, F9 is latched: press it
      once.
6. [ ] **Guest hands-off:** the guest never presses Menu (a following guest has no main menu; it buzzes by
      design), never takes the "Leave diorama" option, and never uses the manual teleport (F11/L3) on camera.
7. [ ] **Stay off-plan areas:** no shops (untested on two PCs), and no world map unless s145 has landed. On s144
      the guest waits on the world map and rejoins at the next field.
8. [ ] **Know the cut point** before rolling. Story battles end at the victory pose.

## 5. If something goes wrong

- **The host freezes at a battle start.** This is the one known, unexplained freeze. Do not close FF9. Wait
  30 s or more for "hang dump written" in the host console. Then save BOTH machines' `Memoria.log` and
  `output_log.txt`, plus both bridge logs from `%LOCALAPPDATA%\ff9mapkit\bridge-logs\`, before relaunching.
- **The guest drifts off the host's field.** Use the manual teleport (F11/L3) off camera, then re-take.
- **The guest fell back to its own autosave** (the link was silent too long). Load back in; `FollowHost` brings
  it to the host's field.
- **The guest commands the wrong character.** Re-run `coop host --guest-slots N --no-bridge`, and read the
  "You: …" line on the next battle.

## 6. After the shoot

- [ ] `coop off` on the laptop, unless it stays a co-op machine.
- [ ] Restore the desktop's backed-up `Memoria.ini` (mod folders, `[SfxProbe]`, `[Folklore]`, swirl), or
      re-enable the folders in the launcher.
- [ ] Archive the logs from any take that misbehaved.
