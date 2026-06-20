# Forking FF9 — your first edit

A guided, GUI-driven walkthrough: fork a slice of *Final Fantasy IX*, change a single line of dialogue,
and play it back in-game. It's the fastest way to see the whole loop — **fork → edit → deploy → play** —
end to end. Start small (a couple of arcs); you can always add more later.

> **Prerequisites:** Python, UnityPy, and the custom Memoria DLL. See **[SETUP.md](SETUP.md)** for the
> full prerequisite details.

---

## Part 1 — Create your Journey file

1. Install all prerequisites (Python, UnityPy, the Memoria custom DLL — see [SETUP.md](SETUP.md)).
2. Open the GUI app at `apps/ff9_workspace.pyw`.
3. Select **Journey** in the top left, then **New Journey**.
4. For **Type**, select **Multi-campaign arc**.
5. For **Hub Name**, **First journey id**, and **First journey name**, put whatever you want (e.g. `MyFF9Mod`, `ff9_test`, `ff9_test`).
6. For **folder**, create a new scratch directory to work from (e.g. `C:/MyFF9ModDirectory`).
7. Click **Pick FF9 Regions…** and add a couple of arcs (**Prima Vista → Evil Forest** is a nice starter pack — more can be added later).
8. Hit **OK**. This creates a `journeys.toml` in your directory (take a look to see the project structure — open it with any text editor), and loads the **Journey Editor** screen.

## Part 2 — Grab the game files

> **Pit stop:** Go to **Import**, scroll all the way down, and hit **Regenerate base templates**. This makes
> grabbing the game files possible — the toolkit ships no proprietary Square Enix data.

1. Hit the big blue **Fork all missing** button and wait until it completes. Forking isn't instant — that's
   why you should only start with a couple of arcs. If you went overboard in the region selector, just wipe
   the journey directory and start fresh. Forking Prima Vista → Evil Forest took me about 10 minutes.
2. Take another look in the project directory if you want. You'll see each zone in its own folder, holding
   its individual fields in their own folders — each extracted as a series of game files the toolkit can
   edit and/or redeploy. For example:

   | File | What it is |
   |---|---|
   | `field.toml` | the project file, with scripting info |
   | `atlas.png` | the background, in a scrambled texture atlas |
   | `sps` | special effects / particles (Vivi's ice-wall-melting fire, fog/mist, etc.) |

3. Hit **Fill entry from forks** to wire New Game to the correct spot.

## Part 3 — Make an edit

> Don't go overboard during these steps — follow the one-line change.

1. Double-click **prima-vista**.
2. You should have **PRIM_TH_CGR** selected. That's the opening field (Zidane lighting the candle).
3. Ignore Field / Camera / Dialogue / etc. for now — go down to **Script (verbatim .eb)** and double-click it.
4. Just follow me here, don't get overwhelmed. Go to **entry 17: player GEO_MAIN_F0_ZDN** and double-click it.
5. Go to **player_loop / tag 1** — this opens the script editor.
6. For **line 34: "Sure is dark…"**, click **Edit…** on the side and change the text to **"Sure is spooky…"**.
7. Hit **Ctrl+S**, or the blue **Save** button under the editable values. Careful messing around in here!

## Part 4 — Deploying to the game (via Memoria mods)

1. On the left panel, scroll all the way back up.
2. Double-click the very first entry (the journey you created before — right now we're still editing a field).
3. Go to the **Build Deploy** tab — your `journeys.toml` file should be pre-selected.
4. Leave the first radio button on **Preview**, then hit the **Check logic** button at the bottom.
5. You'll see a warning about `evil_forest` — since we don't carry field 652 (Qu's Marsh), we can't do the
   tutorial ATE after the escape from Evil Forest.

> **Note:** Here you can proceed to **Part 5** to fix the ATE (recommended and easy), or — if you just want
> to start testing now — skip to **Part 6** and patch in the Marsh later. It won't affect your project to
> patch later, and in the meantime you'll be able to play the game up until that ATE, before being warped
> back into the actual game fields.

## Part 5 — Fixing the ATE

1. Switch back to the Journey Editor tab (or double-click your journey).
2. Click **Add region to arc…**.
3. We've got 3 warnings — we need fields 652, 1201, and 1205. The regions are listed by starting seed number.
4. For those 3 fields, check **Marsh (seed 650)** and **A. Castle (ids 1200+) (seed 1200)**.
5. Hit **Add selected**.
6. **Fork all missing** again (a couple of minutes). We'll have more warnings now — we can ignore them for
   now (they can be patched away later).
7. Nice. Repeat this process later if you want to test/edit more of the base game.

## Part 6 — Deploying to the game after considering warnings

> **Note:** Back up your mods. I've only tested this toolkit with Moguri Mod (+ Moguri Mod Video). That is
> the recommended state for the time being.

1. Same setup — **Preview deploy playbook**.
2. Hit **Build / Deploy Journey** (it will do a Preview; it won't deploy anything until you flip the first
   radio button).
3. You should see nothing in the Problems panel besides the green *"Printed the journey deploy playbook…"*.
4. Change the first set of radio buttons to option 2 — **Deploy journey to game (one-shot: campaigns…)**.
5. Change the second set of radio buttons to option 3 — **straight into the opening**.
6. Hit **Build / Deploy Journey**. This time, it will actually build the mod folders in Memoria.

> **Note:** Right now I create a mod folder for each region you fork. This will be fixed in the future, but
> for now you just have to deal with it — the old paradigm wasn't compatible with forking the entire game.

7. Add the new mod folders to the `FolderNames` line in `Memoria.ini` (the deploy's console output lists
   exactly which ones — or use the Memoria launcher). Their **order no longer matters for dialogue** — each
   forked region now gets its own text blocks — so you just need them all present. For example:

   ```ini
   FolderNames = "FF9CustomMap-prim", "FF9CustomMap-aca2", "FF9CustomMap-acas", "FF9CustomMap-alex", "FF9CustomMap-camp", "FF9CustomMap-evil", "FF9CustomMap-mars", "FF9CustomMap-pri2", "MoguriMain", "MoguriVideo"
   ```

## Part 7 — See if it worked

1. Load Memoria, hit **New Game**.
2. The cinematic plays (you can skip it).
3. Zidane should say **"Sure is spooky…"**
