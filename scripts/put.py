"""Write translations into texts/<group>/<name>.json and check line widths.

Usage: python3 -I scripts/put.py <name> < input
Input format: blocks separated by lines '@<id>'; text follows (multi-line).
  @0
  Бастион:
  Ну же, отец!
"""
import sys, os, json, re
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from cyr_glyphs import encode, line_px
name = sys.argv[1]
MAX_PX = 150 if name[0] == 'q' else 238      # quips: battle-animation text beside a portrait
MAX_LINES = 2 if name[0] == 'q' else 3
import texts
path = texts.path(name)
js = json.load(open(path, encoding='utf-8'))
if 'max_px' in js: MAX_PX, MAX_LINES = js['max_px'], js['max_lines']   # x*: limits of the original
byid = {l['id']: l for l in js['lines']}
cur = None; buf = {}
for line in sys.stdin.read().split('\n'):
    m = re.fullmatch(r'@(\d+)', line.strip())
    if m: cur = int(m.group(1)); buf[cur] = []; continue
    if cur is not None: buf[cur].append(line)
bad = 0
def wrap(paragraph):
    """Greedy word wrap by pixel width; '//' forces a line break."""
    out = []
    for part in paragraph.split('//'):
        cur = ''
        for w in part.split():
            t = (cur + ' ' + w) if cur else w
            try: too_wide = line_px(encode(t)) > MAX_PX
            except ValueError: too_wide = False
            if cur and too_wide:
                out.append(cur); cur = w
            else:
                cur = t
        if cur: out.append(cur)
    if len(out) > MAX_LINES == 2 and '//' not in paragraph:   # try any 2-line split
        ws = paragraph.split()
        fits = lambda t: line_px(encode(t)) <= MAX_PX
        for n in sorted(range(1, len(ws)), key=lambda n: abs(2*n - len(ws))):
            a, b = ' '.join(ws[:n]), ' '.join(ws[n:])
            try:
                if fits(a) and fits(b): return [a, b]
            except ValueError: break
    return out

def prepare(ls):
    ls = [l.rstrip() for l in ls]
    while ls and not ls[-1]: ls.pop()
    if any('{' in l for l in ls):            # choice menus etc.: keep as typed
        return '\n'.join(ls)
    head = []
    if name[0] != 'q' and ls and ls[0].endswith(':') and len(ls) > 1:
        head = [ls[0]]; ls = ls[1:]
    return '\n'.join(head + wrap(' '.join(l.strip() for l in ls)))

for i, ls in buf.items():
    text = prepare(ls)
    if i not in byid: print('no id', i); bad += 1; continue
    if not re.search('[A-Za-z]', byid[i]['en']):
        print(f'#{i}: REFUSED - English line has no text: {byid[i]["en"]!r}'); bad += 1; continue
    byid[i]['ru'] = text
    if re.search(r'[а-яё][a-z]|[a-z][а-яё]', text, re.I):
        print(f'#{i}: mixed Latin/Cyrillic letters in a word'); bad += 1
    try: enc = encode(text)
    except ValueError as e: print(f'#{i}: {e}'); bad += 1; continue
    segs = enc.replace(b'\x00', b'\n').split(b'\n')
    tlines = text.replace('{00}', '\n').split('\n')
    body = segs[1:] if segs and segs[0].endswith(b':') else segs
    if len([x for x in body if x]) > MAX_LINES and b'\x02' not in enc:
        print(f'#{i}: more than {MAX_LINES} lines: ' + ' | '.join(text.split(chr(10)))); bad += 1
    for n, s in enumerate(segs):
        if n == 0 and s.endswith(b':'): continue
        px = line_px(s)
        if px > MAX_PX:
            print(f'#{i}: {px}px  {tlines[n] if n < len(tlines) else ""}'); bad += 1
json.dump(js, open(path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
total = len(js['lines']); filled = sum(1 for l in js['lines'] if l['ru'])
print(f'{name}: {len(buf)} written, {filled}/{total} translated, {bad} problems')
