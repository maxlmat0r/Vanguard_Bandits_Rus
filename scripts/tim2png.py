import sys,struct,zlib
def png(path,w,h,rows):
    raw=b''.join(b'\x00'+bytes(r) for r in rows)
    def ch(t,d): return struct.pack('>I',len(d))+t+d+struct.pack('>I',zlib.crc32(t+d)&0xffffffff)
    open(path,'wb').write(b'\x89PNG\r\n\x1a\n'+ch(b'IHDR',struct.pack('>IIBBBBB',w,h,8,2,0,0,0))+ch(b'IDAT',zlib.compress(raw))+ch(b'IEND',b''))
def c15(v): return ((v&31)*255//31,((v>>5)&31)*255//31,((v>>10)&31)*255//31)
def load(d):
    p=8; cl=struct.unpack('<IHHHH',d[p:p+12]); clut=[struct.unpack('<H',d[p+12+2*i:p+14+2*i])[0] for i in range(cl[3]*cl[4])]; p+=cl[0]
    il=struct.unpack('<IHHHH',d[p:p+12]); w=il[3]*4; h=il[4]; px=d[p+12:p+12+il[3]*2*h]
    idx=[[ (px[y*w//2+x//2]>>(4*(x&1)))&15 for x in range(w)] for y in range(h)]
    return clut,w,h,idx,p+12
if __name__=='__main__':
    b=open(sys.argv[1],'rb').read(); k=int(sys.argv[2])
    o,s=struct.unpack('<II',b[k*8:k*8+8]); d=b[o:o+s]
    clut,w,h,idx,_=load(d)
    print('clut',[hex(c) for c in clut])
    sc=int(sys.argv[4]) if len(sys.argv)>4 else 3
    gray=lambda i:(i*17,i*17,i*17)
    rows=[]
    for y in range(h):
        r=[]
        for x in range(w):
            col=gray(idx[y][x]) if idx[y][x] else (40,0,60)
            # grid lines every 16 x / 15 y
            if x%16==0 or y%15==0: col=tuple(min(255,c+60) for c in col) if idx[y][x] else (90,40,110)
            r+=list(col)*sc
        for _ in range(sc): rows.append(r)
    png(sys.argv[3],w*sc,h*sc,rows)
