"""Set UI translations: python3 -I scripts/exe_put.py [m0|m1|m2] < 'id<TAB>text' lines.
No argument = EXE strings (exe_ui.json). In text, \\n and \\t stand for newline / tab.
Reports encoding errors, in-place length overflows and pixel width vs English."""
import sys, os, json
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from cyr_glyphs import encode, line_px
NAME = sys.argv[1] if len(sys.argv) > 1 else 'exe_ui'
import texts
p = texts.path(NAME)
js = json.load(open(p, encoding='utf-8')); by = {l['id']: l for l in js['lines']}
exe = open(os.path.join(HERE, '..', 'orig', 'SLUS_010.70'), 'rb').read()
def room(l):
    if 'room' in l: return l['room'] - 1
    f = int(l['addr'], 16) - 0x80010000 + 0x800
    end = f + len(l['en'])
    while end + 1 < len(exe) and exe[end + 1] == 0: end += 1
    return end - f
bad = 0
for line in sys.stdin.read().split('\n'):
    if not line.strip(): continue
    i, t = line.split('\t', 1); i = int(i); l = by[i]
    t = t.replace('\\n', '\n').replace('\\t', '\t')
    try: enc = encode(t)
    except ValueError as e: print(i, e); bad += 1; continue
    l['ru'] = t
    if l.get('mode', 'inplace') == 'inplace' and len(enc) > room(l):
        if l.get('refs'): print(f'{i}: moves to spare space {len(enc)}>{room(l)}: {t!r}')
        elif 'room' not in l: print(f'{i}: too long {len(enc)}>{room(l)}: {t}'); bad += 1
    pe, pr = line_px(l['en'].encode()), line_px(enc.replace(b'\t', b''))
    if pr > pe * 1.25 + 4: print(f'{i}: wider {pr}px vs {pe}px  {l["en"]} -> {t}')
json.dump(js, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('done, problems', bad, 'translated', sum(1 for l in js['lines'] if l['ru']), '/', len(js['lines']))
