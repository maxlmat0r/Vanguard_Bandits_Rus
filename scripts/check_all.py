"""Check every translated line in texts/*/*.json: width, line count, mixed scripts."""
import sys, os, json, glob, re
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from cyr_glyphs import encode, line_px
MAX_PX = 238
bad = 0
import texts
for p in texts.all_files(prefixes='bsqx'):
    name = os.path.basename(p)[:-5]
    MAX_PX, MAX_LINES = (150, 2) if name[0] == 'q' else (238, 3)
    _js = json.load(open(p, encoding='utf-8'))
    if 'max_px' in _js: MAX_PX, MAX_LINES = _js['max_px'], _js['max_lines']
    for l in json.load(open(p, encoding='utf-8'))['lines']:
        t = l['ru']
        if not t: continue
        if not re.search('[A-Za-z]', l['en']):
            print(f'{name} #{l["id"]}: translation on a line without English text'); bad += 1
        try: enc = encode(t)
        except ValueError as e: print(f'{name} #{l["id"]}: {e}'); bad += 1; continue
        segs = enc.replace(b'\x00', b'\n').split(b'\n')
        # a speaker line only where the English has one too (narration may end with ':')
        named = segs[0].endswith(b':') and name[0] != 'q' and l['en'].split('\n')[0].endswith(':')
        body = segs[1:] if named else segs
        if len([x for x in body if x]) > MAX_LINES and b'\x02' not in enc:
            print(f'{name} #{l["id"]}: >{MAX_LINES} lines'); bad += 1
        for n, s in enumerate(segs):
            if n == 0 and named: continue
            if line_px(s) > MAX_PX: print(f'{name} #{l["id"]}: {line_px(s)}px'); bad += 1
        if re.search(r'[а-яё][a-z]|[a-z][а-яё]', t, re.I): print(f'{name} #{l["id"]}: mixed'); bad += 1
print('problems:', bad)
