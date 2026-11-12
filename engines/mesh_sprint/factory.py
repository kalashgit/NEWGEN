#!/usr/bin/env python3
"""LAST LIGHT MESH SPRINT v0.1 — deterministic, CPU-first candidate GLB compiler.

No AI is invoked during production. User-supplied recipes and all generated content
are UNAPPROVED until both technical and human visual review. No source imagery is copied.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import importlib.util
import json
import math
import os
import re
import struct
import tempfile
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from functools import lru_cache
from pathlib import Path

import numpy as np
import trimesh

VERSION = 'newgen-mesh-sprint-0.3.2-geometry-pbr'
FAMILIES = ('avocado', 'backpack', 'axe', 'armor', 'shelf', 'bottle',
            'barrel', 'crate', 'helmet', 'medkit', 'chair', 'canister')
IDENT = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,110}\Z')
MAX_COMPONENTS = 80
MAX_VERTICES = 160000

COLORS = {
 'leaf': (42,89,39,255), 'leaf_light': (85,130,55,255), 'skin': (37,67,32,255),
 'flesh': (173,189,93,255), 'pit': (94,51,30,255), 'fabric': (71,86,78,255),
 'fabric_light': (110,120,97,255), 'fabric_dark': (39,46,43,255),
 'steel': (115,127,133,255), 'steel_dark': (49,61,68,255),
 'edge': (199,202,194,255), 'wood': (99,67,42,255),
 'wood_light': (153,111,70,255), 'black': (38,43,43,255),
 'leather': (95,58,39,255), 'red': (135,46,47,255), 'white': (197,201,184,255),
 'plastic': (181,175,139,255), 'glass': (110,155,143,240),
 'flesh_green':(105,145,55,255),'pit_shadow':(70,82,28,255),
 'pit_light':(146,94,56,255),'skin_dark':(25,53,29,255),
 'seam':(42,53,46,255),'stitch':(165,168,135,255),
 'wood_grain':(114,82,51,255),'wood_dark':(71,48,31,255),
 'olive': (102,104,68,255), 'paint': (70,86,96,255), 'paint_light': (122,130,126,255)
}

def digest(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()

def finite(v):
    return np.all(np.isfinite(v))

def require_vec(data, n, positive=False):
    if not isinstance(data, (list, tuple)) or len(data) != n:
        raise ValueError(f'Expected {n}-vector')
    result = np.asarray(data, dtype=float)
    if not finite(result) or np.max(np.abs(result)) > 500 or (positive and np.min(result) <= 0):
        raise ValueError('Invalid vector dimensions')
    return result

class MeshBuilder:
    def __init__(self,material_specs=None,preserve_parts=False):
        self.material_specs = material_specs or {}
        self.colors = dict(COLORS)
        for name,info in self.material_specs.items():
            rgba=info.get('pbr',{}).get('base_rgba',[])
            if len(rgba)!=4 or not all(isinstance(x,(int,float)) and 0<=x<=1 for x in rgba):
                raise ValueError('Invalid recipe PBR base_rgba: '+name)
            self.colors[name]=tuple(int(round(float(x)*255)) for x in rgba)
        self.groups = {}
        self.components = 0
        self.preserve_parts = bool(preserve_parts)
        self.part_records = []

    def add(self, material, vertices, faces, part_id=None):
        if material not in self.colors:
            raise ValueError(f'Unknown material {material}')
        v=np.asarray(vertices, dtype=np.float32)
        f=np.asarray(faces, dtype=np.int64)
        if v.ndim != 2 or v.shape[1] != 3 or f.ndim != 2 or f.shape[1] != 3 or not finite(v):
            raise ValueError('Invalid mesh array')
        if not len(f) or not len(v) or f.min()<0 or f.max()>=len(v):
            raise ValueError('Malformed mesh faces')
        self.groups.setdefault(material, []).append((v, f))
        safe_id = str(part_id) if part_id is not None else f'component_{self.components:04d}'
        if not IDENT.fullmatch(safe_id):
            raise ValueError('Invalid component name for GLB hierarchy')
        self.part_records.append((safe_id,material,v,f))
        self.components += 1
        if self.components > MAX_COMPONENTS:
            raise ValueError('Too many parts for fast lane')

    def box(self, loc, dims, material):
        x,y,z=require_vec(loc,3); dx,dy,dz=require_vec(dims,3,positive=True)/2
        v=np.array([[x+sx*dx,y+sy*dy,z+sz*dz] for sz in (-1,1) for sy in (-1,1) for sx in (-1,1)],dtype=float)
        # Face winding is outward by axis.
        f=[[0,2,3],[0,3,1],[4,5,7],[4,7,6],
           [0,1,5],[0,5,4],[2,6,7],[2,7,3],
           [0,4,6],[0,6,2],[1,3,7],[1,7,5]]
        self.add(material,v,f)

    def rings(self, profile, center, material, n=16, rx=1.0, ry=1.0):
        c=require_vec(center,3)
        if not 6 <= n <= 48 or len(profile)<2 or len(profile)>80: raise ValueError('Invalid lathe')
        prof=np.array(profile,dtype=float)
        if prof.shape[1]!=2 or not finite(prof) or (prof[:,1]<0).any(): raise ValueError('Invalid profile')
        theta=np.arange(n)*2*np.pi/n
        v=[]
        for z,r in prof:
            for a in theta: v.append([c[0]+r*rx*math.cos(a),c[1]+r*ry*math.sin(a),c[2]+z])
        f=[]
        for i in range(len(prof)-1):
            for j in range(n):
                a=i*n+j;b=i*n+(j+1)%n;d=(i+1)*n+j;e=(i+1)*n+(j+1)%n
                f.extend([[a,b,e],[a,e,d]])
        bottom=len(v);v.append([c[0],c[1],c[2]+prof[0][0]])
        top=len(v);v.append([c[0],c[1],c[2]+prof[-1][0]])
        for j in range(n):
            k=(j+1)%n
            f.extend([[bottom,k,j],[top,(len(prof)-1)*n+j,(len(prof)-1)*n+k]])
        self.add(material,v,f)

    def ellipsoid(self, loc, radii, material, segments=16, rings=9, boxiness=1.0):
        c=require_vec(loc,3); r=require_vec(radii,3,positive=True)
        if not 8<=segments<=48 or not 4<=rings<=32 or not .3<=boxiness<=3: raise ValueError('Invalid ellipsoid')
        def exp(a):return np.sign(a)*np.abs(a)**boxiness
        v=[]
        for t in range(rings+1):
            phi=-np.pi/2+np.pi*t/rings
            h=exp(math.cos(phi));vz=exp(math.sin(phi))
            for s in range(segments):
                a=2*np.pi*s/segments
                v.append(c+r*np.array([h*exp(math.cos(a)),h*exp(math.sin(a)),vz]))
        f=[]
        for t in range(rings):
            for s in range(segments):
                a=t*segments+s;b=t*segments+(s+1)%segments
                d=(t+1)*segments+s;e=(t+1)*segments+(s+1)%segments
                f.extend([[a,b,e],[a,e,d]])
        self.add(material,v,f)

    def tube(self, points, radius, material, sides=7):
        p=np.asarray(points,dtype=float)
        if p.ndim!=2 or p.shape[1]!=3 or len(p)<2 or len(p)>64 or not finite(p) or not 3<=sides<=24 or radius<=0: raise ValueError('Invalid tube')
        v=[]; f=[]
        for i,q in enumerate(p):
            tangent=p[min(i+1,len(p)-1)]-p[max(0,i-1)]
            tangent/=max(np.linalg.norm(tangent),1e-10)
            v1=np.cross(tangent,[0,1,0]);
            if np.linalg.norm(v1)<.05: v1=np.cross(tangent,[1,0,0])
            v1/=max(np.linalg.norm(v1),1e-10)
            v2=np.cross(tangent,v1)
            for j in range(sides):
                a=2*np.pi*j/sides
                v.append(q+radius*(v1*math.cos(a)+v2*math.sin(a)))
        for i in range(len(p)-1):
            for j in range(sides):
                a=i*sides+j;b=i*sides+(j+1)%sides;d=(i+1)*sides+j;e=(i+1)*sides+(j+1)%sides
                f.extend([[a,b,e],[a,e,d]])
        first=len(v);v.append(p[0]);last=len(v);v.append(p[-1])
        for j in range(sides):
            f.extend([[first,(j+1)%sides,j],[last,(len(p)-1)*sides+j,(len(p)-1)*sides+(j+1)%sides]])
        self.add(material,v,f)

    def polygon_prism(self, points_xz, depth, center_y, material):
        p=np.asarray(points_xz,dtype=float)
        if p.ndim!=2 or p.shape[1]!=2 or len(p)<3 or len(p)>60 or not finite(p) or not 0<depth<100:raise ValueError('Invalid polygon')
        # Ear-clipping in X/Z. Supports concave blade outlines.
        signed=sum(p[i,0]*p[(i+1)%len(p),1]-p[(i+1)%len(p),0]*p[i,1] for i in range(len(p)))
        if abs(signed)<1e-9: raise ValueError('Degenerate polygon')
        if signed < 0: p=p[::-1]
        ids=list(range(len(p)));tris=[]
        def cross(a,b,c):return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
        while len(ids)>3:
            ear=False
            for k in range(len(ids)):
                i,j,h=ids[k-1],ids[k],ids[(k+1)%len(ids)]
                if cross(p[i],p[j],p[h])<=1e-8:continue
                if any(t not in (i,j,h) and
                       min(cross(p[i],p[j],p[t]),cross(p[j],p[h],p[t]),cross(p[h],p[i],p[t]))>=-1e-8
                       for t in ids):continue
                tris.append((i,j,h));ids.pop(k);ear=True;break
            if not ear:raise ValueError('Self-intersecting/degenerate outline')
        tris.append(tuple(ids));n=len(p)
        v=[[x,center_y-depth/2,z] for x,z in p]+[[x,center_y+depth/2,z] for x,z in p]
        f=[]
        for a,b,c in tris: f.extend([[c,b,a],[a+n,b+n,c+n]])
        for i in range(n):
            j=(i+1)%n;f.extend([[i,j,j+n],[i,j+n,i+n]])
        self.add(material,v,f)

    def transform_variant(self, seed, strength=1.0):
        """Small deterministic, coherent profile/scale variation across ALL parts.

        This deliberately creates geometry diversity; it does NOT create distinct
        semantic items or substitute for reference-matched authored recipes.
        """
        rng=np.random.default_rng(seed)
        sx,sy,sz=1.0+(rng.uniform(-.08,.08,3)*strength)
        shear=rng.uniform(-.055,.055)*strength
        bend=rng.uniform(-.03,.03)*strength
        for material,meshes in self.groups.items():
            for i,(v,f) in enumerate(meshes):
                vv=v.copy()
                xx=vv[:,0].copy(); yy=vv[:,1].copy(); zz=vv[:,2].copy()
                vv[:,0]=sx*xx+shear*zz+bend*zz*zz
                vv[:,1]=sy*yy
                vv[:,2]=sz*zz
                meshes[i]=(vv,f)

    def export(self):
        # NEWGEN V0.3 material and shape refiners run on real 3D geometry, not concept imagery.
        from importlib import util as _util
        def _sibling(name):
            spec=_util.spec_from_file_location('_newgen_'+name,Path(__file__).with_name(name+'.py'))
            module=_util.module_from_spec(spec);spec.loader.exec_module(module);return module
        geo=_sibling('geometry_finish')
        surface=_sibling('materials_pbr')
        sc=trimesh.Scene()
        faces_n=0;verts_n=0
        if self.preserve_parts:
            # Keep each V2 node addressable by the downstream corrective modeler.
            # Merging every node by material would erase its semantic part identity.
            groups=[(part_id,mat,[(v,f)]) for part_id,mat,v,f in self.part_records]
        else:
            # Fast lane groups by material to keep GLB object count low.
            groups=[(mat,mat,self.groups[mat]) for mat in sorted(self.groups)]
        names=set()
        for name,mat,meshes in groups:
            if name in names:raise ValueError('Duplicate semantic part ID: '+name)
            names.add(name)
            refined=[geo.sanitize_faces(*geo.refine_component(v,f,mat,seed=len(v))) for v,f in meshes]
            verts=np.concatenate([m[0] for m in refined],axis=0)
            faces=[];off=0
            for v,f,_removed in refined:
                faces.append((f+off).astype(np.int32));off+=len(v)
            faces=np.concatenate(faces)
            if len(verts)>MAX_VERTICES:raise ValueError('Excessive vertex count')
            mesh=trimesh.Trimesh(vertices=verts,faces=faces,process=False)
            surface.texture_mesh(mesh,mat,self.colors[mat],self.material_specs.get(mat,{}).get('pbr'))
            sc.add_geometry(mesh,geom_name=name,node_name=name)
            verts_n+=len(mesh.vertices);faces_n+=len(mesh.faces)
        if verts_n>MAX_VERTICES or not faces_n:raise ValueError('Invalid aggregate mesh')
        dims=np.asarray(sc.bounds[1]-sc.bounds[0])
        if not finite(dims) or np.any(dims<=0) or np.max(dims)>100:raise ValueError('Invalid scene extent')
        audit=geo.audit_scene(sc)
        if not audit['pass']:
            raise ValueError('Geometry audit rejected scene: '+', '.join(audit['defects'][:8]))
        data=sc.export(file_type='glb')
        if data[:4]!=b'glTF' or len(data)<100 or struct.unpack_from('<I',data,8)[0]!=len(data):
            raise ValueError('GLB exporter output invalid')
        return data, {'vertices':verts_n,'triangles':faces_n,'materials':len(self.groups),
                      'bounds_m':[[round(float(x),5) for x in p] for p in sc.bounds],
                      'parts':self.components,'part_ids':([p[0] for p in self.part_records] if self.preserve_parts else []),
                      'semantic_parts_preserved':self.preserve_parts,'geometry_audit':audit,
                      'surface_tier':'procedural_pbr_albedo_normal','uv_mapped':True}


@lru_cache(maxsize=1)
def _quality_geometry():
    """Load the sibling geometry module by exact path: works with Python -m, raw pytest,
    and importlib-loaded source without mutating global sys.path."""
    source=Path(__file__).with_name('quality_geometry.py')
    spec=importlib.util.spec_from_file_location('_ll_mesh_quality_geometry',source)
    if not spec or not spec.loader:
        raise RuntimeError('Geometry module unavailable: '+str(source))
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if set(module.BUILDERS)!=set(FAMILIES):
        raise RuntimeError('Family builder registry does not match factory contract')
    return module



def compile_parts(b,row):
    parts=row['parts']
    if not isinstance(parts,list) or not 1<=len(parts)<=MAX_COMPONENTS:
        raise ValueError('parts must be a list of 1..80 operators')
    for part in parts:
        if not isinstance(part,dict):raise ValueError('Invalid part')
        # V2 nodes carry local geometry plus a composed world transform matrix.
        # Compile locally then transform vertices (never silently ignore transforms).
        if '_matrix' in part:
            mat4=np.asarray(part['_matrix'],dtype=float)
            if mat4.shape!=(4,4) or not np.isfinite(mat4).all():
                raise ValueError('Invalid V2 node transform')
            local={key:value for key,value in part.items() if key not in ('_matrix','_part_id')}
            child=MeshBuilder(material_specs=b.material_specs)
            compile_parts(child,{'parts':[local]})
            for mat,comps in child.groups.items():
                for vertices,faces in comps:
                    hv=np.column_stack((vertices,np.ones(len(vertices))))
                    transformed=(hv@mat4.T)[:,:3]
                    if np.linalg.det(mat4[:3,:3])<0:faces=faces[:,[0,2,1]]
                    b.add(mat,transformed,faces,part_id=part.get('_part_id'))
            continue
        op=part.get('op') or part.get('operator')
        mat=part.get('material','steel')
        if op=='superloft':
            _quality_geometry().superloft(b,mat,part['sections'],n=int(part.get('segments',36)),
                      exponent=float(part.get('exponent',2.8)),
                      noise_seed=int(row.get('seed',0)),
                      center_x=float(part.get('center_x',0.0)))
        elif op=='ribbon':
            _quality_geometry().ribbon(b,mat,part['points'],part['widths'],
                   thickness=float(part.get('thickness',.009)))
        elif op=='beam':
            _quality_geometry().beam(b,mat,part['start'],part['end'],
                   float(part['width']),float(part['depth']))
        elif op=='forge_blade':
            _quality_geometry()._head_bevel(b,part['x'],part['top_z'],
                   part['bottom_z'],part['thickness'],mat)
        elif op=='box':b.box(part['location'],part['dimensions'],mat)
        elif op=='ellipsoid':b.ellipsoid(part['location'],part['radii'],mat,
                                       int(part.get('segments',16)),int(part.get('rings',9)),float(part.get('boxiness',1)))
        elif op=='lathe':b.rings(part['profile'],part.get('location',[0,0,0]),mat,int(part.get('segments',16)),
                                float(part.get('radius_x',1)),float(part.get('radius_y',1)))
        elif op=='tube':b.tube(part['points'],float(part['radius']),mat,int(part.get('sides',7)))
        elif op=='polygon_prism':b.polygon_prism(part['outline_xz'],float(part['depth']),float(part.get('center_y',0)),mat)
        else:raise ValueError(f'Unsupported operator: {op}')


def normalize(row):
    if not isinstance(row,dict):raise ValueError('Expected mapping')
    x=dict(row)
    x['asset_id']=str(x.get('asset_id') or x.get('id') or '').strip()
    if not IDENT.fullmatch(x['asset_id']):raise ValueError('Invalid asset_id')
    x['family']=str(x.get('family') or x.get('geometry_family') or '').strip().lower()
    if x.get('require_detailed') and x.get('parts'):
        parts=x['parts'] if isinstance(x['parts'],list) else json.loads(x['parts'])
        advanced={'superloft','ribbon','beam','forge_blade','lathe','tube','polygon_prism'}
        if not any(p.get('op',p.get('operator')) in advanced for p in parts if isinstance(p,dict)):
            raise ValueError('Strict detailed geometry: primitive-only custom recipe rejected')
    if not x.get('parts') and x['family'] not in FAMILIES:raise ValueError(f'Unsupported/unknown family {x["family"]}: recipe required')
    for key in ('seed','variant'):
        x[key]=int(x.get(key) or 0)
        if abs(x[key])>2**31-1:raise ValueError('Seed out of bounds')
    x['recipe_version']=str(x.get('recipe_version') or '1')
    if len(x['recipe_version'])>70:raise ValueError('Invalid recipe_version')
    if 'parts' in x and isinstance(x['parts'],str): x['parts']=json.loads(x['parts'])
    # Do not silently treat an unverified classification as a known geometry recipe.
    return x


def process_one(args):
    original,out=args
    start=time.perf_counter()
    try:
        row=normalize(original)
        key=row['asset_id'];recipe_hash=digest({'version':VERSION,'recipe':row})
        root=Path(out);dest=root/'models'/f'{key}.glb'; side=root/'metadata'/f'{key}.json'
        if dest.exists() and side.exists():
            try:
                prev=json.loads(side.read_text())
                if prev.get('recipe_sha256')==recipe_hash and hashlib.sha256(dest.read_bytes()).hexdigest()==prev['sha256']:
                    return {'asset_id':key,'status':'cached','sha256':prev['sha256'], 'elapsed_seconds':round(time.perf_counter()-start,5),
                            'family':row['family'],'technical_qa':prev.get('technical_qa')}
            except (OSError,ValueError,KeyError): pass
        b=MeshBuilder(material_specs=row.get('material_specs'),
                      preserve_parts=bool(row.get('preserve_parts',False)))
        if row.get('parts'): compile_parts(b,row)
        else:
            _quality_geometry().BUILDERS[row['family']](b,seed=row['seed'],variant=row['variant'])
            b.transform_variant(row['seed'],strength=.06)
        glb,metrics=b.export()
        sha=hashlib.sha256(glb).hexdigest()
        meta={'asset_id':key,'family':row['family'],'recipe_version':row['recipe_version'],
              'factory_version':VERSION,'recipe_sha256':recipe_hash,'sha256':sha,
              'source_reference':str(row.get('source_reference') or ''),
              'technical_qa':'passed','review_state':'generated_candidate',
              'geometry_tier':('custom_recipe_unreviewed' if row.get('parts') else 'detailed_procedural'),
              'visual_qa':'not_tested','gameplay_qa':'not_tested',
              'golden_approved':False,'identity_verified':False,
              'canonical_catalog_row':row.get('canonical_catalog_row'),
              'source_filename':row.get('source_filename'),
              'v2_review_warnings':row.get('v2_review_warnings',[]),**metrics}
        dest.parent.mkdir(parents=True,exist_ok=True);side.parent.mkdir(parents=True,exist_ok=True)
        # Atomic replace survives interruptions, preserves last valid candidate for resume.
        with tempfile.NamedTemporaryFile(dir=dest.parent,prefix='tmp_',suffix='.glb',delete=False) as h:
            tmp=h.name;h.write(glb)
        os.replace(tmp,dest)
        with tempfile.NamedTemporaryFile(dir=side.parent,prefix='tmp_',mode='w',encoding='utf8',delete=False) as h:
            tmp=h.name;json.dump(meta,h,sort_keys=True)
        os.replace(tmp,side)
        return {'asset_id':key,'family':row['family'],'status':'built','sha256':sha,
                'technical_qa':'passed','triangles':metrics['triangles'],
                'elapsed_seconds':round(time.perf_counter()-start,5)}
    except Exception as exc:
        return {'asset_id':str(original.get('asset_id') or original.get('id') or '')[:111],
                'status':'failed','error':f'{type(exc).__name__}: {exc}',
                'elapsed_seconds':round(time.perf_counter()-start,5)}


def load_rows(path):
    if not path.exists():raise ValueError(f'No input file: {path}')
    if path.suffix.lower()=='.csv':
        with path.open(newline='',encoding='utf-8-sig') as h:rows=list(csv.DictReader(h))
    elif path.suffix.lower()=='.jsonl':
        with path.open(encoding='utf8') as h:rows=[json.loads(line) for line in h if line.strip()]
    elif path.suffix.lower()=='.json':
        data=json.loads(path.read_text(encoding='utf8'));rows=data['assets'] if isinstance(data,dict) else data
    else:raise ValueError('Supply CSV, JSON, or JSONL')
    if not isinstance(rows,list):raise ValueError('Input must contain rows')
    seen=set()
    for row in rows:
        k=str(row.get('asset_id') or row.get('id') or '')
        if k in seen:raise ValueError('Duplicate asset_id: '+k)
        seen.add(k)
    # Convert full canonical LAST LIGHT V2 recipes into executable NEWGEN rows.
    from importlib import util as _util
    source=Path(__file__).with_name('v2_adapter.py')
    if any(r.get('schema')=='LAST_LIGHT_3D_MESH_RECIPE_V2_CANDIDATE' for r in rows):
        spec=_util.spec_from_file_location('_newgen_recipe_v2',source)
        module=_util.module_from_spec(spec);spec.loader.exec_module(module)
        rows=[module.adapt(r) if r.get('schema')=='LAST_LIGHT_3D_MESH_RECIPE_V2_CANDIDATE' else r for r in rows]
    return rows


def demo_rows(n,seed):
    return [{'asset_id':f'benchmark_{i:05d}_{FAMILIES[i%len(FAMILIES)]}',
             'family':FAMILIES[i%len(FAMILIES)],'seed':seed*1000003+i,
             'variant':i//len(FAMILIES),'recipe_version':'demo-v1',
             'source_reference':'SYNTHETIC_BENCHMARK_NOT_MASTER_CATALOG'} for i in range(n)]


def write_json(path,obj):
    tmp=path.with_suffix(path.suffix+'.tmp')
    tmp.write_text(json.dumps(obj,indent=2,sort_keys=True)+'\n',encoding='utf8');os.replace(tmp,path)


def run(rows,output,workers,budget_seconds=900):
    output.mkdir(parents=True,exist_ok=True)
    if workers<1 or workers>32:raise ValueError('workers must be between 1 and 32')
    t=time.perf_counter();results=[]
    with ProcessPoolExecutor(max_workers=workers) as pool:
        futs=[pool.submit(process_one,(r,str(output))) for r in rows]
        for fut in as_completed(futs): results.append(fut.result())
    results.sort(key=lambda x:x['asset_id'])
    sec=time.perf_counter()-t
    with (output/'manifest.jsonl').open('w',encoding='utf8') as h:
        for r in results:h.write(json.dumps(r,sort_keys=True)+'\n')
    with (output/'failures.jsonl').open('w',encoding='utf8') as h:
        for r in results:
            if r['status']=='failed':h.write(json.dumps(r,sort_keys=True)+'\n')
    unique_hashes=len({r['sha256'] for r in results if r['status']!='failed'})
    built=sum(r['status']=='built' for r in results)
    cached=sum(r['status']=='cached' for r in results)
    fails=len(results)-built-cached
    report={'factory_version':VERSION,'requested':len(rows),'built':built,'cached':cached,
            'failed':fails,'total_valid':built+cached,'distinct_glb_sha256':unique_hashes,'seconds':round(sec,4),
            'assets_per_second':round(len(results)/sec,3) if sec else None,
            'new_assets_per_second':round(built/sec,3) if sec else None,
            'target_assets':2000,'target_seconds':budget_seconds,
            'met_rate_target_on_this_batch': bool(not fails and len(rows)>0 and sec/len(rows)<=budget_seconds/2000),
            'met_full_2000_in_15_minutes':bool(not fails and len(rows)>=2000 and unique_hashes>=2000 and sec<=budget_seconds),
            'qa_scope':'GLB signature/bounds/mesh structure only; distinct hashes prove only different file bytes, not independent semantic identities or visual quality',
            'approval_state':'CANDIDATE_ONLY_NOT_GOLDEN'}
    write_json(output/'report.json',report)
    return report


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    src=p.add_mutually_exclusive_group(required=True)
    src.add_argument('--input',type=Path,help='CSV / JSONL / JSON asset recipes')
    src.add_argument('--demo',type=int,metavar='N',help='Synthetic throughput benchmark, NOT 2000 unique catalog assets')
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--workers',type=int,default=min(4,max(1,os.cpu_count() or 1)))
    p.add_argument('--require-detailed',action='store_true',
                   help='Reject primitive-only custom recipes; no visual approval implied')
    p.add_argument('--seed',type=int,default=17)
    p.add_argument('--budget-seconds',type=int,default=900)
    opts=p.parse_args(argv)
    if opts.demo is not None and not 1<=opts.demo<=100000: p.error('--demo must be 1..100000')
    rows=demo_rows(opts.demo,opts.seed) if opts.demo is not None else load_rows(opts.input)
    if opts.require_detailed:
        rows=[{**row,'require_detailed':True} for row in rows]
    report=run(rows,opts.out,opts.workers,opts.budget_seconds)
    print(json.dumps(report,indent=2))
    return 0 if report['failed']==0 else 2

if __name__=='__main__':raise SystemExit(main())
