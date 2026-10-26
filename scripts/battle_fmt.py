"""Battle dialogue files (EPICA.BIN 121-176): script + string table.

header u16 BE[1] = T (offset of the string table).
Table: n = first_entry/2 big-endian u16 offsets, relative to T.
String record: 3 control bytes + text (CRLF newlines) + 0x00.
Entries that point past the last string are "end" markers.
Bytes after the last referenced string (padding / unreferenced text) are kept as tail.
"""
import struct


def parse(d):
    T = struct.unpack('>H', d[2:4])[0]
    first = struct.unpack('>H', d[T:T+2])[0]
    n = first // 2
    offs = list(struct.unpack('>%dH' % n, d[T:T+first]))
    uniq = sorted(set(offs))
    last = T + uniq[-1]
    if last >= len(d) or not any(d[last:]):
        endmark = uniq[-1]; recs_at = uniq[:-1]
    else:
        endmark = None; recs_at = uniq
    recs = {}
    for i, u in enumerate(recs_at):
        a = T + u
        if i + 1 < len(recs_at): b = T + recs_at[i+1]
        elif endmark is not None: b = T + endmark
        else: b = d.index(b'\x00', a + 3) + 1
        recs[u] = d[a:b]
    tail_start = T + endmark if endmark is not None else T + recs_at[-1] + len(recs[recs_at[-1]])
    return T, offs, recs, endmark, d[tail_start:]


def strings(d):
    """-> list of (index, ctrl(3 bytes), text bytes) for every table entry with a string."""
    T, offs, recs, endmark, tail = parse(d)
    out = []
    for i, v in enumerate(offs):
        if v in recs:
            r = recs[v]
            txt = r[3:-1] if r.endswith(b'\x00') else r[3:]
            out.append((i, r[:3], txt))
    return out


def build(d, new_texts):
    """new_texts: dict table_index -> new text bytes (CRLF newlines)."""
    T, offs, recs, endmark, tail = parse(d)
    first = offs[0]
    body = bytearray(); pos = {}
    for i, v in enumerate(offs):
        if v not in recs or v in pos: continue
        r = recs[v]
        if i in new_texts: r = r[:3] + new_texts[i] + b'\x00'
        pos[v] = first + len(body)
        body += r
    end = first + len(body)
    table = [pos.get(v, end) for v in offs]
    assert end < 0x10000
    out = bytearray(d[:T]) + struct.pack('>%dH' % len(table), *table) + body + tail
    return bytes(out)
