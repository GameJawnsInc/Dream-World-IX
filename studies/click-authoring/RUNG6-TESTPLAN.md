# Floorplan tab — first-contact test plan (~1 hour)

> **Status: UNVALIDATED BY ANY HUMAN.** Written 2026-07-30 for the tab's first contact. Timings in
> Step 5 are measured, not estimated. Findings and verdicts belong back in `PLAN.md`'s Rung 6 block.


## What this is

The **Floorplan** tab (Author rail, right of Place) lets you draw a dungeon as a *plan view* — rectangles for rooms, a click on a shared wall for a door — and press **Compose** to get N wired FF9 fields out of it: one field per room, gateways both directions, an arrival position *and* facing on each side, encounters, save-point siting. The payoff is that a five-room dungeon becomes a real, buildable campaign in about two minutes of drawing instead of five hand-written `field.toml`s.

**No human has ever used this tab.** It was built by an agent and reviewed by a second agent; it has 73 automated fences and a wall of rendered screenshots, and zero minutes of human hands. You are the first. "I don't understand what this is asking me to do" is a *finding*, not a failure on your part — write it down.

**One thing settled before you start, so you can relax about it:** the offline pipeline works. A hand-built 3-room plan composed, linted and `build-all`'d clean, with a real deployable `dist/` for all three rooms. Nothing is fundamentally broken. What is unproven is everything a *mouse* touches.

---

## Before you start

**Launch:** `py apps/ff9_workspace.pyw` from `C:/gd/Dream-World-IX`. Then **maximise the window** — the tab wants ~1100px of height and only gets 850 in the default window; a cramped chart is not the design's fault and you'll misjudge it.

**Nothing needs to be open.** No project, no campaign, no field. The tab is self-contained; a fresh Workspace with "No project open" in the breadcrumb is the correct starting state. Nothing needs to be on disk either.

**Two setup items, both 10 seconds:**

1. Click **Author → Floorplan**.
2. In the **First id** box, type **`30700`**. Leave nothing to chance here — the box's "auto" fallback reads a gitignored `.ff9deploy.toml` that does not exist at the repo root, so from a plain checkout the tab will sit there with Compose greyed out and a refusal in the list. That refusal is *correct behaviour*, not a bug, but it looks like a dead tab. 30700–30705 are free on this install (registered scratch ids today: 30058, 30301, 30421, 30424, 30425, 30500, 30501, 30510).

**If you run the CALIBRE text dial at 125 or 150:** drop it to 100 for this hour. At 150 the drawing surface collapses to 179–207px, room labels vanish and the compass chip paints over the top room. See "Known and deliberate".

**Read the blue line at the very bottom of the panel first.** It is the tab's entire tutorial and it is ~540px below where your eye lands: *"Draw a room: click its corners on the chart, then click the first corner again to close it."*

---

## What you should be seeing

These are rendered from the real widget. Open them next to the app so you can tell a bug from the design.

| State | PNG |
|---|---|
| Empty tab | `C:/gd/Dream-World-IX/tools/scroll_out/gui_snaps/fp_dark_100/floorplan-bare_dark_100.png` |
| 3 rooms, no doors (warning) | `.../fp_dark_100/floorplan-rooms_dark_100.png` |
| Doors mode, one door declared | `.../fp_dark_100/floorplan-door_dark_100.png` |
| A hard gate refusing | `.../fp_dark_100/floorplan-refused_dark_100.png` |
| Findings list dragged shut | `.../fp_dark_100/floorplan-reclaimed_dark_100.png` |

**Layout, top to bottom:** a `Rooms | Doors` pill pair with `Undo` / `Clear` at the right → the dark chart (compass chip top-left, "Ctrl+scroll zooms · Ctrl+0 fits" chip bottom-right) → `Open… / Dungeon / Mod` → `First id` + the `Compose…` button → a one-line coloured status → a hairline → the findings list.

**Colour legend — you cannot read the chart without this:**

- **Blue** room outline = composes fine.
- **Amber** outline + a leading **`!`** on the label = warning; it still builds.
- **Red** outline + a leading **`✕`** = refused; **Compose… greys out.** That greying is the single clearest signal on the screen.
- **Green dashes** on a wall = a declared door (or a hoverable candidate).
- **White circles** at corners = drag handles.
- **Dashed line** = a wall two rooms share.

Look at `floorplan-refused_dark_100.png` before anything else — that is the tab at its best: both rooms red, Compose off, and the findings row naming the number, the consequence *and* the value to use.

---

## The walkthrough

### Why the order is what it is

