"""Add visible mechanical details to the existing JR rolling-stock templates.
The original train bodies, wheel locations, formations and pantographs are retained.
"""
import bpy,math,numpy as np
from mathutils import Vector,Matrix
import v11lib as H
L=H.L

def run():
    masters={}
    for o in bpy.context.scene.objects:
        if o.instance_collection and (o.name.startswith('Track ') or o.name.startswith('V9 train') or o.get('V9_train')):
            masters[o.instance_collection.name]=o.instance_collection
    # V9 uses its own naming; collect all live instantiated vehicle templates explicitly.
    for o in bpy.context.scene.objects:
        c=o.instance_collection
        if c and any(s in c.name for s in ['E233','E235','N700','E5 car','panto variant','actual_car','V9 Green car']):masters[c.name]=c
    H.REPORT['rolling_stock_templates']={}
    for name,c in masters.items():
        mb=L.MeshBuilder();details=0
        objs=[o for o in c.all_objects if o.type=='MESH' and not o.hide_render]
        for o in objs:
            n=o.name.lower()
            if 'air spring' in n:
                lo,hi=H.bounds(o);p=(lo+hi)/2;r=max(hi[0]-lo[0],hi[1]-lo[1])/2
                if r>.6:continue
                for z in np.linspace(lo[2]+.025,hi[2]-.025,4):H.ring(mb,(p[0],p[1],z),r+.009,.017,'rubber',n=20)
                details+=1
            elif 'bogie sideframe' in n:
                lo,hi=H.bounds(o);p=(lo+hi)/2;a=o.rotation_euler.z
                F=Matrix.Translation(p)@Matrix.Rotation(a,4,'Z')
                for dx in (-.85,.85):
                    # Axleboxes, retaining bolt heads and a small damper linkage.
                    H.box(mb,(dx,0,-.03),(.28,.25,.25),'dark',F=F)
                    for yy in (-.14,.14):
                        pp=F@Vector((dx,yy,0))
                        H.rod(mb,pp,pp+F.to_3x3()@Vector((0,.04 if yy>0 else -.04,0)),.075,'steel',10)
                    H.beam(mb,F@Vector((dx-.2,0,-.08)),F@Vector((dx+.2,0,.12)),.08,.08,'steel')
                details+=1
            elif 'hvac' in n or 'roof air conditioning' in n:
                lo,hi=H.bounds(o);p=(lo+hi)/2;sx,sy=hi[0]-lo[0],hi[1]-lo[1]
                if sx>8 or sy>5:continue
                for xx in (-sx*.25,sx*.25):
                    rr=min(.45,sy*.32);cp=(p[0]+xx,p[1],hi[2]+.017)
                    H.cyl(mb,cp,rr,.035,'dark',24);H.ring(mb,(cp[0],cp[1],cp[2]+.027),rr,.018,'steel',n=24)
                    for q in np.arange(-rr+.04,rr,.10):
                        d=math.sqrt(max(0,rr*rr-q*q));H.rod(mb,(cp[0]-d,cp[1]+q,cp[2]+.035),(cp[0]+d,cp[1]+q,cp[2]+.035),.009,'steel',4)
                for xx in np.arange(lo[0]+.12,hi[0]-.1,.15):
                    for s in (-1,1):H.box(mb,(xx,p[1]+s*(sy/2+.008),p[2]),(.045,.02,(hi[2]-lo[2])*.6),'dark')
                details+=1
        # Collection-space dimensions of conventional JR cars are shared by the source.
        if ('E233' in name or 'E235' in name or 'panto variant' in name or 'actual_car' in name or 'Green' in name) and 'formation' not in name:
            for s in (-1,1):
                for x in np.arange(-8.7,8.8,1.55):
                    H.box(mb,(x,s*1.466,1.28),(.40,.016,.22),'steel')
                    for dx in (-.16,.16):H.box(mb,(x+dx,s*1.480,1.28),(.022,.013,.022),'dark')
                # Inter-car anti-fall ribs on the rear end; narrow and inside the existing width.
                for x in (-9.91,-9.85,-9.79):H.box(mb,(x,s*.72,2.05),(.035,.07,1.95),'rubber')
            if 'cab' in name.lower():
                for y in (-.27,.27):H.tube(mb,[(9.94,y,.83),(10.03,y,.66),(9.97,y+.07,.47)],.023,'rubber',8)
            details+=1
        if not mb.f:continue
        obj=mb.build('V11 rolling-stock fittings | '+name,c,H.M);obj['V11_kind']='jr_vehicle_detail'
        H.REPORT['rolling_stock_templates'][name]=details;H.count('jr_vehicle_templates_detailed')
    print('V11_ROLLING_STOCK_OK',len(H.REPORT['rolling_stock_templates']),flush=True)
