"""Native geometry and reversible replacement helpers for V14."""
import bpy,numpy as np
import v11lib as B
L=B.L;M=B.M;I=B.I
box=B.box;rod=B.rod;tube=B.tube;cyl=B.cyl;ring=B.ring;beam=B.beam;text=B.text
world=B.world;bounds=B.bounds;ty=B.ty;yc=B.yc
R={'revision':14,'retained':[],'counts':{},'ground':{},'catenary':{}}
def count(k,n=1):R['counts'][k]=R['counts'].get(k,0)+n
def col(key):return L.collection('V14_'+key)
def material(key,color,rough=.7,metal=0,noise=0):
 m=B.mat(key,color,rough,metal,noise=noise);m.name='V14 | '+key;return m
def setup():
 for key in ['steel','paint','cream','white','dark','rubber','red','orange','green','blue','yellow','copper','mint','wood','bronze','concrete','granite','pale_stone','floor','glass','window','lamp','soil','hedge']:
  I[key]=len(M);M.append(bpy.data.materials['V11 | '+key])
 for k,c,n in [('asphalt',(.085,.09,.092),65),('paving',(.39,.40,.37),35),('mortar',(.35,.32,.26),25),('brick_a',(.29,.115,.058),16),('brick_b',(.38,.17,.083),16),('brick_c',(.24,.105,.057),16),('brick_d',(.35,.135,.074),16),('soffit',(.22,.24,.23),8),('road_patch',(.12,.125,.12),55),('shutter',(.42,.44,.40),0),('drain',(.095,.10,.09),0)]:material(k,c,noise=n)
def build(mb,name,group,kind=None,**props):
 if not mb.f:return
 o=mb.build('V14 '+name,col(group),M);o['V14_kind']=kind or group
 for k,v in props.items():o[k]=v
 return o
def retire(o):
 name=o.name;cs=list(o.users_collection);o.name=name+' [before V14]';o['V14_original_name']=name
 for c in cs:c.objects.unlink(o)
 c=col('Replaced_hidden');c.objects.link(o);c.hide_render=True;c.hide_viewport=True;o.hide_render=True;o.hide_viewport=True
 R['retained'].append({'original':name,'retained':o.name,'collections':[c.name for c in cs]})
def copy_replace(o):
 name=o.name;cs=list(o.users_collection);q=o.copy();q.data=o.data.copy();retire(o);q.name=name
 for c in cs:c.objects.link(q)
 q.hide_render=False;q.hide_viewport=False;q['V14_modified_copy']=True;return q
def component_labels(o):
 v=world(o);lab=np.arange(len(v));ed=np.empty(len(o.data.edges)*2,dtype=np.int32);o.data.edges.foreach_get('vertices',ed);ed=ed.reshape(-1,2)
 for _ in range(120):
  old=lab.copy();m=np.minimum(lab[ed[:,0]],lab[ed[:,1]]);np.minimum.at(lab,ed[:,0],m);np.minimum.at(lab,ed[:,1],m);lab=lab[lab]
  if np.array_equal(lab,old):break
 roots,inv=np.unique(lab,return_inverse=True);lo=np.full((len(roots),3),np.inf);hi=np.full((len(roots),3),-np.inf)
 np.minimum.at(lo,inv,v);np.maximum.at(hi,inv,v)
 return v,inv,lo,hi
