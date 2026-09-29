"""THE AMBIENT CLEAR -- restore, silently, the report/clear tail every stock Main_Init closes its ambient prologue with.

The stock rule (real field ids; the census is in studies/story-trace). Every stock US Main_Init (818 of 818) opens
with the field-ambient prologue, once per slot (slot 0 = ``Int16[9]`` / ``Byte[13]``, slot 1 = ``Int16[11]`` /
``Byte[14]``)::

    Int16[9] := K                                   # the field's own ambient id, 65535 = none
    if Byte[13] == 9 {}
    elif Byte[13] == 2 && Int16[9] < 0 { Byte[13] := 9 }
    elif Int16[9] < 0 { Byte[13] := 0 }
    else { Byte[13] := 1 }

An arriving 2 means "the previous field's ambient is still playing" (a ``Field()`` without stock's exit idiom
``if Byte[13] < 9 { Byte[13] := 3 }``); a field that owns no ambient turns it into 9, an error mark. In 813 of 818
fields Main_Init then closes the prologue with the report/clear tail, after the second ``Wait(2)`` and immediately
before ``set MAP159 = 1``, on every path::

    if Byte[n] == 9 { SetTextVariable(2, n - 13); WindowAsync(6, 0, <own txid>); RaiseWindows(); WaitWindow(6)
                      Byte[n] := 0 }

(the five exceptions: 70 owns its ambient; 209 is only ever entered with 0; 1250/1251/1607 run it in Main_Loop).

What the blank lost. The kit's blank field is field 1357 (EVT_LIND2_CS_LB_HNG_0) patched by
``data/provenance/blank.<lang>.patch``, whose ops ``[c 435 29][c 532 105]`` skip 1357 src[464:532] -- both tail
blocks. The docstrings called that "popups removed"; the CLEAR went out with the popup. So every synthesized
Main_Init (``build_script`` is the only consumer of the blank) kept the prologue and lost the clear: an arriving 2
or 9 left as 9, and the next stock or verbatim field entered opened stock's developer report window. Verbatim
forks ship their donor's whole ``.eb`` and are not affected.

The fix. :data:`TAIL` is the test and the clear for both slots, each 8-byte statement byte for byte 1357's own
encoding (src[464:472], [490:498], [498:506], [524:532]); only the ``JMP_IFNOT`` displacement changes, 23 -> 8,
because the 15-byte window block is gone. :func:`restore_clear` inserts it at stock's position; ``build_script``
runs it FIRST on the blank, through this module's attribute, so every later pass (``set_control_direction``,
``entry_settle``'s ``2d 22 00 NN`` hold before ``set MAP159 = 1``, entrylock, the object injectors) anchors by
pattern after it -- stock's order. ``0x05`` and ``0x02`` never yield: no tick is added.

The one deliberate deviation: no window. The txid would index the kit field's OWN ``.mes`` (which has no such line);
copying stock's wording would be new game text in the repo; stock never reaches the window on a stock path; and the
harness cannot close it. ``tools/suppress_alex_popup.py`` (dcb6a836) made the same call. ``SetTextVariable(2, n)``
goes too -- its only reader is that window. Like stock's, the tail does not stop a leftover sound (resident sounds
survive ``Field()``); it only clears the mark.

The blank, its 7 patches and the manifest's ``blank.sha256`` are unchanged (956 B), so no extracted template cache
is invalidated.
"""

from __future__ import annotations

from ..eb import EbScript, edit, opcodes
from . import entry_settle as _entry_settle

SLOTS = (13, 14)                    # Byte[13] = ambient slot 0, Byte[14] = slot 1
NO_AMBIENT = 65535                  # Int16[9] := 65535 -- the field owns no slot-0 ambient
_OWN_ID = bytes([0x05, 0xD8, 0x09, 0x7D])   # ``Int16[9] := <u16>`` ... ``2c 7f`` -- the prologue's first statement
SNDEFFECTRES_STOP = 20864           # FF9Snd.FF9SOUND_SNDEFFECTRES_STOP: stop a resident sound, Arg1 = fade ms


def ambient_id(data) -> int | None:
    """The field's own slot-0 ambient id ``K`` from its Main_Init prologue's ``Int16[9] := K``, or None when
    Main_Init has no such statement (ValueError when there is no Main_Init). Every stock US Main_Init (818 of 818)
    sets it in the one 8-byte form ``05 d8 09 7d <K u16> 2c 7f``; 526 own a sound, 292 set :data:`NO_AMBIENT`.
    Synthesized fields carry the blank's 65535. ``newgame`` reads it to decide the New-Game override's handoff."""
    b = data.to_bytes() if isinstance(data, EbScript) else bytes(data)
    _f, stmts = _main_init(b)
    for _off, raw in stmts:
        if len(raw) == 8 and raw[:4] == _OWN_ID and raw[6:] == b"\x2c\x7f":
            return int.from_bytes(raw[4:6], "little")
    return None


