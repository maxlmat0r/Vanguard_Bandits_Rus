"""'Now Loading...' in the UI sheet (EPICA file 8, x163..255, y161..175, gray palette row 9:
index = brightness 0..15) -> 'Загрузка...'. Needs Pillow. Appends to assets/f8_patch.txt.
Usage: <python with Pillow> scripts/gen_loading.py <VBE_work dir>"""
import sys
from PIL import Image, ImageDraw, ImageFont
W = sys.argv[1]
X0, X1, Y0, Y1 = 163, 256, 161, 176
SS = 4
font = ImageFont.truetype('/System/Library/Fonts/Supplemental/Georgia.ttf', 11 * SS)
text = 'Загрузка...'
big = Image.new('L', ((X1 - X0) * SS, (Y1 - Y0) * SS), 0)
dr = ImageDraw.Draw(big)
tw = dr.textlength(text, font=font)
dr.text((((X1 - X0) * SS - tw) / 2, -1 * SS), text, font=font, fill=255)
m = big.resize((X1 - X0, Y1 - Y0), Image.LANCZOS)
lines = [l for l in open(f'{W}/assets/f8_patch.txt').read().split('\n') if l and not l.endswith(' #loading')]
for y in range(Y0, Y1):
    for x in range(X0, X1):
        v = round(m.getpixel((x - X0, y - Y0)) / 255 * 14)
        lines.append(f'{x} {y} {v} #loading')
open(f'{W}/assets/f8_patch.txt', 'w').write('\n'.join(lines) + '\n')
print('ok', tw / SS)
