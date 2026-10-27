"""The co-op guest-traversal table (engine patch s156), INSTALL-FREE half: the committed JSON, the generated C#,
and the shared slice / CRC vectors -- held to EACH OTHER and to the contract's literal vectors.

The JSON (``ff9mapkit/data/guest_traversal.json``) is the only owner of the table's counts and CRC: nothing here
hard-codes a row / function / field count or the table CRC. The vectors below ARE literals on purpose (the contract's
shared set, also compiled into the engine selftest): ``func_slice`` and the JSON are both kit-authored, so a vector
recomputed from ``func_slice`` alone could drift together with it. The install-gated half (re-derive == committed,
census faithfulness) is ``test_guest_traversal_install.py``.

Every JSON read happens inside a function (``conftest._MODULE_LEVEL_IO`` would ignore-collect a module that reads at
import time in a fresh worktree).
"""
from __future__ import annotations

import copy
import functools
import json
import re
import struct
import zlib

import pytest

import ff9mapkit
from ff9mapkit import guest_traversal as G
from ff9mapkit.eb import pressclosure as P

from ._patchstack import msr


@functools.lru_cache(maxsize=1)
def _committed_text() -> str:
    return G.JSON_PATH.read_text(encoding="utf-8")


def _obj() -> dict:
    return json.loads(_committed_text())


# ================================================================================================ the table's laws
def _problems(obj) -> list:
    """Every way ``obj`` breaks the table contract (CONTRACT.md 2.2 / 2.4 / 2.7). Empty == lawful."""
    bad = []
    rows = obj["rows"]
    keys = [(r["field"], r["entry"]) for r in rows]
    if keys != sorted(set(keys)):
        bad.append("rows are not strictly ascending by (field, entry)")
    for r in rows:
        at = f"{r['field']}:{r['entry']}"
        if not (1 <= r["field"] <= 3100) or not (0 <= r["entry"] <= 255):
            bad.append(f"{at}: field/entry out of range")
        if r["kind"] not in G.KIND_CODES:
            bad.append(f"{at}: kind {r['kind']!r}")
        fs = r["funcs"]
        if len(fs) < 2 or len(fs) > 255:
            bad.append(f"{at}: {len(fs)} functions")
            continue
        h = fs[0]
        if (h["role"], h["entry"], h["tag"], h["uid"]) != ("region", r["entry"], 3, 0):
            bad.append(f"{at}: the first function is not the region's tag 3 with uid 0")
        rest = fs[1:]
        trip = [(G.ROLE_CODES.get(f["role"], 99), f["entry"], f["tag"]) for f in rest]
        if trip != sorted(set(trip)):
            bad.append(f"{at}: functions not sorted by (role, entry, tag), each once")
        for f in fs:
            if f["role"] not in G.ROLE_CODES or (f is not h and f["role"] == "region"):
                bad.append(f"{at}: role {f['role']!r}")
            if not (G.MIN_FUNC_LEN <= f["len"] <= 0xFFFF):
                bad.append(f"{at}: {f['entry']}:{f['tag']} length {f['len']}")
            if not re.fullmatch(r"0x[0-9a-f]{8}", f["crc"]):
                bad.append(f"{at}: crc {f['crc']!r}")
            if not (0 <= f["tag"] <= 0xFFFF and 0 <= f["entry"] <= 255):
                bad.append(f"{at}: entry/tag out of range")
            if f["role"] == "ctrl" and f["uid"] != 250:
                bad.append(f"{at}: a ctrl function with uid {f['uid']}")
            if f["role"] == "fixed_ctrl" and not (1 <= f["uid"] <= 249):
                bad.append(f"{at}: a fixed_ctrl function with uid {f['uid']}")
            if f["role"] in ("region", "seq") and f["uid"] != 0:
                bad.append(f"{at}: a {f['role']} function with uid {f['uid']}")
            if f["role"] == "seq" and f["tag"] != 0:
                bad.append(f"{at}: a seq function with tag {f['tag']}")
        ctrl = [f for f in fs if f["role"] == "ctrl"]
        fixed = [f for f in fs if f["role"] == "fixed_ctrl"]
        if bool(ctrl) == bool(fixed):
            bad.append(f"{at}: needs ctrl bodies XOR fixed_ctrl bodies")
        if len({f["uid"] for f in fixed}) > 1:
            bad.append(f"{at}: more than one fixed uid")
    c = obj["counts"]
    if c["rows"] != len(rows) or c["funcs"] != sum(len(r["funcs"]) for r in rows) \
            or c["fields"] != len({r["field"] for r in rows}) or c["refused"] != len(obj["refused"]):
        bad.append(f"counts {c} do not match the rows")
    if obj["table_crc"] != "0x%08x" % G.table_crc(rows):
        bad.append(f"table_crc {obj['table_crc']} != 0x{G.table_crc(rows):08x} of the rows")
    for r in rows:
        if "r15" in r:
            bad.append(f"{r['field']}:{r['entry']}: shipped with R15 not evaluated ({r['r15']!r})")
    for x in obj["refused"]:
        if not re.match(r"R\d+ [a-z0-9-]+: \S", x["refusal"]):
            bad.append(f"refused {x['field']}:{x['entry']}: refusal text {x['refusal']!r}")
        if (x["field"], x["entry"]) in set(keys):
            bad.append(f"{x['field']}:{x['entry']} is both shipped and refused")
    waived = [(w["field"], w["entry"]) for w in obj["waivers"]]
    if waived != sorted(set(waived)):
        bad.append("waivers are not strictly ascending by (field, entry)")
    for w in obj["waivers"]:
        if list(w) != ["field", "entry", "waiver"] or (w["field"], w["entry"]) not in set(keys) \
                or not w["waiver"].startswith("R15 walk-in waived: jp F1 hole -- "):
            bad.append(f"waiver {w.get('field')}:{w.get('entry')}: not a shipped row's R15 jp waiver ({w!r})")
    if any("waived" in r for r in rows):
        bad.append("a row carries its waiver (the rows feed table_crc and render_cs: waivers live apart)")
    want = sorted({r["field"] for r in rows} | {x["field"] for x in obj["refused"]})
    if [e["field"] for e in obj["eb_sha1"]] != want:
        bad.append("eb_sha1 does not list exactly the fields of rows + refused, ascending")
    for e in obj["eb_sha1"]:
        if list(e) != ["field", *G.LANGS] or not all(re.fullmatch(r"[0-9a-f]{40}", e[lang] or "") for lang in G.LANGS):
            bad.append(f"eb_sha1 {e['field']}: not 7 languages of sha1")
    return bad


