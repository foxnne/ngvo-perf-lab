import struct, numpy as np, os
GD=r"C:\Modlists\NGVO 8.0 Beta\mods\NGVO - Grass Cache\grass"
def parse(path, verbose=False):
    b=open(path,'rb').read(); pos=0
    ntypes=struct.unpack_from('<I',b,pos)[0]; pos+=4
    out=[]
    for ti in range(ntypes):
        n=struct.unpack_from('<I',b,pos)[0]; pos+=4
        name=b[pos:pos+n].split(b'\0')[0].decode('cp1252'); pos+=n
        f0,hsh=struct.unpack_from('<fI',b,pos); pos+=8
        b3=b[pos:pos+3]; pos+=3
        nblk=struct.unpack_from('<I',b,pos)[0]; pos+=4
        if verbose: print(ti,name,f0,hex(hsh),b3.hex(),nblk)
        for bi in range(nblk):
            cx,cy,cz,ex,ey,ez=struct.unpack_from('<6f',b,pos); pos+=24
            z0,cnt,nval=struct.unpack_from('<III',b,pos); pos+=12
            inst=np.frombuffer(b,'<f2',cnt*nval,pos).reshape(cnt,nval).astype(np.float32); pos+=cnt*nval*2
            if verbose and bi<2: print('   blk',(cx,cy,cz),(ex,ey,ez),z0,cnt,nval); print(inst[:2].round(2))
            out.append((name,(cx,cy,cz,ex,ey,ez),inst))
    assert pos==len(b),(pos,len(b))
    return out
if __name__=='__main__':
    r=parse(os.path.join(GD,'tamrielx0003y-001.cgid'),True)
    print(len(r),sum(len(i) for _,_,i in r))
