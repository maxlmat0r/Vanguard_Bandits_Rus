"""Generate translated title-screen images (needs Pillow; run once, output goes to assets/).
Usage: <python with Pillow> scripts/gen_title.py <VBE_work dir>
  assets/t413_2.tim : title screen, credit line re-rendered
  assets/t413_4.tim : START / LOAD / OPTIONS menu sprite sheet in Russian
  assets/t413_menu.txt : highlight table bytes for module 2 (x, width per item)"""
import sys, os, struct
from PIL import Image, ImageDraw, ImageFont
W = sys.argv[1]
sys.path.insert(0, os.path.join(W, 'scripts'))
import sect_fmt

b = open(f'{W}/orig/EPICA.BIN', 'rb').read()
o, s = struct.unpack('<II', b[413*8:413*8+8])
tims = sect_fmt.unpack(b[o:o+s])

def c15(v): return ((v & 31) * 255 // 31, ((v >> 5) & 31) * 255 // 31, ((v >> 10) & 31) * 255 // 31)

# ---------------------------------------------------------------- title credit line (8bpp)
t = bytearray(tims[2])
cl = struct.unpack('<I', t[8:12])[0]
clut = [struct.unpack('<H', t[20+2*i:22+2*i])[0] for i in range((cl - 12) // 2)]
pal = [c15(v) for v in clut]
p = 8 + cl + 12; Wd, H = 320, 240
px = lambda x, y: t[p + y*Wd + x]
def setpx(x, y, v): t[p + y*Wd + x] = v
TOP, BOT = 216, 227                       # text rows 216..226
lum = lambda rgb: 0.3*rgb[0] + 0.59*rgb[1] + 0.11*rgb[2]
orig = bytes(t)
for x in range(Wd):
    up, dn = pal[orig[p + (TOP-1)*Wd + x]], pal[orig[p + BOT*Wd + x]]
    if lum(up) > lum(dn) + 40: up = dn          # robot above the line: use the colour below
    for y in range(TOP, BOT):
        f = (y - TOP + 1) / (BOT - TOP + 1)
        bg = tuple(round(u*(1-f) + d*f) for u, d in zip(up, dn))
        cur = pal[orig[p + y*Wd + x]]
        if lum(cur) > lum(bg) + 18:              # text or its anti-aliasing: repaint background
            setpx(x, y, min(range(1, len(pal)), key=lambda i: sum((a-c)**2 for a, c in zip(pal[i], bg))))
text = 'Original Game ©1998-00 Human;  Русский перевод ©2026 Maximator & Claude'
SS, TRACK = 4, 0.25                       # 4x supersampling, +0.25 px between letters
font = ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial Narrow.ttf', 10 * SS)
adv = [font.getlength(c) + TRACK * SS for c in text]
big = Image.new('L', (Wd * SS, 20 * SS), 0); dr = ImageDraw.Draw(big)
x = (Wd * SS - sum(adv)) / 2
for c, a in zip(text, adv):
    dr.text((x, 0), c, font=font, fill=255); x += a
mask = big.resize((Wd, 20), Image.LANCZOS)
# put cap tops at row 217 (original): find first non-empty mask row of a capital
top = min(y for y in range(20) for x in range(Wd) if mask.getpixel((x, y)) > 128)
ink = (232, 232, 232)
used = [i for i in range(1, len(pal))]
def nearest(rgb):
    return min(used, key=lambda i: sum((a - c) ** 2 for a, c in zip(pal[i], rgb)))
cache = {}
for my in range(20):
    y = 217 + my - top
    if not (TOP - 1 <= y < BOT + 1): continue
    for x in range(Wd):
        a = mask.getpixel((x, my)) / 255
        if a < 0.08: continue
        bg = pal[px(x, y)]
        rgb = tuple(round(a * i + (1 - a) * g) for i, g in zip(ink, bg))
        if rgb not in cache: cache[rgb] = nearest(rgb)
        setpx(x, y, cache[rgb])
open(f'{W}/assets/t413_2.tim', 'wb').write(t)

# ---------------------------------------------------------------- menu (4bpp 256x128)
m = bytearray(tims[4])
cl = struct.unpack('<I', m[8:12])[0]; p = 8 + cl + 12; MW = 256
def mset(x, y, v):
    i = p + y*MW//2 + x//2
    m[i] = (m[i] & (0xf0 if x % 2 == 0 else 0x0f)) | (v << (4 * (x % 2)))
for y in range(0, 47):
    for x in range(0, 64): mset(x, y, 0)
G = {
 'С': ['.####.', '#....#', '#.....', '#.....', '#.....', '#....#', '.####.'],
 'Т': ['#####', '..#..', '..#..', '..#..', '..#..', '..#..', '..#..'],
 'А': ['..##..', '.#..#.', '#....#', '#....#', '######', '#....#', '#....#'],
 'Р': ['#####.', '#....#', '#....#', '#....#', '#####.', '#.....', '#.....'],
 'З': ['.####.', '#....#', '.....#', '..###.', '.....#', '#....#', '.####.'],
 'Г': ['######', '#.....', '#.....', '#.....', '#.....', '#.....', '#.....'],
 'У': ['#....#', '#....#', '#....#', '.#####', '.....#', '#....#', '.####.'],
 'К': ['#....#', '#...#.', '#..#..', '###...', '#..#..', '#...#.', '#....#'],
 'Н': ['#....#', '#....#', '#....#', '######', '#....#', '#....#', '#....#'],
 'О': ['.####.', '#....#', '#....#', '#....#', '#....#', '#....#', '.####.'],
 'И': ['#....#', '#....#', '#...##', '#..#.#', '#.#..#', '##...#', '#....#'],
 'Й': ['#.##.#', '#....#', '#...##', '#..#.#', '#.#..#', '##...#', '#....#'],
}
words = ['СТАРТ', 'ЗАГРУЗКА', 'НАСТРОЙКИ']
table = []
for n, wd in enumerate(words):
    width = sum(len(G[c][0]) + 1 for c in wd) - 1
    x = max(0, 31 - width // 2); y = 2 + 11 * n
    table += [134 + x, width + 2]
    for c in wd:
        g = G[c]
        core = {(x + cx, y + cy) for cy, row in enumerate(g) for cx, ch in enumerate(row) if ch == '#'}
        for (cx, cy) in core:
            if (cx + 1, cy + 1) not in core and cx + 1 < 64: mset(cx + 1, cy + 1, 2)
        for (cx, cy) in core: mset(cx, cy, 1)
        x += len(g[0]) + 1
open(f'{W}/assets/t413_4.tim', 'wb').write(m)
open(f'{W}/assets/t413_menu.txt', 'w').write(' '.join(map(str, table)) + '\n')
print('menu table', table)
