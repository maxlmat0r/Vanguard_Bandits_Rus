"""Battle-animation quips (EPICA files 358-409, raw).
Header: BE u16 offsets (count = first/2). Record: 1 control byte + text (CRLF) + 00,
usually followed by one padding 00 (not always)."""
import struct

def strings(d):
    n = struct.unpack('>H', d[:2])[0] // 2
    offs = [struct.unpack('>H', d[2*i:2*i+2])[0] for i in range(n)]
    out = []
    for i, a in enumerate(offs):
        e = d.index(b'\x00', a + 1)
        out.append((i, d[a], d[a+1:e]))
    return out

def build(d, new_texts):
    """new_texts: {index: bytes}. Rebuilds the whole file."""
    recs = strings(d)
    n = len(recs)
    body = bytearray(); offs = []
    for i, ctrl, t in recs:
        offs.append(2*n + len(body))
        body += bytes([ctrl]) + new_texts.get(i, t) + b'\x00\x00'
    assert 2*n + len(body) < 0x10000
    return b''.join(struct.pack('>H', o) for o in offs) + bytes(body)