def exit_stop(k: int) -> bytes:
    """Stock's exit stop for slot-0 ambient ``k``, 28 bytes::

        if Byte[13] < 9 { Byte[13] := 3 }
        RunSoundCode1(20864, k, 0)            # FF9SOUND_SNDEFFECTRES_STOP, no fade

    The exact form appears 2,669 times across the 526 stock fields that own an ambient, every time with the
    field's OWN ``k``; exits run it right before ``Int16[2] := N; Field(N)`` (Dali inn 351, all six exits) unless
    ``Map.Bit[162]`` marks a keep-playing handoff. Field 70's own copy is its disc-change branch (Main_Init
    rel 812-839). The 3 is the mark every stock prologue turns into 0 (stopped), never 9."""
    return (bytes([0x05, 0xD4, 13, 0x7D, 0x09, 0x00, 0x18, 0x7F])     # Byte[13] < 9
            + bytes([0x02, 0x08, 0x00])                               # JMP_IFNOT over the mark
            + bytes([0x05, 0xD4, 13, 0x7D, 0x03, 0x00, 0x2C, 0x7F])   # Byte[13] := 3
            + opcodes.encode(0xC6, SNDEFFECTRES_STOP, k, 0))          # RunSoundCode1(20864, k, 0)


def _eq9(n: int) -> bytes:
    """``Byte[n] == 9`` -- 1357 src[464:472] / [498:506]."""
    return bytes([0x05, 0xD4, n, 0x7D, 0x09, 0x00, 0x20, 0x7F])


def _let9(n: int) -> bytes:
    """``Byte[n] := 9`` -- the prologue's error mark."""
    return bytes([0x05, 0xD4, n, 0x7D, 0x09, 0x00, 0x2C, 0x7F])


def _let1(n: int) -> bytes:
    """``Byte[n] := 1`` -- the prologue's last branch (slot 1's ends the prologue)."""
    return bytes([0x05, 0xD4, n, 0x7D, 0x01, 0x00, 0x2C, 0x7F])


def _let0(n: int) -> bytes:
    """``Byte[n] := 0`` -- 1357 src[490:498] / [524:532], the clear."""
    return bytes([0x05, 0xD4, n, 0x7D, 0x00, 0x00, 0x2C, 0x7F])


_SKIP = bytes([0x02, 0x08, 0x00])   # JMP_IFNOT over the clear: stock's +23 minus the 15-byte window block

# ``if Byte[13] == 9 { Byte[13] := 0 }`` then the same for Byte[14]: 38 bytes, only 0x05/0x02 ops.
TAIL = b"".join(_eq9(n) + _SKIP + _let0(n) for n in SLOTS)


def _main_init(data: bytes):
    """``(func, [(rel_off, instruction bytes)])`` of entry 0 / function tag 0; raises ValueError if absent."""
    eb = EbScript.from_bytes(data)
    try:
        f = eb.entry(0).func_by_tag(0)
    except (IndexError, ValueError) as exc:
        raise ValueError(f"no Main_Init (entry 0, function tag 0): {exc}") from exc
    if f is None:
        raise ValueError("no Main_Init (entry 0, function tag 0)")
    stmts = [(i.off - f.abs_start, bytes(data[i.off:i.end])) for i in eb.instrs(f)]
    return f, stmts


def _sites(stmts, pat: bytes) -> list:
    """Main_Init-relative offsets of the WHOLE instructions equal to ``pat`` (never a match inside an operand)."""
    return [off for off, raw in stmts if raw == pat]


def _anchor(stmts) -> int | None:
    """The first ``set MAP159 = 1`` after the prologue's ``Byte[14] := 1`` (stock's tail sits right before it)."""
    ends = _sites(stmts, _let1(14))
    if not ends:
        return None
    return next((off for off in _sites(stmts, _entry_settle._SET_MAIN_READY) if off > ends[0]), None)


def classify(data) -> str:
    """How a script's Main_Init stands against the stock tail:

    * ``"restored"``   -- :data:`TAIL` is present;
    * ``"stock-tail"`` -- ``Byte[n] == 9`` appears twice for EACH slot (the prologue's test and stock's own tail);
    * ``"missing"``    -- exactly one ``:= 9`` and one ``== 9`` per slot (the prologue alone), plus a
      ``set MAP159 = 1`` after the prologue's ``Byte[14] := 1`` to anchor the tail on.

    Anything else raises ValueError: template drift must fail loudly, never silently skip the clear."""
    b = data.to_bytes() if isinstance(data, EbScript) else bytes(data)
    f, stmts = _main_init(b)
    if TAIL in b[f.abs_start:f.abs_end]:
        return "restored"
    eq9 = {n: len(_sites(stmts, _eq9(n))) for n in SLOTS}
    let9 = {n: len(_sites(stmts, _let9(n))) for n in SLOTS}
    if all(eq9[n] == 2 for n in SLOTS):
        return "stock-tail"
    bad = {n: (let9[n], eq9[n]) for n in SLOTS if (let9[n], eq9[n]) != (1, 1)}
    if bad:
        raise ValueError(f"Main_Init is not the ambient prologue the blank template carries: (':= 9', '== 9') "
                         f"counts per slot {bad}, want exactly (1, 1) each -- template drift")
    if _anchor(stmts) is None:
        raise ValueError("Main_Init carries the ambient prologue but no `set MAP159 = 1` after its "
                         "`Byte[14] := 1` to seat the clear before -- template drift")
    return "missing"


def restore_clear(data) -> bytes:
    """Return the script with the ambient clear restored: unchanged when :func:`classify` says ``"restored"`` or
    ``"stock-tail"``; for ``"missing"``, :data:`TAIL` inserted into Main_Init immediately before the first
    ``set MAP159 = 1`` after the prologue (``eb.edit.insert_in_function``, which moves the later functions'
    ``fpos`` and fixes any jump that straddles the point). Raises ValueError on template drift."""
    b = data.to_bytes() if isinstance(data, EbScript) else bytes(data)
    if classify(b) != "missing":
        return b
    _f, stmts = _main_init(b)
    return edit.insert_in_function(b, 0, 0, _anchor(stmts), TAIL)
