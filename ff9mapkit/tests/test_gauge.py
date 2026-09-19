"""``[[gauge]]`` -- the tiles-as-sprites value bar (:mod:`ff9mapkit.content.gauge`).

Golden provenance: ``FieldMap.EBG_animShowFrame`` (frame *i* activates target
overlay *i*, 255 hides all), ``BGSCENE_DEF.ReadMemoriaBGS`` (the OVERLAY /
ANIMATION ``.bgx`` schema; USE_BASE_SCENE appends after the donor counts), and
field 64's Code1 Sin-pulse daemon (``allocate 2``; the shade formula carried
verbatim, driven from entry locals via the new ``loc`` seat parameter)."""
from __future__ import annotations

import pytest

from ff9mapkit import build as BLD
from ff9mapkit.content import gauge as G
from ff9mapkit.eb import disasm as D, edit as EDIT, exprasm, opcodes
from ff9mapkit.eb.model import EbScript
from ff9mapkit.scene import bgx as BGX

RAW = {"name": "cistern", "source": "global:2000", "max": 100, "segments": 10,
       "pos": [140, 24], "width": 96, "height": 10}


def _spec(**over):
    return G.from_raw({**RAW, **over}, 0)


def _verify_body(body: bytes) -> int:
    starts, count = set(), 0
    for ins in D.iter_code(body, 0, len(body)):
        starts.add(ins.off)
        count += 1
        assert ins.end <= len(body)
    ends = starts | {len(body)}
    for ins in D.iter_code(body, 0, len(body)):
        if ins.op in (0x01, 0x02, 0x03):
            t = D.jump_target(ins)
            assert t is None or t in ends, f"jump at {ins.off} -> {t} misses a boundary"
    return count


# ------------------------------------------------------------------- spec validation
@pytest.mark.parametrize("over,frag", [
    ({"name": ""}, "name"),
    ({"source": "bogus"}, "source"),
    ({"source": "global:2"}, "4..2016"),
    ({"source": "global:2040"}, "4..2016"),
    ({"source": "global:2018"}, "4..2016"),      # the [[qte]] scratch band (2018-2031)
    ({"source": "item:NotAnItemAnywhere"}, "resolve"),
    ({"max": 0}, "max"),
    ({"segments": 1}, "segments"),
    ({"segments": 25}, "segments"),
    ({"width": 10}, "width"),
    ({"height": 2}, "width/height"),
    ({"pulse_below": 11}, "pulse_below"),
    ({"color": "#12"}, "color"),
    ({"camera": 9}, "camera"),
    ({"bogus": 1}, "unknown"),
])
def test_from_raw_rejects(over, frag):
    with pytest.raises(G.GaugeError) as ei:
        G.from_raw({**RAW, **over}, 0, resolve_item=lambda s: (_ for _ in ()).throw(ValueError(s)))
    assert frag in str(ei.value)


def test_sources_canonicalize():
    assert _spec().source == "global:2000"
    assert G.from_raw({**RAW, "source": "gil"}, 0).source == "gil"
    sp = G.from_raw({**RAW, "source": "item:Potion"}, 0, resolve_item=lambda s: 236)
    assert sp.source == "item:236"
    assert G.from_raw({**RAW, "source": "item:236"}, 0).source == "item:236"
    assert _spec(color="#40c8ff").color == (0x40, 0xC8, 0xFF)
    assert _spec(color=[1, 2, 3]).color == (1, 2, 3)


def test_source_and_level_exprs():
    assert G.source_expr(_spec()) == "Global.Int16[2000]"
    assert G.source_expr(G.from_raw({**RAW, "source": "gil"}, 0)) == "B_SYSVAR[6]"
    assert G.source_expr(G.from_raw({**RAW, "source": "item:236"}, 0)) == "const(236) B_HAVE_ITEM"
    lv = G.level_expr(_spec())
    assert "const(10) B_MULT const(100) B_DIV" in lv     # value * segments / max
    assert "B_GT" in lv and "B_MINUS" in lv              # the branchless min clamp
    assert lv.endswith("const(0) B_GT B_MULT")           # the max0 floor
    # the whole thing assembles -> a pure expression an opcode arg can carry
    blob = exprasm.assemble(lv + " B_EXPR_END")
    assert blob[-1] == 0x7F


