"""THE list of member ``field.toml`` keys that hold a field id THIS campaign owns.

Two things need this list and they were maintained separately, which is exactly how they drifted:
:mod:`ff9mapkit.reid` REWRITES these keys when a campaign moves band, and
:func:`ff9mapkit.campaign.lint_campaign`'s ``(e3)`` CHECKS that each one names a member or a declared
``[[seam]]``. A key present in one table and missing from the other is the worst possible split --
``reid --apply`` strands a door at a retired id and the lint then certifies the result clean. That is
not hypothetical: ``[[platform]] warp_to`` is validated as "a field id (int)" at ``build.py:1695`` and
was in neither table.

So the table lives here, both import it, and a new id-bearing key is added in ONE place.

WHAT IS DELIBERATELY ABSENT is as load-bearing as what is present -- every one of these is a DONOR id
(the real FF9 field a member was forked from) and moving it un-forks the member:
  ``[[field]] source`` / ``[field] source_field``   the donor, the right column of ForkDonorPatch
  ``[[seam]] to_real``                              what the REAL game pointed at (donor-by-default;
                                                    it CAN name a sibling campaign's fork id inside a
                                                    journey, which is why reid reports it rather than
                                                    rewriting it in either direction)
  a ``retarget`` table's KEYS                       donor destinations standing in the donor .eb
  ``[[logic_edit]] old``                            the donor literal the edit searches for
  ``[[sps]] copy_from.field`` / ``template``        donor art/effect sources
  ``[[save_moogle]] from``                          a donor id, emitted QUOTED
"""

from __future__ import annotations

SCALAR = "scalar"            # the whole value is one of OUR field ids
TABLE_VALUES = "table"       # an INLINE table {<donor real id> = <our fork id>} -- VALUES only
SECTION_VALUES = "section"   # the same table written long-form as [a.b] -- every row's VALUE is ours

# (section path, key) -> what the value MEANS. `None` as the key means "every row in this section".
OUR_ID_SITES = {
    (("field",), "id"): SCALAR,                  # the member's own identity (not a door)
    (("gateway",), "to"): SCALAR,                # declarative door           build.py:1385-1395
    (("ladder",), "top_field"): SCALAR,          # navigable ladder exit      build.py:1611-1614
    (("cutscene",), "then_warp"): SCALAR,        # auto-return destination    build.py:2654
    (("platform",), "warp_to"): SCALAR,          # elevator/platform exit     build.py:1693-1695
    # `new` is OURS but ONLY on a kind="field" row; `old` is the donor literal (logic_edit.py:115).
    # The gate is not optional: on kind="gil"/"flag_index" the same key holds an amount or a flag index,
    # and the custom id band overlaps both, so an unconditional rewrite corrupts an unrelated number.
    (("logic_edit",), "new"): SCALAR,
    (("verbatim_eb",), "retarget"): TABLE_VALUES,
    (("verbatim_eb", "retarget"), None): SECTION_VALUES,
    (("gateway_carry",), "retarget"): TABLE_VALUES,
    (("gateway_carry", "retarget"), None): SECTION_VALUES,
}

# `[field] id` is the member's IDENTITY, not a destination: (e3) compares it to the manifest directly,
# and a door check would read it as a self-loop.
_IDENTITY = (("field",), "id")


def _rows(raw, key):
    """An array-of-tables block, defensively. A member that writes ``[gateway]`` where ``[[gateway]]``
    was meant parses as a bare dict; that shape is build.validate's to reject, and a reader that raises
    on it reports nothing at all."""
    v = raw.get(key)
    return [r for r in v if isinstance(r, dict)] if isinstance(v, list) else []


def _int(v):
    return isinstance(v, int) and not isinstance(v, bool) and v > 0


def dest_ids(raw) -> list:
    """Every INTRA-CAMPAIGN destination id a member ``field.toml`` names, as ``(label, id)``.

    Excludes the member's own ``[field] id``. Excludes every donor-side key listed in the module
    docstring. Both the reid rewrite and the (e3) door check are driven from this, so neither can
    grow a blind spot the other does not have.
    """
    out = []
    for (path, key), kind in OUR_ID_SITES.items():
        if (path, key) == _IDENTITY:
            continue
        block = path[0]
        if kind == SCALAR:
            for i, row in enumerate(_rows(raw, block)):
                if block == "logic_edit" and row.get("kind") != "field":
                    continue                       # `new` is only a field id on a kind="field" row
                if _int(row.get(key)):
                    out.append((f"[[{block}]] {key}", int(row[key])))
            sub = raw.get(block)                   # the same block written as a single [table]
            if isinstance(sub, dict) and _int(sub.get(key)):
                if not (block == "logic_edit" and sub.get("kind") != "field"):
                    out.append((f"[{block}] {key}", int(sub[key])))
        elif kind == TABLE_VALUES:
            holders = _rows(raw, block)
            single = raw.get(block)
            if isinstance(single, dict):
                holders = holders + [single]
            for h in holders:
                rt = h.get(key)
                if isinstance(rt, dict):
                    for dk, dv in rt.items():
                        if _int(dv):
                            out.append((f"{block} retarget {dk} ->", int(dv)))
    return out
