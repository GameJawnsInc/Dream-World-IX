"""C10 verification step D: an INDEPENDENT container walk + 0x80+N corpus check.

Written from a fresh reading of the native walker fn 0xd390 (@0xd3a3..0xd4cc), the
id-3 record builder (@0xd415..0xd499), the sequence fetch fn 0x315f1 (@0x31647,
3-byte records, terminator 0x00), the >=0x20 router @0x31a69 (curChunkSlot from
[0x323178]) and LOAD_CHUNK @0x31712 -> 0x30bd0 (linear search of the 2-word table
@0x32321c, whose values fn 0x3de37 @0x3e265 writes as the id-3 LOAD COUNTER).

Reads ONLY the user's own extracted files under C:/gd/SCRATCH/summon-format/.
Writes nothing. Prints counts.
"""
import glob
import os
import struct
import sys
from collections import Counter

SCRATCH = r"C:/gd/SCRATCH/summon-format"
SECTOR = 0x800


def s16(b, o):
    return struct.unpack_from("<h", b, o)[0]


def u16(b, o):
    return struct.unpack_from("<H", b, o)[0]


def s8(b, o):
    return struct.unpack_from("<b", b, o)[0]


def u32(b, o):
    return struct.unpack_from("<I", b, o)[0]


def walk(data):
    """Mirror of fn 0xd390. Returns (chunks, cursor). chunks[i] = dict."""
    n_chunks = s16(data, 0)
    p = 2
    cursor = SECTOR
    chunks = []
    for ci in range(n_chunks):
        chunk_index = u16(data, p)
        n_res = s16(data, p + 2)
        p += 4
        res = []
        for _ in range(n_res):
            rid = s8(data, p)
            info = s8(data, p + 1)
            nbytes = s16(data, p + 2) << 11
            p += 4
            off = cursor
            cursor += nbytes
            extra = 0
            if rid == 2 and info != 0:          # @0xd3ff / @0xd49f
                extra = s16(data, p) << 11
                cursor += extra
                p += 2
            res.append(dict(id=rid, info=info, off=off, size=nbytes, extra=extra))
        chunks.append(dict(index=chunk_index, ordinal=ci, res=res))
    return chunks, cursor, p


def programs(data, chunk):
    """Mirror of the id-3 arm @0xd415..0xd499: 16 relocated program offsets."""
    id3 = [r for r in chunk["res"] if r["id"] == 3]
    if not id3:
        return None
    r = id3[0]
    psx_low = (0x801E7700 + (chunk["ordinal"] & 1) * 0x5000) & 0x0FFFFFFF
    ptr = u32(data, r["off"])
    header_rel = (ptr & 0x0FFFFFFF) - psx_low
    if not (0 < header_rel < r["size"]):
        return dict(bad=True, header_rel=header_rel, n_id3=len(id3))
    tbl = r["off"] + header_rel + 8
    progs = []
    for k in range(16):                          # @0xd493 cmp rdx,0x10
        v = u32(data, tbl + 4 * k)
        progs.append(0 if v == 0 else (v & 0x0FFFFFFF) - psx_low)
    return dict(bad=False, header_rel=header_rel, progs=progs,
                n_id3=len(id3), payload=r["off"], size=r["size"],
                hdr0=u32(data, r["off"] + header_rel),
                hdr1=u32(data, r["off"] + header_rel + 4))


def sequence(data):
    """3-byte records from file offset 0x400 until code 0x00 (fn 0x315f1 @0x31647)."""
    out = []
    o = 0x400
    while o + 3 <= len(data):
        c, a1, a2 = data[o], data[o + 1], data[o + 2]
        out.append((c, a1, a2, o))
        o += 3
        if c == 0x00:
            break
    return out


