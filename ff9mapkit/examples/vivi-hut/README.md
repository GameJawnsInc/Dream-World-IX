# Example: "Vivi's House" (interior)

A complete, compilable `field.toml` for a custom interior room — and the kit's build oracle:
compiling `hut_int.field.toml` reproduces the in-game-verified `EVT_HUT_INT.eb` script
byte-for-byte (the test suite asserts this).

```bash
ff9mapkit build hut_int.field.toml --out dist --mod-name FF9CustomMap
```

It shows every part of the format: a 48° camera, two background layers, a flat quad walkmesh,
a player spawn, a talking NPC (Vivi, with a custom dialogue line), and a door gateway back to
the exterior field 4000.

The art under `art/` is **placeholder** (flat colors) so the example is self-contained — in a
real field you paint these layers to match the camera (`ff9mapkit guide` shows you where the
floor lands). The geometry and the compiled script are the real, proven thing.
