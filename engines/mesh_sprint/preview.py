#!/usr/bin/env python3
"""Reproducible orthographic CPU preview of actual GLB geometry (not AI concept art).

Optional Pillow dependency. This is a diagnostic z-buffer renderer, not Blender,
not a PBR material test, and not evidence of gameplay or Golden approval.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import numpy as np
import trimesh
from PIL import Image, ImageDraw, ImageFilter, ImageFont


def _unit(v):
    v=np.asarray(v,float);return v/(np.linalg.norm(v)+1e-12)


def render_glb(glb, view=(1.,-2.,1.5), size=560):
    scene=trimesh.load(glb,force='scene')
    if scene.is_empty: raise ValueError('Cannot preview an empty GLB')
    view=_unit(view);right=_unit(np.cross([0,0,1.],view));up=_unit(np.cross(view,right))
    center=np.asarray(scene.bounds).mean(axis=0)
    source=[];all_points=[]
    light=_unit([-1.2,-1.4,2.6])
    for mesh in scene.geometry.values():
        verts=np.asarray(mesh.vertices,float)-center
        project=np.stack((verts@right,verts@up,verts@view),axis=1)
        faces=np.asarray(mesh.faces,dtype=np.int64)
        if not len(faces):continue
        # Real GLB PBR textures must be sampled from UVs; vertex-color-only previews
        # silently turn textured objects white and conceal material regressions.
        material=getattr(mesh.visual,'material',None)
        tex=getattr(material,'baseColorTexture',None)
        if tex is not None and getattr(mesh.visual,'uv',None) is not None:
            rgba=np.asarray(tex.convert('RGB'),dtype=np.float64)
            uv=np.asarray(mesh.visual.uv,dtype=float)[faces].mean(axis=1)
            v0=np.mod(uv[:,0],1.);v1=np.mod(uv[:,1],1.)
            tx=np.clip((v0*(rgba.shape[1]-1)).astype(int),0,rgba.shape[1]-1)
            ty=np.clip(((1-v1)*(rgba.shape[0]-1)).astype(int),0,rgba.shape[0]-1)
            face_color=rgba[ty,tx,:3]
        else:
            colors=np.asarray(getattr(mesh.visual,'vertex_colors',np.empty((0,4))),dtype=float)
            if len(colors)!=len(verts):colors=np.tile([170,170,170,255],(len(verts),1))
            face_color=colors[faces,:3].mean(axis=1)
        # Approximate engine smooth shading with barycentric mean of vertex normals;
        # raw face normals make finely subdivided softgoods look falsely faceted.
        vert_norm=np.asarray(mesh.vertex_normals,float)
        normals=np.asarray(vert_norm[faces].mean(axis=1),float)
        normals/=np.maximum(np.linalg.norm(normals,axis=1,keepdims=True),1e-9)
        shade=np.clip(.62+.37*np.clip(normals@light,0,1),.62,1.0)
        # Preview is diffuse diagnostic: metallic/specular highlights need Blender.
        rgb=np.clip(face_color*shade[:,None],0,255).astype(np.uint8)
        source.append((project,faces,rgb));all_points.append(project[:,:2])
    if not source:raise ValueError('No triangles found')
    points=np.vstack(all_points);lo=points.min(axis=0);hi=points.max(axis=0)
    span=np.maximum(hi-lo,.0001);scale=(size*.77)/np.max(span)
    xpad=(size-span[0]*scale)/2;ypad=(size-span[1]*scale)/2
    zbuf=np.full((size,size),-np.inf,dtype=np.float32)
    img=np.full((size,size,3),[241,242,241],dtype=np.uint8)
    for projected,faces,colors in source:
        xy=np.stack((xpad+(projected[:,0]-lo[0])*scale,
                      size-ypad-(projected[:,1]-lo[1])*scale),axis=1)
        z=projected[:,2]
        for face,rgb in zip(faces,colors):
            a,b,c=xy[face];depth=z[face]
            minx=max(0,int(np.floor(min(a[0],b[0],c[0]))))
            maxx=min(size-1,int(np.ceil(max(a[0],b[0],c[0]))))
            miny=max(0,int(np.floor(min(a[1],b[1],c[1]))))
            maxy=min(size-1,int(np.ceil(max(a[1],b[1],c[1]))))
            if maxx<minx or maxy<miny:continue
            den=(b[1]-c[1])*(a[0]-c[0])+(c[0]-b[0])*(a[1]-c[1])
            if abs(den)<.00001:continue
            ys,xs=np.mgrid[miny:maxy+1,minx:maxx+1]
            x=xs+.5;y=ys+.5
            u=((b[1]-c[1])*(x-c[0])+(c[0]-b[0])*(y-c[1]))/den
            v=((c[1]-a[1])*(x-c[0])+(a[0]-c[0])*(y-c[1]))/den
            w=1-u-v
            mask=(u>=-1e-6)&(v>=-1e-6)&(w>=-1e-6)
            if not np.any(mask):continue
            zd=(depth[0]*u+depth[1]*v+depth[2]*w)
            patchz=zbuf[miny:maxy+1,minx:maxx+1]
            mask&=(zd>patchz)
            if np.any(mask):
                patchz[mask]=zd[mask]
                img[miny:maxy+1,minx:maxx+1][mask]=rgb
    return Image.fromarray(img,'RGB')


def compare(before,after,title,out,size=460):
    im=Image.new('RGB',(size*2+40,size+105),(250,250,248));dr=ImageDraw.Draw(im)
    font='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
    face=ImageFont.truetype(font,26) if Path(font).exists() else None
    im.paste(render_glb(before,size=size),(10,65))
    im.paste(render_glb(after,size=size),(size+30,65))
    dr.text((14,12),title,fill=(30,36,38),font=face)
    dr.text((14,size+74),'BEFORE · primitive procedural',fill=(110,74,74))
    dr.text((size+33,size+74),'AFTER · construction geometry',fill=(42,80,56))
    out=Path(out);out.parent.mkdir(parents=True,exist_ok=True)
    im.save(out);return str(out)


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--glb',type=Path,required=True)
    ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--size',type=int,default=560)
    args=ap.parse_args()
    render_glb(args.glb,size=args.size).save(args.out)
    print(args.out)
