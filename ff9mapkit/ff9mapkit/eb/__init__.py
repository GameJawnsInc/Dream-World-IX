"""The FF9 field event-script (``.eb``) library.

  model    - EbScript: byte-exact parsed view (round-trip is identity)
  disasm   - instruction decoder (Instr) over the baked opcode tables
  edit     - structural edits: insert_bytes, append_entry, nop_range, locators, jump safety
  opcodes  - byte encoders for the opcodes the kit emits
"""

from . import disasm, edit, model, opcodes
from .model import EbScript, Entry, Func

__all__ = ["model", "disasm", "edit", "opcodes", "EbScript", "Entry", "Func"]
