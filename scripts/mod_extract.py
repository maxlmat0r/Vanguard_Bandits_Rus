"""Dump UI strings of the code modules (EPICA files 0-3, loaded at 0x800751a8).

Usage: <python with capstone> scripts/mod_extract.py <VBE_work dir> [k ...]
Writes texts/ui/m<k>.json: {id, addr, en, ru, refs, ptrs, room}
  refs = instructions whose 16-bit immediate is the low half of addr (lui/addiu pairs)
  ptrs = 32-bit words in the module that hold addr
  room = bytes the string may use in place (own text + NUL + zero padding after it)
Existing "ru" values are kept. Strings that are not referenced are not listed.
"""
import sys, os, re, struct, json, collections
import capstone
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import texts

W = sys.argv[1]
MODS = [int(a) for a in sys.argv[2:]] or [0, 1, 2, 3]
BASE = 0x800751a8
epica = open(f'{W}/orig/EPICA.BIN', 'rb').read()


def code_refs(d):
    md = capstone.Cs(capstone.CS_ARCH_MIPS, capstone.CS_MODE_MIPS32 + capstone.CS_MODE_LITTLE_ENDIAN)
    md.skipdata = True
    ins = [(i.address, i.mnemonic, i.op_str) for i in md.disasm(d, BASE)]
    refs = collections.defaultdict(list)
    for n, (a, mn, ops) in enumerate(ins):
        if mn != 'lui': continue
        r, imm = [x.strip() for x in ops.split(',')]
        hi = int(imm, 16) << 16
        for b, mn2, ops2 in ins[n+1:n+40]:
            parts = [x.strip() for x in ops2.split(',')]
            if mn2 == 'addiu' and len(parts) == 3 and parts[1] == r:
                imm2 = int(parts[2], 16)
                refs[(hi + imm2) & 0xffffffff].append(b)
            m = re.match(r'(-?0x[0-9a-f]+|-?\d+)\((\$\w+)\)', parts[-1]) if parts else None
            if m and m.group(2) == r:
                refs[(hi + int(m.group(1), 0)) & 0xffffffff].append(b)
            if parts and parts[0] == r and mn2 not in ('sw', 'sh', 'sb', 'beq', 'bne', 'beqz', 'bnez',
                    'blez', 'bgtz', 'bltz', 'bgez', 'jr', 'jalr', 'mult', 'multu', 'div', 'divu'):
                break
    return refs


def text(raw):
    return ''.join(chr(c) if 32 <= c < 127 or c in (9, 10) else '{%02X}' % c for c in raw)


for k in MODS:
    o, s = struct.unpack('<II', epica[k*8:k*8+8]); d = epica[o:o+s]
    refs = code_refs(d)
    ptrs = collections.defaultdict(list)
    for i in range(0, len(d) - 3, 4):
        v = struct.unpack('<I', d[i:i+4])[0]
        if BASE <= v < BASE + s: ptrs[v].append(BASE + i)
    items = []
    for m in re.finditer(rb'[\t\n\x20-\x7e]{2,}\x00', d):
        start = m.start(); end = m.end() - 1          # end = index of NUL
        for off in range(start, end):
            a = BASE + off
            if a not in refs and a not in ptrs: continue
            if not re.search(rb'[A-Za-z]{2}', d[off:end]): continue
            pad = end + 1
            while pad < len(d) and d[pad] == 0: pad += 1
            items.append({'addr': hex(a), 'en': text(d[off:end]),
                          'refs': [hex(x) for x in refs.get(a, [])],
                          'ptrs': [hex(x) for x in ptrs.get(a, [])],
                          'room': pad - off, 'tail': off != start})
    path = texts.path(f'm{k}', W)
    old = {}
    if os.path.exists(path):
        for it in json.load(open(path, encoding='utf-8'))['lines']: old[it['addr']] = it.get('ru', '')
    for i, it in enumerate(items):
        it['id'] = i; it['ru'] = old.get(it['addr'], '')
    lines = [{k2: it[k2] for k2 in ('id', 'addr', 'en', 'ru', 'refs', 'ptrs', 'room', 'tail')} for it in items]
    json.dump({'file': k, 'kind': 'module', 'base': hex(BASE), 'lines': lines},
              open(path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'm{k}: {len(lines)} strings')
