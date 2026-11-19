import struct,bisect,sys,json
def load(path):
    f=open(path,'rb'); rd=lambda fmt:struct.unpack(fmt,f.read(struct.calcsize(fmt)))
    fmt_,=rd('<i'); ver=rd('<4i'); nl,=rd('<i'); name=f.read(nl); ps,=rd('<i'); cnt,=rd('<i')
    pid=0; poff=0; out=[]
    for _ in range(cnt):
        t=f.read(1)[0]; lo=t&0xF; hi=t>>4
        if lo==0: i,=rd('<Q')
        elif lo==1: i=pid+1
        elif lo==2: i=pid+f.read(1)[0]
        elif lo==3: i=pid-f.read(1)[0]
        elif lo==4: i=pid+rd('<H')[0]
        elif lo==5: i=pid-rd('<H')[0]
        elif lo==6: i,=rd('<H')
        else: i,=rd('<I')
        tp=(poff//ps) if (hi&8) else poff
        h=hi&7
        if h==0: o,=rd('<Q')
        elif h==1: o=tp+1
        elif h==2: o=tp+f.read(1)[0]
        elif h==3: o=tp-f.read(1)[0]
        elif h==4: o=tp+rd('<H')[0]
        elif h==5: o=tp-rd('<H')[0]
        elif h==6: o,=rd('<H')
        else: o,=rd('<I')
        if hi&8: o*=ps
        out.append((o,i)); pid=i; poff=o
    out.sort(); return out
if __name__=='__main__':
    db=load(sys.argv[1]); offs=[o for o,_ in db]
    for a in sys.argv[2:]:
        v=int(a,16); k=bisect.bisect_right(offs,v)-1
        print(a,'-> id',db[k][1],'func+0x%X'%(v-db[k][0]),'(start 0x%X)'%db[k][0])
