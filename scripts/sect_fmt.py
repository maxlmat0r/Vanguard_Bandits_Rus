"""Section archives (e.g. EPICA 413 = intro/title images).
Header: pairs of LE u16 (offset/2, size/2), terminated by a pair with size 0
(its offset = end of data). Each section is a separate LZSS stream (lz.py), 2-aligned.
Files 414-418 use the same idea with u32 units of 4 (not handled here)."""
import struct
from lz import decompress

def sections(d, unit=2):
    """unit 2: u16 pairs (413); unit 4: u32 pairs (414-419)."""
    fmt = '<HH' if unit == 2 else '<II'; w = 2 * unit
    out = []; i = 0
    while True:
        off, size = struct.unpack(fmt, d[i:i+w]); i += w
        if size == 0: return out
        out.append(d[off*unit:off*unit + size*unit])

def tim_len(t):
    fl = struct.unpack('<I', t[4:8])[0]; p = 8
    if fl & 8: p += struct.unpack('<I', t[p:p+4])[0]
    return p + struct.unpack('<I', t[p:p+4])[0]

def unpack(d):
    """-> list of decompressed TIMs (trimmed to their exact length)."""
    res = []
    for s in sections(d):
        t = decompress(s); res.append(t[:tim_len(t)])
    return res

def build(comp_sections, unit=2):
    """comp_sections: list of section bytes (already compressed if needed) -> archive bytes."""
    fmt = '<HH' if unit == 2 else '<II'
    n = len(comp_sections)
    pos = 2 * unit * (n + 1); pairs = []; body = bytearray()
    for c in comp_sections:
        c = bytes(c) + bytes(-len(c) % unit)
        pairs.append((pos // unit, len(c) // unit)); body += c; pos += len(c)
    pairs.append((pos // unit, 0))
    return b''.join(struct.pack(fmt, a, s) for a, s in pairs) + bytes(body)
