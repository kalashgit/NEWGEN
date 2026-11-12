#!/usr/bin/env python3
"""LAST LIGHT V3 draft recipe -> physically exported GLB candidate meshes.
Geometry is procedural/provisional; not visual-verified or golden approved.
Works without Blender/GPU using numpy and trimesh.
"""
import os,sys,json,math,hashlib,argparse,zipfile,collections,time,csv,traceback
import numpy as np
import trimesh
from trimesh.visual.material import PBRMaterial

INPUT=os.environ.get('NEWGEN_LAST_LIGHT_CATALOG', 'LAST_LIGHT_4347_3D_MESH_RECIPES_V3.jsonl')
ROOT=os.environ.get('NEWGEN_LAST_LIGHT_OUTPUT', 'build/last_light_meshes')

def clamp_dims(v):
    try: x=np.array(v,dtype=float); return np.clip(np.nan_to_num(x,nan=.12),.004,60.0)
    except: return np.array([.12,.12,.12])

def seednum(s): return int(hashlib.sha256(str(s).encode()).hexdigest()[:8],16)

def uvball(ext,mode='organic',seed=0):
    m=trimesh.creation.icosphere(subdivisions=1 if mode=='faceted' else 2, radius=1)
    v=m.vertices.copy();
    if mode=='organic':
        zz=v[:,2];
        v[:,0]*=(1+.07*np.sin(3*zz+seed%5));v[:,1]*=(1+.05*np.cos(4*zz+seed%7));
        v[:,2]*=(1+.04*np.sin(3*v[:,0]+seed%11));
    m.vertices=v*np.array(ext)/2
    return m

def bblock(ext,shape='box'):
    ext=np.maximum(ext,.001)
    m=trimesh.creation.box(extents=ext)
    if shape=='bevel':
        # Eight-corner parametric bevel using truncated cube corners, not a featureless block.
        x,y,z=ext/2; e=min(ext)*.1
        if e>0:
            p=[]
            for k in [-1,1]:
                for j in [-1,1]:
                    for i in [-1,1]:
                        p.extend([[i*(x-e),j*y,k*z],[i*x,j*(y-e),k*z],[i*x,j*y,k*(z-e)]])
            try: m=trimesh.convex.convex_hull(np.array(p))
            except: pass
    return m

def lathe(ext,kind='bottle',hollow=False):
    rx,ry,h=np.maximum(ext,[.004,.004,.005]); r=min(rx,ry)/2
    if kind=='bottle':
        prof=[(0,0),(.78*r,0),(.92*r,.06*h),(r,.16*h),(r,.67*h),(.92*r,.77*h),(.45*r,.85*h),(.36*r,.95*h),(.36*r,h),(0,h)]
    elif kind=='bowl':
        prof=[(0,.04*h),(.35*r,.04*h),(.6*r,.12*h),(.89*r,.72*h),(r,h),(.86*r,h),(.62*r,.6*h),(.28*r,.2*h),(0,.18*h)]
    elif kind=='can':
        prof=[(0,0),(.92*r,0),(r,.05*h),(r,.94*h),(.92*r,h),(0,h)]
    elif hollow:
        prof=[(0,0),(.94*r,0),(r,.06*h),(r,.92*h),(.95*r,h),(.82*r,h),(.79*r,.17*h),(0,.17*h)]
    else:
        prof=[(0,0),(.8*r,0),(r,.1*h),(r,.92*h),(.9*r,h),(0,h)]
    try:
        m=trimesh.creation.revolve(np.array(prof),sections=16)
    except: m=trimesh.creation.cylinder(radius=r,height=h,sections=16)
    m.apply_scale([rx/(2*r),ry/(2*r),1]);m.apply_translation([0,0,-h/2]);return m

def ring(ext):
    rx,ry,h=np.maximum(ext,[.006,.006,.003]);
    radius=max(.003,min(rx,ry)/2*.75);thick=max(.002,min(h, radius*.18));
    try:m=trimesh.creation.torus(radius,thick,major_sections=20,minor_sections=7)
    except:m=trimesh.creation.annulus(radius*.68,radius,height=thick,sections=20)
    m.apply_scale([rx/(2*(radius+thick)),ry/(2*(radius+thick)),1]);return m

