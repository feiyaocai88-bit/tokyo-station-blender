import json, numpy as np
T=json.load(open('/home/claude/geo/v2/gsi_tracks_model.json'))
segs=[]
for t in T:
    if t['code'] not in (2802,2803): continue
    X=np.array(t['X']); Y=np.array(t['Y'])
    for k in range(len(X)-1): segs.append((X[k],Y[k],X[k+1],Y[k+1]))
segs=np.array(segs)
def crossings(xq):
    x0,y0,x1,y1=segs.T
    m=((x0-xq)*(x1-xq)<=0)&(x0!=x1)
    ys=y0[m]+(y1[m]-y0[m])*(xq-x0[m])/(x1[m]-x0[m])
    ys=np.sort(ys); out=[]
    for y in ys:
        if out and abs(out[-1]-y)<0.6: continue
        out.append(float(y))
    return np.array(out)
ORDER=['01','02','04','05','06','07','08','09','10','20','21','22','23','14','15','16','17','18','19']
SEED=[15.8,30.7,45.5,51.1,65.3,70.0,82.8,88.9,104.4,109.7,125.1,129.1,146.6,151.5,166.5,171.7,186.2,190.6,205.2]
def track(step=2.5, xmin=-262, xmax=262, gate=2.0):
    res={k:{0.0:v} for k,v in zip(ORDER,SEED)}
    for direction in (+1,-1):
        cur={k:v for k,v in zip(ORDER,SEED)}; slope={k:0.0 for k in ORDER}; lost={k:0 for k in ORDER}
        x=0.0
        while True:
            x+=direction*step
            if x<xmin or x>xmax: break
            cs=crossings(x)
            for k in ORDER:
                pred=cur[k]+slope[k]*step*direction
                if len(cs):
                    j=np.argmin(abs(cs-pred)); d=abs(cs[j]-pred)
                else: d=99
                if d<gate and lost[k]<8:
                    new=cs[j]; lost[k]=0
                else:
                    new=pred; lost[k]+=1
                slope[k]=0.7*slope[k]+0.3*((new-cur[k])/(step*direction))
                cur[k]=new; res[k][x]=(new, lost[k])
    return res
if __name__=="__main__":
    R=track()
    out={k:sorted([(x,(v if isinstance(v,float) else v[0]), (0 if isinstance(v,float) else v[1])) for x,v in R[k].items()]) for k in R}
    json.dump(out,open('/home/claude/geo/v2/gsi_tracked.json','w'))
    for x in range(-250,251,25):
        print("%5d "%x+" ".join("%6.1f%s"%(dict((a,b) for a,b,c in out[k])[float(x)], "*" if dict((a,c) for a,b,c in out[k])[float(x)] else " ") for k in ORDER))
