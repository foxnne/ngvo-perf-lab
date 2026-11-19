# Extracts a few named NIFs from an SSE BSA in memory (pure-python LZ4 frame) and counts triangles. No files written.
import struct,sys,io,re,importlib.util,os,tempfile
import bsa_list
def lz4_block(src,out):
    i=0;n=len(src)
    while i<n:
        t=src[i];i+=1
        ll=t>>4
        if ll==15:
            while True:
                b=src[i];i+=1;ll+=b
                if b!=255:break
        out+=src[i:i+ll];i+=ll
        if i>=n:break
        off=src[i]|(src[i+1]<<8);i+=2
        ml=t&15
        if ml==15:
            while True:
                b=src[i];i+=1;ml+=b
                if b!=255:break
        ml+=4
        st=len(out)-off
        if off>=ml: out+=out[st:st+ml]
        else:
            for k in range(ml): out.append(out[st+k])
def lz4_frame(d):
    assert struct.unpack_from('<I',d,0)[0]==0x184D2204
    flg=d[4];p=6
    if flg&8:p+=8
    if flg&1:p+=4
    p+=1
    out=bytearray()
    while True:
        sz,=struct.unpack_from('<I',d,p);p+=4
        if sz==0:break
        raw=sz&0x80000000;sz&=0x7fffffff
        if raw: out+=d[p:p+sz]
        else: lz4_block(d[p:p+sz],out)
        p+=sz
        if flg&16:p+=4
    return bytes(out)
src=open('nif_tris.py').read().split("for line in sys.stdin")[0].replace("b = open(path, 'rb').read()","b = path")
ns={};exec(src,ns)
bsa=sys.argv[1];pats=sys.argv[2:]
lst,aflags=bsa_list.listing(bsa)
f=open(bsa,'rb')
for pt in pats:
    hits=[x for x in lst if re.search(pt,x[3].replace(chr(92),'/'),re.I)][:int(os.environ.get('MAXHIT','2'))]
    for size,comp,off,name in hits:
        f.seek(off);d=f.read(size)
        if aflags&0x100: d=d[1+d[0]:]
        if comp: d=lz4_frame(d[4:])
        t,v,s,n=ns['parse'](d)
        print('%7d %7d %3d %9d %s'%(t,v,s,n,name.replace(chr(92),'/')))