def bentbar(ext,seed=0,taper=False):
    x,y,z=np.maximum(ext,[.002,.002,.003]);n=6;k=9;zv=np.linspace(-z/2,z/2,n);verts=[];faces=[]
    for i,t in enumerate(zv):
        wiggle=.08*x*np.sin(i*.75+(seed%6))
        for j in range(k):
            a=2*np.pi*j/k;radius=(.7 if taper else 1)*(.6+.4*(1-i/(n-1)) if taper else 1)
            verts.append([(x/2)*radius*math.cos(a)+wiggle,(y/2)*radius*math.sin(a),t])
    for i in range(n-1):
        for j in range(k):
            a=i*k+j;b=i*k+(j+1)%k;c=(i+1)*k+j;d=(i+1)*k+(j+1)%k
            faces.extend([(a,b,c),(b,d,c)])
    verts+= [[0,0,-z/2],[0,0,z/2]]
    for j in range(k): faces.extend([(n*k,j,(j+1)%k),(n*k+1,(n-1)*k+(j+1)%k,(n-1)*k+j)])
    return trimesh.Trimesh(vertices=verts,faces=faces,process=False)

def blade(ext,seed=0):
    x,y,z=np.maximum(ext,[.005,.003,.005]);
    # 2D wedge/edge across X, with beveled, sharpened leading edge, not a box
    verts=np.array([[-x/2,-y*.4,-z/2],[-x/2,+y*.4,-z/2],[-x/2,-y*.4,z/2],[-x/2,+y*.4,z/2],[.15*x,-y*.25,-z/2],[.15*x,+y*.25,-z/2],[.15*x,-y*.25,z/2],[.15*x,+y*.25,z/2],[x/2,0,-.45*z],[x/2,0,.45*z]])
    faces=np.array([[0,2,4],[2,6,4],[1,5,3],[3,5,7],[4,6,8],[6,9,8],[5,8,7],[7,8,9],[0,1,2],[2,1,3],[0,4,1],[1,4,5],[2,3,6],[3,7,6],[6,7,9],[4,8,5]])
    return trimesh.Trimesh(vertices=verts,faces=faces,process=True)

def flatcloth(ext,seed=0):
    w,d,h=np.maximum(ext,[.003,.003,.003]); nx=5; ny=5; v=[];f=[]
    for j in range(ny+1):
        for i in range(nx+1):
            xx=(i/nx-.5)*w;yy=(j/ny-.5)*d
            zz=.06*h*math.sin((i+j*.7+seed%4)*1.7)
            v.append([xx,yy,zz])
    for j in range(ny):
        for i in range(nx):
            a=j*(nx+1)+i;b=a+1;c=a+nx+1;d1=c+1;f.extend([(a,b,c),(b,d1,c),(c,b,a),(c,d1,b)])
    return trimesh.Trimesh(vertices=np.array(v),faces=np.array(f),process=False)

def polyrock(ext,seed=0):
    rng=np.random.default_rng(seed); m=trimesh.creation.icosphere(subdivisions=1,radius=1)
    vertices=m.vertices.copy();vertices*=rng.uniform(.8,1.17,(len(vertices),1));m.vertices=vertices*np.array(ext)/2;return m

def jacket(ext,part='body',seed=0):
    x,y,z=np.maximum(ext,[.005,.005,.005]);
    # construct torsos with narrowed waist and prominent shoulders
    if 'sleeve' in part or 'leg' in part: return bentbar(ext,seed,True)
    # tapered trapezoid volume
    verts=np.array([[-.38*x,-.42*y,-z/2],[.38*x,-.42*y,-z/2],[.38*x,.42*y,-z/2],[-.38*x,.42*y,-z/2],[-x/2,-y/2,z/2],[x/2,-y/2,z/2],[x/2,y/2,z/2],[-x/2,y/2,z/2]])
    faces=[[0,2,1],[0,3,2],[4,5,6],[4,6,7],[0,1,5],[0,5,4],[1,2,6],[1,6,5],[2,3,7],[2,7,6],[3,0,4],[3,4,7]]
    return trimesh.Trimesh(vertices=verts,faces=faces,process=True)

