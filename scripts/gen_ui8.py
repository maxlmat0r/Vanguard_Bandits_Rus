"""Redraw graphic text in the UI sheet (EPICA file 8, 4bpp 256x200):
"MORE INFO..." banner -> "ДОП. ИНФО...". Output: assets/f8_patch.txt with lines "x y idx".
No external libraries needed. Usage: python3 -I scripts/gen_ui8.py <VBE_work dir>"""
import sys, os
W = sys.argv[1]
G = {
 'Д': ['.###.', '.#.#.', '.#.#.', '#####', '#...#'],
 'О': ['.###.', '#...#', '#...#', '#...#', '.###.'],
 'П': ['#####', '#...#', '#...#', '#...#', '#...#'],
 '.': ['.', '.', '.', '.', '#'],
 'И': ['#...#', '#..##', '#.#.#', '##..#', '#...#'],
 'Н': ['#...#', '#...#', '#####', '#...#', '#...#'],
 'Ф': ['.###.', '#.#.#', '#.#.#', '.###.', '..#..'],
}
SHADE = [1, 1, 1, 2, 4]          # bright top, darker bottom (palette indices of the banner letters)
F = 15                            # black letter background / outline
out = []
def word(text, x0, y0, x_clear):
    for y in range(y0, y0 + 5):
        for x in range(*x_clear): out.append((x, y, F))
    x = x0
    for ch in text:
        g = G[ch]
        for r, row in enumerate(g):
            for c, v in enumerate(row):
                if v == '#': out.append((x + c, y0 + r, SHADE[r]))
        x += len(g[0]) + 1
out += [(228, 6, F), (229, 6, F), (228, 14, F)]   # stray shadow pixels of the old letters
word('ДОП.', 213, 1, (209, 236))
word('ИНФО', 219, 9, (219, 243))
import os
keep = [l for l in open(f'{W}/assets/f8_patch.txt').read().split('\n') if l.endswith(' #loading')] if os.path.exists(f'{W}/assets/f8_patch.txt') else []
open(f'{W}/assets/f8_patch.txt', 'w').write('\n'.join([f'{x} {y} {v}' for x, y, v in out] + keep) + '\n')
print(len(out), 'pixels')