def test_the_committed_table_is_lawful():
    obj = _obj()
    assert obj["schema"] == G.SCHEMA and obj["langs"] == list(G.LANGS)
    assert list(obj) == ["schema", "generated_from", "regenerate", "langs", "rule", "counts", "table_crc", "rows",
                         "refused", "waivers", "eb_sha1", "op_classes", "selftest"]
    assert list(obj["rule"]) == ["tier", "kinds", "slice", "crc", "uid", "func_order", "refusals"]
    assert list(obj["counts"]) == ["fields_scanned", "quad_roots", "census_candidates", "rows", "funcs", "fields",
                                   "refused"]
    assert obj["counts"]["census_candidates"] == obj["counts"]["rows"] + obj["counts"]["refused"]
    assert _problems(obj) == []


@pytest.mark.parametrize("mutate, expect", [
    (lambda o: o["rows"].insert(0, o["rows"].pop(1)), "strictly ascending"),
    (lambda o: o["rows"][0]["funcs"][1].update(crc="0x%08x" % (int(o["rows"][0]["funcs"][1]["crc"], 16) ^ 1)),
     "table_crc"),
    (lambda o: o["rows"][0]["funcs"][0].update(len=o["rows"][0]["funcs"][0]["len"] + 1), "table_crc"),
    (lambda o: o["rows"][-1]["funcs"].pop(), "counts"),
    (lambda o: next(r for r in o["rows"] if len(r["funcs"]) >= 3)["funcs"].reverse(), "region's tag 3"),
    (lambda o: next(f for r in o["rows"] for f in r["funcs"] if f["role"] == "ctrl").update(uid=0), "ctrl function"),
    (lambda o: o["refused"].append(dict(o["rows"][0], refusal="R11 latch: x")), "both shipped and refused"),
    (lambda o: o["rows"][0].update(r15=G.R15_NOT_EVALUATED), "R15 not evaluated"),
    (lambda o: o["refused"].append({"field": 1, "entry": 1, "kind": "ladder", "refusal": "R15 walk_in: x"}),
     "refusal text"),
    (lambda o: o["waivers"].append({"field": 1, "entry": 1, "waiver": "R15 walk-in waived: jp F1 hole -- x"}),
     "not a shipped row's R15 jp waiver"),
    (lambda o: o["waivers"].append({"field": o["rows"][0]["field"], "entry": o["rows"][0]["entry"],
                                    "waiver": "R16 watcher waived: x"}), "not a shipped row's R15 jp waiver"),
    (lambda o: o["waivers"].reverse() if len(o["waivers"]) > 1 else o["waivers"].extend(o["waivers"]),
     "waivers are not strictly ascending"),
    (lambda o: o["rows"][0].update(waived="R15 walk-in waived: jp F1 hole -- x"), "a row carries its waiver"),
])
def test_the_table_laws_can_fail(mutate, expect):
    """A check that cannot fail is not a check: each mutation of a deep copy turns the laws red."""
    obj = copy.deepcopy(_obj())
    mutate(obj)
    probs = _problems(obj)
    assert any(expect in p for p in probs), probs


def test_the_json_text_is_its_own_render_and_loads_from_the_package():
    raw = G.JSON_PATH.read_bytes()                # BYTES: read_text's universal newlines would hide a CRLF checkout
    assert b"\r" not in raw, "the committed JSON is checked out CRLF (the .gitattributes eol=lf rule is missing)"
    assert raw.isascii() and raw.endswith(b"\n")
    text = raw.decode("ascii")
    assert G.render_json(json.loads(text)) == text, "the committed JSON is not render_json of itself"
    assert G.load() == json.loads(text)
    for banned in (ff9mapkit.__version__, "C:\\", "C:/", "Users", "2026-"):
        assert banned not in text, f"the JSON carries a version/path/date string {banned!r}"


def test_git_checks_the_json_out_lf():
    """The attribute that keeps the bytes test honest on a fresh checkout: under core.autocrlf=true a file with no
    rule is smudged CRLF (the nightly gate worktree is such a checkout). Skips only when git or the checkout is
    absent (a wheel / sdist)."""
    import shutil
    import subprocess
    repo = G.JSON_PATH.resolve().parents[3]
    git = shutil.which("git")
    if git is None or not (repo / ".git").exists():
        pytest.skip("no git checkout here (git or the repo's .git is absent)")
    rel = G.JSON_PATH.resolve().relative_to(repo).as_posix()
    out = subprocess.run([git, "-C", str(repo), "check-attr", "text", "eol", "--", rel], capture_output=True,
                         text=True, check=True).stdout
    assert f"{rel}: text: set" in out and f"{rel}: eol: lf" in out, out