def material_for(slot,record,seed):
    txt=(str(slot)+' '+record['interpretation']['archetype']+' '+record['product_name']).lower()
    if 'avocado_peel' in txt:return PBRMaterial(name=str(slot),baseColorFactor=(46,91,42,255),metallicFactor=0,roughnessFactor=.8,doubleSided=True)
    if 'avocado_flesh' in txt:return PBRMaterial(name=str(slot),baseColorFactor=(192,214,113,255),metallicFactor=0,roughnessFactor=.72,doubleSided=True)
    if 'avocado_pit' in txt:return PBRMaterial(name=str(slot),baseColorFactor=(118,67,32,255),metallicFactor=0,roughnessFactor=.48,doubleSided=True)
    if slot=='organic_cap':return PBRMaterial(name=str(slot),baseColorFactor=(105,82,48,255),metallicFactor=0,roughnessFactor=.78,doubleSided=True)
    state=record['interpretation'].get('object_state_tokens') or []
    if any(x in txt for x in ['metal','steel','iron','blade','aluminium','brass','silver','gold','copper','chrome','armor']): col=(135,144,153,255);met=.68;rough=.45
    elif any(x in txt for x in ['wood','plank','bark','haft','handle']): col=(127,88,57,255);met=.0;rough=.77
    elif any(x in txt for x in ['leaf','plant','stem','grass','zucchini','peel','foliage']):col=(88,127,62,255);met=0;rough=.82
    elif any(x in txt for x in ['skin','flesh','food','fruit','meat','dough','organic','seed']):col=(173,136,88,255);met=0;rough=.68
    elif any(x in txt for x in ['cloth','fabric','leather','canvas','nylon','thread','seam','garment','sleeve']):col=(92,107,97,255);met=0;rough=.9
    elif any(x in txt for x in ['glass','lens','transparent']):col=(134,179,192,210);met=.0;rough=.17
    elif any(x in txt for x in ['plastic','polymer','rubber']):col=(73,83,89,255);met=0;rough=.7
    elif any(x in txt for x in ['bone','ivory','tooth']):col=(209,198,169,255);met=0;rough=.73
    elif any(x in txt for x in ['stone','rock','ore','concrete','brick']):col=(120,116,110,255);met=0;rough=.9
    elif any(x in txt for x in ['paper','cardboard','label','book','page']):col=(189,169,128,255);met=0;rough=.83
    else:col=(113,118,112,255);met=0;rough=.7
    if 'red' in txt: col=(164,58,50,255)
    if 'blue' in txt: col=(52,98,156,255)
    if 'pink' in txt: col=(187,101,132,255)
    if 'yellow' in txt:col=(203,165,60,255)
    if 'black' in txt:col=(56,57,61,255)
    if 'white' in txt:col=(206,206,196,255)
    if 'brown' in txt:col=(123,81,55,255)
    if 'rotten' in state or 'burnt' in state or 'charred' in state: col=tuple(max(20,int(c*.65)) for c in col[:3])+(255,)
    if 'rusty' in state: col=(129,74,48,255)
    return PBRMaterial(name=str(slot),baseColorFactor=col,metallicFactor=met,roughnessFactor=rough,doubleSided=True)

def is_enabled(pt,rec):
    e=(pt.get('enabled_if') or 'always').lower();name=rec['product_name'].lower();states=[str(t).lower() for t in (rec['interpretation'].get('object_state_tokens') or [])]
    if e in ('always','true','yes','') or e.startswith('optional'):return True
    if any(s in e for s in ['only if opened','if opened','if open','visible hollow']):return 'open' in name or 'opened' in states
    if 'if broken' in e: return 'broken' in name or 'damaged' in name
    if 'if state' in e: return bool(states)
    if 'when named' in e: return any(t in name for t in ['handle','lid','strap','neck','sleeve','pocket','stem','blade','horn','cap'])
    if 'if applicable' in e:return False  # avoid invented pedestals/parts
    if 'when visible' in e or 'when present' in e:return False
    if 'if biologically appropriate' in e: return rec['interpretation']['archetype'] in ('fruit','seed','root_veg','mushroom','zucchini')
    return True

