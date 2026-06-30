# Workspace / installer icon source art

Drop your hand-drawn PNGs **here**, one per size, named exactly:

```
icon_16.png   icon_24.png   icon_32.png   icon_48.png
icon_64.png   icon_128.png  icon_256.png
```

Optional DPI in-betweens (only if you want pixel-perfect 125% / 150% scaling —
otherwise the nearest size is downscaled): `icon_20.png`, `icon_40.png`, `icon_96.png`.

Requirements: **square**, **transparent RGBA PNG**, exact pixel dimensions matching the
filename. If you only finish `icon_256.png`, that's enough — the rest get generated from
it (but the hand-drawn smalls look noticeably crisper at 16/24/32).

## Build the `.ico` (done by the toolchain, not you)

```
magick installer/icon/icon_16.png installer/icon/icon_24.png installer/icon/icon_32.png \
       installer/icon/icon_48.png installer/icon/icon_64.png installer/icon/icon_128.png \
       installer/icon/icon_256.png  installer/dreamworldix.ico
```

The resulting `installer/dreamworldix.ico` is wired into:
- the installer (`SetupIconFile`) + the Start-Menu shortcut, and
- the Qt Workspace window icon (`ff9mapkit/workspace/shell.py`).
