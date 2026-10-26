"""Build patched EPICA.BIN + SLUS_010.70 from clean originals.

Usage: python3 -I scripts/build.py <VBE_work dir>
Reads  orig/EPICA.BIN, orig/SLUS_010.70, texts/*/*.json, assets/*
Writes extracted/EPICA.BIN, extracted/SLUS_010.70 (then run mkpsxiso).
"""
import sys, os, struct, json, glob
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from lz import decompress, compress
from cyr_glyphs import G, CHARMAP, encode, SMALL, SMALL_FROM_LATIN, CAPS_AS_LOWER
import battle_fmt, story_fmt, quip_fmt, sect_fmt, strtab_fmt, texts

W = sys.argv[1]
epica = bytearray(open(f'{W}/orig/EPICA.BIN', 'rb').read())
exe = bytearray(open(f'{W}/orig/SLUS_010.70', 'rb').read())
ORIG_ENTRIES = [struct.unpack('<II', epica[k*8:k*8+8]) for k in range(704)]

def ram2file(a): return a - 0x80010000 + 0x800

def entry(k):
    return struct.unpack('<II', epica[k*8:k*8+8])

def set_entry(k, off, size):
    epica[k*8:k*8+8] = struct.pack('<II', off, size)

def slot_size(k):
    """Space the original layout reserved for file k (up to the next file)."""
    o = ORIG_ENTRIES[k][0]
    nxt = min((off for off, sz in ORIG_ENTRIES if off > o), default=len(epica))
    return nxt - o

def append_file(k, data):
    end = (len(epica) + 0x7ff) & ~0x7ff
    epica.extend(bytes(end - len(epica)))
    epica.extend(data)
    epica.extend(bytes(((len(epica) + 0x7ff) & ~0x7ff) - len(epica)))
    set_entry(k, end, len(data))

def place_file(k, data):
    """Write file k back in its own slot if it fits, otherwise move it to the end."""
    o = ORIG_ENTRIES[k][0]; slot = slot_size(k)
    if len(data) <= slot:
        epica[o:o+slot] = data + bytes(slot - len(data))
        set_entry(k, o, len(data))
        return False
    append_file(k, data)
    return True

# ---------------------------------------------------------------- font
OLD_W, NEW_W = 168, 248           # pixels (4bpp); 208-247 = small Cyrillic + copy of file 10
SMALL_OLD, SMALL_NEW = 0x70, 0x98  # u offset of the small font

