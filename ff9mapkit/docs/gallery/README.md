# Gallery

Visual proof of each headline capability. Drop a screenshot or short GIF next to this file using the
exact filename in each `![...]()` below and it renders automatically. Aim for ~800px-wide PNGs or
short (3–6s) GIFs; in-game shots are far more convincing than UI screenshots.

> Tip: capture in a consistent window size, and prefer a moment that shows the feature *doing
> something* (the player on the walkmesh, the NPC mid-line, the camera mid-switch).

---

### A from-scratch custom room, in-game
Painted background + custom walkmesh + the player standing on it, in real gameplay.

![A custom-painted FF9 field running in-game](room-painted.png)

### Fork a real field
A real FF9 field (e.g. Gargan Roo) imported and running as a custom field with your own NPC dropped in.

![A forked real field with a custom NPC](fork-real-field.png)

### Pixel-accurate paint guide
The generated guide (floor frame + perspective grid + height poles) beside the painting done over it.

![Paint guide next to the finished painting](paint-guide.png)

### NPC + custom dialogue
An NPC mid-conversation with your own authored line.

![NPC speaking custom dialogue](npc-dialogue.png)

### Gateways (room-to-room)
Stepping through a door from one custom room into another (or back into the real world).

![Walking through a gateway between rooms](gateway.gif)

### Random encounter
A battle triggered from the custom field (bonus: with the field's own battle music).

![A random encounter triggered in a custom field](encounter.png)

### Events — chest / story flag
A switch/chest firing: item + gil + a message; or a flag flip that reveals an NPC / unlocks a door.

![A treasure/flag event firing](event.gif)

### Cutscene (actor)
An NPC walking in, turning, emoting, and talking under a control-locked scene.

![An actor cutscene playing on entry](cutscene-actor.gif)

### Multi-camera switch
The view cutting between two camera angles as the player crosses a switch zone (tint/perspective change).

![Multi-camera switch as the player crosses a zone](multi-camera.gif)

### Scrolling field
A larger-than-screen room where the camera pans to follow the player.

![A scrolling field following the player](scrolling.gif)

### Foreground occlusion
The player walking behind a near foreground layer that draws over them.

![Foreground layer occluding the player](occlusion.png)

### Blender authoring
The add-on: posed FF9 camera, walkmesh on the floor guide, and placed markers (NPC / gateway / spawn).

![Authoring a field in the Blender add-on](blender-authoring.png)

### Form editor
`ff9mapkit edit` — dialogue / events / cutscene steps authored in forms, no TOML.

![The form-based logic editor](form-editor.png)

---

## Shot list (checklist)

- [ ] `room-painted.png` — custom painted room, player on the floor
- [ ] `fork-real-field.png` — imported real field + your NPC
- [ ] `paint-guide.png` — guide ↔ finished painting
- [ ] `npc-dialogue.png` — NPC speaking a custom line
- [ ] `gateway.gif` — door transition
- [ ] `encounter.png` — battle from the custom field
- [ ] `event.gif` — chest/flag event firing
- [ ] `cutscene-actor.gif` — actor walk/talk cutscene
- [ ] `multi-camera.gif` — camera switch
- [ ] `scrolling.gif` — scrolling/pan
- [ ] `occlusion.png` — foreground occlusion
- [ ] `blender-authoring.png` — the Blender add-on
- [ ] `form-editor.png` — the editor