def make_part(pt,rec,seed):
    bbox=clamp_dims(rec['coordinates_and_scale'].get('estimated_bbox_xyz_m'))
    c=np.asarray(pt.get('center_normalized',[0,0,.5]),dtype=float);e=clamp_dims(pt.get('extent_normalized',[1,1,.5]))
    if len(c)!=3 or len(e)!=3:return None
    c=np.nan_to_num(c);e=np.minimum(e,4)
    ext=np.maximum(bbox*e,.003)
    op=(pt.get('operator') or 'source_guided_mesh').lower();part=(pt.get('part_id') or '').lower();arch=rec['interpretation']['archetype'];
    # All outputs use real triangulated volumes or intentionally double-sided sheets.
    if 'torus' in op or 'ring' in op or any(k in op for k in ['loop','collar','annular','aperture_rim']):
        m=ring(ext)
    elif any(k in op for k in ['lathe','hollow_cylinder','hollow_dome','bowl','vessel','hollow_shell']):
        kind='bottle' if arch in ('bottle','jar') else 'bowl' if arch in ('bowl','plate','pan') else 'can' if arch in ('can',) else 'cup'
        m=lathe(ext,kind,hollow=True)
    elif any(k in op for k in ['sweep','curve','fiber','cord','rope','rod','tube','cylinder','capsule','axle','strand','limb','leg','stem','staff','shaft','needle','wire','tine','spike']):
        if any(k in op for k in ['paired','four','five']):
            # Use a single tube here; procedural duplications below.
            m=bentbar(ext,seed,True)
        else:m=bentbar(ext,seed, 'taper' in op or 'needle' in op or 'stem' in op)
    elif any(k in op for k in ['blade','wedge','profile_extrude','profile_extrude_taper','extruded_profile','sharp','head_eye']):
        m=blade(ext,seed)
    elif any(k in op for k in ['cloth','sheet','surface','drape','ribbon','folded_plane','fabric','page','panel_patch','patch','inset_surface','decal','crease','strap','band']):
        if 'box' in op or 'shell' in op or 'garment' in op or 'tube' in op or 'inflated' in op:
            m=jacket(ext,part,seed)
        else:m=flatcloth(ext,seed)
    elif any(k in op for k in ['rock','fractur','polyhedron','gem','faceted','stone','crystal']):
        m=polyrock(ext,seed)
    elif any(k in op for k in ['organic','anatomical','ellipsoid','sphere','ovoid','lobed','sculpt','food','soft_volume','body','pear','subdiv','rounded','bulb','pear']):
        m=uvball(ext,'organic',seed)
    elif any(k in op for k in ['box','prism','block','slab','beam','cuboid','brick','solid','frame','plate','extrusion','bevel','hard_surface']):
        m=bblock(ext,'bevel' if 'bevel' in op or 'rounded' in op else 'box')
    elif any(k in op for k in ['boolean','cut','cavity','hole','inset']):
        m=lathe(ext,'cup',hollow=True) if arch in ('cup','bowl','pot','bucket','jar','bottle') else bblock(ext,'bevel')
    else:
        if arch in ('fruit','food','animal','meat','ore','fish','bone','zucchini','head_specimen','mushroom','root_veg','plush','seed'):m=uvball(ext,'organic',seed)
        elif arch in ('bottle','jar','cup','can','pot','bucket','bowl'):m=lathe(ext,'cup',True)
        elif arch in ('axe','knife','sword','spear','tool_head'):m=blade(ext,seed)
        elif arch in ('clothes','shirt','pants','jacket','dress','hat','glove','skirt'):m=jacket(ext,part,seed)
        else:m=bblock(ext,'bevel')
    m.apply_translation(bbox*c)
    # clamp overshoot instead of fake precise positioning
    return m

def superellipsoid(ext,exponent=.55,seed=0,top_taper=0.0):
    """Smooth rounded fabric, leather and accessory bodies from closed superquadric."""
    m=trimesh.creation.icosphere(subdivisions=2,radius=1);v=m.vertices.copy()
    v=np.sign(v)*np.power(np.abs(v),exponent)
    # narrow upper cap for backpack and natural pouch shaping
    v[:,:2]*=(1-top_taper*np.clip(v[:,2],0,1))[:,None]
    v[:,0]*=1+0.03*np.sin(v[:,2]*4+seed%4)
    m.vertices=v*np.maximum(ext,.002)/2
    return m

def arc_ribbon(start,finish,width,depth=.006,outward=.03,seg=10):
    """Curved vertical band with volume. Endpoints may be 3D; backs of straps stay attached."""
    p0=np.asarray(start,float);p1=np.asarray(finish,float)
    v=[];faces=[]
    for i in range(seg+1):
        t=i/seg;p=p0*(1-t)+p1*t
        p=p+np.array([0,outward*np.sin(np.pi*t),0])
        for d in [-depth/2,depth/2]:
            for w in [-width/2,width/2]:v.append([p[0]+w,p[1]+d,p[2]])
    for i in range(seg):
        for j,k in [(0,1),(2,3),(0,2),(1,3)]:
            a=i*4+j;b=i*4+k;c=(i+1)*4+j;d=(i+1)*4+k
            faces.extend([(a,b,c),(b,d,c)])
    for j in range(4):faces.extend([(j,(j+1)%4,4+j),(4+j,(j+1)%4,4+(j+1)%4)])
    return trimesh.Trimesh(vertices=v,faces=faces,process=False)

