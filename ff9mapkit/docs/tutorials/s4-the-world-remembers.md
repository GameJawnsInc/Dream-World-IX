# S4 — The world remembers

```toml
[tutorial]
track = "S"
step = 4
builds_on = ["s3-a-door-of-your-own"]
goal = "A treasure chest that stays looted across saves, and an NPC who appears only after it."
requires = ["game", "gui", "assets"]
```

So far the rooms forget everything the moment they reload. This step gives the world memory:
a **story flag** — one save-backed bit that something sets and other content reads. That single
mechanism is how FF9 worlds gain state: loot a chest → a character appears; pull a lever → a door
unlocks.

**Starting from:** the two connected rooms from S3 (any deployed fork works).

## 1. A chest with a name

In the Editor, add a **Chest** entry — a real openable chest: the model with solid collision, the
lid animation, FF9's centered *"Received …!"* box:

![A chest entry in the Editor forms — position, the item reward, and the required opened-flag](../../../docsite/assets/shots/editor-chest_light.png)

- **Position (x, z)** — on the walkable floor, reachable to press.
- **Reward item** — the treasure, by name (`Potion, 1`) or id; or **Reward gil** instead.
- **Opened-flag** — REQUIRED: the save bit that makes the loot stick. Use a **named flag**: add
  a **Flag** entry (`name = chest_potion`, `index = 8720`) and put the name here. Indices must
  sit in the **safe band `[8712, 16320)`** — lower bands belong to the real game's save data,
  and the lint refuses them.

## 2. Someone who noticed

On an **NPC** entry (new or the S2 resident), set **Appears when flag set** to `chest_potion` —
the same field visible in the NPC form from S2. Give the NPC a line that acknowledges the loot.

That is the whole producer/consumer pattern: the chest *sets* the bit, the NPC *reads* it. The
**Check** button (and Problems) lints the pair — a gate no producer ever sets is reported as dead
content before the game ever runs.

## 3. Prove the memory

Deploy, reload, then:

1. Talk to the spot where the gated NPC should be — nobody there.
2. Open the chest: lid animation, *"Received Potion!"*, and the NPC now exists.
3. Press the chest again — it stays open, no double loot.
4. **Save, reload the save.** The chest is still open; the NPC is still there.

**What you should see:** step 4 is the point — the state lives in the save file, not the room.

Locked doors are the same trick on the S3 form: a gateway's **requires flag** holds the exit shut
until the bit is set. Invisible walk-over triggers (a message zone, a pickup without a chest
model) are the [`[[event]]`](../FORMAT.md#event-optional-repeatable) form — same flags, no
furniture.

## Next

- [S5 — Lights, camera](s5-lights-camera.md): an entry cutscene over your own music pick.
- The full flag story (bands, naming, campaign-wide flags):
  [story flags & branching](../FORMAT.md#story-flags--branching).