# ================================================================================================ the shared vectors
#: the contract's shared vectors, LITERALLY (CONTRACT.md 2.5): (blob, tag) -> (start, len, crc) | None
SLICE_WANT = {
    ("A", 0): (14, 2, 0x25b5d7fb), ("A", 2): (16, 3, 0x5640bad9), ("A", 3): (19, 9, 0x3e5ed723), ("A", 9): None,
    ("A+", 3): (19, 10, 0x705bc028), ("B", 3): (10, 3, 0xf84871ce), ("C", 1): (10, 3, 0x164f4116),
    ("C", 0): (13, 4, 0xb63cfbcd), ("D", 0): None, ("E", 0): None, ("T", 0): (18, 2, 0x46b4d6e6),
    ("T", 2): (20, 4, 0xbd70cc87), ("T", 3): (24, 5, 0xc5fb80d9), ("T", 8): (24, 0, 0x00000000), ("T", 5): None,
    ("P", 3): (202, 0, 0x00000000),
}
FLIP_WANT = {("T", 3, 2): 0xc439eaee, ("T", 3, 5): 0xc5fb80d9, ("A", 3, 0): 0x2925c360, ("A", 3, 8): 0x4959e7b5}
MATCH_WANT = [("A", 3, 9, 0x3e5ed723, True), ("A+", 3, 9, 0x3e5ed723, False), ("A", 3, 9, 0x3e5ed722, False)]
CRC_WANT = [("", 0x00000000), ("123456789", 0xcbf43926), ("The quick brown fox jumps over the lazy dog", 0x414fa339)]
TOY_WANT = {"toy1": 0xdbf99d93, "toy3": 0x822000d4}
TOY1_BYTES = "720009010200090300006600de30e5f4010b1100fa8402e4a3c10e"


def _blobs(obj) -> dict:
    return {b["name"]: bytes.fromhex(b["hex"]) for b in obj["selftest"]["blobs"]}


def test_the_json_vectors_are_the_contracts():
    st = _obj()["selftest"]
    assert [b["name"] for b in st["blobs"]] == ["A", "A+", "B", "C", "D", "E", "T", "P"]
    assert [(c["blob"], c["tag"]) for c in st["slice"]] == list(SLICE_WANT)
    for c in st["slice"]:
        w = SLICE_WANT[(c["blob"], c["tag"])]
        assert (c["start"], c["len"], c["crc"]) == ((-1, -1, None) if w is None else (w[0], w[1], "0x%08x" % w[2])), c
    assert {(c["blob"], c["tag"], c["at"]): int(c["crc"], 16) for c in st["flip"]} == FLIP_WANT
    assert [(c["blob"], c["tag"], c["len"], int(c["crc"], 16), c["ok"]) for c in st["match"]] == MATCH_WANT
    assert [(c["text"], int(c["crc"], 16)) for c in st["crc"]] == CRC_WANT
    assert {t["name"]: int(t["table_crc"], 16) for t in st["toy"]} == TOY_WANT
    assert st == G.build_selftest(), "the committed vectors are not the generator's"


def _vector_failures(slice_fn=G.func_slice, flip_fn=G.crc_flip, match_fn=G.func_matches, crc_fn=G.table_crc) -> list:
    """Run EVERY shared vector through the given rules; return the failing cases, named exactly like the engine
    selftest rows (crc.N, slice.<blob>.<tag>, flip.<blob>.<tag>.<at>, flip.pure, match.N, toy.<name>)."""
    obj = _obj()
    blobs = _blobs(obj)
    before = {k: bytes(v) for k, v in blobs.items()}
    out = []
    for i, (text, want) in enumerate(CRC_WANT):
        if zlib.crc32(text.encode("ascii")) != want:
            out.append(f"crc.{i}")
    for (name, tag), want in SLICE_WANT.items():
        s = slice_fn(blobs[name], tag)
        got = None if s is None else (s[0], s[1], zlib.crc32(blobs[name][s[0]:s[0] + s[1]]))
        if got != want:
            out.append(f"slice.{name}.{tag}")
    for (name, tag, at), want in FLIP_WANT.items():
        s = slice_fn(blobs[name], tag)
        if s is None or flip_fn(blobs[name], s[0], s[1], at) != want:
            out.append(f"flip.{name}.{tag}.{at}")
    if blobs != before:
        out.append("flip.pure")
    for i, (name, tag, ln, crc, ok) in enumerate(MATCH_WANT):
        if match_fn(blobs[name], tag, ln, crc) != ok:
            out.append(f"match.{i}")
    for t in obj["selftest"]["toy"]:
        if crc_fn(t["rows"]) != TOY_WANT[t["name"]]:
            out.append(f"toy.{t['name']}")
    return out


def test_every_shared_vector_passes_the_kit_rule():
    assert _vector_failures() == []
    assert G.serialize_rows(_obj()["selftest"]["toy"][0]["rows"]).hex() == TOY1_BYTES


def _table(entry):
    n = entry[1]
    return [(entry[2 + 4 * k] | entry[3 + 4 * k] << 8, entry[4 + 4 * k] | entry[5 + 4 * k] << 8) for k in range(n)]


def _fits(entry):
    return len(entry) >= 2 and 2 + 4 * entry[1] <= len(entry)


def _slice_next_listed(entry, tag):
    """MUTANT: the end is the next LISTED row's fpos (what the kit model did before it learned unsorted tables)."""
    if not _fits(entry):
        return None
    t = _table(entry)
    hit = next((k for k, (tg, _) in enumerate(t) if tg == tag), None)
    if hit is None:
        return None
    start = 2 + t[hit][1]
    end = 2 + t[hit + 1][1] if hit + 1 < len(t) else len(entry)
    return start, max(0, min(end, len(entry)) - start)


def _slice_tie_earlier(entry, tag):
    """MUTANT: a tie goes to the EARLIER-listed row (so the alias gets the full body)."""
    if not _fits(entry):
        return None
    t = _table(entry)
    hit = next((k for k, (tg, _) in enumerate(t) if tg == tag), None)
    if hit is None:
        return None
    fp = t[hit][1]
    end = len(entry)
    for j, (_, f) in enumerate(t):
        if j != hit and (f > fp or (f == fp and j < hit)):
            end = min(end, 2 + f)
    return 2 + fp, max(0, min(end, len(entry)) - (2 + fp))