Steps 1–3 are gesture work that looks trivial and is not. Every automated fence but one drives the tab's *internal* seam (`click_world`, `press_world`…) rather than a real Qt mouse event — and that gap is exactly how a control that was **dead on click** shipped past 47 fences and every screenshot last round. Anything your mouse does in steps 1–3 is, in the strict sense, being run for the first time. Go slowly and deliberately there; you can move fast from step 4 on.

---

### Step 1 — Draw one room, and abuse the clicks (~8 min)

**Do this**
- `Rooms` mode. Click four corners of a rough rectangle, **single deliberate clicks, no dragging**, roughly 1200 × 1600 units — about a fifth of the chart's width at the opening zoom.
- Before closing it: click **exactly on the corner you just placed**, a second time.
- Press **Escape**.
- Draw it again, and this time close it by clicking the **first** corner. Then draw a second throwaway shape and close *that* one with a **double-click**.

**Expect this**
- Each click adds a corner and the status reads `1 corner placed — keep clicking; a room needs at least 3.`, then at 3+ it changes to `…click the first corner again (or double-click) to close it.`
- The duplicate click is **refused out loud**: `That is the corner you just placed — a duplicated corner is refused by gate G1, so it is not added.` No corner appears.
- Escape wipes the in-progress outline, status `outline abandoned`.
- Both close gestures produce a closed room, named `ROOM1` / `ROOM2`, blue, with white handles, labelled with its name, its `N × Nu` size and (on the first) `entry`.

**Suspect a bug if**
- A single click does nothing at all — that is the dead-on-click class returning. **Stop and tell me.**
- Double-click closes but self-click doesn't, or vice versa.
- The duplicate-corner click silently adds a corner (no message).
- Escape does nothing while an outline is pending.

---

### Step 2 — Draw a second room abutting the first (~8 min)

**Do this**
- **Zoom in first**: Ctrl+scroll up two or three notches. This matters — see below.
- Draw ROOM2 sharing a wall with ROOM1: place its first corner **directly on top of one of ROOM1's existing corner handles** (a still, deliberate click — do not let the mouse travel).
- Finish and close it.

**Expect this**
- The click on ROOM1's handle starts ROOM2's outline. It does **not** grab and drag ROOM1's corner.
- Once both rooms exist the shared wall draws as a **dashed** line.
- ROOM2 goes **amber** with a `!`, and the findings list says `unreachable from ROOM1: ROOM2 — no chain of doors leads there, so the player can only arrive by a debug warp`. That warning is correct; you haven't made a door yet.

**Suspect a bug if**
- The click on ROOM1's corner *moves ROOM1's corner* instead of starting a new outline. This is the precise defect the last review caught; it is fenced now, but only for one synthesised case. **Report immediately if you see it.**
- No dashed shared wall appears even though the walls look flush.

**Why zoom first:** two rooms must abut within **8 world units** to be offered as a door. At the zoom the chart opens at, one screen pixel is already ~9 units — a single-pixel miss is out of tolerance. Rooms 9u apart offer *nothing at all*, and the only feedback is a note saying no shared wall is here. If Doors mode offers you nothing in step 3, this is almost certainly why: zoom in and nudge a corner.

---

### Step 3 — The rest of the mouse: drag, right-click, zoom, fit (~8 min)

**Do this**
- Drag a **corner handle** of ROOM2, slowly.
- Drag the **middle** of ROOM2 to move the whole room.
- **Right-click** a room (Rooms mode) → `Rename…`, `Make ROOM2 the entry room`, `Delete ROOM2`. Use Rename, cancel the rest.
- **Ctrl+scroll** to zoom, **Ctrl+0** to fit, **Ctrl+1** for 1:1.
- Left-drag on empty chart space.

**Expect this**
- While dragging, a floating chip shows live coordinates: `ROOM2 corner 1 · x -1200 · z 800` (or `ROOM2 · centre x … · z …` for a whole-room drag). It hides on release.
- The right-click menu has exactly three items; `Make … the entry room` is **greyed out** on the room that is already the entry.
- Ctrl+0 frames everything; left-drag on empty space **pans**.

**Suspect a bug if**
- ⚠ **The room snaps back to where it was when you let go.** This is a *known confirmed defect* and I want to know whether you actually hit it in practice: a background gate check finishing mid-drag cancels the drag silently, with no message and no undo entry. It needs a plan big enough for the check to be slow (3+ rooms) and a slow drag. If it happens, note roughly how many rooms were on the chart.
- The coordinate chip stays on screen after you release, or overlaps the "Ctrl+scroll zooms" chip in the bottom-right corner. (This one is genuinely unverified — no static screenshot can render a hover chip.)
- Ctrl+scroll scrolls the page instead of zooming.

---

### Step 4 — Declare a door, and watch a hard gate fire (~10 min)

