# Dream World IX — Windows installer (uv bootstrap)

A small `DreamWorldIX-Setup.exe` that removes the only friction a new user can't avoid: **installing
Python and pip-installing the toolkit.** It does *not* (and cannot) remove the one-time
`extract-templates` step — that still runs against the user's own legally-owned FF9 install, and this
installer ships **zero** game bytes.

## Why a bootstrap, not a frozen `.exe`

This installer **redistributes nothing but its own files**. It installs [`uv`](https://docs.astral.sh/uv/)
and then runs:

```
uv tool install --python 3.12 ff9mapkit[gui,assets,save]
```

`uv` fetches a managed CPython **and every dependency from PyPI onto the user's machine** — exactly like
a normal `pip install`. Two launchers land on `PATH`:

| Command | What it is |
|---|---|
| `ff9mapkit` | the CLI (everything works headless) |
| `ff9mapkit-workspace` | the PySide6 Workspace GUI (console-less; Start-Menu shortcut) |

Because the project never *ships* the dependency binaries, the two licensing obligations that would
otherwise apply never attach to this distribution:

- **Qt / PySide6 (LGPLv3)** — no relink/source-offer duty, because we don't bundle Qt. (The `gui` extra
  is pinned to `PySide6-Essentials`, so no GPL-only Qt module is ever involved either.)
- **FMOD** — UnityPy transitively pulls `fmod_toolkit`, which bundles proprietary FMOD binaries. Here the
  user's own `uv` fetches it from PyPI, so we redistribute nothing. *(A frozen build that baked deps in
  would have to exclude the FMOD libs — see `tools/gen_third_party_notices.py`.)*

A frozen single-folder build is still possible later (PyInstaller `--onedir` + this same Inno script) if
an offline, no-internet-on-first-run installer is ever needed — but it inherits all of the above
obligations and ~100 MB of size, so the bootstrap is the recommended default.

## Building it

1. Install **Inno Setup 6** — <https://jrsoftware.org/isdl.php>.
2. *(Optional, recommended)* generate the bundled notices file:
   ```powershell
   py -m pip install pip-licenses
   py -m pip install ".\ff9mapkit[gui,assets,save]"
   py tools\gen_third_party_notices.py -o installer\THIRD-PARTY-NOTICES.txt
   ```
3. Compile:
   ```powershell
   & "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer\ff9mapkit.iss
   ```
   Output: `installer\Output\DreamWorldIX-Setup.exe`.

## Files

| File | Role |
|---|---|
| `ff9mapkit.iss` | the Inno Setup script (metadata, license page, shortcuts, runs the bootstrap) |
| `bootstrap.ps1` | install/uninstall logic: ensure `uv`, `uv tool install/uninstall ff9mapkit[…]` |
| `THIRD-PARTY-NOTICES.txt` | *(generated)* aggregated dependency licenses; bundled if present |

## Notes / caveats

- **Internet required on first run** (uv downloads CPython + wheels). An offline variant would need a
  pre-seeded wheelhouse — not wired here.
- **SmartScreen**: an unsigned `setup.exe` shows an "unknown publisher" warning until it builds download
  reputation. As of 2026, *no* certificate (incl. EV) bypasses this instantly; cheapest own-identity
  signing is Azure Artifact Signing (~$10/mo), or free via SignPath Foundation (publisher shows as
  "SignPath Foundation"). See memory `project-ff9-installer-packaging`.
- **VC++ runtime**: uv's managed CPython needs `vcruntime140.dll` (present on virtually all current
  Windows; UnityPy needs it too). The bootstrap notes this if a launch ever fails.
- **Uninstall** removes the `ff9mapkit` tool via `uv tool uninstall`; `uv` itself and any managed CPython
  are left in place (they may be shared). Remove uv with `uv self uninstall`.