def _slice_last_tag(entry, tag):
    """MUTANT: the LAST row whose tag matches (GetIP takes the first)."""
    if not _fits(entry):
        return None
    t = _table(entry)
    hits = [k for k, (tg, _) in enumerate(t) if tg == tag]
    if not hits:
        return None
    rev = bytearray(entry)
    order = list(range(len(t)))
    k = hits[-1]
    order[0], order[k] = order[k], order[0]      # list the last hit first, then slice with the real rule
    for i, j in enumerate(order):
        struct.pack_into("<HH", rev, 2 + 4 * i, *t[j])
    return G.func_slice(bytes(rev), tag)


def _match_prefix_crc(entry, tag, want_len, want_crc, flip_at=-1):
    """MUTANT: the CRC over want_len bytes from the start, no length check (A+ then matches A's want)."""
    s = G.func_slice(entry, tag)
    return s is not None and zlib.crc32(entry[s[0]:s[0] + want_len]) == want_crc


def _table_crc_kind0(rows):
    """MUTANT: the generator design's 0-based kinds (superseded by the contract's 1/2/3)."""
    b = bytearray()
    for r in rows:
        b += struct.pack("<HBBB", r["field"], r["entry"], G.KIND_CODES[r["kind"]] - 1, len(r["funcs"]))
        for f in r["funcs"]:
            b += struct.pack("<BBHBHI", G.ROLE_CODES[f["role"]], f["entry"], f["tag"], f["uid"], f["len"],
                             int(f["crc"], 16))
    return zlib.crc32(bytes(b))


@pytest.mark.parametrize("name, kw, caught", [
    ("next_listed", {"slice_fn": _slice_next_listed}, "slice.C.0"),
    ("tie_earlier", {"slice_fn": _slice_tie_earlier}, "slice.T.8"),
    ("last_tag", {"slice_fn": _slice_last_tag}, "slice.B.3"),
    ("prefix_crc", {"match_fn": _match_prefix_crc}, "match.1"),
    ("kind_zero", {"crc_fn": _table_crc_kind0}, "toy.toy1"),
])
def test_each_vector_mutant_is_caught_by_its_named_case(name, kw, caught):
    fails = _vector_failures(**kw)
    assert caught in fails, (name, fails)


def test_r10_cross_checks_the_vectors_against_the_kit_model(monkeypatch):
    """build_selftest refuses to emit vectors on which func_slice and the kit's EbScript slicing disagree (R10). A
    tie-to-earlier twin disagrees on the tie blob T, so it must raise -- the hard error is live, not described."""
    assert G.build_selftest() == _obj()["selftest"]
    monkeypatch.setattr(G, "func_slice", _slice_tie_earlier)
    with pytest.raises(G.TableError, match="R10"):
        G.build_selftest()


# ================================================================================================ the opcode classes
def test_the_op_classes_are_pressclosures_buckets():
    oc = _obj()["op_classes"]
    assert oc == G.build_op_classes()
    names, table = oc["names"], oc["table"]
    assert names == list(G.OP_CLASS_NAMES) and len(names) == 17 and names[0] is None and len(table) == 0x120
    for op, cls in ((0x2B, "exit"), (0x2A, "battle"), (0x1F, "window"), (0x112, "item_party")):
        assert names[table[op]] == cls, hex(op)
    for op in (0x2D, 0x27, 0x14, 0x1D):          # movelock, the talk bracket, a call, locomotion
        assert table[op] == 0, hex(op)
    assert table[0x112] != table[0x12], "the 0xFF page must not alias the 1-byte page"
    for op, v in enumerate(table):
        bucket = P.B.get(op)
        assert (names[v] == bucket) if v else (bucket not in names[1:]), hex(op)
    assert all(n is None or n not in P.NEUTRAL for n in names)
    assert not set(P.KEY_OPS.values()) & set(n for n in names if n)


# ================================================================================================ the generated C#
_ROW_RE = re.compile(r"new GuestLocalRow\((\d+), (\d+), (\d+), (\d+), (\d+)\)")
_FUNC_RE = re.compile(r"new GuestLocalFunc\((\d+), (\d+), (\d+), (\d+), (\d+), 0x([0-9A-F]{8})u\)")


def _block(cs: str, decl: str) -> str:
    i = cs.index(decl)
    return cs[i:cs.index("};", i)]


def _parse_cs(cs: str) -> dict:
    """The C# parsed back: the consts, the Rows/Funcs arrays, the toys -- the text-independent half of the pin."""
    const = {m.group(1): m.group(2) for m in re.finditer(r"internal const \w+ (\w+) = (0x[0-9A-F]{8}u|\d+);", cs)}
    rows = [tuple(int(x) for x in m.groups()) for m in _ROW_RE.finditer(_block(cs, "GuestLocalRow[] Rows ="))]
    funcs = [tuple(int(x) for x in m.groups()[:5]) + (int(m.group(6), 16),)
             for m in _FUNC_RE.finditer(_block(cs, "GuestLocalFunc[] Funcs ="))]
    return {"const": const, "rows": rows, "funcs": funcs}


def _json_rows_as_cs(obj):
    rows, funcs, start = [], [], 0
    for r in obj["rows"]:
        rows.append((r["field"], r["entry"], G.KIND_CODES[r["kind"]], start, len(r["funcs"])))
        start += len(r["funcs"])
        funcs += [(G.ROLE_CODES[f["role"]], f["entry"], f["tag"], f["uid"], f["len"], int(f["crc"], 16))
                  for f in r["funcs"]]
    return rows, funcs


