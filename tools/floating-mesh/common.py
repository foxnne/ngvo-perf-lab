import pickle, os, struct, math
import numpy as np
HERE=os.path.dirname(os.path.abspath(__file__))
HM=r'C:\Users\foxnn\dev\terrain-heightmap\mod\textures\terrain\HeightMaps\Tamriel.Terrain.HeightMap.-57.-43.61.50.-4629.4924.dds'
def load():
    return pickle.load(open(os.path.join(HERE,'refs.pkl'),'rb'))
def load_hm():
    b=open(HM,'rb').read()
    h,w=struct.unpack_from('<II',b,12)
    off=128+(20 if b[84:88]==b'DX10' else 0)
    raw=np.frombuffer(b,'<u2',w*h,off).reshape(h,w)
    return (raw.astype(np.float32)-32767)*8
MINX,MINY=-57*4096,-43*4096
def ground(hm,x,y):
    x=np.asarray(x,float); y=np.asarray(y,float)
    fi=(x-MINX)/128; fr=hm.shape[0]-1-(y-MINY)/128
    fi=np.clip(fi,0,hm.shape[1]-1.001); fr=np.clip(fr,0,hm.shape[0]-1.001)
    i=fi.astype(int); r=fr.astype(int); a=fi-i; b=fr-r
    return hm[r,i]*(1-a)*(1-b)+hm[r,i+1]*a*(1-b)+hm[r+1,i]*(1-a)*b+hm[r+1,i+1]*a*b
def final(hist):
    return hist[-1]