def cylinder_between(a,b,r0,r1=None,sections=12):
    a=np.asarray(a,float);b=np.asarray(b,float)
    vec=b-a;length=np.linalg.norm(vec)
    if length<1e-5:return uvball([.01,.01,.01])
    r0=max(r0,.002)
    m=trimesh.creation.cone(radius=r0,height=length,sections=sections) if r1==0 else trimesh.creation.cylinder(radius=r0,height=length,sections=sections)
    tf=trimesh.geometry.align_vectors([0,0,1],vec/length)
    m.apply_transform(tf);m.apply_translation((a+b)/2)
    return m

def flat_profile(poly,thickness):
    """Extrude a closed, moderately concave profile along Y with a guaranteed triangulated cap."""
    P=np.asarray(poly,float);n=len(P);y=thickness/2
    verts=np.vstack([np.column_stack([P[:,0],np.full(n,-y),P[:,1]]),np.column_stack([P[:,0],np.full(n,y),P[:,1]])])
    centroid=np.mean(P,axis=0)
    verts=np.vstack([verts,[[centroid[0],-y,centroid[1]],[centroid[0],y,centroid[1]]]])
    f=[]
    for i in range(n):
        j=(i+1)%n;f.extend([[2*n,j,i],[2*n+1,n+i,n+j],[i,j,n+i],[j,n+j,n+i]])
    return trimesh.Trimesh(vertices=verts,faces=f,process=False)

def food_gourd(B,seed=0):
    rx,ry,h=np.maximum(B,[.01,.01,.03]);ringnum=16;slices=15;verts=[];faces=[]
    for i in range(slices):
        t=i/(slices-1)
        radial=(.48+.43*np.sin(np.pi*t)**.6)*(1-.18*t)
        for j in range(ringnum):
            theta=2*np.pi*j/ringnum
            ridge=1+.04*np.cos(7*theta+seed%7)
            verts.append([.5*rx*radial*math.cos(theta)*ridge,.5*ry*radial*math.sin(theta)*ridge,h*t])
    for i in range(slices-1):
        for j in range(ringnum):
            a=i*ringnum+j;b=i*ringnum+(j+1)%ringnum;c=(i+1)*ringnum+j;d=(i+1)*ringnum+(j+1)%ringnum
            faces.extend([[a,b,c],[b,d,c]])
    verts.extend([[0,0,0],[0,0,h]])
    for j in range(ringnum):faces.extend([[slices*ringnum,(j+1)%ringnum,j],[slices*ringnum+1,(slices-1)*ringnum+j,(slices-1)*ringnum+(j+1)%ringnum]])
    return trimesh.Trimesh(vertices=verts,faces=faces,process=False)

def face_cap(B):
    # shallow hemispherical cup whose rim lies exactly across top of the tapered nut
    rx,ry,h=np.maximum(B,[.01,.01,.01]);R=min(rx,ry)/2
    prof=[(0,h*.09),(.62*R,h*.13),(.84*R,h*.26),(R,h*.37),(.94*R,h*.57),(.72*R,h*.76),(0,h*.83)]
    m=trimesh.creation.revolve(prof,sections=22)
    m.apply_scale([rx/(2*R),ry/(2*R),1]);return m

def shoe_outsole(B):
    x,y,z=B; # X = toe-heel length; front toe +X
    outline=[(-.5*x,-.32*y),(-.41*x,-.46*y),(.2*x,-.5*y),(.44*x,-.42*y),(.54*x,0),(.44*x,.42*y),(.2*x,.5*y),(-.41*x,.46*y),(-.5*x,.32*y)]
    v=[];f=[];n=len(outline);thick=z*.14
    for zz in [0,thick]:
        v.extend([[a,b,zz] for a,b in outline])
    # centered caps with fans
    v.extend([[0,0,0],[0,0,thick]])
    for i in range(n):
        j=(i+1)%n;f.extend([[2*n,j,i],[2*n+1,n+i,n+j],[i,j,n+j],[i,n+j,n+i]])
    return trimesh.Trimesh(vertices=v,faces=f,process=False)

