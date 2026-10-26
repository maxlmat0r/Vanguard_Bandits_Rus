"""String tables inside section archives (EPICA 417 section 0, 419 section 3).
Layout: BE u16 offsets (count = first/2), then records. Each record starts at an offset;
text runs to the first NUL, the bytes after it (up to the next record) are kept as is.
Several table entries may share one record. ctrl = number of control bytes before the
text (1 for 417, 2 for 419 = speaker/expression codes); they are kept in the tail part."""
import struct

def parse(d, ctrl=0):
    n = struct.unpack('>H', d[:2])[0] // 2
    offs = [struct.unpack('>H', d[2*i:2*i+2])[0] for i in range(n)]
    starts = sorted(set(offs)); recs = []
    for j, a in enumerate(starts):
        end = starts[j+1] if j + 1 < len(starts) else len(d)
        t0 = min(a + ctrl, end)
        e = d.index(b'\x00', t0, end) if b'\x00' in d[t0:end] else end
        recs.append((a, d[a:t0], d[t0:e], d[e:end]))
    return offs, recs

def strings(d, ctrl=0):
    return [(i, t) for i, (a, head, t, tail) in enumerate(parse(d, ctrl)[1])]

def build(d, new, ctrl=0):
    offs, recs = parse(d, ctrl)
    n = len(offs); body = bytearray(); newpos = {}
    for i, (a, head, t, tail) in enumerate(recs):
        newpos[a] = 2*n + len(body)
        body += head + new.get(i, t) + tail
    assert 2*n + len(body) < 0x10000
    return b''.join(struct.pack('>H', newpos[o]) for o in offs) + bytes(body)