def main():
    files = sorted(glob.glob(os.path.join(SCRATCH, "ef*.bytes")))
    print(f"files: {len(files)}")
    n_ok_len = 0
    n_chunks = 0
    viol_ordinal = []
    viol_field = []
    prog_live_hist = Counter()
    opcode_hist = Counter()
    seq_no_end = []
    hdr_words_nonzero = 0
    prog_out_of_code = 0
    no_loadchunk_before_prog = []
    multi_id3 = 0
    per_file = {}
    for path in files:
        name = os.path.basename(path)[:5]
        data = open(path, "rb").read()
        try:
            chunks, cursor, tbl_end = walk(data)
        except Exception as ex:
            print(f"{name}: WALK FAIL {ex}")
            continue
        if cursor == len(data):
            n_ok_len += 1
        else:
            print(f"{name}: cursor {cursor:#x} != len {len(data):#x}")
        n_chunks += len(chunks)
        pinfo = []
        for ch in chunks:
            pi = programs(data, ch)
            pinfo.append(pi)
            if pi is None:
                continue
            if pi.get("n_id3", 0) > 1:
                multi_id3 += 1
            if pi["bad"]:
                print(f"{name}: chunk {ch['ordinal']} headerRel bad {pi['header_rel']:#x}")
                continue
            if pi["hdr0"] or pi["hdr1"]:
                hdr_words_nonzero += 1
            live = [k for k, v in enumerate(pi["progs"]) if v]
            prog_live_hist[len(live)] += 1
            for v in pi["progs"]:
                if v and not (0 < v < pi["header_rel"]):
                    prog_out_of_code += 1
        seq = sequence(data)
        if not seq or seq[-1][0] != 0:
            seq_no_end.append(name)
        cur_ord = None
        cur_field = None
        for c, a1, a2, off in seq:
            opcode_hist[c] += 1
            if c == 0x05:
                cur_ord = a1
                # the alternative key: match a1 against the chunkIndex FIELD
                m = [i for i, ch in enumerate(chunks) if ch["index"] == a1]
                cur_field = m[0] if m else None
            elif c >= 0x80:
                n = c - 0x80
                o = 0 if cur_ord is None else cur_ord
                if cur_ord is None:
                    no_loadchunk_before_prog.append((name, off))
                ok_o = (o < len(chunks) and pinfo[o] and not pinfo[o]["bad"]
                        and pinfo[o]["progs"][n] != 0)
                if not ok_o:
                    viol_ordinal.append((name, off, c, o))
                f = cur_field if cur_field is not None else 0
                ok_f = (f < len(chunks) and pinfo[f] and not pinfo[f]["bad"]
                        and pinfo[f]["progs"][n] != 0)
                if not ok_f:
                    viol_field.append((name, off, c, f))
        per_file[name] = (chunks, pinfo, seq)

    print(f"cursor==filelen: {n_ok_len}/{len(files)}")
    print(f"chunks total: {n_chunks}   chunks with >1 id-3: {multi_id3}")
    print(f"sequences without END: {len(seq_no_end)} {seq_no_end[:5]}")
    print(f"id-3 header words (0,0): violations {hdr_words_nonzero}")
    print(f"live program offsets outside code region: {prog_out_of_code}")
    print(f"live-program-count histogram: {dict(sorted(prog_live_hist.items()))}")
    print(f"0x80+N VIOLATIONS keyed by TABLE ORDINAL : {len(viol_ordinal)}")
    for v in viol_ordinal[:20]:
        print("   ", v)
    print(f"0x80+N VIOLATIONS keyed by chunkIndex FIELD: {len(viol_field)}")
    for v in viol_field[:20]:
        print("   ", v)
    print(f"0x80+N before any LOAD_CHUNK: {len(no_loadchunk_before_prog)}"
          f" {no_loadchunk_before_prog[:5]}")
    hi = {hex(k): v for k, v in sorted(opcode_hist.items()) if k >= 0x80}
    print(f"0x80+ opcode histogram: {hi}")
    print(f"total opcodes: {sum(opcode_hist.values())}, distinct: {len(opcode_hist)}")

    # worked example
    for probe in ("ef431", "ef227"):
        if probe in per_file:
            chunks, pinfo, seq = per_file[probe]
            for i, pi in enumerate(pinfo):
                if pi and not pi["bad"]:
                    live = [k for k, v in enumerate(pi["progs"]) if v]
                    print(f"{probe} chunk{i} chunkIndexField={chunks[i]['index']} "
                          f"headerRel={pi['header_rel']:#x} live programs={live}")
            used = sorted({c for c, _, _, _ in seq if c >= 0x80})
            lc = [(a1) for c, a1, a2, _ in seq if c == 0x05]
            print(f"{probe} sequence 0x80+ codes used: {[hex(c) for c in used]}  "
                  f"LOAD_CHUNK args: {lc}  ops={len(seq)}")


if __name__ == "__main__":
    main()
