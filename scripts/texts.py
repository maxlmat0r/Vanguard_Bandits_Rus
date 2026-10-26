"""Where the translation files live: texts/<group>/<name>.json
  story/  s482..s700  story scenes        battle/ b121..b176  battle dialogue
  quips/  q358..q409  battle-animation quips  camp/ x417, x419  Puck help, camp talks
  ui/     exe_ui, m0, m1, m2  interface strings"""
import os, glob
ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
GROUP = {'s': 'story', 'b': 'battle', 'q': 'quips', 'x': 'camp', 'm': 'ui', 'e': 'ui'}

def path(name, root=ROOT):
    return os.path.join(root, 'texts', GROUP[name[0]], name + '.json')

def all_files(root=ROOT, prefixes=None):
    fs = sorted(glob.glob(os.path.join(root, 'texts', '*', '*.json')))
    if prefixes: fs = [f for f in fs if os.path.basename(f)[0] in prefixes]
    return fs
