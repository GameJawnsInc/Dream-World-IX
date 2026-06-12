"""ff9mapkit — author novel custom field maps for Final Fantasy IX (Memoria engine).

The kit compiles a declarative per-field TOML project into a drop-in Memoria mod:
field background scene (.bgx + overlay PNGs), walkmesh (.bgi), event script (.eb, all
languages), dialogue text (.mes), and the DictionaryPatch / BattlePatch registration —
everything a custom field needs at runtime on a *stock* (unmodified) Memoria install.

Public surface is organized as:
  ff9mapkit.config    — game/mod path resolution + the FF9 mod folder layout
  ff9mapkit.binutils  — little-endian struct helpers shared by the binary codecs
  ff9mapkit.eb        — the field event-script (.eb) library (model / edit / disasm / opcodes)
  ff9mapkit.scene     — camera math, .bgx scene, .bgi walkmesh, paint guides
  ff9mapkit.content   — generalized script-content injectors (npc/gateway/encounter/...)
  ff9mapkit.build     — the field.toml -> mod-folder builder
  ff9mapkit.battle    — the battle.toml -> custom battle-background (BBG) builder (fork/edit/build a 3D battle map)
"""

__version__ = "0.9.32"
