"""Story scene files (EPICA.BIN 482-700, LZSS-compressed).

Decompressed layout: header of n little-endian u32 section offsets (hdr[0] = header size,
hdr[-1] = file length). Section 1 = text: little-endian u16 offsets (relative to the
section start, first entry = table size), then strings (LF newlines) ending in 0x00.
Rebuilding the text section shifts all later sections; the shift is kept a multiple
of 4 so 32-bit data in later sections stays aligned.
"""
import struct


def header(d):
    h0 = struct.unpack('<I', d[:4])[0]
    return list(struct.unpack('<%dI' % (h0 // 4), d[:h0]))


def is_story(d):
    try:
        h0 = struct.unpack('<I', d[:4])[0]
        if h0 % 4 or h0 < 8 or h0 > 0x100: return False
        hdr = header(d)
        if hdr[-1] != len(d) or any(hdr[i] > hdr[i+1] for i in range(len(hdr)-1)): return False
        S, E = hdr[1], hdr[2]
        first = struct.unpack('<H', d[S:S+2])[0]
        if not (0 < first and S + first <= E and first % 2 == 0): return False
        t = d[S+first:S+first+8]
        return len(t) == 8 and all(32 <= c < 127 or c == 10 for c in t)
    except Exception:
        return False


def parse(d):
    hdr = header(d)
    S, E = hdr[1], hdr[2]
    sec = d[S:E]
    first = struct.unpack('<H', sec[:2])[0]
    offs = list(struct.unpack('<%dH' % (first // 2), sec[:first]))
    uniq = sorted(set(offs))
    recs = {}
    for i, u in enumerate(uniq):
        if u >= len(sec): continue
        nxt = uniq[i+1] if i + 1 < len(uniq) else None
        if nxt is not None and nxt <= len(sec):
            recs[u] = sec[u:nxt]
        else:
            e = sec.index(b'\x00', u) + 1
            recs[u] = sec[u:e]
    last_u = max(recs) if recs else first
    tail = sec[last_u + len(recs[last_u]):] if recs else sec[first:]
    return hdr, offs, recs, tail


def strings(d):
    hdr, offs, recs, tail = parse(d)
    out = []
    for i, v in enumerate(offs):
        if v in recs:
            r = recs[v]
            out.append((i, r[:-1] if r.endswith(b'\x00') else r))
    return out


def build(d, new_texts):
    """new_texts: dict table_index -> new text bytes (LF newlines)."""
    hdr, offs, recs, tail = parse(d)
    S, E = hdr[1], hdr[2]
    first = offs[0]
    body = bytearray(); pos = {}
    for i, v in enumerate(offs):
        if v not in recs or v in pos: continue
        r = recs[v]
        if i in new_texts: r = new_texts[i] + b'\x00'
        pos[v] = first + len(body)
        body += r
    end = first + len(body)
    table = [pos.get(v, end if v >= len(d[S:E]) else v) for v in offs]
    assert max(table) < 0x10000
    sec = bytearray(struct.pack('<%dH' % len(table), *table) + body)
    # keep the original tail (padding) unless the section shrank/grew: then re-pad to 4
    if not new_texts:
        sec += tail
    else:
        while (len(sec) - (E - S)) % 4: sec.append(0)
    delta = len(sec) - (E - S)
    nh = hdr[:2] + [h + delta for h in hdr[2:]]
    out = bytearray(struct.pack('<%dI' % len(nh), *nh)) + d[len(nh)*4:S] + sec + d[E:]
    assert len(out) == nh[-1]
    return bytes(out)
