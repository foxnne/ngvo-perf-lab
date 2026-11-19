import math, numpy as np
W,H=3440,1440
class Cam:
    def __init__(s, pos=(19157,-7419,-2970), yaw=270.0, pitch=-3.0, fov169=65.0, focal=None):
        s.pos=np.array(pos,float)
        s.focal=focal if focal else (W/2)/(math.tan(math.radians(fov169/2))*(W/H)/(16/9))
        y=math.radians(yaw); p=math.radians(pitch)
        s.f=np.array([math.sin(y)*math.cos(p), math.cos(y)*math.cos(p), math.sin(p)])
        s.r=np.array([math.cos(y), -math.sin(y), 0.0])
        s.u=np.cross(s.r, s.f)
    def project(s, P):
        d=np.asarray(P,float)-s.pos
        z=d@s.f; x=d@s.r; y=d@s.u
        return W/2+s.focal*x/z, H/2-s.focal*y/z, z
    def ray(s, px, py):
        v=s.f*s.focal+s.r*(px-W/2)+s.u*(H/2-py)
        return v/np.linalg.norm(v)
