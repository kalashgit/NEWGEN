"""Real GLB -> game integration artifacts. No fake gameplay verification.

Produces LOD GLBs, collision hull, Godot scene, catalog manifest and static sprites.
Separate from artistic Golden approval. Engine neutral enough to re-use in NEWGEN.
"""
from __future__ import annotations
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import trimesh
from PIL import Image


def cluster_mesh(mesh, resolution):
    """Pure-numpy vertex clustering reduction; no proprietary decimator dependency.

    Vertex averages preserve broad shape, but can reduce small details. The original
    mesh remains LOD0. Broken/degenerate triangles are removed by design.
    """
    v=np.asarray(mesh.vertices,dtype=np.float64)
    f=np.asarray(mesh.faces,dtype=np.int64)
    if len(v)<12 or len(f)<10:return mesh.copy()
    span=max(float(np.ptp(v,axis=0).max()),1e-5)
    step=span/max(1,resolution)
    key=np.round(v/step).astype(np.int64)
    unique, inverse=np.unique(key,axis=0,return_inverse=True)
    if len(unique)==len(v):return mesh.copy()
    counts=np.bincount(inverse).astype(float)
    vv=np.column_stack([np.bincount(inverse,weights=v[:,i])/np.maximum(counts,1) for i in range(3)])
    ff=inverse[f]
    ok=(ff[:,0]!=ff[:,1])&(ff[:,0]!=ff[:,2])&(ff[:,1]!=ff[:,2]);ff=ff[ok]
    if not len(ff):return mesh.copy()
    # Drop duplicate triangles after vertex collapses without changing face winding.
    _,ids=np.unique(np.sort(ff,axis=1),axis=0,return_index=True)
    ff=ff[np.sort(ids)]
    area=np.linalg.norm(np.cross(vv[ff[:,1]]-vv[ff[:,0]],vv[ff[:,2]]-vv[ff[:,0]]),axis=1)
    ff=ff[area>1e-12]
    if not len(ff):return mesh.copy()
    sub=trimesh.Trimesh(vertices=vv,faces=ff,process=False)
    return sub


def create_lods(scene, out, base_name):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    from importlib import util
    path=Path(__file__).with_name('materials_pbr.py')
    s=util.spec_from_file_location('ng_factory_materials',path)
    mod=util.module_from_spec(s);s.loader.exec_module(mod)
    result=[]
    for level,resolution in [(0,None),(1,34),(2,17)]:
        dest=out/f'{base_name}_LOD{level}.glb'
        if level==0:
            raw=scene.export(file_type='glb')
            dest.write_bytes(raw)
        else:
            target=trimesh.Scene()
            for name,mesh in sorted(scene.geometry.items()):
                reduced=cluster_mesh(mesh,resolution)
                mat=getattr(getattr(mesh.visual,'material',None),'name',None) or 'plastic'
                base=np.asarray(mesh.visual.material.baseColorTexture.convert('RGB')).mean(axis=(0,1)) if hasattr(mesh.visual.material,'baseColorTexture') and mesh.visual.material.baseColorTexture is not None else np.array([140,140,140])
                rgba=tuple(int(x) for x in [*base,255])
                pbr=getattr(mesh.visual,'material',None)
                mod.texture_mesh(reduced,mat if mat in mod.PRESETS else 'plastic',rgba,
                    {'metallic':float(getattr(pbr,'metallicFactor',0)), 'roughness':float(getattr(pbr,'roughnessFactor',.75))})
                target.add_geometry(reduced,geom_name=name,node_name=name)
            dest.write_bytes(target.export(file_type='glb'))
        reread=trimesh.load(dest,force='scene')
        if reread.is_empty or not len(reread.geometry):raise RuntimeError(f'Failed LOD{level} reimport')
        face_count=sum(len(g.faces) for g in reread.geometry.values())
        result.append({'lod':level,'file':dest.name,'triangles':face_count,'sha256':hashlib.sha256(dest.read_bytes()).hexdigest()})
    return result


