"""Region names for the travel map (EPICA 592: one LZ TIM, 384x480 halfwords used as a
4bpp sheet 1536x480; names column x 1280..1407, 8 bands of 16 rows, centred on x=1341,
index = brightness through grey clut row 15). Needs Pillow.
Usage: <python with Pillow> scripts/gen_mapnames.py <VBE_work dir> -> assets/f592_names.bin
(raw 4bpp block: 128 rows x 64 bytes for x 1280..1407)."""
import sys, os, struct
from PIL import Image, ImageDraw, ImageFont
W = sys.argv[1]
sys.path.insert(0, os.path.join(W, 'scripts'))
from lz import decompress
NAMES = ['Княжество Авалон', 'Герцогство Хиберния', 'Страна Муспель', 'Южный союз',
         'Дионн-Леве', 'Королевство Фарастия', 'Лес Нордилейн', 'Империя Джунарис']
X0, X1, CX, MAXW = 1280, 1408, 1341, 112   # CX moved +8 (backdrop widened, see build.py)
FONT = '/System/Library/Fonts/Supplemental/Luminari.ttf'
SS = 4
b = open(f'{W}/orig/EPICA.BIN', 'rb').read()
o, s = struct.unpack('<II', b[592*8:592*8+8]); d = decompress(b[o:o+s])
L = struct.unpack('<I', d[8:12])[0]; p = 8 + L + 12
px = bytearray(d[p:p+768*480])
def setv(x, y, val):
    i = y*768 + x//2
    px[i] = (px[i] & (0xf0 if x % 2 == 0 else 0x0f)) | (val << (4*(x % 2)))
for y in range(128):
    for x in range(X0, X1): setv(x, y, 0)
for n, name in enumerate(NAMES):
    size = 11
    while True:
        f = ImageFont.truetype(FONT, size * SS)
        tw = ImageDraw.Draw(Image.new('L', (1, 1))).textlength(name, font=f) / SS
        if tw <= MAXW or size <= 8: break
        size -= 1
    big = Image.new('L', ((X1 - X0) * SS, 16 * SS), 0)
    ImageDraw.Draw(big).text(((CX - X0) * SS - tw * SS / 2, 0), name, font=f, fill=255)
    m = big.resize((X1 - X0, 16), Image.LANCZOS)
    for y in range(16):
        for x in range(X1 - X0):
            a = m.getpixel((x, y)) / 255
            if a >= 0.25: setv(X0 + x, n*16 + y, min(15, max(4, round(3 + a * 12))))
    print(name, size, round(tw))
out = bytes(px[y*768 + X0//2: y*768 + X1//2] for y in range(128)) if False else b''.join(bytes(px[y*768 + X0//2: y*768 + X1//2]) for y in range(128))
open(f'{W}/assets/f592_names.bin', 'wb').write(out)
prev = Image.new('L', (X1 - X0, 128))
prev.putdata([((out[y*64 + x//2] >> (4*(x & 1))) & 15) * 17 for y in range(128) for x in range(X1 - X0)])
prev.resize(((X1 - X0) * 3, 384), Image.NEAREST).save(f'{W}/assets/f592_names_preview.png')