def _assert_cs_is_the_json(cs: str, obj: dict):
    p = _parse_cs(cs)
    rows, funcs = _json_rows_as_cs(obj)
    assert p["rows"] == rows, "the C# Rows are not the JSON rows"
    assert p["funcs"] == funcs, "the C# Funcs are not the JSON functions"
    assert p["const"]["RowCount"] == str(len(rows)) and p["const"]["FuncCount"] == str(len(funcs))
    assert p["const"]["TableCrc"] == "0x%08Xu" % int(obj["table_crc"], 16)
    assert p["const"]["Schema"] == str(obj["schema"])
    oc = re.search(r"Byte\[\] OpClass =[^{]*\{([^}]*)\}", cs).group(1)
    assert [int(x) for x in re.findall(r"\d+", oc)] == obj["op_classes"]["table"]


def test_render_cs_is_the_json_row_for_row():
    obj = _obj()
    cs = G.render_cs(obj)
    _assert_cs_is_the_json(cs, obj)


def test_render_cs_is_ascii_crlf_and_a_pure_function_of_the_json():
    obj = _obj()
    cs = G.render_cs(obj)
    raw = cs.encode("ascii")
    assert not raw.startswith(b"\xef\xbb\xbf")
    assert raw.count(b"\n") == raw.count(b"\r\n") and raw.endswith(b"\r\n"), "CRLF only"
    assert cs.startswith("// <auto-generated/>\r\n") and "[ff9mapkit netsync s156]" in cs and "DO NOT EDIT BY HAND" in cs
    assert "guest_traversal.json" in cs and "py -m ff9mapkit.guest_traversal --write --cs" in cs
    assert G.render_cs(copy.deepcopy(obj)) == cs
    for banned in (ff9mapkit.__version__, "C:\\", "C:/", "Users", "2026-"):
        assert banned not in cs, f"the generated C# carries a version/path/date string {banned!r}"
    moved = copy.deepcopy(obj)
    moved["rows"][0]["funcs"][0]["crc"] = "0x%08x" % (int(moved["rows"][0]["funcs"][0]["crc"], 16) ^ 1)
    assert G.render_cs(moved) != cs


def _added_generated_file():
    """The LAST live patch's section for NetSyncGuestLocalTable.cs: (patch name, its '+' lines, its other lines, the
    section's raw bytes). The lines are CRLF-normalised and the '\\ No newline' marker dropped -- the BYTES pin
    (:func:`_check_capture_bytes`) reads the raw section."""
    last = None
    for name in msr.stack():
        if name in msr.DEAD:
            continue
        for path, sec in msr.sections((msr.PATCHES / name).read_bytes()):
            if path and path.replace("\\", "/").rsplit("/", 1)[-1] == G.CS_NAME:
                last = (name, sec)
    if last is None:
        return None
    name, sec = last
    body = sec.decode("ascii", "replace").replace("\r\n", "\n").split("\n")
    hunk = [ln for ln in body if not ln.startswith(("diff --git", "index ", "--- ", "+++ ", "new file mode",
                                                    "@@", "\\ No newline"))]
    added = [ln[1:] for ln in hunk if ln.startswith("+")]
    other = [ln for ln in hunk if ln and not ln.startswith("+")]
    return name, added, other, sec


#: THE DEPLOYED-AHEAD PIN: the rows the captured engine table ships beyond the JSON, each with its why. AT THE NEXT
#: ENGINE CAPTURE (the generator writes the engine tree, the lead re-captures the patch from it) EMPTY THIS -- the pin
#: is then exact equality with render_cs(json) again
S156_DEPLOYED_AHEAD = {
    "1209:5": {"evt": "EVT_ALEX2_AC_PRISON_B",
               "why": "refused by R15's walker bound since round 3, after the engine was captured; the next capture "
                      "drops it; on a guest its worst case is a bump whose Battle the engine already skips for a "
                      "mirroring guest (EventEngine.DoEventCode.cs ENCOUNT: NetSyncClient.IsMirroringStory returns 0)"},
}
_ROW_NOTE_RE = re.compile(r"new GuestLocalRow\((\d+), (\d+), \d+, \d+, \d+\),?   // \d+:\d+ \w+ ?(.*)$", re.M)


def _cs_rows_as_json(added) -> dict:
    """The captured table's rows JSON-shaped, ``{(field, entry): row}`` (``evt`` from each row's note): what render_cs
    needs to write those lines back."""
    cs = "\n".join(added)
    p = _parse_cs(cs)
    roles = {v: k for k, v in G.ROLE_CODES.items()}
    kinds = {v: k for k, v in G.KIND_CODES.items()}
    evt = {(int(m.group(1)), int(m.group(2))): m.group(3) for m in _ROW_NOTE_RE.finditer(_block(cs, "GuestLocalRow[] Rows ="))}
    return {(f, e): {"field": f, "entry": e, "kind": kinds[k], "evt": evt.get((f, e), ""),
                     "funcs": [{"role": roles[r], "entry": fe, "tag": t, "uid": u, "len": ln, "crc": "0x%08x" % c}
                               for (r, fe, t, u, ln, c) in p["funcs"][s:s + n]]}
            for (f, e, k, s, n) in p["rows"]}


