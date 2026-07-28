"""Default names for freshly added entities — FF9-flavoured compounds, never twins.

Born from a playtest: every new ``[[npc]]`` defaulted to the literal name "NPC", so a
field with three of them had three IDENTICAL names — and names are load-bearing here
(behavior units bind by npc name, the field/scene merge keys on it, the archetype
wizard lists them). A fresh compound like ``gysahl_peddler`` is unique on arrival,
reads like the game, and survives as a real identifier if the author never renames it.

Provenance: these are VOCABULARY words in the kit's own voice (the docs and examples
already speak Lindblum and gysahl) — no Square-Enix binary bytes, no game text.
Both editors mint through here (the Workspace shell and the tkinter form editor).
"""

from __future__ import annotations

import random as _random

# First halves: places, creatures, and props of FF9's world. Second halves: humble
# townsfolk trades (the kit's demo cast voice — watchman, porter, raider).
FLAVOR = (
    "mist", "gysahl", "oglop", "kupo", "moogle", "chocobo", "gargant", "tantalus",
    "pluto", "lindblum", "burmecia", "cleyra", "treno", "dali", "gizamaluke",
    "fossil", "iifa", "mognet",
)
ROLES = (
    "porter", "sentry", "vendor", "scamp", "bard", "tinker", "courier", "dockhand",
    "sweeper", "lamplighter", "gambler", "peddler", "juggler", "wrangler", "watch",
    "herald",
)


def fresh_npc_name(taken=(), rng=None) -> str:
    """A fresh ``flavor_role`` compound not in ``taken`` (existing npc names).

    ``rng`` (any object with ``choice``) makes it deterministic for tests; default is
    the module's own randomness — a DEFAULT name is a suggestion, not state, so
    randomness here breaks no replay contract. If the sampler keeps colliding on a
    crowded field, a numeric suffix settles it (``mist_porter_2``).
    """
    r = rng if rng is not None else _random
    taken = {str(t) for t in taken}
    cand = ""
    for _ in range(24):
        cand = f"{r.choice(FLAVOR)}_{r.choice(ROLES)}"
        if cand not in taken:
            return cand
    n = 2
    while f"{cand}_{n}" in taken:
        n += 1
    return f"{cand}_{n}"
