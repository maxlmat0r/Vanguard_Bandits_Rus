"""GAME OVER screen (EPICA 420: LZ TIM 8bpp 320x240) -> "КОНЕЦ ИГРЫ". Needs Pillow.
Usage: <python with Pillow> scripts/gen_gameover.py <VBE_work dir>  -> assets/f420.tim"""
import sys, os, struct
from PIL import Image, ImageDraw, ImageFont, ImageFilter
W = sys.argv[1]
sys.path.insert(0, os.path.join(W, 'scripts'))
from lz import decompress
b = open(f'{W}/orig/EPICA.BIN', 'rb').read()
o, s = struct.unpack('<II', b[420*8:420*8+8])
t = bytearray(decompress(b[o:o+s]))
cl = struct.unpack('<I', t[8:12])[0]
c15 = lambda v: ((v & 31) * 255 // 31, ((v >> 5) & 31) * 255 // 31, ((v >> 10) & 31) * 255 // 31)
pal = [c15(struct.unpack('<H', t[20+2*i:22+2*i])[0]) for i in range(256)]
p = 8 + cl + 12; Wd, H = 320, 240
t = t[:p + Wd*H]
img = Image.new('RGB', (Wd, H)); img.putdata([pal[t[p+i]] for i in range(Wd*H)])
# 1. remove the old text + glow: left part is plain dark background
bgc = img.getpixel((4, 4))
lum = lambda c: 0.3*c[0] + 0.59*c[1] + 0.11*c[2]
red = lambda c: c[0] - max(c[1], c[2])
for y in range(H):
    for x in range(0, 200):
        c = img.getpixel((x, y))
        if red(c) > 20 or lum(c) > 60:           # glow / letters (robot is blue-grey)
            if x < 175 or red(c) > 20: img.putpixel((x, y), bgc)
# 2. new text with red glow
font = ImageFont.truetype('/System/Library/Fonts/Supplemental/Georgia Bold.ttf', 38)
lines = ['КОНЕЦ', 'ИГРЫ']
mask = Image.new('L', (Wd, H), 0); dr = ImageDraw.Draw(mask)
cx, y0 = 92, 72
for i, ln in enumerate(lines):
    w = dr.textlength(ln, font=font)
    dr.text((cx - w/2, y0 + i*44), ln, font=font, fill=255)
glow = mask.filter(ImageFilter.GaussianBlur(5))
out = img.copy()
for y in range(H):
    for x in range(Wd):
        g = glow.getpixel((x, y)) / 255 * 1.6; a = mask.getpixel((x, y)) / 255
        if g < 0.02 and a == 0: continue
        c = out.getpixel((x, y))
        c = tuple(min(255, round(v*(1-min(g,1)) + r*min(g,1))) for v, r in zip(c, (200, 16, 16)))
        c = tuple(round(v*(1-a) + 245*a) for v in c)
        out.putpixel((x, y), c)
# 3. back to the original 256-colour palette
cache = {}
def near(c):
    if c not in cache: cache[c] = min(range(256), key=lambda i: sum((a-b)**2 for a, b in zip(pal[i], c)))
    return cache[c]
for y in range(H):
    for x in range(Wd):
        t[p + y*Wd + x] = near(out.getpixel((x, y)))
open(f'{W}/assets/f420.tim', 'wb').write(t)
out.save(f'{W}/assets/f420_preview.png')
print('ok')