def _check_deployed_ahead(added, obj, ahead) -> dict:
    """The captured table's lines ``added`` against the JSON ``obj`` and the pinned ``ahead`` rows: the rows it carries
    beyond the JSON are EXACTLY ``ahead`` (no more, no fewer -- a pinned row the JSON ships is one fewer), each the JSON's
    own REFUSED row function for function and kind for kind, its row note naming the ``evt`` the pin records (the note
    is read back from the capture, so render_cs would only echo a hand edit), and the text is render_cs of the JSON plus
    them, line for line (counts, start offsets and TableCrc recomputed; every other line the JSON's) -- so taking them
    out leaves render_cs(json). With ``ahead`` empty that is exact equality. Returns that JSON-plus-pinned object, which
    the BYTES pin (:func:`_check_capture_bytes`) renders."""
    patch = _cs_rows_as_json(added)
    shipped = {(r["field"], r["entry"]) for r in obj["rows"]}
    extra = {f"{f}:{e}" for (f, e) in patch if (f, e) not in shipped}
    assert extra == set(ahead), f"the captured table carries {sorted(extra)} beyond the JSON; the pin says {sorted(ahead)}"
    lack = sorted(f"{f}:{e}" for (f, e) in shipped - set(patch))
    assert not lack, f"the captured table lacks the JSON's rows {lack}"
    refused = {f"{x['field']}:{x['entry']}": x for x in obj["refused"]}
    rows = [patch[tuple(int(x) for x in key.split(":"))] for key in sorted(ahead)]
    for key, r in zip(sorted(ahead), rows):
        assert key in refused and [{k: v for k, v in f.items() if k not in ("call", "level")} for f in
                                   refused[key]["funcs"]] == r["funcs"] and refused[key]["kind"] == r["kind"], \
            f"{key} is not the JSON's refused row of that key, function for function"
        assert r["evt"] == ahead[key]["evt"], f"{key}'s row note names {r['evt']!r}; the pin records {ahead[key]['evt']!r}"
    full = copy.deepcopy(obj)
    full["rows"] = sorted(obj["rows"] + rows, key=lambda r: (r["field"], r["entry"]))
    full["table_crc"] = "0x%08x" % G.table_crc(full["rows"])
    want = G.render_cs(full).replace("\r\n", "\n").split("\n")
    if want and want[-1] == "":
        want = want[:-1]
    assert added == want, "the captured NetSyncGuestLocalTable.cs is not render_cs(json + the pinned rows) (hand edit or stale)"
    _assert_cs_is_the_json("\n".join(added), full)
    return full


def _check_capture_bytes(sec: bytes, full: dict) -> None:
    """THE BYTES PIN: the file the captured section writes is render_cs(``full``) BYTE for byte -- every hunk '+' line
    CRLF (render_cs's ending, which :func:`_added_generated_file` normalises away), no '\\ No newline' marker after the
    last one (the file ends with its CRLF), and the '+' lines, their '+' dropped and their own endings kept, ARE
    render_cs's bytes."""
    lines = re.findall(rb"[^\n]*\n|[^\n]+$", sec)
    at = next(k for k, ln in enumerate(lines) if ln.startswith(b"@@"))
    hunk = lines[at + 1:]
    assert not any(ln.startswith(b"\\") for ln in hunk), "a '\\ No newline' marker: the captured file has no final newline"
    bad = [k for k, ln in enumerate(hunk) if ln.startswith(b"+") and not ln.endswith(b"\r\n")]
    assert not bad, f"captured line {bad[0] + 1} is not CRLF (render_cs writes CRLF only)"
    assert b"".join(ln[1:] for ln in hunk if ln.startswith(b"+")) == G.render_cs(full).encode("ascii"), \
        "the captured file's bytes are not render_cs(json + the pinned rows)"


def test_the_s156_patch_carries_render_cs_of_the_json_and_only_the_pinned_rows_ahead():
    """THE PIN THAT ORDERS THE WORK: the engine's generated table is render_cs(json) verbatim, captured whole in the
    LAST live patch touching it (a generated file is only ever replaced WHOLE -- no context or removed lines) -- exact
    about everything but :data:`S156_DEPLOYED_AHEAD`, the rows a deployed engine still ships after the kit refused
    them (_check_deployed_ahead). AT THE NEXT CAPTURE: regenerate the engine tree (`py -m ff9mapkit.guest_traversal
    --write --cs ...`), re-capture the patch from it, and EMPTY S156_DEPLOYED_AHEAD -- this is exact equality again."""
    got = _added_generated_file()
    if got is None:
        pytest.fail("s156 not captured: no live memoria-patches/*.patch adds Memoria/Netsync/NetSyncGuestLocalTable.cs "
                    "yet -- capture s156 from the engine tree the generator wrote")
    name, added, other, sec = got
    assert other == [], f"{name}: the generated file must be replaced WHOLE, but its section has {other[:3]}"
    _check_capture_bytes(sec, _check_deployed_ahead(added, _obj(), S156_DEPLOYED_AHEAD))


def _flip_hex(line: str, after: str) -> str:
    """``line`` with the last digit of the 8-digit hex constant that follows ``after`` XOR 1."""
    return re.sub(re.escape(after) + r"(0x[0-9A-F]{7})([0-9A-F])u",
                  lambda m: f"{after}{m.group(1)}{int(m.group(2), 16) ^ 1:X}u", line, count=1)


def _pinned_probe():
    """``(added, obj, ahead)``: the captured lines, a copy of the JSON and of the pin -- once the pin is emptied, the
    JSON's first row moved to refused and pinned (green), so the pinned-row mutations stay live."""
    got = _added_generated_file()
    if got is None:
        pytest.fail("s156 not captured")
    added, obj, ahead = list(got[1]), copy.deepcopy(_obj()), copy.deepcopy(S156_DEPLOYED_AHEAD)
    if not ahead:
        r = obj["rows"].pop(0)
        obj["refused"].append(dict(r, refusal="R15 walk-in: probe"))
        ahead = {f"{r['field']}:{r['entry']}": {"evt": r.get("evt", ""), "why": "probe"}}
    _check_deployed_ahead(added, obj, ahead)
    return added, obj, ahead


def _refused_of(obj, key) -> dict:
    (x,) = [x for x in obj["refused"] if f"{x['field']}:{x['entry']}" == key]
    return x


def _flip_refused_crc(obj, key) -> None:
    f = _refused_of(obj, key)["funcs"][0]
    f["crc"] = "0x%08x" % (int(f["crc"], 16) ^ 1)


