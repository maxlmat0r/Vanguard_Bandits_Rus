"""Set module UI translations by English text.
Usage: python3 -I scripts/mod_put.py m1 < 'english<TAB>russian' lines  (\\n, \\t escapes allowed)
Every listed string of the module with that exact English gets the translation."""
import sys, os, json
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from cyr_glyphs import encode
import texts
p = texts.path(sys.argv[1])
js = json.load(open(p, encoding='utf-8'))
esc = lambda t: t.replace('\\n', '\n').replace('\\t', '\t')
bad = 0
for line in sys.stdin.read().split('\n'):
    if not line.strip(): continue
    en, ru = (esc(x) for x in line.split('\t', 1)) if '\t' in line else (None, None)
    if en is None: print('no TAB:', line); bad += 1; continue
    hit = [l for l in js['lines'] if l['en'] == en and not l['tail']]
    if not hit: print('not found:', repr(en)); bad += 1; continue
    try: enc = encode(ru)
    except ValueError as e: print(repr(en), e); bad += 1; continue
    for l in hit:
        l['ru'] = ru
        if len(enc) + 1 > l['room']:
            print(f"  {l['id']} {'moves (code ref)' if l['refs'] else 'appended'}: {len(enc)+1}>{l['room']} {ru!r}")
json.dump(js, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('problems', bad, 'translated', sum(1 for l in js['lines'] if l['ru']), '/', len(js['lines']))
