"""Translation memory: fill empty "ru" wherever the same English text is already translated.
python3 -I scripts/tm.py"""
import os, json, glob, re
HERE = os.path.dirname(os.path.abspath(__file__))
import sys; sys.path.insert(0, HERE); import texts
files = texts.all_files(prefixes='bsqx')
data = {p: json.load(open(p, encoding='utf-8')) for p in files}
mem = {}                     # quips (q*) have narrower lines: separate memory
group = lambda p: {'q': 1, 'x': 2}.get(os.path.basename(p)[0], 0)
for p, js in data.items():
    for l in js['lines']:
        if l['ru']: mem.setdefault((group(p), l['en']), l['ru'])
filled = 0
for p, js in data.items():
    ch = False
    for l in js['lines']:
        if not l['ru'] and (group(p), l['en']) in mem:
            l['ru'] = mem[(group(p), l['en'])]; filled += 1; ch = True
    if ch: json.dump(js, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
todo = sum(1 for js in data.values() for l in js['lines'] if not l['ru'] and re.search('[A-Za-z]', l['en']))
done = sum(1 for js in data.values() for l in js['lines'] if l['ru'])
print(f'filled {filled}; translated {done}; remaining {todo}')
