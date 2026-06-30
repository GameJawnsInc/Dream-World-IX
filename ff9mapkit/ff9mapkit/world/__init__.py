"""World-map (overworld) tooling -- the geometry-edit / custom-overworld pillar (Path C/D).

Today: an OFFLINE reader for the disc-1/disc-4 block TERRAIN meshes that ARE the overworld's render +
collision + per-tile field-entry source (Memoria raycasts these Unity meshes; the per-triangle ``tangent.x``
carries the world map/event id -- the legacy ``model_hm.nwp`` PSX packs are not read for collision). See
:mod:`ff9mapkit.world.extract`. → project-memory ``project-ff9-worldmap-feasibility``.
"""
