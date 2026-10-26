def decompress(src):
    buf=bytearray(1024); r=0x3be; out=bytearray(); i=0; n=len(src)
    flags=0
    while i<n:
        flags>>=1
        if not flags&0x100:
            flags=src[i]|0xff00; i+=1
        if not flags&1:
            if i>=n: break
            c=src[i]; i+=1; out.append(c); buf[r]=c; r=(r+1)&0x3ff
        else:
            if i+1>=n: break
            b1,b2=src[i],src[i+1]; i+=2
            pos=b1+((b2&0xc0)<<2); ln=(b2&0x3f)+3
            for _ in range(ln):
                c=buf[pos&0x3ff]; pos+=1; out.append(c); buf[r]=c; r=(r+1)&0x3ff
    return bytes(out)

def compress(data, max_chain=256):
    # history = 1024 zero bytes (initial ring) + data; ring pos of history index h is (h - 1024 + 0x3be) & 0x3ff
    H=bytes(1024)+bytes(data); base=1024; n=len(H)
    MINL,MAXL,WIN=3,66,1024
    heads={}; prev=[-1]*n
    def ins(h):
        if h+3<=n:
            k=H[h:h+3]; prev[h]=heads.get(k,-1); heads[k]=h
    for h in range(base-WIN,base): ins(h)
    out=bytearray(); p=base
    def find(p):
        best_l,best_h=0,-1
        if p+MINL>n: return 0,-1
        h=heads.get(H[p:p+3],-1); c=0; lim=min(MAXL,n-p)
        while h>=0 and c<max_chain:
            if p-h>WIN: break
            l=3
            while l<lim and H[h+l]==H[p+l]: l+=1
            if l>best_l:
                best_l,best_h=l,h
                if l==lim: break
            h=prev[h]; c+=1
        return best_l,best_h
    while p<n:
        fpos=len(out); out.append(0); flags=0
        for bit in range(8):
            if p>=n: break
            l,h=find(p)
            if l>=3:
                # lazy matching: prefer literal if next position gives a longer match
                l2,_=find(p+1) if p+1<n else (0,-1)
                if l2>l+1: l=0
            if l>=3:
                pos=(h-base+0x3be)&0x3ff
                out.append(pos&0xff); out.append(((pos>>8)<<6)|(l-3))
                flags|=1<<bit
                for q in range(p,p+l): ins(q)
                p+=l
            else:
                out.append(H[p]); ins(p); p+=1
        out[fpos]=flags
    return bytes(out)