# ------------------------------------------------------------------- art
def test_art_pngs_deterministic_and_shaped():
    import re as _re
    from PIL import Image
    import io as _io
    spec = _spec()
    eff = G.effective_width(spec)
    assert eff == 2 + 8 * 10 + 9                         # the exact uniform-cell fit (91 <= 96)
    pngs = G.art_pngs(spec)
    # content-hashed names (THE OVERLAY-TEXTURE-CACHE LAW: same-name art edits
    # would keep serving the engine's static path-keyed texture cache)
    assert all(_re.fullmatch(rf"gauge_cistern_{k:02d}_[0-9a-f]{{8}}\.png", n)
               for k, (n, _) in enumerate(pngs))
    assert len({n for n, _ in pngs}) == 11               # distinct art -> distinct hashes
    assert pngs == G.art_pngs(spec)                      # byte-deterministic
    fills = []
    for _n, data in pngs:
        im = Image.open(_io.BytesIO(data)).convert("RGBA")
        assert im.size == (eff * G.ART_SCALE, 10 * G.ART_SCALE)   # hi-res texels, canvas-size quad
        fills.append(sum(1 for px in im.getdata() if px[:3] == spec.color))
    assert fills[0] == 0                                 # empty state: no fill pixels
    assert all(b > a for a, b in zip(fills, fills[1:]))  # each state adds one cell
    assert G.overlay_blocks(spec)[0].image == pngs[0][0]  # .bgx references the hashed names