def build_font():
    o, s = entry(7)
    d = epica[o:o+s]
    clut_len = struct.unpack('<I', d[8:12])[0]
    clut_block = d[8:8+clut_len]
    p = 8 + clut_len
    _, x, y, wh, h = struct.unpack('<IHHHH', d[p:p+12])
    assert (x, y, wh, h) == (960, 256, 42, 256)
    px = d[p+12:p+12+wh*2*h]
    old = [[(px[r*OLD_W//2 + c//2] >> (4*(c & 1))) & 15 for c in range(OLD_W)] for r in range(h)]
    new = [[0]*NEW_W for _ in range(h)]
    for r in range(h):
        for c in range(SMALL_OLD):                 # main font, columns 0-6
            new[r][c] = old[r][c]
        for c in range(SMALL_OLD, OLD_W):          # small font -> shifted right
            new[r][c - SMALL_OLD + SMALL_NEW] = old[r][c]
    widths = {}
    for ch, (top, rows) in G.items():
        if ch in CAPS_AS_LOWER: continue
        code = CHARMAP[ch]
        glyph = code - 0x20 if code < 0x80 else code - 0x40
        u, v = 16*(glyph // 16), 15*(glyph % 16)
        for rr in range(15):                       # clear cell
            for cc in range(16): new[v+rr][u+cc] = 0
        stroke = set()
        for ry, line in enumerate(rows):
            for cx, ch2 in enumerate(line):
                if ch2 == '#': stroke.add((cx, top+ry))
        for (cx, cy) in stroke:
            new[v+cy][u+cx] = 1
        for (cx, cy) in stroke:                    # shadow (+1,+1)
            if (cx+1, cy+1) not in stroke and cx+1 < 16 and cy+1 < 15:
                new[v+cy+1][u+cx+1] = 2
        widths[glyph] = max(cx for cx, _ in stroke) + 1
    # copy of EPICA file 10 (4bpp 8x96 at VRAM 1012,256) - our wider TIM covers it
    o10, s10 = entry(10); d10 = epica[o10:o10+s10]
    p10 = 8 + struct.unpack('<I', d10[8:12])[0]
    _, x10, y10, w10, h10 = struct.unpack('<IHHHH', d10[p10:p10+12])
    assert (x10, y10, w10, h10) == (1012, 256, 8, 96)
    px10 = d10[p10+12:p10+12+w10*2*h10]
    for r in range(h10):
        for c in range(w10*4):
            new[r][208 + c] = (px10[r*w10*2 + c//2] >> (4*(c & 1))) & 15
    # small-font Cyrillic
    old_small_w = exe[ram2file(0x80064ac0):ram2file(0x80064ac0)+0x70]
    for ch in list(G):
        if ch in CAPS_AS_LOWER: continue
        code = CHARMAP[ch]
        gl = code - 0x20 if code < 0x80 else code - 0x40
        if gl < 0x70: u, v = SMALL_NEW + 8*(gl // 16), 16*(gl % 16)
        else: u, v = 208 + 8*((gl - 0x70) >> 3), 16*(8 + ((gl - 0x70) & 7))
        for rr in range(16):
            for cc in range(8): new[v+rr][u+cc] = 0
        if ch in SMALL_FROM_LATIN:
            lg = ord(SMALL_FROM_LATIN[ch]) - 32
            lu, lv = SMALL_OLD + 8*(lg // 16), 16*(lg % 16)
            for rr in range(16):
                for cc in range(8): new[v+rr][u+cc] = old[lv+rr][lu+cc]
            SMALL_WIDTHS[gl] = old_small_w[lg]
            continue
        top, rows = SMALL[ch]
        stroke = {(cx, top+ry) for ry, line in enumerate(rows) for cx, c2 in enumerate(line) if c2 == '#'}
        for (cx, cy) in stroke: new[v+cy][u+cx] = 1
        for (cx, cy) in stroke:
            if (cx+1, cy+1) not in stroke and cx+1 < 8 and cy+1 < 16 and new[v+cy+1][u+cx+1] == 0:
                new[v+cy+1][u+cx+1] = 2
        SMALL_WIDTHS[gl] = max(cx for cx, _ in stroke) + 1
    out = bytearray()
    for r in range(h):
        for c in range(0, NEW_W, 2):
            out.append(new[r][c] | (new[r][c+1] << 4))
    nw = NEW_W // 4
    tim = struct.pack('<II', 0x10, 8) + clut_block + struct.pack('<IHHHH', 12 + len(out), 960, 256, nw, h) + out
    append_file(7, tim)                            # bigger than its slot
    return widths

# ---------------------------------------------------------------- exe
NEW_TABLE = 0x80010158     # over the debug-menu text "<SELECT PROCESS>..."
SMALL_WIDTHS = {}
CAVE = 0x80011200          # small-font Cyrillic code cave (end of the UI string pool)
SMALL_TABLE = 0x80011250   # relocated small-font width table, 0x90 bytes

R = dict(ra=31, zero=0, at=1, v0=2, v1=3, a0=4, a1=5, a2=6, a3=7, t0=8, t1=9, s5=21, t8=24, t9=25, fp=30)
def I(rs, rt, imm, op): return (op << 26) | (R[rs] << 21) | (R[rt] << 16) | (imm & 0xffff)
def addiu(rt, rs, imm): return I(rs, rt, imm, 9)
def andi(rt, rs, imm): return I(rs, rt, imm, 12)
def sltiu(rt, rs, imm): return I(rs, rt, imm, 11)
def lbu(rt, off, rs): return I(rs, rt, off, 36)
def addu(rd, rs, rt): return (R[rs] << 21) | (R[rt] << 16) | (R[rd] << 11) | 0x21
def srl(rd, rt, sa): return (R[rt] << 16) | (R[rd] << 11) | (sa << 6) | 0x02
def sll(rd, rt, sa): return (R[rt] << 16) | (R[rd] << 11) | (sa << 6) | 0x00
def bne(rs, rt, off): return I(rs, rt, off, 5)
def j(target): return (2 << 26) | ((target >> 2) & 0x3ffffff)
def jal(target): return (3 << 26) | ((target >> 2) & 0x3ffffff)
def jr(rs): return (R[rs] << 21) | 0x08
NOP = 0

def small_font_cave():
    # replaces the small-font branch of the single-byte glyph path (0x800310bc..0x800310d0):
    # loads width from the relocated table, and for glyphs >= 0x70 remaps them into the
    # Cyrillic block at u=208+8*q, v=16*(8+r)  (q,r = (g-0x70)>>3, (g-0x70)&7)
    return [addiu('a3', 'zero', 8), addiu('t0', 'zero', 0x10), addu('a0', 't0', 'zero'),
            andi('v0', 'v1', 0xffff), addu('v0', 'v0', 's5'), lbu('a2', 0, 'v0'),
            sltiu('at', 'v1', 0x70), bne('at', 'zero', 8), NOP,
            addiu('t9', 'v1', -0x70), srl('t8', 't9', 3), sll('t8', 't8', 4),
            andi('t9', 't9', 7), addu('t8', 't8', 't9'), addiu('v1', 't8', 8),
            addiu('t1', 'zero', 208),
            j(0x800310d4), NOP]

def put32(addr, val, expect=None):
    f = ram2file(addr)
    if expect is not None:
        cur = struct.unpack('<I', exe[f:f+4])[0]
        assert cur == expect, (hex(addr), hex(cur), hex(expect))
    exe[f:f+4] = struct.pack('<I', val)

def patch_exe(widths):
    old_tab = exe[ram2file(0x80064a4c):ram2file(0x80064a4c)+0x70]
    tab = bytearray(old_tab) + bytes(0x20)          # glyphs 0x00-0x8F
    for gl, wv in widths.items(): tab[gl] = wv
    f = ram2file(NEW_TABLE)
    assert exe[f:f+17] == b'\n<SELECT PROCESS>' and exe.find(b'EXIT', f) > f + len(tab), exe[f:f+17]
    exe[f:f+len(tab)] = tab
    WIDTHS[:] = tab
    lo = NEW_TABLE & 0xffff
    put32(0x80030d10, 0x3c178001, 0x3c178006)               # lui   s7,0x8001
    put32(0x80030d14, 0x26f60000 | lo, 0x26f64a4c)          # addiu s6,s7,lo
    put32(0x800312a8, 0x92e30000 | lo, 0x92e34a4c)          # lbu   v1,lo(s7)
    for a in (0x80030e00, 0x80030f60, 0x8003109c, 0x800311a0,
              0x80031990, 0x800319d0, 0x80031a10, 0x80031a50):
        put32(a, 0x24090000 | SMALL_NEW, 0x24090000 | SMALL_OLD)  # addiu t1,zero,..
    # small font: relocated width table + Cyrillic remap cave
    st = bytearray(exe[ram2file(0x80064ac0):ram2file(0x80064ac0)+0x70]) + bytes(0x20)
    for gl, wv in SMALL_WIDTHS.items(): st[gl] = wv
    f = ram2file(SMALL_TABLE); exe[f:f+len(st)] = st
    slo = SMALL_TABLE & 0xffff
    put32(0x80030d18, 0x3c1e8001, 0x3c1e8006)               # lui   fp,0x8001
    put32(0x80030d1c, 0x27d50000 | slo, 0x27d54ac0)         # addiu s5,fp,slo
    put32(0x800312b4, 0x93c30000 | slo, 0x93c34ac0)         # lbu   v1,slo(fp)
    cave = small_font_cave(); assert CAVE + 4*len(cave) <= SMALL_TABLE
    for k, w in enumerate(cave): put32(CAVE + 4*k, w)
    put32(0x800310bc, j(CAVE), 0x24070008)                  # was addiu a3,zero,8
    put32(0x800310c0, NOP, 0x24080010)                      # was addiu t0,zero,0x10

# ---------------------------------------------------------------- 8x8 memcard font
# Memory-card screen text (renderer 0x80029868) uses its own uppercase 8x8 font:
# EPICA file 8 (LZ TIM at VRAM 896,0, 4bpp, 200 rows, no free cells), cell n at
# u=8*(n&31), v=0xb0+8*(n>>5). Rows below the TIM hold battle portraits, so instead of
# adding rows we redraw rarely used symbol cells with Cyrillic. Codes 0x60-0xCF go through
# a lookup table (TABLE8, tail of the UI string pool); the cave sits in the dead debug-menu
# text after the main width table. NOTE: 0x80064a4c/0x80064ac0 (old width tables) are
# still used by the battle-animation module (EPICA file 1) - never reuse them.
# Letters without a cell (Щ Ъ Ю... see CELLS8) show as '?'.
CAVE8 = 0x800101e8
TABLE8 = 0x8001116c
T8LO = 0x3c                # TABLE8 covers codes T8LO..0xCF
# Battle UI draws '%' '^' '+' etc. with this same font, so no cell may be redrawn:
# memcard hints are written with letters that have Latin look-alikes (ОК, ОТМЕНА, СНОВА,
# КАРТА); the table maps А К М Н (own codes) to the Latin cells.
# Cells 0x1B-0x1F of row 0 are unused placeholder boxes: they may hold extra letters.
# Symbol cells @ [ \ ] _ are reached only through TABLE8 (codes >= 0x40) and no displayed
# string uses them as symbols, so they hold letters too. '^' stays (terrain box uses it).
CELLS8 = {'П': 0x1B, 'И': 0x1C, 'Ф': 0x1D, 'Д': 0x1E, 'Ч': 0x1F,
          'Ц': 0x40, 'Я': 0x5B, 'Б': 0x5C, 'Л': 0x5D, 'Ы': 0x5F}
ART8 = {
 'Б': ['#####', '#....', '####.', '#...#', '####.'],
 'Г': ['#####', '#....', '#....', '#....', '#....'],
 'Д': ['.###.', '.#.#.', '.#.#.', '.#.#.', '#####'],
 'Ж': ['#.#.#', '#.#.#', '.###.', '#.#.#', '#.#.#'],
 'З': ['####.', '....#', '.###.', '....#', '####.'],
 'И': ['#...#', '#..##', '#.#.#', '##..#', '#...#'],
 'Й': ['.###.', '#..##', '#.#.#', '##..#', '#...#'],
 'Л': ['.####', '.#..#', '.#..#', '.#..#', '#...#'],
 'П': ['#####', '#...#', '#...#', '#...#', '#...#'],
 'Ф': ['.###.', '#.#.#', '#.#.#', '.###.', '..#..'],
 'Ц': ['#..#.', '#..#.', '#..#.', '#####', '....#'],
 'Ч': ['#...#', '#...#', '.####', '....#', '....#'],
 'Ш': ['#.#.#', '#.#.#', '#.#.#', '#.#.#', '#####'],
 'Щ': ['#.#.#', '#.#.#', '#.#.#', '#####', '....#'],
 'Ю': ['#..#.', '#.#.#', '###.#', '#.#.#', '#..#.'],
 'Ы': ['#...#', '#...#', '###.#', '#.#.#', '###.#'],
 'Ь': ['#....', '#....', '####.', '#...#', '####.'],
 'Э': ['####.', '....#', '.####', '....#', '####.'],
 'Я': ['.####', '#...#', '.####', '.#..#', '#...#'],
 'У': ['#...#', '#...#', '.####', '....#', '####.'],
}
COPY8 = {'А': 'A', 'К': 'K', 'М': 'M', 'Н': 'H', 'В': 'B', 'Т': 'T', 'Е': 'E', 'О': 'O',
         'Р': 'P', 'С': 'C', 'Х': 'X'}

def table8():
    t = bytearray(c if c < 0x61 else c - 0x20 for c in range(T8LO, 0xd0))
    for ch, code in CHARMAP.items():
        if not ('А' <= ch <= 'я' or ch in 'Ёё'): continue
        if chr(code).isascii() and chr(code).isalpha() and ch.upper() not in ('У',):
            continue                                         # Latin homoglyph
        up = ch.upper()
        if code < 0x60:                                      # slot codes: own cell or the symbol
            if up in CELLS8: t[code - T8LO] = CELLS8[up]
            continue
        t[code - T8LO] = CELLS8.get(up) or (ord(COPY8[up]) if up in COPY8 else 0x3f)
    return t

def build_font8():
    o, s = entry(8)
    d = bytearray(decompress(bytes(epica[o:o+s])))
    cl = struct.unpack('<I', d[8:12])[0]; p = 8 + cl
    L, x, y, wh, h = struct.unpack('<IHHHH', d[p:p+12])
    assert (x, y, wh, h) == (896, 0, 64, 200) and len(d) == p + L
    W8 = wh * 4
    def setpx(c, r, val):
        i = p + 12 + r*W8//2 + c//2
        d[i] = (d[i] & (0xf0 if c & 1 == 0 else 0x0f)) | (val << (4*(c & 1)))
    for up, n in CELLS8.items():
        u, v = 8*(n & 31), 0xb0 + 8*(n >> 5)
        stroke = {(1+cx, 1+cy) for cy, line in enumerate(ART8[up]) for cx, c2 in enumerate(line) if c2 == '#'}
        for r in range(8):
            for c in range(8):
                if (c, r) in stroke: val = 8
                elif any((c+dx, r+dy) in stroke for dx in (-1, 0, 1) for dy in (-1, 0, 1)): val = 7
                else: val = 0
                setpx(u+c, v+r, val)
    for line in open(f'{W}/assets/f8_patch.txt'):        # graphic text, see scripts/gen_ui8.py
        x_, y_, v_ = map(int, line.split()[:3]); setpx(x_, y_, v_)
    place_file(8, compress_fixed(bytes(d)))

def beq(rs, rt, off): return I(rs, rt, off, 4)
def lui(rt, imm): return I('zero', rt, imm, 15)

def patch_font8_exe():
    # replaces 0x80029cdc..0x80029ce8 (slti/bnez/nop/addiu a2,a2,-0x20) with jal CAVE8
    # (same 4 instructions exist in the copies inside modules 0 and 1, see MOD_PATCHES):
    #   c < T8LO: unchanged;  c >= 0xD0: c-0x20 (as before);  else cell = TABLE8[c-T8LO]
    # The callers saved ra on the stack, so clobbering it with jal is safe.
    A = TABLE8 - T8LO; hi = (A + 0x8000) >> 16 & 0xffff; lo = A & 0xffff
    cave = [sltiu('v0', 'a2', T8LO), bne('v0', 'zero', 8), sltiu('v0', 'a2', 0xd0),
            beq('v0', 'zero', 4), lui('v0', hi), addu('v0', 'v0', 'a2'),
            jr('ra'), lbu('a2', lo, 'v0'),
            jr('ra'), addiu('a2', 'a2', -0x20),
            jr('ra'), NOP]
    t = table8()
    assert len(cave) == 12 and CAVE8 + 48 <= 0x80010226 and TABLE8 + len(t) <= CAVE
    assert NEW_TABLE + 0x90 <= CAVE8
    for k, w in enumerate(cave): put32(CAVE8 + 4*k, w)
    f = ram2file(TABLE8); exe[f:f+len(t)] = t
    for a, w in font8_site(0x80029cdc): put32(a, w[0], w[1])

def font8_site(a):
    return [(a, (jal(CAVE8), 0x28c20061)), (a+4, (NOP, 0x14400002)),
            (a+8, (NOP, 0)), (a+12, (NOP, 0x24c6ffe0))]

# ---------------------------------------------------------------- code modules
# EPICA files 0 (field/shop/status), 1 (battle UI), 2 (title/extras) are overlays loaded at
# 0x800751a8. RAM after the biggest one (file 1, ends 0x800a5ffe) is free up to the heap
# at 0x800b0000, so modules may grow a little.
MOD_BASE = 0x800751a8
MOD_END = 0x800b0000
MOD_PATCHES = {
    0: font8_site(0x80076f24),
    1: font8_site(0x80092598) + [
        # battle-animation text renderer (quips): Cyrillic needs the relocated width tables
        (0x800a488c, (0x3c038001, 0x26634a4c)),     # lui v1,0x8001     (was addiu v1,s3,0x4a4c)
        (0x800a4894, (0x90460158, 0x90460000)),     # lbu a2,0x158(v0)  -> NEW_TABLE
        (0x800a48b0, (0x3c028001, 0x3c028006)),     # lui v0,0x8001
        (0x800a48b4, (0x24421250, 0x24424ac0)),     # addiu v0,v0,0x1250 -> SMALL_TABLE
        (0x800a4588, (0x24090098, 0x24090070)),     # small font u 0x70 -> 0x98
        (0x800a46ec, (0x24090098, 0x24090070)),
        (0x800a482c, (0x240a0098, 0x240a0070)),
        (0x800a4878, (0x240a0098, 0x240a0070)),
        # dark smudge under the terrain name (POLY_FT4 x 0..88): Russian names are longer
        (0x800820d4, (0x24030078, 0x24030058)),     # addiu v1,zero,120 (right edge)
    ],
}
# debug-only strings whose bytes may hold relocated text
MOD_DEAD = {
    0: [0x80075e98, 0x80075eb4, 0x80075ed0],
    1: [0x800751d8, 0x80075358, 0x80075368, 0x8007537c, 0x80075388, 0x80075964,
        0x80075bbc, 0x80075bfc],
    2: [0x80075664, 0x800756a0],
}

def hi16(a): return (a + 0x8000) >> 16

def MOD_BYTES():
    # title menu highlight bars (x, width per item), generated with assets/t413_4.tim
    menu = bytes(int(v) for v in open(f'{W}/assets/t413_menu.txt').read().split())
    return {2: [(0x8007a0f4, (menu, bytes([144, 36, 146, 32, 137, 50])))]}

# ---------------------------------------------------------------- title screen images
def patch_title():
    """EPICA 413 (intro/title images): section 2 = title screen with the credit line,
    section 4 = START/LOAD/OPTIONS menu. Replacements come from scripts/gen_title.py."""
    o, s = ORIG_ENTRIES[413]
    raw = bytes(open(f'{W}/orig/EPICA.BIN', 'rb').read()[o:o+s])
    secs = sect_fmt.sections(raw)
    for n in (2, 4):
        tim = open(f'{W}/assets/t413_{n}.tim', 'rb').read()
        assert len(tim) == len(sect_fmt.unpack(raw)[n])
        secs[n] = compress_fixed(tim)
    place_file(413, sect_fmt.build(secs))
    # EPICA 420 = GAME OVER screen (whole file is one LZ TIM), see scripts/gen_gameover.py
    o, s = ORIG_ENTRIES[420]
    old = decompress(bytes(open(f'{W}/orig/EPICA.BIN', 'rb').read()[o:o+s]))
    tim = open(f'{W}/assets/f420.tim', 'rb').read()
    assert len(tim) == len(old), (len(tim), len(old))
    place_file(420, compress_fixed(tim))

def patch_modules():
    total = 0
    for k in (0, 1, 2):
        o, s = ORIG_ENTRIES[k]
        d = bytearray(open(f'{W}/orig/EPICA.BIN', 'rb').read()[o:o+s])
        def w32(a, v=None):
            f = a - MOD_BASE
            if v is None: return struct.unpack('<I', d[f:f+4])[0]
            d[f:f+4] = struct.pack('<I', v)
        for a, (new, expect) in MOD_PATCHES.get(k, []):
            assert w32(a) == expect, (k, hex(a), hex(w32(a)), hex(expect))
            w32(a, new)
        for a, (new, expect) in MOD_BYTES().get(k, []):
            f = a - MOD_BASE; assert d[f:f+len(expect)] == expect, (k, hex(a)); d[f:f+len(new)] = new
        path = texts.path(f'm{k}', W)
        if not os.path.exists(path): continue
        lines = json.load(open(path, encoding='utf-8'))['lines']
        byaddr = {int(l['addr'], 16): l for l in lines}
        free = []
        for a in MOD_DEAD.get(k, []):
            l = byaddr[a]; f = a - MOD_BASE
            d[f:f+l['room']] = bytes(l['room']); free.append([a, a + l['room']])
        tail = bytearray(); n = 0; moves = []
        for l in lines:
            if not l['ru']: continue
            a = int(l['addr'], 16); f = a - MOD_BASE
            assert a not in MOD_DEAD.get(k, []) and not l['tail'], l
            assert not any(a < b < a + l['room'] for b in byaddr), ('string has a shared tail', l)
            enc = encode(l['ru'])
            if len(enc) + 1 <= l['room']:
                d[f:f+l['room']] = enc + bytes(l['room'] - len(enc)); n += 1
            else:
                moves.append((l, a, enc))
        moves.sort(key=lambda m: (not m[0]['refs'], -len(m[2])))   # code refs first, biggest first
        for l, a, enc in moves:
            need = len(enc) + 1
            if l['refs']:                          # code refs: lo half only, stay in the same 64K
                cand = [fr for fr in free if fr[1] - fr[0] >= need and hi16(fr[0]) == hi16(a)]
                assert cand, ('no room near', k, l['id'], l['ru'])
                fr = min(cand, key=lambda fr: fr[1] - fr[0])
                new = fr[0]; fr[0] += need
            else:                                  # pointer refs only: append to the module
                new = MOD_BASE + len(d) + len(tail)
                tail += enc + b'\x00'
            nf = new - MOD_BASE
            if nf < len(d): d[nf:nf+need] = enc + b'\x00'
            for r in l['refs']:
                w = w32(int(r, 16)); assert w & 0xffff == a & 0xffff, (k, l['id'], r)
                w32(int(r, 16), (w & 0xffff0000) | (new & 0xffff))
            for p in l['ptrs']:
                assert w32(int(p, 16)) == a; w32(int(p, 16), new)
            n += 1
        while len(tail) % 4: tail.append(0)
        d += tail
        assert MOD_BASE + len(d) <= MOD_END, (k, hex(MOD_BASE + len(d)))
        place_file(k, bytes(d)); total += n
        print(f'module {k}: {n} strings, +{len(tail)} bytes appended')
    return total

# ---------------------------------------------------------------- text
WIDTHS = bytearray()   # final width table (glyph -> px), filled by patch_exe
MAX_PX = 238           # text area when the portrait is on the right (measured in-game)

def glyph_of(c):
    return c - 0x20 if c < 0x80 else c - 0x40

def line_px(line):
    return sum(WIDTHS[glyph_of(c)] + 1 for c in line if c >= 0x20)

def check_width(where, encoded):
    errors = []
    for seg in encoded.replace(b'\x00', b'\n').split(b'\n'):
        if seg.endswith(b':') and line_px(seg) < MAX_PX: continue   # speaker name
        px = line_px(seg)
        if px > MAX_PX:
            errors.append(f'{where}: {px}px > {MAX_PX}px')
    return errors

def compress_fixed(d):
    c = bytearray(compress(d))
    i = 0; last = 0; nb = 0
    while i < len(c):                       # mark unused bits of the last flag byte
        last = i; fl = c[i]; i += 1; nb = 0
        for bit in range(8):
            if i >= len(c): break
            i += 2 if fl >> bit & 1 else 1; nb += 1
    for bit in range(nb, 8): c[last] |= 1 << bit
    assert decompress(bytes(c)) == d
    return bytes(c)

# ---------------------------------------------------------------- location titles
LOCTITLES = {}      # story file -> 3072 bytes of 4bpp pixels (scripts/gen_loctitles.py)
LOCDONE = set()
def load_loctitles():
    a = open(f'{W}/assets/loctitles.bin', 'rb').read()
    for i in range(0, len(a), 3074):
        LOCTITLES[struct.unpack('<H', a[i:i+2])[0]] = a[i+2:i+3074]

def patch_loctitle(k, d):
    """Story files 648-700: section 6 = title over the battle map (clut 32 B + 256x24 4bpp)."""
    if k not in LOCTITLES: return d
    n = struct.unpack('<I', d[:4])[0] // 4
    offs = struct.unpack('<%dI' % n, d[:4*n])
    a, e = offs[6], offs[7]
    assert e - a == 3104, (k, e - a)
    d = bytearray(d); d[a+32:a+3104] = LOCTITLES[k]
    return bytes(d)

def remaining_loctitles():
    for k in sorted(set(LOCTITLES) - LOCDONE):
        o, s = entry(k)
        place_file(k, compress_fixed(patch_loctitle(k, decompress(bytes(epica[o:o+s])))))

def apply_translations():
    errors = []; done = 0; moved = []
    for path in texts.all_files(W):
        js = json.load(open(path, encoding='utf-8'))
        if js.get('kind') not in ('battle', 'story', 'quip', 'strtab'): continue
        lines = [l for l in js['lines'] if l.get('ru')]
        if not lines: continue
        k = js['file']; name = os.path.basename(path)
        new = {}
        for l in lines:
            try:
                enc = encode(l['ru'])
            except ValueError as ex:
                errors.append(f'{name} #{l["id"]}: {ex}'); continue
            if js['kind'] not in ('quip', 'strtab'): errors += check_width(f'{name} #{l["id"]}', enc)
            new[l['id']] = enc
        o, s = entry(k)
        if js['kind'] == 'battle':
            new = {i: t.replace(b'\n', b'\r\n') for i, t in new.items()}
            data = battle_fmt.build(bytes(epica[o:o+s]), new)
        elif js['kind'] == 'strtab':
            raw = bytes(epica[o:o+s]); secs = sect_fmt.sections(raw, 4)
            nl = b'\r\n' if b'\r\n' in secs[js['section']] else b'\n'
            new = {i: t.replace(b'\n', nl) for i, t in new.items()}
            secs[js['section']] = strtab_fmt.build(secs[js['section']], new, js['ctrl'])
            data = sect_fmt.build(secs, 4)
        elif js['kind'] == 'quip':
            new = {i: t.replace(b'\n', b'\r\n') for i, t in new.items()}
            data = quip_fmt.build(bytes(epica[o:o+s]), new)
        else:
            d = story_fmt.build(decompress(bytes(epica[o:o+s])), new)
            d = patch_loctitle(k, d); LOCDONE.add(k)
            data = compress_fixed(d)
        if place_file(k, data): moved.append(k)
        done += len(new)
    return done, moved, errors

# ---------------------------------------------------------------- exe UI strings
POOL = (0x800102e0, 0x8001116c)   # then TABLE8, small-font cave, small width table

def patch_exe_strings():
    path = texts.path('exe_ui', W)
    if not os.path.exists(path): return 0
    lines = [l for l in json.load(open(path, encoding='utf-8'))['lines'] if l['ru']]
    pool = bytearray(); placed = {}; moved = {}
    for l in lines:
        enc = encode(l['ru']); a = int(l['addr'], 16); f = ram2file(a)
        if l['mode'] == 'inplace':
            end = f + len(l['en'])
            while exe[end + 1] == 0: end += 1
            assert len(enc) <= end - f, (l['id'], l['ru'])
            exe[f:f + len(l['en'])] = bytes(len(l['en']))
            exe[f:f + len(enc)] = enc
        else:
            if enc not in placed:
                placed[enc] = POOL[0] + len(pool); pool += enc + b'\x00'
            moved[a] = placed[enc]
    assert POOL[0] + len(pool) <= POOL[1], ('pool overflow', len(pool))
    # untranslated pointer strings must survive: copy them into the pool too
    js = json.load(open(path, encoding='utf-8'))['lines']
    for l in js:
        a = int(l['addr'], 16)
        if l['mode'] == 'ptr' and a not in moved and POOL[0] <= a < POOL[1]:
            enc = l['en'].encode()
            if enc not in placed:
                placed[enc] = POOL[0] + len(pool); pool += enc + b'\x00'
            moved[a] = placed[enc]
    assert POOL[0] + len(pool) <= POOL[1], ('pool overflow', len(pool))
    fp = ram2file(POOL[0])
    exe[fp:ram2file(POOL[1])] = bytes(POOL[1] - POOL[0])
    exe[fp:fp + len(pool)] = pool
    n = 0
    for i in range(0, len(exe) - 3, 4):
        v = struct.unpack('<I', exe[i:i+4])[0]
        if v in moved:
            exe[i:i+4] = struct.pack('<I', moved[v]); n += 1
    print(f'exe UI: {len(lines)} strings, pool {len(pool)}/{POOL[1]-POOL[0]} bytes, {n} pointers updated')
    return len(lines)

if __name__ == '__main__':
    widths = build_font()
    patch_exe(widths)
    patch_exe_strings()
    build_font8(); patch_font8_exe()
    patch_modules()
    patch_title()
    load_loctitles()
    done, moved, errors = apply_translations()
    remaining_loctitles()
    if errors:
        print('ERRORS:'); print('\n'.join('  ' + e for e in errors))
        sys.exit(1)
    open(f'{W}/extracted/EPICA.BIN', 'wb').write(epica)
    open(f'{W}/extracted/SLUS_010.70', 'wb').write(exe)
    print(f'EPICA.BIN {len(epica)} bytes, {done} translated lines, files moved to end: {moved}')
