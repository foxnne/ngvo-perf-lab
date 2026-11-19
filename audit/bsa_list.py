# Lists files in an SSE BSA (v105) from the directory tables only: size(compressed) offset path
import struct,sys
def listing(path):
    f=open(path,'rb'); h=f.read(36)
    magic,ver,off,aflags,nfold,nfiles,tfl,tfil,fflags=struct.unpack('<4sIIIIIIII',h)
    assert ver==105,ver
    folders=[struct.unpack('<QIIQ',f.read(24)) for _ in range(nfold)]
    recs=[]
    for (hsh,cnt,pad,o) in folders:
        n=f.read(1)[0]; name=f.read(n)[:-1].decode('latin1')
        for _ in range(cnt):
            fh,size,foff=struct.unpack('<QII',f.read(16)); recs.append([name,size,foff])
    names=f.read(tfil).split(b'\0')
    out=[]
    for r,nm in zip(recs,names):
        out.append((r[1]&0x3fffffff,bool(r[1]&0x40000000)^bool(aflags&4),r[2],r[0]+'/'+nm.decode('latin1')))
    return out,aflags
if __name__=='__main__':
    out,fl=listing(sys.argv[1])
    for s,c,o,n in out: print(s,int(c),o,n.replace(chr(92),'/'))
