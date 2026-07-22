"""
GAP probe 3: determine whether FMV000.bytes carries its own audio (Vorbis) track
alongside the Theora video, or is video-only (title music played separately as
the sound-bank entry music033).

FMV000.bytes is an Ogg container. Each Ogg logical bitstream is identified by the
codec-id string in the first page of each serial number:
  - Theora video  -> page begins with 0x80 'theora'
  - Vorbis audio  -> page begins with 0x01 'vorbis'
We scan Ogg pages (capture pattern 'OggS'), collect distinct serial numbers, and
record the codec header seen on each stream's BOS (beginning-of-stream) page.

READ-ONLY. Run: py probe_fmv000_streams.py
"""
import struct

FMV = r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX\StreamingAssets\ma\FMV000.bytes"

with open(FMV, "rb") as f:
    data = f.read()

print("file size:", len(data))
print("first 4 bytes:", data[:4])

streams = {}   # serial -> codec string
order = []
pos = 0
pages = 0
scan_limit = min(len(data), 2_000_000)  # header/BOS pages are all near the front
while pos < scan_limit:
    idx = data.find(b"OggS", pos)
    if idx < 0:
        break
    # Ogg page header: 'OggS'(4) ver(1) htype(1) granulepos(8) serial(4) seq(4) crc(4) nsegs(1)
    if idx + 27 > len(data):
        break
    htype = data[idx+5]
    serial = struct.unpack_from("<I", data, idx+14)[0]
    nsegs = data[idx+26]
    seg_table = data[idx+27: idx+27+nsegs]
    body = idx + 27 + nsegs
    payload = data[body: body+64]
    pages += 1
    if serial not in streams:
        # BOS page: record codec signature from payload
        codec = "?"
        if payload[:7] == b"\x80theora":
            codec = "theora (VIDEO)"
        elif payload[:7] == b"\x01vorbis":
            codec = "vorbis (AUDIO)"
        elif payload[1:7] == b"theora":
            codec = "theora (VIDEO)"
        elif payload[1:7] == b"vorbis":
            codec = "vorbis (AUDIO)"
        else:
            codec = "unknown hdr=" + payload[:8].hex()
        streams[serial] = codec
        order.append(serial)
    pos = body
    if pages > 5000:
        break

print("pages scanned:", pages)
print("distinct logical streams:", len(streams))
for s in order:
    print(f"  serial={s} codec={streams[s]}")

has_vorbis = any("vorbis" in c for c in streams.values())
has_theora = any("theora" in c for c in streams.values())
print("\nVERDICT:")
print("  contains THEORA video stream:", has_theora)
print("  contains VORBIS audio stream:", has_vorbis)
if has_vorbis:
    print("  => FMV000.bytes CARRIES its own audio track.")
else:
    print("  => FMV000.bytes is VIDEO-ONLY; title music is separate (music033).")
