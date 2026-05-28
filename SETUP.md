# SETUP.md — Session 0: one-time environment setup

> Goal of this session: get the tools installed, confirm the game still
> launches, init the mod repo, and fill in every `TO VERIFY / TO SET` path in
> `CLAUDE.md` section 3. Do NOT start editing fields yet.
>
> These commands assume Windows (the FF9 Steam modding toolchain — Memoria
> Patcher and Hades Workshop — is Windows-native). `git` commands are identical
> everywhere. Steps marked **(manual GUI)** must be done by the human, not
> Claude Code.

---

## 0. Prerequisites

- Steam copy of *Final Fantasy IX* installed and launched at least once.
- `git` installed (`git --version` to check).
- **Back up your clean game folder now**, before any patching. Copy the entire
  `FINAL FANTASY IX` install somewhere safe. This is your only true reset.

---

## 1. Find and record the game folder

In Steam: right-click *Final Fantasy IX* → Manage → Browse local files. Copy
that absolute path. Typical default:

```
C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX
```

➡ Record it in `CLAUDE.md` section 3 as the **Game install folder**.

---

## 2. Create the mod repo (keep it OUTSIDE the game folder)

```bash
mkdir ff9-custom-map-mod
cd ff9-custom-map-mod
git init
mkdir backups reference mod docs
# drop CLAUDE.md, SETUP.md, and .gitignore into this folder
git add -A
git commit -m "chore: scaffold mod repo (docs, gitignore, folder layout)"
```

---

## 3. Get Memoria (the engine + patcher + compiler)

Clone the source for reference, and grab the player release for the patcher.

```bash
# Reference source (read-only for us — lets Claude Code study the engine):
git clone https://github.com/Albeoris/Memoria.git
```

Then download the **latest player release** (contains `Memoria.Patcher.exe`):

- Releases: https://github.com/Albeoris/Memoria/releases
- Mirror / Nexus: https://www.nexusmods.com/finalfantasy9/mods/3

**(manual GUI)** Run `Memoria.Patcher.exe` and point it at the game folder from
step 1. After it finishes, confirm these now exist:

```
<game>\StreamingAssets\Scripts\Compiler\Memoria.Compiler.exe
<game>\StreamingAssets\Scripts\Sources\Battle\
<game>\Memoria.ini
```

➡ Record each confirmed absolute path in `CLAUDE.md` section 3.

**(manual GUI)** Launch the game once through the new Memoria launcher to
confirm it still boots cleanly. If it doesn't, restore the clean backup and stop.

---

## 4. Get Hades Workshop (field-script + data editor)

```bash
git clone https://github.com/Tirlititi/Hades-Workshop.git
```

For the ready-to-run tool, download the latest build from that repo's releases
page (or the linked Nexus/forum mirror in its README).

**(manual GUI)** Open Hades Workshop → open the game by selecting
`FF9_Launcher.exe` from the game directory. Confirm the **Environment → Fields**
panel loads (it's slow — that's normal).

➡ Mark the Hades Workshop rows in `CLAUDE.md` section 3 as verified.

---

## 5. Export a reference field (template for later sessions)

**(manual GUI, with Claude Code's guidance)** In Hades Workshop, open a simple
existing field and export its script. Save it under `reference/` in the repo so
Claude Code can study the real script format instead of guessing.

```bash
git add reference/
git commit -m "reference: export sample field script as template"
```

---

## 6. Pick the throwaway field to repurpose

Choose a field the game doesn't need for a normal playthrough (an optional or
dead-end room is safest). Before committing to it:

- Grep the exported scripts / dictionaries for that field's ID to check nothing
  else references it. (Claude Code can do this once the files are in the repo.)

➡ Record the chosen field ID in `CLAUDE.md` section 1 and section 9.

---

## 7. Close out Session 0

```bash
git add -A
git commit -m "session 0: environment verified, paths recorded, field chosen"
git tag KNOWN_GOOD
```

Then update the **Session Log** at the bottom of `CLAUDE.md`:
what you verified, the field you picked, and the next step (Session 1: prove the
build/test loop with one trivial edit).
