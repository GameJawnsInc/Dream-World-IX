# Rung 7 — the two open playtests

Both of Rung 7's open in-game questions are already **built, deployed and reachable**. Nothing
below needs a build step; it needs a controller.

| # | The claim under test | Rung | Fields |
|---|---|---|---|
| A | A composed room too wide for one screen **scrolls, and walks correctly**, at both 768 and 960 | 7b | 30701, 30702 |
| B | An NPC placed by clicking a composed room's art **stands where it was clicked** | 7d | 30700, 30701, 30702 |

The fixture is one three-room dungeon, `studies/click-authoring/rung7-playtest/`, drawn so the
three rooms land on the three camera regimes the composer can choose: a **static 384** painting, a
**768** scroll and a **960** scroll. Every room carries one NPC, placed through the real click path.

> ⚠ **These ids were registered while the game was running, so the first launch after this must be
> a full relaunch** (DictionaryPatch is read once at launch). After that, `~ → Reload field` is
> enough for content edits.

---

## Reach it

```bash
py tools/deploy_field.py studies/click-authoring/rung7-playtest/HALL_STATIC/hall_static.field.toml --id 30700
```

Already deployed — that line is only for a re-deploy after an edit (the other two rooms are
`HALL_768/hall_768.field.toml --id 30701` and `HALL_960/hall_960.field.toml --id 30702`).

In-game: **`~` → Warp to field → 30700**. The rooms are wired both ways, so the whole test is one
continuous walk:

```
HALL_STATIC (30700, static 384)  --east door-->  HALL_768 (30701, scrolls)  --north door-->  HALL_960 (30702, scrolls)
```

---

## The reference frames — this is what makes it a measurement

`studies/click-authoring/rung7-playtest/reference/*.png` is each room's **own painting** with the
NPC (red), the spawn (blue) and each arrival (green) marked, at 1:1 canvas scale.

Every NPC was placed on a **checkerboard lattice corner** — the exact point where four checker
squares meet — on purpose: it is a landmark you can see in-game and point at, so "did it land
where it was clicked" is a comparison and not a judgement call.

| Room | NPC | world (x, z) | the landmark it must stand on |
|---|---|---|---|
| HALL_STATIC 30700 | `moogle_bard` | (-500, -869) | corner of checker column 3 / row 4, counting from the room's left-front |
| HALL_768 30701 | `fossil_bard` | (800, -1304) | column 8 / row 3 |
| HALL_960 30702 | `cleyra_scamp` | (2000, -1662) | column 9 / row 4 |

The rooms are 12×12 checkers. Row 0 is the FAR edge and row 12 the near edge; column 0 is the left
edge. Each NPC is at a *corner*, not a square centre.

---

## A — the scrolling rooms

**HALL_768 (30701).** Walk the full width, west wall to east wall.

1. The view **pans** as you approach either side; it does not jump, and the floor does not tear.
2. The checkerboard stays put under you the whole way — the walkmesh and the art agree at the far
   left and the far right, not just in the middle. *(This is the one thing a static camera cannot
   get wrong and a scrolling one can: the painting is 768 wide and the screen is 384.)*
3. Walk into the far east wall and the far west wall. You stop at the wall, not before it or
   through it.
4. Your character is not a sliver — the composer measured this room at 10.9 canvas px per
   character against FF9's own median of 9.3.

**HALL_960 (30702).** The same walk, on the width **that has never been walked in this repo**.
768 was proven by the field-4003 spike; 960 is inside FF9's own shipped envelope and nothing more.

5. Everything in 1–4 again, west wall to east wall. This room is 8000u across.
6. Specifically watch the **far east end**, which is the part of the painting the viewport reaches
   only at the clamp (`Viewport: 160, 800, 112, 336`) — if the pan's right-hand limit is wrong,
   this is where the art runs out from under you.

**What a failure looks like:** the character drifts off the checkerboard as you cross (walkmesh
and painting disagree), the view stops panning before the wall, or the floor draws over your head
(the layer depths — measured offline as 758u / 803u / 1236u of clearance over the whole mesh, so
this one should be clean).

---

## B — the placed NPC

In each of the three rooms:

7. Find the NPC. Compare where it stands against the reference frame and the checker corner in the
   table above. **It should be standing on the corner itself**, not one square off.
8. Do it in all three. If only 30702 is wrong, the defect is in how the wide (960) frame is
   resolved for placement, not in placement; if all three are wrong the same way, it is the
   placement path; if only the scrolling two are wrong, it is the scroll frame.

Then reproduce the gesture yourself, which is the part that closes the rung:

9. Workspace → open `studies/click-authoring/rung7-playtest/HALL_960/hall_960.field.toml` →
   **Place** tab → Load the room → click a *different* checker corner → deploy that room again →
   walk to it. This is the claim in its own words: *"place an NPC in a composed room and confirm it
   stands where you clicked."*

---

## What was already settled offline, so it does not need eyes

Stated so a playtest verdict can be attributed. Every one of these is a measurement, not a claim
that it looks right — that is exactly what the playtest is for.

- The built `.bgx` for 30701 reads `Range: 768, 448` / `Viewport: 160, 608, 112, 336`, and 30702
  reads `Range: 960, 448` / `Viewport: 160, 800, 112, 336` — both exactly `cam.scroll_bounds`.
  `ViewDistance: 498` on all three, i.e. the focal length is measured at the 384-wide **screen**,
  not at the painting.
- Both scrolling rooms' `.eb` opens `Main_Init` with `EnableCameraServices`; the static room's
  script does not contain the opcode anywhere. Decoded structurally through `eb.disasm`, not by
  searching for a raw `0x71` byte (which would say "present" for both and prove nothing).
- Each NPC's canvas pixel round-trips back through `cam.to_canvas` to **0.0 px** (worst 1.1e-13),
  and the click path lands on the intended checker corner to within 8e-13 world units.
- `ff9mapkit lint` on all three rooms: 0 errors.
- The layer depths clear the player over the *whole* mesh in every room (above).

## What is deliberately NOT covered

- **Depth.** Scroll pans a viewport across a FIXED camera, so it buys width and nothing else. None
  of these rooms is deep enough to test far-edge foreshortening; the composer's answer for a deep
  room is to split it.
- **1536-wide paintings.** `SCROLL_RANGE_CAP` is 960 because that is the widest painting Square
  shipped. Wider builds clean offline and is not offered.