def specialty_asset(rec,seed):
    ar=rec['interpretation']['archetype'];name=rec['product_name'].lower()
    B=clamp_dims(rec['coordinates_and_scale'].get('estimated_bbox_xyz_m'));x,y,z=B
    P=[]
    if ar=='bag' or 'backpack' in name or 'alicebag' in name or 'rucksack' in name:
        main=superellipsoid(B*np.array([.89,.86,.82]),.48,seed,top_taper=.20);main.apply_translation([0,.015*y,.52*z]);P.append(('main_body',main,'canvas'))
        front=superellipsoid(B*np.array([.63,.29,.35]),.54,seed+2);front.apply_translation([0,-.42*y,.35*z]);P.append(('front_pocket',front,'canvas'))
        flap=superellipsoid(B*np.array([.74,.55,.20]),.48,seed+5);flap.apply_translation([0,-.04*y,.86*z]);P.append(('top_flap',flap,'leather'))
        for sign in [-1,1]:
            s=np.array([sign*.30*x,.46*y,.86*z]);e=np.array([sign*.30*x,.47*y,.15*z]);
            P.append((('L' if sign<0 else 'R')+'_shoulder_strap',arc_ribbon(s,e,.12*x,.03*y,.26*y),'nylon'))
        P.append(('carry_loop',arc_ribbon([-.10*x,.14*y,.92*z],[.10*x,.14*y,.92*z],.07*x,.05*y,.15*z),'nylon'))
        P.append(('zipper',arc_ribbon([-.27*x,-.51*y,.52*z],[.27*x,-.51*y,.52*z],.025*z,.02*y,.01*y),'metal'))
        return P
    if ar in ('jacket','shirt','dress','armor','pants','skirt'):
        if ar=='pants':
            waist=superellipsoid(B*np.array([.72,.86,.2]),.55,seed);waist.apply_translation([0,0,.88*z]);P.append(('waist',waist,'fabric'))
            for sign in [-1,1]:
                leg=cylinder_between([sign*.18*x,0,.83*z],[sign*.2*x,0,.12*z],.14*x)
                P.append((('left' if sign<0 else 'right')+'_leg',leg,'fabric'))
            return P
        if ar=='skirt':
            base=lathe(B*np.array([.87,.87,.84]),'cup',True);base.apply_translation([0,0,.48*z]);return [('skirt',base,'fabric')]
        body=jacket(B*np.array([.68,.78,.80]),'torso',seed);body.apply_translation([0,0,.49*z]);P.append(('torso',body,'fabric'))
        # two sleeves form distinctive shoulders and taper down
        if ar not in ('dress',):
            for sign in [-1,1]:
                shoulder=[sign*.33*x,0,.79*z];cuff=[sign*.47*x,0,.34*z]
                sleeve=cylinder_between(shoulder,cuff,.12*x)
                P.append((('left' if sign<0 else 'right')+'_sleeve',sleeve,'fabric'))
        coll=ring(B*np.array([.26,.42,.07]));coll.apply_translation([0,0,.88*z]);P.append(('neckline',coll,'fabric'))
        if ar in ('jacket','armor'):
            seam=bblock(B*np.array([.022,.03,.58]));seam.apply_translation([0,-.4*y,.52*z]);P.append(('front_closure',seam,'metal'))
        return P
    if ar=='shoe':
        sole=shoe_outsole(B);P.append(('sole',sole,'rubber'))
        main=superellipsoid(B*np.array([.96,.90,.68]),.64,seed);main.apply_translation([0,0,.50*z]);P.append(('upper',main,'leather'))
        toe=superellipsoid(B*np.array([.30,.87,.30]),.60,seed+4);toe.apply_translation([.33*x,0,.40*z]);P.append(('toe',toe,'rubber'))
        tongue=flatcloth(B*np.array([.31,.48,.015]),seed);tongue.apply_translation([-.13*x,-.32*y,.84*z]);P.append(('tongue',tongue,'fabric'))
        for j in range(3):
            lace=arc_ribbon([(-.22+.1*j)*x,-.49*y,.70*z],[(-.22+.1*j)*x,.49*y,.70*z],.027*x,.018*y,.03*z)
            P.append(('lace'+str(j),lace,'thread'))
        return P
    if ar in ('zucchini','root_veg') or 'zucchini' in name:
        body=food_gourd(B,seed);P.append(('fruit_body',body,'peel'))
        stem=cylinder_between([0,0,.95*z],[0,0,1.02*z],.12*min(x,y));P.append(('stem',stem,'stem'))
        return P
    if name=='acorn':
        nut=superellipsoid(B*np.array([.67,.72,.76]),.8,seed);nut.apply_translation([0,0,.40*z]);
        c=face_cap(B*np.array([.76,.78,.29]));c.apply_translation([0,0,.66*z])
        st=cylinder_between([0,0,.85*z],[0,0,1.06*z],.04*x)
        return [('nut',nut,'organic_shell'),('cap',c,'organic_cap'),('stem',st,'organic_stem')]
    if ar=='axe':
        shaft=bentbar(B*np.array([.14,.13,.96]),seed,True);shaft.apply_translation([0,0,.50*z]);
        # Body extends from handle to blade with flared cutting edge
        poly=[(-.50*x,-.065*z),(-.12*x,-.11*z),(.34*x,-.165*z),(.48*x,-.13*z),(.5*x,.17*z),(.34*x,.18*z),(-.12*x,.10*z),(-.50*x,.075*z)]
        head=flat_profile(poly,.52*y);head.apply_translation([.22*x,0,.84*z]);return [('haft',shaft,'wood'),('head',head,'metal')]
    if 'avocado' in name:
        rind=superellipsoid(B*np.array([.96,.72,.92]),.8,seed);rind.apply_translation([0,.08*y,.50*z])
        flesh=superellipsoid(B*np.array([.79,.15,.79]),.75,seed);flesh.apply_translation([0,-.30*y,.50*z]);P=[('rind',rind,'avocado_peel'),('flesh',flesh,'avocado_flesh')]
        if 'seedless' not in name:
            pit=uvball(B*np.array([.32,.26,.34]),'organic',seed);pit.apply_translation([0,-.52*y,.45*z]);P.append(('pit',pit,'avocado_pit'))
        return P
    return None