**Do this**
- Click the **Doors** pill. Hover the shared wall.
- Click it.
- Now set **Door depth** to **100** and watch the chart.
- Set it back to 250.
- Right-click the door → `Delete the ROOM1–ROOM2 door`. Then re-declare it.

**Expect this**
- Doors mode reveals two extra controls inline: `Door depth [250 u]` and a readout of the selected wall.
- Hovering the shared wall shows `1200u shared wall — click for a door`; clicking it lays **green dashes** along the wall, both rooms turn **blue**, and the unreachable warning drops away.
- At depth 100 both rooms flip to **red with ✕**, the status line goes red, **Compose… greys out**, and the findings list reads, verbatim: *door ROOM1-ROOM2: depth 100u leaves a standable window only 20u wide — the player centre is clamped 80u off the wall, so the strip would be drawn and (near-)never fire. Use at least 160u; 250 is the default and 170 is the in-game-proven floor.*
- Back at 250 everything returns to blue and Compose re-enables.

**Suspect a bug if**
- Compose stays **enabled** while rooms are red. That is the gate failing to hold the door.
- The depth spinbox refuses to accept 100. (It shouldn't — a too-shallow value is *meant* to reach the gate and be refused out loud rather than silently clamped.)
- Clicking a wall declares a door on the *wrong* pair of rooms.

**Two right-click dead ends, both by design, neither in a tooltip** — don't report them, but tell me if they annoyed you: in **Doors** mode a right-click inside a room opens nothing at all (the room menu is Rooms-mode only); and if even one stray pending corner is down, a right-click is eaten as "abandon the outline" and the menu never opens.

---

### Step 5 — Grow it to four rooms and judge the responsiveness (~7 min)

**Do this**
- Add two more rooms and doors, to four rooms total.
- After each gesture, watch the status line and the Compose button.
- Then click into the **Dungeon** box and type a long name like `GREATHALL` at normal typing speed.

**Expect this** — measured twice on this machine, and **room SIZE dominates**, because the clearance
test grid-samples each room's bounding box at 8-unit steps (a 2400×1800 room is ~67,500 samples,
re-walked per room, per door strip, and again to site the spawn):

| rooms | small rooms (1200×1600) | full-size rooms (2400×1800) |
|---|---|---|
| 1 | 0.42s | **1.02s** |
| 2 | 2.5s | **3.75s** |
| 3 | 3.9s | **5.46s** |
| 5 | 7.8s | **9.11s** |
| 8 | — | **16.45s** |

- The gate re-runs on **every** edit, on a worker thread, 140ms after you stop.
- So: live at one room, awkward at two, and past four every gesture leaves Compose disabled with the
  status stuck on `checking the gates…` for the better part of ten seconds. **At a real dungeon's
  size this is not a live gate, it is a stall.**
- Typing fires a full re-check **per keystroke** and nothing cancels a superseded one — they stack.
  The whole Workspace can drop to a crawl while several run at once.

**You do not need to characterise this — it is a confirmed design problem and the numbers above are
mine, not an estimate.** The only thing wanted from you here is the judgement call: **is live gating
worth keeping at all once it is fast** (the fix is straightforward — cache `standable` per room and
only re-judge what changed), **or would you rather it were a button you press?**

---

### Step 6 — Compose (~5 min)

**Do this**
- Confirm **First id** reads `30700`, give the dungeon a name, press **Compose…**, and pick an output folder *outside the repo* — use your Desktop or `C:/temp/`.

**Expect this**
- A directory picker, then the Output panel streaming `py -m ff9mapkit floorplan <path>` with per-room id / vert / pitch / dist lines, then the exact next-step commands.
- ⚠ **The app switches you away to the Map tab** and renders the composed dungeon's graph with the entry room selected; the status bar reads `NAME — 4 fields — mod folder FF9CustomMap`. That jump is the success signal — don't sit on the Floorplan tab waiting for something.
- Roughly **3 seconds per room** of waiting; the GUI stays usable throughout.
- On disk: one folder per room, plus `campaign.toml` and `floorplan.json`.

**Suspect a bug if**
- Compose does nothing, or the Output shows a traceback.
- The Map graph's rooms or door edges don't match what you drew.

**Do not be alarmed by:** the ids in the Output not matching the ids the status line promised. The live status line doesn't know what's already registered in the game; the CLI checks and shifts. **Read your real ids off the Output panel's `deploy_field.py … --id N` lines, never off the status line.** Also, `floorplan.json` gets rewritten in canonical pretty-printed form on every compose — expected.

---

### Step 7 — Build, then walk ONE room (~12 min, and the only step that touches the game)

RUNG6 asks for exactly this before anyone emits a whole dungeon: **look at the first composed room in-game.** Whether the camera's front-align framing *looks* right is the one thing no offline math can settle.

