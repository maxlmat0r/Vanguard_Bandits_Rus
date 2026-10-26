"""Dump all dialogue to texts/<group>/*.json (one file per game file).

Usage: python3 -I scripts/extract.py <VBE_work dir>
Existing "ru" values are preserved when re-extracting.
Text tokens: newline = \n, raw control bytes = {XX} (hex), e.g. choice menus
"{02}Option one{00}{00}Option two".
"""
import sys, os, struct, json
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from lz import decompress
import battle_fmt, story_fmt, quip_fmt, sect_fmt, strtab_fmt
from cyr_glyphs import line_px

W = sys.argv[1]
import texts
epica = open(f'{W}/orig/EPICA.BIN', 'rb').read()


def entry(k):
    return struct.unpack('<II', epica[k*8:k*8+8])


def to_text(raw):
    raw = raw.replace(b'\r\n', b'\n')
    out = []
    for c in raw:
        if c == 10 or 32 <= c < 127: out.append(chr(c))
        else: out.append('{%02X}' % c)
    return ''.join(out)


def dump(name, kind, k, items, **extra):
    path = texts.path(name, W); os.makedirs(os.path.dirname(path), exist_ok=True)
    old = {}
    if os.path.exists(path):
        for it in json.load(open(path, encoding='utf-8'))['lines']:
            old[it['id']] = it.get('ru', '')
    lines = [{'id': i, 'en': to_text(t), 'ru': old.get(i, '')} for i, t in items]
    json.dump(dict({'file': k, 'kind': kind}, **extra, lines=lines),
              open(path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    return len(lines)


total = 0; files = 0
for k in range(121, 177):
    o, s = entry(k)
    items = [(i, t) for i, _, t in battle_fmt.strings(epica[o:o+s])]
    total += dump(f'b{k}', 'battle', k, items); files += 1
for k in range(177, 704):
    o, s = entry(k)
    if not s: continue
    try: d = decompress(epica[o:o+s])
    except Exception: continue
    if not story_fmt.is_story(d): continue
    total += dump(f's{k}', 'story', k, story_fmt.strings(d)); files += 1
for k in range(358, 410):                          # battle-animation quips (raw)
    o, s = entry(k)
    items = [(i, t) for i, _, t in quip_fmt.strings(epica[o:o+s])]
    total += dump(f'q{k}', 'quip', k, items); files += 1
# string tables inside section archives: Puck's menu help (417) and camp talks (419)
for k, sec, ctrl in ((417, 0, 1), (419, 3, 2)):
    o, s = entry(k)
    tab = sect_fmt.sections(epica[o:o+s], 4)[sec]
    items = strtab_fmt.strings(tab, ctrl)
    lines = [l.replace(b'\r', b'') for i, t in items for l in t.split(b'\n') if all(c < 0x80 for c in l)]
    total += dump(f'x{k}', 'strtab', k, items, section=sec, ctrl=ctrl,
                  max_px=max(map(line_px, lines)), max_lines=max(t.count(b'\n') + 1 for i, t in items)); files += 1
print(files, 'files,', total, 'lines ->', os.path.join(W, 'texts'))
