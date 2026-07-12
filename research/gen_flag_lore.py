"""Per-bit story-flag LORE candidates -- the per-flag-meaning pass over the ~1900 un-annotated
gEventGlobal heap bytes (the standing UNDERSTAND frontier, STORY_FLAGS.md par.8).

For every bit-flag the census saw that is NOT already per-bit named (engine NAMED_WORDS bytes,
reserved BIT_REGIONS like the chest band / menu handshake), join -- deterministically, from real
bytes, no inference:

  * WHO writes it: field id -> manifest room/area, the exact statement offset, set vs clear.
  * WHAT is said around the write: the nearest dialogue window in the SAME entry+func within a
    byte window, resolved through the field's real .mes to the actual line (v1 is byte-proximity
    within one function -- branches are not control-flow-analyzed; confidence reflects that).
  * WHAT its gates guard: the ops inside each conditional body the bit controls (NPC spawns via
    InitObject, Field() warps, Battle, dialogue) and the polarity (body runs when SET or CLEAR).
  * WHEN it can fire: the writer field's own ScenarioCounter writes -> beat names (plus its area).
  * Engine evidence: any direct Memoria C# `gEventGlobal[<byte>]` read of the bit's byte (tier a).

Confidence tiers (mirrors flags.py's a/b/c convention):
  a = engine C# reads the byte (the only non-inference tier)
  b = single writer field AND (a dialogue match in range OR a decoded gate body) -- the payoff tier
  c = everything else (multi-writer, no nearby context, or a shared compiled-verbatim block --
      detected by identical statement bytes across >= SHARED_BLOCK_MIN writer fields, the same
      shape as the chest-band 130-entry dispatch block)

Known v1 limitations (deliberate; same discipline as the census): only statements whose FIRST
token is the global var are seen (compound `A && B` conditions attribute to A); byte-proximity
within a function ignores branch reachability; a "nearest line" in a dense dialogue func can be
the wrong speaker. Candidates are RESEARCH OUTPUT for human curation -- nothing here is merged
into ff9mapkit/flags.py automatically.

Inputs:  research/flag_census.json (run flag_census.py first) + reference/field-manifest.tsv
         + the game install (event + text bundles) + optionally C:/gd/FFIX/Memoria (tier-a grep).
Outputs: research/flag_lore.json (machine form) + research/FLAG_LORE.md (human digest).
Run:     cd ff9mapkit && py ../research/gen_flag_lore.py [--probe BIT [BIT ...]] [--no-mes]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import struct
import sys
from collections import defaultdict

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HERE)
for p in (os.path.join(_REPO, "ff9mapkit"), _REPO, _HERE):
    if p not in sys.path:
        sys.path.insert(0, p)

import flag_census as FC                                    # noqa: E402  (decode/classify primitives)
from ff9mapkit.eb import EbScript                           # noqa: E402
from ff9mapkit import flags as KF                           # noqa: E402
from ff9mapkit import dialogue as KD                        # noqa: E402
from ff9mapkit._fieldtext import EVENT_ID_TO_MES            # noqa: E402

MEMORIA_SRC = r"C:\gd\FFIX\Memoria\Assembly-CSharp"         # optional; tier-a evidence when present

# --- opcodes of lore interest inside a gate's guarded body ---
OP_INITOBJ, OP_FIELD, OP_BATTLE = 0x09, 0x2B, 0x2A
WINDOW_OPS = KD.WINDOW_OPS                                  # {op: txid operand index}
T_NOT, T_END = 0x0E, 0x7F
JMP_FALSE, JMP_TRUE = 0x02, 0x03

DIALOGUE_WINDOW = 150        # bytes: max |write_off - window_off| for a "nearby line" claim
SHARED_BLOCK_MIN = 8         # identical statement bytes across >= this many fields = a compiled block
TEXT_PREVIEW = 110           # chars of dialogue preview in the digest

# --- field id -> room/area labels (mirrors gen_understand_layer.py, which is not import-safe) ---
AREA_NORM = {
    "L. Castle": "Lindblum Castle", "A. Castle": "Alexandria Castle", "I. Castle": "Ipsen's Castle",
    "S. Gate": "South Gate", "N. Gate": "North Gate", "Mdn. Sari": "Madain Sari",
    "Mountain Path": "Conde Petie Mt. Path", "Gulug": "Mount Gulug", "Hilda Garde 3": "Hilda Garde",
    "Hilda Garde 1": "Hilda Garde", "Hilda Garde 2": "Hilda Garde", "last": "Crystal World (ending)",
    "Gizamaluke": "Gizamaluke's Grotto", "Marsh": "Qu's Marsh", "Palace": "Desert Palace",
    "Pand.": "Pandemonium",
}


def _load_rooms() -> dict:
    room = {}
    path = os.path.join(_REPO, "reference", "field-manifest.tsv")
    try:
        lines = open(path, encoding="utf-8").read().splitlines()
    except UnicodeDecodeError:
        lines = open(path, encoding="cp1252").read().splitlines()
    for ln in lines:
        p = ln.split("\t")
        if len(p) >= 3 and p[1].strip().isdigit():
            room.setdefault(int(p[1]), p[2].strip())
    return room


ROOM = _load_rooms()


def area_of(fid: int) -> str:
    rm = ROOM.get(fid)
    if not rm:
        return "?"
    a = rm.split("/")[0]
    return AREA_NORM.get(a, a)


def beat_names(values) -> list:
    """SC values -> milestone labels (exact anchor, else nearest lower anchor + '+')."""
    out = []
    anchors = sorted(KF.SCENARIO_MILESTONES)
    for v in sorted(set(values)):
        name = KF.SCENARIO_MILESTONES.get(v)
        if name is None:
            lower = [a for a in anchors if a <= v]
            name = (KF.SCENARIO_MILESTONES[lower[-1]] + "+") if lower else "?"
        out.append(f"{v} ({name})")
    return out


def strip_tags(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"\[[^\]]*\]", "", text)).strip()


# ------------------------------------------------------------------ coverage filter ---
_NAMED_WORD_BYTES = {b for w in KF.NAMED_WORDS for b in range(w.byte, w.byte + w.width)}


def skip_reason(bit: int):
    """Why a bit needs no lore row (already covered), or None to keep it."""
    r = KF.bit_region(bit)
    if r is not None and r.reserved:
        return f"reserved:{r.name}"
    if (bit >> 3) in _NAMED_WORD_BYTES:
        return "named-word-byte"
    return None


def story_region_name(bit: int):
    r = KF.bit_region(bit)
    return r.name if (r is not None and not r.reserved) else None


# ------------------------------------------------------------------ per-field sweep ---
def sweep_field(eb: EbScript):
    """One pass over a field's .eb: every GLOBAL-bit statement occurrence (with offset + gate span),
    every dialogue-window call (with offset), and every lore-interesting op (with offset)."""
    d = eb.data
    occs, wins, ops = [], [], []
    for e in eb.entries:
        if e.empty:
            continue
        for f in e.funcs:
            for ins in eb.instrs(f):
                if ins.op == 0x05:
                    dec = FC.decode_global_var(d, ins.off + 1)
                    if dec is None or dec[0] not in (0, 1):          # bit/sbit types only
                        continue
                    _vt, bit, vlen = dec
                    role, val, op = FC.classify(d, ins.off + 1, vlen)
                    stmt, end = FC.statement_tokens(d, ins.off + 1)
                    o = {"bit": bit, "entry": e.index, "tag": f.tag, "off": ins.off,
                         "role": role, "val": val, "op": op, "stmt": bytes(stmt)}
                    if role == "gate" and end + 3 < len(d) and d[end] == T_END:
                        jmp = d[end + 1]
                        skip = struct.unpack("<h", d[end + 2:end + 4])[0]
                        negated = d[ins.off + 1 + vlen] == T_NOT
                        # JMP_FALSE skips when expr==0 -> body runs when expr TRUE; JMP_TRUE inverse.
                        body_when = (not negated) if jmp == JMP_FALSE else negated
                        o["body_span"] = (end + 4, end + 4 + max(0, skip))
                        o["body_when_set"] = body_when
                    occs.append(o)
                elif ins.op in WINDOW_OPS:
                    txid = ins.imm(WINDOW_OPS[ins.op])
                    if txid is not None:
                        wins.append({"entry": e.index, "tag": f.tag, "off": ins.off, "txid": txid})
                elif ins.op in (OP_INITOBJ, OP_FIELD, OP_BATTLE):
                    ops.append({"entry": e.index, "tag": f.tag, "off": ins.off,
                                "op": ins.op, "imm": ins.imm(0)})
    return occs, wins, ops


def gate_body_summary(occ, wins, ops):
    """What the guarded body contains -- the 'this bit controls X' evidence."""
    span = occ.get("body_span")
    if not span:
        return None
    lo, hi = span
    same = lambda x: x["entry"] == occ["entry"] and x["tag"] == occ["tag"] and lo <= x["off"] < hi
    body = {"when_set": occ.get("body_when_set")}
    spawns = [x["imm"] for x in ops if x["op"] == OP_INITOBJ and same(x) and x["imm"] is not None]
    warps = [x["imm"] for x in ops if x["op"] == OP_FIELD and same(x) and x["imm"] is not None]
    battles = [x["imm"] for x in ops if x["op"] == OP_BATTLE and same(x) and x["imm"] is not None]
    says = [w["txid"] for w in wins if same(w)]
    for k, v in (("spawns", spawns), ("warps", warps), ("battles", battles), ("says", says)):
        if v:
            body[k] = sorted(set(v))
    return body if len(body) > 1 else None


def nearest_line(occ, wins, mes_map):
    """The dialogue window nearest the write, same entry+func, within DIALOGUE_WINDOW bytes.
    Preceding lines win ties (talk -> latch is the common shape). None when nothing is in range."""
    cands = [w for w in wins if w["entry"] == occ["entry"] and w["tag"] == occ["tag"]
             and abs(w["off"] - occ["off"]) <= DIALOGUE_WINDOW]
    if not cands:
        return None
    best = min(cands, key=lambda w: (abs(w["off"] - occ["off"]), w["off"] > occ["off"]))
    entry = mes_map.get(best["txid"]) if mes_map else None
    text = strip_tags(entry.text)[:TEXT_PREVIEW] if entry else None
    if text is not None and (len(text) < 2 or text.startswith("Error ")):
        text = None                       # debug/system windows and bare "!" bubbles are noise, not lore
    return {"txid": best["txid"], "delta": best["off"] - occ["off"], "text": text}


# ------------------------------------------------------------------ tier-a engine grep ---
def engine_byte_reads() -> dict:
    """{byte_index: ['file:line', ...]} for every literal gEventGlobal[<const>] in the Memoria source."""
    out = defaultdict(list)
    if not os.path.isdir(MEMORIA_SRC):
        return out
    pat = re.compile(r"gEventGlobal\[(\d+)\]")
    for root, _dirs, files in os.walk(MEMORIA_SRC):
        for fn in files:
            if not fn.endswith(".cs"):
                continue
            path = os.path.join(root, fn)
            try:
                text = open(path, encoding="utf-8", errors="replace").read()
            except OSError:
                continue
            for i, ln in enumerate(text.splitlines(), 1):
                for m in pat.finditer(ln):
                    out[int(m.group(1))].append(f"{os.path.relpath(path, MEMORIA_SRC)}:{i}")
    return out


# ------------------------------------------------------------------ main ---
def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--probe", type=int, nargs="*", default=None,
                    help="print full candidate rows for these bit indices (skips nothing) and exit")
    ap.add_argument("--no-mes", action="store_true", help="skip .mes text resolution (faster; txids only)")
    args = ap.parse_args()

    census_path = os.path.join(_HERE, "flag_census.json")
    if not os.path.exists(census_path):
        sys.exit("research/flag_census.json missing -- run flag_census.py first (cd ff9mapkit && "
                 "py ../research/flag_census.py)")
    census = json.load(open(census_path, encoding="utf-8"))
    bit_flags = {int(k): v for k, v in census["bit_flags"].items()}
    per_field = {int(k): v for k, v in census["per_field"].items()}

    probe_bits = set(args.probe or [])
    keep, skipped = {}, defaultdict(int)
    for bit in sorted(bit_flags):
        why = skip_reason(bit)
        if why and bit not in probe_bits:
            skipped[why.split(":")[0]] += 1
            continue
        keep[bit] = bit_flags[bit]
    if probe_bits:
        keep = {b: keep[b] for b in sorted(probe_bits) if b in keep}
        missing = probe_bits - set(keep)
        for b in sorted(missing):
            print(f"probe bit {b}: not in the census (never touched by a field .eb)")

    # which fields do we need to open? every writer/reader of a kept bit.
    need_fields = sorted({f for rec in keep.values() for f in rec["writers"] + rec["readers"]})
    print(f"bits: {len(bit_flags)} in census -> {len(keep)} kept "
          f"(skipped: {dict(skipped)}) across {len(need_fields)} fields", flush=True)

    print("loading field event bundle ...", flush=True)
    from ff9mapkit.extract import EventBundle
    bundle = EventBundle()

    # one sweep per needed field
    field_data = {}                      # fid -> (occs, wins, ops)
    for n, fid in enumerate(need_fields, 1):
        try:
            raw = bundle.eb_for_id(fid)
            if raw:
                field_data[fid] = sweep_field(EbScript.from_bytes(raw))
        except Exception as ex:                                      # noqa: BLE001
            print(f"  field {fid}: sweep failed ({ex!r})")
        if n % 100 == 0:
            print(f"  swept {n}/{len(need_fields)} fields", flush=True)

    # .mes maps, cached by text zone (many fields share a zone block)
    mes_by_zone = {}

    def mes_for(fid):
        if args.no_mes:
            return None
        zone = EVENT_ID_TO_MES.get(fid)
        if zone is None:
            return None
        if zone not in mes_by_zone:
            try:
                body = KD.extract_field_mes(str(fid), lang="us")
                mes_by_zone[zone] = KD.parse_mes(body) if body else None
            except Exception:                                        # noqa: BLE001
                mes_by_zone[zone] = None
        return mes_by_zone[zone]

    eng_reads = engine_byte_reads()
    print(f"engine tier-a byte reads found: {len(eng_reads)} distinct bytes", flush=True)

    # ---- assemble per-bit lore rows ----
    rows = {}
    for bit, rec in keep.items():
        writers, readers = [], []
        stmt_hashes = set()
        dialogue_found = False
        for fid in rec["writers"]:
            fd = field_data.get(fid)
            if fd is None:
                continue
            occs, wins, _ops = fd
            for o in occs:
                if o["bit"] != bit or o["role"] != "write":
                    continue
                stmt_hashes.add(o["stmt"])
                line = nearest_line(o, wins, mes_for(fid))
                dialogue_found |= bool(line and line["text"])
                writers.append({
                    "field": fid, "room": ROOM.get(fid, "?"), "area": area_of(fid),
                    "entry": o["entry"], "tag": o["tag"], "off": o["off"],
                    "sets_to": o["val"], "dialogue": line,
                })
        for fid in rec["readers"]:
            fd = field_data.get(fid)
            if fd is None:
                continue
            occs, wins, ops = fd
            for o in occs:
                if o["bit"] != bit or o["role"] not in ("gate", "read"):
                    continue
                readers.append({
                    "field": fid, "room": ROOM.get(fid, "?"), "area": area_of(fid),
                    "entry": o["entry"], "tag": o["tag"], "role": o["role"],
                    "guards": gate_body_summary(o, wins, ops) if o["role"] == "gate" else None,
                })

        writer_fields = sorted({w["field"] for w in writers})
        writer_areas = sorted({w["area"] for w in writers})
        reader_areas = sorted({r["area"] for r in readers})
        shared_block = (len(writer_fields) >= SHARED_BLOCK_MIN and len(stmt_hashes) == 1)
        beats = beat_names([v for f in writer_fields
                            for v in per_field.get(f, {}).get("scenario_sets", [])])
        engine = eng_reads.get(bit >> 3, [])
        has_gate_evidence = any(r.get("guards") for r in readers)

        notes = []
        if shared_block:
            notes.append("shared compiled block (one statement shape across all writers)")
        if len(writer_fields) > 1 and len(writer_areas) > 1:
            notes.append("multi-area writers")
        if not dialogue_found:
            notes.append("no dialogue in range")
        if not writers:
            notes.append("read-only in field scripts (writer may be engine/worldmap-side)")

        if engine:
            conf = "a"
        elif len(writer_fields) == 1 and (dialogue_found or has_gate_evidence) and not shared_block:
            conf = "b"
        else:
            conf = "c"

        rows[bit] = {
            "bit": bit, "byte": bit >> 3, "bit_in_byte": bit & 7,
            "region": story_region_name(bit), "confidence": conf, "notes": notes,
            "writer_areas": writer_areas, "reader_areas": reader_areas,
            "beats": beats, "engine_reads": engine[:6],
            "writers": writers, "readers": readers,
        }

    if probe_bits:
        for bit in sorted(rows):
            print(f"\n=== probe bit {bit} ===")
            print(json.dumps(rows[bit], indent=1, default=str))
        return

    # ---- write outputs ----
    n_conf = defaultdict(int)
    for r in rows.values():
        n_conf[r["confidence"]] += 1
    summary = {
        "bits_in_census": len(bit_flags), "bits_kept": len(rows), "skipped": dict(skipped),
        "confidence": dict(n_conf), "fields_swept": len(field_data),
        "dialogue_window_bytes": DIALOGUE_WINDOW,
    }
    out_json = os.path.join(_HERE, "flag_lore.json")
    with open(out_json, "w", encoding="utf-8") as fh:
        json.dump({"summary": summary, "bits": {str(b): rows[b] for b in sorted(rows)}}, fh, indent=1)
    write_digest(rows, summary)
    print(f"\n=== flag lore summary ===\n  {json.dumps(summary, indent=2)}\n  wrote {out_json}")


def _fmt_writer(w) -> str:
    to = {1: "SET", 0: "CLEARED", None: "WRITTEN"}.get(w["sets_to"], f"={w['sets_to']}")
    s = f"{to} by {w['room']} (field {w['field']})"
    if w["dialogue"] and w["dialogue"]["text"]:
        side = "after" if w["dialogue"]["delta"] < 0 else "before"
        s += f' {side} “{w["dialogue"]["text"]}”'
    elif w["dialogue"]:
        s += f" near txid {w['dialogue']['txid']}"
    return s


def _fmt_guard(r) -> str:
    g = r["guards"]
    pol = "when SET" if g.get("when_set") else "when CLEAR"
    bits = []
    if g.get("spawns"):
        bits.append(f"spawns obj {','.join(map(str, g['spawns']))}")
    if g.get("warps"):
        bits.append(f"warps to {','.join(map(str, g['warps']))}")
    if g.get("battles"):
        bits.append(f"battle {','.join(map(str, g['battles']))}")
    if g.get("says"):
        bits.append(f"says txid {','.join(map(str, g['says'][:4]))}")
    return f"{r['room']} (field {r['field']}) {pol}: {'; '.join(bits)}"


def write_digest(rows: dict, summary: dict):
    md = os.path.join(_HERE, "FLAG_LORE.md")
    by_region = defaultdict(list)
    for bit in sorted(rows):
        by_region[rows[bit]["region"] or "(unclustered)"].append(rows[bit])
    with open(md, "w", encoding="utf-8") as fh:
        w = fh.write
        w("# FF9 story-flag LORE candidates (per-bit)\n\n")
        w("> Generated by `research/gen_flag_lore.py` -- deterministic joins over real bytes; a\n"
          "> CANDIDATE table for human curation, not shipped names. Confidence: a = engine C# reads\n"
          "> the byte; b = single writer + dialogue/gate evidence; c = inference only.\n\n")
        w(f"Summary: {json.dumps(summary)}\n\n")
        for region in sorted(by_region):
            group = by_region[region]
            w(f"\n## {region}  ({len(group)} bits)\n\n")
            for r in group:
                head = f"**bit {r['bit']}** (byte {r['byte']}.{r['bit_in_byte']}) [{r['confidence']}]"
                if r["beats"]:
                    head += f"  beats: {', '.join(r['beats'][:3])}"
                w(head + "\n")
                for wr in r["writers"][:4]:
                    w(f"  - {_fmt_writer(wr)}\n")
                if len(r["writers"]) > 4:
                    w(f"  - ... +{len(r['writers']) - 4} more writers\n")
                for rd in r["readers"][:4]:
                    if rd.get("guards"):
                        w(f"  - gates: {_fmt_guard(rd)}\n")
                other = [rd for rd in r["readers"] if not rd.get("guards")]
                if other:
                    areas = sorted({o['area'] for o in other})
                    w(f"  - also read by {len(other)} site(s) in {', '.join(areas[:4])}\n")
                if r["engine_reads"]:
                    w(f"  - engine: {', '.join(r['engine_reads'][:3])}\n")
                if r["notes"]:
                    w(f"  - notes: {'; '.join(r['notes'])}\n")
                w("\n")
    print(f"  wrote {md}")


if __name__ == "__main__":
    main()