def _recompute_table_crc(added, obj, ahead) -> None:
    """Rewrite the captured TableCrc line as render_cs would for the captured pinned rows (a self-consistent edit)."""
    patch = _cs_rows_as_json(added)
    rows = sorted(obj["rows"] + [patch[tuple(int(x) for x in k.split(":"))] for k in ahead],
                  key=lambda r: (r["field"], r["entry"]))
    (j,) = [k for k, ln in enumerate(added) if "UInt32 TableCrc = " in ln]
    added[j] = re.sub(r"0x[0-9A-F]{8}u", "0x%08Xu" % G.table_crc(rows), added[j], count=1)


@pytest.mark.parametrize("how", ["pin_loses_a_row", "pin_gains_a_row", "json_gains_a_row", "json_ships_a_pinned_row",
                                 "patch_gains_a_row", "pinned_row_crc", "header_line", "selftest_vector", "table_crc",
                                 "refused_len", "refused_crc", "refused_kind", "pinned_row_crc_recomputed",
                                 "note_hand_edited", "note_dropped", "pin_evt_edited"])
def test_the_deployed_ahead_pin_can_fail(how):
    """A check that cannot fail is not a check: each mutation of the pin, the JSON or the captured lines turns it red.
    The refused-row and note cases are edits the TEXT compare cannot see (the capture's own pinned row and note are what
    render_cs echoes): the JSON's refused entry changed under an untouched capture, the pinned row's crc flipped with
    the capture's TableCrc recomputed, the note hand-edited or dropped -- each is red, and (for the self-consistent ones)
    green again once the other side agrees, so the clause that catches it is the one under test."""
    added, obj, ahead = _pinned_probe()
    key = min(ahead)
    agree = None                                      # the counter-edit that makes a self-consistent case green again
    if how == "pin_loses_a_row":
        del ahead[key]
    elif how == "pin_gains_a_row":
        ahead["1:1"] = {"evt": "", "why": "probe"}
    elif how == "refused_len":
        _refused_of(obj, key)["funcs"][-1]["len"] += 1
    elif how == "refused_crc":
        _flip_refused_crc(obj, key)
    elif how == "refused_kind":
        r = _refused_of(obj, key)
        r["kind"] = next(k for k in G.KIND_CODES if k != r["kind"])
    elif how == "pinned_row_crc_recomputed":
        (i,) = [k for k, ln in enumerate(added) if "new GuestLocalFunc(" in ln and ln.endswith(f"   // {key}")]
        added[i] = _flip_hex(added[i], ", ")
        _recompute_table_crc(added, obj, ahead)
        agree = functools.partial(_flip_refused_crc, obj, key)
    elif how in ("note_hand_edited", "note_dropped"):
        evt = ahead[key]["evt"]
        (i,) = [k for k, ln in enumerate(added) if "new GuestLocalRow(" in ln and f"   // {key} " in ln]
        assert evt and added[i].endswith(f" {evt}")
        added[i] = added[i][:-len(evt) - 1] + ("" if how == "note_dropped" else f" {evt}X")
        agree = functools.partial(ahead[key].__setitem__, "evt", "" if how == "note_dropped" else f"{evt}X")
    elif how == "pin_evt_edited":
        ahead[key]["evt"] += "X"
    elif how == "json_gains_a_row":
        obj["rows"].insert(1, dict(copy.deepcopy(obj["rows"][0]), entry=254))
    elif how == "json_ships_a_pinned_row":
        row = _cs_rows_as_json(added)[tuple(int(x) for x in key.split(":"))]
        obj["rows"] = sorted(obj["rows"] + [row], key=lambda r: (r["field"], r["entry"]))
    elif how == "patch_gains_a_row":
        i = next(k for k, ln in enumerate(added) if "new GuestLocalRow(" in ln)
        added.insert(i + 1, re.sub(r"GuestLocalRow\((\d+), \d+,", r"GuestLocalRow(\1, 254,", added[i]))
    elif how == "pinned_row_crc":
        (i,) = [k for k, ln in enumerate(added) if "new GuestLocalFunc(" in ln and ln.endswith(f"   // {key}")]
        added[i] = _flip_hex(added[i], ", ")
    elif how == "header_line":
        (i,) = [k for k, ln in enumerate(added) if "DO NOT EDIT BY HAND." in ln]
        added[i] = added[i].replace("BY HAND.", "BY HAND!")
    else:
        after = "CrcWant = { " if how == "selftest_vector" else "UInt32 TableCrc = "
        (i,) = [k for k, ln in enumerate(added) if after in ln]
        added[i] = _flip_hex(added[i], after)
    with pytest.raises(AssertionError):
        _check_deployed_ahead(added, obj, ahead)
    if agree is not None:
        agree()
        _check_deployed_ahead(added, obj, ahead)


@pytest.mark.parametrize("how", ["lf_only", "no_final_newline", "marker_after_crlf", "one_lf_line", "one_byte",
                                 "stray_cr"])