def make_scene(asset_id,glb,bounds,gameplay,asset_dir):
    """An importable Godot .tscn that instantiates the GLB, not a screenshot prop.

    Box collider is an interim gameplay approximation and is explicitly labeled.
    """
    b=np.asarray(bounds,float);span=b[1]-b[0];center=(b[1]+b[0])*.5
    for n in (*span,*center):
        if not math.isfinite(float(n)):raise ValueError('Bad bounds')
    name='NEWGEN_'+asset_id.replace('-','_')
    size=', '.join(f'{max(.001,float(n)):.5f}' for n in span)
    pos=', '.join(f'{float(n):.5f}' for n in center)
    pickable=gameplay['pickable']
    body_type='RigidBody3D' if pickable else 'StaticBody3D'
    scene=f'''[gd_scene load_steps=3 format=3]\n\n[ext_resource type="PackedScene" path="res://{glb}" id="1_visual"]\n\n[sub_resource type="BoxShape3D" id="BoxShape3D_coll"]\nsize = Vector3({size})\n\n[node name="{name}" type="Node3D"]\n\n[node name="Visual" parent="." instance=ExtResource("1_visual")]\n\n[node name="Physics" type="{body_type}" parent="."]\n\n[node name="CollisionShape3D" type="CollisionShape3D" parent="Physics"]\nshape = SubResource("BoxShape3D_coll")\nposition = Vector3({pos})\n'''
    path=Path(asset_dir)/'asset.tscn';path.write_text(scene)
    return {'scene':'asset.tscn','physics':body_type,'collision_type':'BOX_APPROXIMATION_NOT_ARTIST_VALIDATED',
            'collision_size_m':[round(float(x),5) for x in span],
            'collision_center_m':[round(float(x),5) for x in center]}


def transparent_sprite(im):
    rgba=im.convert('RGBA')
    arr=np.asarray(rgba).copy()
    bg=np.array([241,242,241])
    delta=np.max(np.abs(arr[:,:,:3].astype(np.int16)-bg[None,None,:]),axis=2)
    arr[:,:,3]=np.where(delta>18,255,0).astype(np.uint8)
    arr[delta<=18,:3]=0
    return Image.fromarray(arr,'RGBA')


def package(model_path,contract,target):
    """Write Godot scene, three tested LODs, collision, eight static directions,
    and a versioned manifest. NEVER grants Golden or gameplay-runtime approval."""
    from importlib import util
    src=Path(__file__).with_name('preview.py');spec=util.spec_from_file_location('ng_render_for_game',src)
    mod=util.module_from_spec(spec);spec.loader.exec_module(mod)
    target=Path(target);target.mkdir(parents=True,exist_ok=True)
    scene=trimesh.load(model_path,force='scene')
    if scene.is_empty:raise ValueError('Empty GLB')
    bounds=scene.bounds
    lods=create_lods(scene,target,contract['asset_id'])
    collision=make_scene(contract['asset_id'],f'assets/{contract["asset_id"]}/model/{lods[0]["file"]}',bounds,contract['gameplay'],target)
    # Reorganize LOD output to consistent game asset folder.
    (target/'model').mkdir(exist_ok=True)
    for item in lods:
        file=target/item['file'];file.rename(target/'model'/item['file'])
    # A real model-aware collider hull retained separately from runtime box approximation.
    hull=scene.to_geometry().convex_hull
    hull_path=target/'collision_hull.glb';hull_path.write_bytes(hull.export(file_type='glb'))
    if trimesh.load(hull_path,force='scene').bounds is None:raise RuntimeError('Hull reimport failed')
    sprite_dir=target/'sprites';sprite_dir.mkdir(exist_ok=True)
    views=[]
    for index in range(8):
        angle=math.pi/4-math.pi/2+index*2*math.pi/8
        im=transparent_sprite(mod.render_glb(model_path,view=(math.cos(angle),math.sin(angle),.95),size=256))
        path=sprite_dir/f'direction_{index:02d}.png';im.save(path)
        views.append(str(path.relative_to(target)))
    # Inventory icon from actual GLB, not the source image.
    image=transparent_sprite(mod.render_glb(model_path,size=256))
    image.save(sprite_dir/'inventory.png')
    data={'asset_id':contract['asset_id'],'family':contract['family'],
      'schema':'NEWGEN_GAME_ASSET_CANDIDATE_V1','recipe_sha256':contract['sha256'],
      'source_evidence':contract['source_evidence'],'lods':lods,'collision':collision,
      'collision_hull':'collision_hull.glb','sprite_views':views,'inventory_sprite':'sprites/inventory.png',
      'units':'metres','axis':'X-right,Y-back,Z-up','gameplay':contract['gameplay'],
      'gameplay_qa':'NOT_RUN_NO_GODOT_RUNTIME','source_sprite_fidelity':'NOT_VERIFIED',
      'animation_state':'STATIC_DIRECTIONS_ONLY_NOT_ANIMATED',
      'golden_approved':False,'review_state':'GAME_ASSET_CANDIDATE'}
    (target/'asset_manifest.json').write_text(json.dumps(data,indent=2))
    return data