def improve_asset_specific(rec,parts):
    name=rec['product_name'].lower();arch=rec['interpretation']['archetype']
    # Special case: acorn must be an acorn, not a single generic fruit ball.
    if name=='acorn':
        B=clamp_dims(rec['coordinates_and_scale']['estimated_bbox_xyz_m']);
        nut=uvball(B*np.array([.65,.78,.65]),'organic',2);nut.apply_translation([0,0,B[2]*.4]);
        cap=lathe(B*np.array([.75,.82,.22]),'bowl',False);cap.apply_translation([0,0,B[2]*.8]);
        stem=bentbar(B*np.array([.08,.09,.22]),0,True);stem.apply_translation([0,0,B[2]*.99]);
        return [('nut',nut,'organic_shell'),('cap',cap,'organic_shell'),('stem',stem,'organic_stem')]
    # Avocado halves: cut face, darker rind and prominent pit or cavity
    if 'avocado' in name:
        B=clamp_dims(rec['coordinates_and_scale']['estimated_bbox_xyz_m']);
        rind=uvball(B*np.array([.95,.7,.9]),'organic',6);rind.apply_translation([0,B[1]*.09,B[2]*.5]);
        flesh=uvball(B*np.array([.79,.14,.74]),'organic',3);flesh.apply_translation([0,-B[1]*.28,B[2]*.5]);
        out=[('rind',rind,'peel'),('flesh',flesh,'flesh')]
        if 'no pit' not in name and 'seedless' not in name:
            pit=uvball(B*np.array([.32,.22,.3]),'organic',7);pit.apply_translation([0,-B[1]*.39,B[2]*.43]);out.append(('pit',pit,'seed'))
        return out
    # Axes: distinctive lateral cutting head and long shaft; specified handle/head ratio.
    if arch=='axe':
        B=clamp_dims(rec['coordinates_and_scale']['estimated_bbox_xyz_m']);
        shaft=bentbar(B*np.array([.16,.18,.98]),seednum(name),True);shaft.apply_translation([0,0,B[2]*.5]);
        head=blade(B*np.array([1.0,.52,.23]),seednum(name));head.apply_translation([B[0]*.23,0,B[2]*.84]);
        return [('haft',shaft,'wood'),('blade',head,'blade')]
    return parts