**Do this**
```
cd C:/gd/Dream-World-IX/ff9mapkit
py -m ff9mapkit lint-campaign <out>/campaign.toml
py -m ff9mapkit build-all      <out>/campaign.toml
cd C:/gd/Dream-World-IX
py tools/deploy_field.py <out>/ROOM1/room1.field.toml --id 30700
```
Then **relaunch the game** (a brand-new id needs one launch to register), and `~ → Warp to field → 30700`.

**Expect this**
- `lint-campaign` → `campaign NAME OK — N members, M edges, 0 seams, 0 warning(s)`, exit 0.
- `build-all` → one advisory `entry_settle = "auto"` warning **per room**, exit 0. Harmless.
- In-game: you stand in a placeholder room whose walkable area matches the rectangle you drew, facing into it.

**Suspect a bug if**
- Black screen (an id collision), you spawn outside the walkable area, or the camera is looking at nothing.
- Take a screenshot either way — that framing judgement is the thing I most want your eyes on.

**Hard rules for this step:**
- ⛔ **Never** `deploy-campaign --apply` on this. It `rmtree`s the whole mod folder and this install holds ~400 registrations from other sessions. One `deploy_field.py … --id N` per room, always with `--id`.
- Ignore `py -m ff9mapkit lint <room>.field.toml` if you try it — it exits **1** on that same advisory that `lint-campaign` calls clean. `lint-campaign` is the correct gate.

---

## Known and deliberate — don't spend time reporting these

- **The tab has no title and no purpose line.** Every sibling (Place, Trace) opens with a heading and a one-sentence description; Floorplan's was deliberately deleted to buy the chart 39–52px of height (measured: at CALIBRE 150 it took the chart from 127px to 179px, +41%). **This is a taste call and I want your verdict: worth it, or put the nameplate back?**
- **The findings/chart divider is a bare 1–2px hairline** with no grip texture, sitting directly *under* the status line. Drag it down and the findings list disappears with no visible way to reopen it — the only cue is the status line changing "see the list below" to "**open** the list below". Drag it back up to restore. Verdict wanted: does it need a visible grip?
- **Room labels disappear as the chart shrinks.** The size line drops first, then the whole label. It is deliberate fit-suppression, not lost data — zoom in or grow the window and they return.
- **Captions run through room wall lines.** No background plate behind them. Current behaviour at every scale.
- **The Door depth spinner's up/down arrows are blank grey blocks** in all three themes. The stepper works.
- **The depth box accepts illegal values (1–4000).** Deliberate — a bad depth must reach the gate and be refused with an explanation, not be silently clamped.
- **Undo is a button, not Ctrl+Z.** There is no keyboard undo on this tab, by design (a door spans two rooms and can never be half-undone, so it uses its own history rather than the shell's).
- **`Clear` is undoable, `Open…` is not** — Open replaces your drawing *and* wipes the undo stack.
- **At CALIBRE 150** the chart drops to 179–207px, labels vanish, the compass chip paints over the top room's edge and two of its handles, and the mode strip and status line truncate. Known; run at 100.
- **Ids `9000–9012` are silently skipped**, not refused, if your First id lands in or before that band.
- **Recompose leaves stale room folders** on disk after a rename or delete. Dead weight, not a build hazard.

---

## Questions worth a one-line answer

1. In the first 60 seconds, was it obvious what to do — or did you have to hunt for the instruction line?
2. Does drawing feel *direct*? Does the room go where your mouse went?
3. When a gate refused you (the 100u door), did the message tell you enough to fix it without asking anyone?
4. Is the wait after each edit tolerable at 4 rooms, or does the live gate need to become an on-demand button?
5. The deleted nameplate — better with the extra chart height, or does the tab read as anonymous?
6. Would you actually reach for this to lay out a dungeon, or would you still hand-write the `field.toml`s?
7. What did you expect to be able to do and couldn't? (Grid? Snapping? Typed dimensions? Corridors?)
8. Did the composed room look right in-game — camera framing, where you spawned, which way you faced?

---

## Stop and tell me immediately

- **A single click on the chart does nothing.** Dead-on-click is the failure class this whole plan exists to catch.
- **You lose work.** There is no unsaved-work prompt and no autosave anywhere on this tab: closing the Workspace, or clicking `Open…`, throws the drawing away with no dialog. If you're attached to a drawing, **Compose before you close anything.** If you lose one anyway, tell me exactly what you'd done.
- **A drag snaps back** — note the room count when it happened.
- **Any traceback**, in the Output panel or the console.
- **The composed dungeon is wrong** — rooms missing, doors joining the wrong pair, a room you deleted still present in the Map graph or on disk.
- **A black screen in-game** after warping to 30700 — that means an id collision, and it should be diagnosed before you deploy anything else.