def test_art_cells_are_uniform():
    """WATERWORKS round 1 (owner): 'the last cell is shorter than the rest' —
    the old remainder-px scheme widened the leftmost cells. Now every cell run
    on the mid row is the SAME width, for a segments/width pair that doesn't
    divide evenly."""
    from PIL import Image
    import io as _io
    spec = _spec(segments=12, width=96)                  # inner 83 / 12 -> the round-1 shape
    _n, data = G.art_pngs(spec)[-1]                      # full bar: every cell filled
    im = Image.open(_io.BytesIO(data)).convert("RGBA")
    row = [im.getpixel((x, im.height // 2))[:3] == spec.color for x in range(im.width)]
    runs, cur = [], 0
    for v in row:
        if v:
            cur += 1
        elif cur:
            runs.append(cur)
            cur = 0
    if cur:
        runs.append(cur)
    assert len(runs) == 12 and set(runs) == {6 * G.ART_SCALE}   # 12 cells, one width


# ------------------------------------------------------------------- .bgx blocks
def test_bgx_blocks_and_build():
    spec = _spec()
    ovls = G.overlay_blocks(spec)
    assert len(ovls) == 11
    assert ovls[0].position == (140, 24, 1)
    assert ovls[0].size == (G.effective_width(spec), 10)  # Size == PNG size, no quad stretch
    anim = G.animation_block(spec, 7)
    assert anim.to_lines() == ["ANIMATION", "CameraId: 0", "FrameRate: 256",
                               "Overlays: 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17"]
    text = BGX.build(None, ovls, base_scene="FBG_N11_X", animations=[anim])
    assert text.index("USE_BASE_SCENE") < text.index("OVERLAY") < text.index("ANIMATION")
    assert "Name:" not in text                           # the engine keys off the FILENAME
    # parse round-trip keeps the anim (incl. a bare Loop flag line)
    looped = BGX.Animation(overlays=[1, 2], loop=True)
    sc = BGX.BgxScene.parse(BGX.build(None, [], animations=[looped]))
    a2 = sc.animations[0]
    assert a2.overlays == [1, 2] and a2.loop and not a2.palindrome
    assert "Loop" in sc.to_text()


# ------------------------------------------------------------------- the daemon
def test_daemon_body_census_plain():
    body = G.daemon_body([(_spec(), 0, 0)])
    _verify_body(body)
    names = [i.name for i in D.iter_code(body, 0, len(body))]
    assert names.count("SetTileAnimationFrame") == 1
    assert names.count("SetTileColor") == 0              # no pulse
    assert sum(1 for i in D.iter_code(body, 0, len(body)) if i.op == 0x22) == 1  # Wait(1)


def test_daemon_body_census_full():
    """flag-gated + pulsing: the hide branch adds a const-255 frame write, the
    pulse adds the field-64 shade pair (locals) + two SetTileColor sites."""
    g = _spec(pulse_below=2, requires_flag=8320)
    body = G.daemon_body([(g, 3, 40)])
    _verify_body(body)
    names = [i.name for i in D.iter_code(body, 0, len(body))]
    assert names.count("SetTileAnimationFrame") == 2     # visible + hidden
    assert names.count("SetTileColor") == 2              # pulse + neutral restore
    exprs = [D.pretty_expr(body, i.off + 1)[0]
             for i in D.iter_code(body, 0, len(body)) if i.op == 0x05]
    # the verbatim field-64 shade: Instance locals, Sin(phase << 2)/360 + 144
    assert any(f"Instance.Byte[{G.LOC_SHADE}]" in e and "B_SIN" in e
               and "const(360)" in e and "const(144)" in e for e in exprs)
    assert any(f"Instance.Byte[{G.LOC_PHASE}]" in e and "const(1) B_PLUS" in e for e in exprs)
    assert any(f"Global.Bit[8320]" in e for e in exprs)
    assert body == G.daemon_body([(g, 3, 40)])           # deterministic


def test_entry_bytes_shape():
    eb = G.entry_bytes([(_spec(), 0, 0)])
    assert eb[0] == 0x00 and eb[1] == 0x01               # type 0, ONE function (ticker shape)
    assert eb[2:6] == bytes([G.GAUGE_TAG, 0, 4, 0])      # tag 0 @ fpos 4


def test_append_entry_loc():
    """The new ``loc`` seat parameter writes the entry-table local-var byte
    (stock ``allocate N``); the default stays 0 (byte-identical old behavior)."""
    from ff9mapkit.eb.model import ENTRY_TABLE_OFF, MAGIC
    base = bytes(MAGIC) + bytes([0, 2]) + bytes(124) + bytes(16)  # header + 2 empty slots
    ent = bytes([0x00, 0x01, 0, 0, 4, 0]) + bytes(opcodes.RETURN)
    out = EDIT.append_entry(base, 0, ent, loc=2)
    assert EbScript.from_bytes(out).entry(0).loc == 2
    out0 = EDIT.append_entry(base, 0, ent)
    assert EbScript.from_bytes(out0).entry(0).loc == 0


# ------------------------------------------------------------------- layout + full build
_TOML = (
    '[field]\nid = 30001\nname = "GAUGE"\narea = 11\n'
    "\n[camera]\npitch = 48.0\ndistance = 480.0\nfov = 46.0\n"
    '\n[[npc]]\nname = "keeper"\npreset = "vivi"\npos = [0, -300]\ndialogue = "Hm?"\n'
    '\n[[gauge]]\nname = "cistern"\nsource = "global:2000"\nmax = 100\nsegments = 10\n'
    'pos = [140, 24]\npulse_below = 2\n'
    '\n[[gauge]]\nname = "coffer"\nsource = "gil"\nmax = 5000\nsegments = 8\npos = [140, 44]\n'
)


def test_gauge_layout_novel_and_borrow(tmp_path):
    f = tmp_path / "g.field.toml"
    f.write_text(_TOML, encoding="utf-8")
    p = BLD.FieldProject.load(f)
    resolved, donor = BLD.gauge_layout(p)
    assert donor is None
    (g0, a0, b0), (g1, a1, b1) = resolved
    assert (a0, b0) == (0, 0)                            # novel, no layers
    assert (a1, b1) == (1, 11)                           # after cistern's 11 states
    bor = _TOML.replace('area = 11\n', 'area = 11\nborrow_bg = "LDBM_MAP158_LB_PLZ_0"\n'
                        'borrow_scene_counts = [30, 4]\n')
    f2 = tmp_path / "b.field.toml"
    f2.write_text(bor, encoding="utf-8")
    resolved2, donor2 = BLD.gauge_layout(BLD.FieldProject.load(f2))
    assert donor2 == "FBG_N11_LDBM_MAP158_LB_PLZ_0"
    assert [(a, b) for _g, a, b in resolved2] == [(4, 30), (5, 41)]


def test_gauge_layout_native_reads_the_bgs_header(tmp_path):
    """The own-scene hybrid: base overlay/anim indices come straight from the
    field's OWN shipped .bgs header (offline, no pinning key)."""
    import struct as _struct
    from ff9mapkit.scene import bgs as _bgs
    hdr = _struct.pack("<6H4I12h", 0, 0, 4, 30, 0, 1, 0, 0, 0, 0, *([0] * 12))
    assert (_bgs.parse_header(hdr).animCount, _bgs.parse_header(hdr).overlayCount) == (4, 30)
    (tmp_path / "scene.bgs.bytes").write_bytes(hdr)
    nat = _TOML.replace('area = 11\n', 'area = 11\nbgs = "scene.bgs.bytes"\n')
    f = tmp_path / "n.field.toml"
    f.write_text(nat, encoding="utf-8")
    p = BLD.FieldProject.load(f)
    resolved, donor = BLD.gauge_layout(p)
    assert donor is None                                 # own scene, nothing shared
    assert [(a, b) for _g, a, b in resolved] == [(4, 30), (5, 41)]
    assert not any("gauge" in pr.lower() for pr in BLD.validate(p))


def test_full_build_seats_and_arms(tmp_path):
    f = tmp_path / "g.field.toml"
    f.write_text(_TOML, encoding="utf-8")
    p = BLD.FieldProject.load(f)
    assert BLD.validate(p) == []
    (mes, txids, ev, cs, ch, oe, ate, chest, gw, co, sp, bh, ni) = BLD.collect_text(p)
    plain = BLD.build_script(BLD.FieldProject.load(f), "us", txids, choice_txids=ch,
                             numinput_txids=ni)
    eb = EbScript.from_bytes(plain)
    daemons = [e for i in range(1, eb.entry_count) if not (e := eb.entry(i)).empty
               and e.func_count == 1 and e.loc == G.LOC_BYTES]
    assert len(daemons) == 1
    slot = daemons[0].index
    armed = set()
    for fn in eb.entry(0).funcs:
        for ins in D.iter_code(plain, fn.abs_start, fn.abs_end):
            if ins.op == 0x07:
                armed.add(int(ins.imm(0)))
    assert slot in armed
    fn0 = daemons[0].funcs[0]
    body = plain[fn0.abs_start:fn0.abs_end]
    _verify_body(body)
    names = [i.name for i in D.iter_code(body, 0, len(body))]
    assert names.count("SetTileAnimationFrame") == 2     # one per gauge, no flags
    again = BLD.build_script(BLD.FieldProject.load(f), "us", txids, choice_txids=ch,
                             numinput_txids=ni)
    assert again == plain


def test_validate_negatives_and_coexistence(tmp_path):
    dup = _TOML.replace('name = "coffer"', 'name = "cistern"')
    f = tmp_path / "dup.field.toml"
    f.write_text(dup, encoding="utf-8")
    assert any("duplicate" in pr for pr in BLD.validate(BLD.FieldProject.load(f)))
    bor = _TOML.replace('area = 11\n', 'area = 11\nborrow_bg = "LDBM_MAP158_LB_PLZ_0"\n')
    f2 = tmp_path / "bor.field.toml"
    f2.write_text(bor, encoding="utf-8")
    assert any("borrow_scene_counts" in pr for pr in BLD.validate(BLD.FieldProject.load(f2)))
    # [behavior] coexistence is ALLOWED (daemon state = entry locals, no scratch)
    beh = _TOML + ('\n[behavior]\nwarmup = 30\n'
                   '\n[[behavior.unit]]\nnpc = "keeper"\n'
                   'branch = [{ do = { hold = [0, -300] } }]\n')
    f3 = tmp_path / "beh.field.toml"
    f3.write_text(beh, encoding="utf-8")
    assert not any("gauge" in pr.lower() for pr in BLD.validate(BLD.FieldProject.load(f3)))