def build(rec, out_path):
    no=int(rec['asset_number']);seed=seednum(rec['reference_id']);g=rec['mesh_construction'];ar=rec['interpretation'];
    parts=[];skipped=[]
    for i,pt in enumerate(g.get('part_graph',[])):
        if not is_enabled(pt,rec): skipped.append(pt.get('part_id'));continue
        try:
            m=make_part(pt,rec,seed+i)
            if m is None or not len(m.faces): raise ValueError('empty geometry')
            parts.append((pt.get('part_id') or 'part'+str(i),m,pt.get('material_role') or 'body'))
        except Exception as e: skipped.append((pt.get('part_id'),str(e)))
    special=specialty_asset(rec,seed)
    parts=special if special is not None else improve_asset_specific(rec,parts)
    if not parts:
        B=clamp_dims(rec['coordinates_and_scale'].get('estimated_bbox_xyz_m'))
        fallback=uvball(B,'organic',seed) if ar['archetype'] in ('fruit','food','animal','meat','ore','fish','bone','seed','zucchini','plush') else bblock(B,'bevel')
        fallback.apply_translation([0,0,B[2]/2]);parts=[('fallback_proxy',fallback,'proxy')]
    scene=trimesh.Scene();faces=0;w=0;notes=[]
    for i,(pn,m,role) in enumerate(parts):
        m.remove_unreferenced_vertices()
        # fixed material slots, original PBR, no third-party texture use
        mat=material_for(role,rec,seed+i)
        m.visual=trimesh.visual.TextureVisuals(material=mat)
        scene.add_geometry(m,geom_name=f"LL{no:04d}__{pn}",node_name=f"LL{no:04d}__{pn}")
        faces+=len(m.faces);w+=int(m.is_watertight)
    data=scene.export(file_type='glb');
    if len(data)<200:raise RuntimeError('GLB output unexpectedly small')
    with open(out_path,'wb') as f:f.write(data)
    # Validate round trip, triangle count and existence, independent of export success
    rt=trimesh.load(out_path,force='scene',process=False)
    verified_parts=len(rt.geometry)
    if verified_parts==0: raise ValueError('GLB round-trip loaded with zero geometries')
    return {'asset_number':no,'asset_filename':rec['asset_filename'],'product_name':rec['product_name'],'recipe_id':rec['recipe_id'],'archetype':ar['archetype'],'generator_mode':g.get('generator_mode'),'output':os.path.basename(out_path),'bytes':os.path.getsize(out_path),'components':len(parts),'loaded_components':verified_parts,'triangles':faces,'watertight_parts':w,'skipped_conditions':';'.join(map(str,skipped)),'confidence':'UNVERIFIED_DRAFT','status':'GLB_EXPORTED_ROUNDTRIP_PASS','golden_approval':'NOT_APPROVED','source_url':rec['reference'].get('source_file_page'),'review_flag':'NEEDS_MANUAL_VISUAL_QA' if ar.get('classification_basis','').endswith('unverified') or ar.get('representation_only') or g.get('generator_mode')=='manual_review_required' else 'RECIPE_DERIVED_NOT_VISUAL_QA'}

def main():
    p=argparse.ArgumentParser();p.add_argument('--limit',type=int,default=0);p.add_argument('--start',type=int,default=1);p.add_argument('--input',default=INPUT);p.add_argument('--root',default=ROOT);args=p.parse_args()
    os.makedirs(args.root,exist_ok=True);d=os.path.join(args.root,'glb');os.makedirs(d,exist_ok=True)
    rows=[];errors=[];starttime=time.time()
    with open(args.input) as fp:
        for j,line in enumerate(fp):
            rec=json.loads(line);n=int(rec['asset_number']);
            if n<args.start:continue
            if args.limit and n>=args.start+args.limit:break
            op=os.path.join(d,f"LL-{n:04d}-{rec['product_name'].replace('/','_').replace(' ','_')[:60]}.glb")
            try:rows.append(build(rec,op))
            except Exception as exc:errors.append({'asset_number':n,'name':rec['product_name'],'error':str(exc)});print('ERR',n,str(exc),flush=True)
            if (n-args.start+1)%100==0:
                print('PROGRESS',n,'pass',len(rows),'fail',len(errors),'elapsed',round(time.time()-starttime),flush=True)
                with open(os.path.join(args.root,'build_progress.json'),'w') as f:json.dump({'processed':len(rows)+len(errors),'passed':len(rows),'errors':len(errors),'last_asset':n,'elapsed_s':int(time.time()-starttime)},f)
    if rows:
        with open(os.path.join(args.root,'build_manifest.csv'),'w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=rows[0].keys());w.writeheader();w.writerows(rows)
    with open(os.path.join(args.root,'failures.json'),'w') as f:json.dump(errors,f,indent=2)
    with open(os.path.join(args.root,'build_summary.json'),'w') as f:json.dump({'target':4347,'processed':len(rows)+len(errors),'passed':len(rows),'failed':len(errors),'elapsed_s':int(time.time()-starttime),'status':'candidate_geometry_only_not_golden','total_triangles':sum(x['triangles'] for x in rows),'total_mesh_bytes':sum(x['bytes'] for x in rows)},f,indent=2)
    print('FINISHED',len(rows),'passed',len(errors),'failed',round(time.time()-starttime),'seconds',flush=True)

if __name__=='__main__':main()
