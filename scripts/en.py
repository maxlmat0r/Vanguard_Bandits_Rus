"""Print English lines of translation files compactly: python3 -I scripts/en.py s483 [b122 ...]
Add -todo to show only untranslated lines."""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import texts
HERE = os.path.dirname(os.path.abspath(__file__))
todo = '-todo' in sys.argv
for name in [a for a in sys.argv[1:] if not a.startswith('-')]:
    js = json.load(open(texts.path(name), encoding='utf-8'))
    print(f'##### {name} ({len(js["lines"])})')
    for l in js['lines']:
        if todo and l['ru']: continue
        if not any(c.isalpha() for c in l['en']): continue
        t = l['en']
        if ':\n' in t.split('\n')[0] + '\n' and len(t.split('\n')[0]) < 32:
            first, rest = t.split('\n', 1)
            t = first + ' ' + rest.replace('\n', ' ')
        else:
            t = t.replace('\n', ' ')
        print(f'@{l["id"]} {t}')
