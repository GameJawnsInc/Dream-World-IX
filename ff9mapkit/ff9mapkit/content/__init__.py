"""Generalized field-script content injectors (operate on .eb bytes via the eb library).

  npc        - inject an NPC (model/anims/dialogue) + move the player spawn
  gateway    - inject a field-exit region trigger (warp to another field)
  encounter  - add random battles
  reinit     - add the after-battle handler (+ fast fade-in) custom fields need
  music      - field BGM on entry and after battle
  text       - author dialogue .mes entries (high-TXID, non-colliding)
"""

from . import encounter, gateway, music, npc, reinit, text

__all__ = ["npc", "gateway", "encounter", "reinit", "music", "text"]