def test_the_capture_bytes_pin_can_fail(how):
    """THE BYTES PIN can fail where the line pin cannot (it normalises CRLF and drops the marker): an LF-only capture,
    a capture whose file has no final newline (git's '\\ No newline at end of file', the last line CR-less before it --
    or with its CRLF kept, which only the marker shows: git then strips the final LF), one LF line in the middle, one
    byte changed inside a line, one bare CR inside a line -- each red, while the line pin stays green on all but the
    last two."""
    got = _added_generated_file()
    if got is None:
        pytest.fail("s156 not captured")
    added, obj, ahead = _pinned_probe()
    full = _check_deployed_ahead(added, obj, ahead)
    sec = got[3]
    _check_capture_bytes(sec, full)
    at = sec.index(b"\n+", sec.index(b"\n@@")) + 1
    head, body = sec[:at], sec[at:]
    if how == "lf_only":
        bad = head + body.replace(b"\r\n", b"\n")
    elif how == "no_final_newline":
        assert body.endswith(b"\r\n")
        bad = head + body[:-2] + b"\n\\ No newline at end of file\n"
    elif how == "marker_after_crlf":
        bad = head + body + b"\\ No newline at end of file\n"
    elif how == "one_lf_line":
        k = body.index(b"\r\n", len(body) // 2)
        bad = head + body[:k] + body[k + 1:]
    elif how == "stray_cr":
        k = body.index(b"GuestLocalRow(")
        bad = head + body[:k] + b"\r" + body[k:]
    else:
        k = body.index(b"GuestLocalRow(")
        bad = head + body[:k] + b"GuestLocalRoW(" + body[k + len(b"GuestLocalRow("):]
    with pytest.raises(AssertionError):
        _check_capture_bytes(bad, full)
    if how not in ("one_byte", "stray_cr"):
        lines = bad.decode("ascii").replace("\r\n", "\n").split("\n")
        relined = [ln[1:] for ln in lines[lines.index(next(x for x in lines if x.startswith("@@"))) + 1:]
                   if ln.startswith("+")]
        _check_deployed_ahead(relined, obj, ahead)       # the line pin cannot see it


@pytest.mark.parametrize("how", ["lf_only", "marker_after_crlf", "context_line"])
def test_the_main_pin_reads_the_capture_bytes_and_the_whole_section(how, monkeypatch):
    """THE MAIN PIN is wired to both checks, not only the line pin: fed through its own seam (_added_generated_file) an
    LF-only capture, a capture ending in git's '\\ No newline' marker (the lines unchanged), or a section carrying a
    context line, it turns red -- the can_fail tests above call the helpers directly, so only this shows the main test
    calls them."""
    got = _added_generated_file()
    if got is None:
        pytest.fail("s156 not captured")
    name, added, other, sec = got
    test_the_s156_patch_carries_render_cs_of_the_json_and_only_the_pinned_rows_ahead()   # green as captured
    at = sec.index(b"\n+", sec.index(b"\n@@")) + 1
    head, body = sec[:at], sec[at:]
    if how == "lf_only":
        bad = (name, added, other, head + body.replace(b"\r\n", b"\n"))
    elif how == "marker_after_crlf":
        bad = (name, added, other, head + body + b"\\ No newline at end of file\n")
    else:
        bad = (name, added, other + [" a context line"], sec)
    monkeypatch.setitem(globals(), "_added_generated_file", lambda: bad)
    with pytest.raises(AssertionError):
        test_the_s156_patch_carries_render_cs_of_the_json_and_only_the_pinned_rows_ahead()


def _added_lines_of(fname: str) -> list:
    """Every '+' line the live stack adds to ``fname`` (by basename), in stack order."""
    out = []
    for name in msr.stack():
        if name in msr.DEAD:
            continue
        for path, sec in msr.sections((msr.PATCHES / name).read_bytes()):
            if path and path.replace("\\", "/").rsplit("/", 1)[-1] == fname:
                out += [ln[1:] for ln in sec.decode("ascii", "replace").replace("\r\n", "\n").split("\n")
                        if ln.startswith("+") and not ln.startswith("+++")]
    return out


def test_the_trip_wire_speaks_the_classifiers_terminate_entry_exemption():
    """ONE RULE, THREE PLACES. The classifier's census exemption stays VERBATIM for the tier pin: pressclosure treats any
    Seq-run TerminateEntry (0x1C), or one naming a constant 255 (itself), as FLOW. R12 narrows what SHIPS to the
    constant-255 self form (flag bit 0 clear, operand 255: ``pressclosure.is_const_self_end``) -- a Seq's
    TerminateEntry(X) disposes X. The engine's trip wire speaks the SHIPPED (narrow) rule (TripClassRule), because the
    generated bucket table alone cannot carry it: without it every Seq tail tripped 'spawn' (207, the bench's first run),
    and with the old Seq-wide clause a Seq that disposed the body would never trip. Any side moving turns this red.
    RED until the lead re-captures s156 with the self-only TripClassRule and its selftest rows."""
    import inspect
    from ff9mapkit.eb import pressclosure as pc
    src = inspect.getsource(pc)
    assert ("if op == 0x1C and (actor is not None or (ins.args and not ins.arg_is_expr[0] and ins.args[0] == SELF_UID)):"
            in src), "pressclosure's TerminateEntry exemption moved or changed: the census tier pin reads it verbatim"
    assert pc.SELF_UID == 255 and pc.TERMINATE_OP == 0x1C
    assert ("return ins.op == TERMINATE_OP and bool(ins.args) and not ins.arg_is_expr[0] and ins.args[0] == SELF_UID"
            in src), "R12's constant self-end test moved or changed: re-read the engine's TripClassRule with it"
    gsrc = inspect.getsource(G._derive_one)
    assert "elif ins.op == P.TERMINATE_OP and not P.is_const_self_end(ins):" in gsrc, "R12 no longer ships the narrow rule"
    cs = "\n".join(_added_lines_of("NetSyncGuestLocal.cs"))
    if "TripClassRule" not in cs:
        pytest.fail("s156 not captured: no live patch adds NetSyncGuestLocal.cs's TripClassRule yet")
    assert "internal const Int32 OpTerminateEntry = 0x1C;" in cs
    assert "if (op == OpTerminateEntry && argFlags >= 0 && (argFlags & 1) == 0 && arg0 == 255)" in cs, \
        "the engine's TripClassRule is not the self-only rule R12 ships (the Seq-wide clause is still there?)"
    assert "who == WhoRegionSeq || who == WhoBodySeq" not in cs, "the engine still exempts every Seq-run TerminateEntry"
    assert "Byte cls = TripClassRule(op, who, argFlags, arg0);" in cs     # the hook runs the rule, not ClassOf
    st = "\n".join(_added_lines_of("NetSyncGuestLocal.SelfTest.cs"))
    assert "TripRows(TripClassRule, row);" in st and "mutant.trip.no_exemption" in st and "mutant.trip.seq_wide" in st
