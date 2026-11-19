import struct,sys
def lz4_block(src,out):
    i=0; n=len(src)
    while i<n:
        t=src[i]; i+=1; ll=t>>4
        if ll==15:
            while True:
                b=src[i]; i+=1; ll+=b
                if b!=255: break
        out+=src[i:i+ll]; i+=ll
        if i>=n: break
        off=src[i]|(src[i+1]<<8); i+=2; ml=t&15
        if ml==15:
            while True:
                b=src[i]; i+=1; ml+=b
                if b!=255: break
        ml+=4; s=len(out)-off
        for k in range(ml): out.append(out[s+k])
    return out
def lz4_frame(d):
    assert d[:4]==b'\x04\x22\x4d\x18'
    flg=d[4]; i=6
    if flg&8: i+=8
    if flg&1: i+=4
    i+=1; out=bytearray()
    while True:
        bs=struct.unpack('<I',d[i:i+4])[0]; i+=4
        if bs==0: break
        raw=bs&0x80000000; bs&=0x7fffffff
        blk=d[i:i+bs]; i+=bs
        if flg&16: i+=4
        if raw: out+=blk
        else: lz4_block(blk,out)
    return bytes(out)
def read_bsa(path):
    f=open(path,'rb'); h=f.read(36); _,ver,fo,flags,fc,flc,tfn,tfl,_=struct.unpack('<4sIIIIIIII',h)
    f.seek(fo); folders=[]
    for _ in range(fc):
        hh,cnt,pad,off=struct.unpack('<QIIQ',f.read(24)); folders.append((cnt,off))
    files=[]
    # file record blocks follow folder records; each preceded by name
    for cnt,off in folders:
        nl=f.read(1)[0]; name=f.read(nl).rstrip(b'\0').decode('latin1')
        for _ in range(cnt):
            hh,size,off2=struct.unpack('<QII',f.read(16)); files.append([name,None,size,off2])
    names=f.read(tfl).split(b'\0')
    for i,fl in enumerate(files): fl[1]=names[i].decode('latin1')
    return f,files,flags
if __name__=='__main__':
    f,files,flags=read_bsa(sys.argv[1]); comp=flags&4; embed=bool(flags&0x100)
    tot=0;tn=0;rows=[]
    for d,n,size,off in files:
        if not n.lower().endswith('.nif'): continue
        if 'tree' not in (d+n).lower(): continue
        f.seek(off); size_=size&0x3fffffff; data=f.read(size_)
        if embed: ln=data[0]; data=data[1+ln:]
        if comp: usize=struct.unpack('<I',data[:4])[0]; data=lz4_frame(data[4:])
        has=b"BSTreeNode" in data; tot+=1; tn+=has; rows.append((d+"/"+n,has))
    print(sys.argv[1].split('/')[-1],'tree nifs',tot,'with BSTreeNode',tn)
    for r in rows[:6]: print(' ',r)
