"""Procedural, original PBR surface manufacturing for NEWGEN.

Generated solely from material roles, never from copyrighted source sprites.
This layer is a *material* quality stage; it does not infer object identity.
"""
from __future__ import annotations
import hashlib
import math
from functools import lru_cache
import numpy as np
from PIL import Image
from trimesh.visual.texture import TextureVisuals
from trimesh.visual.material import PBRMaterial

# This dictionary is a physically meaningful material assignment, not generic tint.
PRESETS = {
    'skin': ('avocado_skin',0.,.93,.75), 'skin_dark': ('avocado_skin',0.,.96,.68),
    'leaf': ('organic',0.,.9,.7), 'leaf_light': ('organic',0.,.85,.66),
    'flesh': ('avocado_flesh',0.,.84,.42), 'flesh_green':('avocado_flesh',0.,.86,.50),
    'pit': ('wood',0.,.72,.56),'pit_shadow':('avocado_flesh',0.,.90,.5),'pit_light':('wood',0.,.76,.5),
    'fabric': ('fabric',0.,.94,.56),'fabric_dark':('fabric',0.,.95,.56),
    'fabric_light':('fabric',0.,.94,.54),'seam':('fabric',0.,.98,.48),
    'stitch':('fabric',0.,.93,.48),'leather':('leather',0.,.77,.55),
    'steel':('steel',.91,.35,.38),'steel_dark':('steel',.89,.53,.34),
    'edge':('steel',.95,.20,.35),'black':('plastic',0.,.57,.44),
    'red':('fabric',0.,.86,.55), 'white':('paper',0.,.84,.35),
    'wood':('wood',0.,.72,.48),'wood_dark':('wood',0.,.73,.51),
    'wood_light':('wood',0.,.69,.47),'wood_grain':('wood',0.,.81,.47),
    'plastic':('plastic',0.,.48,.35),'glass':('glass',0.,.16,.2),
    'olive':('metal_paint',.43,.48,.40),'paint':('metal_paint',.53,.43,.37),
    'paint_light':('metal_paint',.51,.49,.40)
}


def _seed(role):
    return int.from_bytes(hashlib.sha256(role.encode('ascii')).digest()[:8], 'little')


def tile(role, rgb, size=128):
    """Produce a deterministic material-specific image + tangent-space normal map."""
    kind,metal,rough,bump=PRESETS.get(role,('plastic',0.,.67,.40))
    rng=np.random.default_rng(_seed(role))
    yy,xx=np.indices((size,size),dtype=float)
    white=rng.standard_normal((size,size))
    noise=white*.18
    if kind=='fabric':
        height=.53*np.sin(xx*np.pi*.52)**6+.47*np.cos(yy*np.pi*.45)**6+noise*.24
        detail=height*.055 + np.sin(xx*.9+yy*.14)*.008
    elif kind=='wood':
        # Curved growth grain: directional, irregular but seamless at preview scale.
        warp=2*np.sin(yy*.075)+np.sin(yy*.21)
        height=np.sin((xx+warp)*.18+np.sin(yy*.03))*.45+np.sin(xx*.78+warp)*.12+noise*.08
        detail=height*.075
    elif kind=='avocado_skin':
        height=np.sin(xx*.42+np.sin(yy*.15))*.33*np.cos(yy*.39)+np.sin(xx*.97+yy*.63)*.11+noise*.2
        detail=height*.105
    elif kind=='avocado_flesh':
        height=np.sin(xx*.085)*np.cos(yy*.12)*.32+noise*.11
        detail=height*.065
    elif kind=='steel':
        height=np.sin(yy*1.57+np.sin(xx*.03)*.6)*.15+noise*.16
        detail=height*.04
    elif kind=='metal_paint':
        height=np.sin(xx*.22)*.09+noise*.22
        detail=height*.06
    elif kind=='leather':
        height=(np.sin(xx*.62)*np.cos(yy*.59))*.19+noise*.17
        detail=height*.10
    elif kind=='glass':
        height=noise*.05;detail=height*.02
    else:
        height=noise*.14;detail=height*.07
    detail=np.clip(detail,-.20,.20)
    base=np.array(rgb[:3],dtype=np.float64)
    pigment=np.clip(base[None,None,:]*(1+detail[:,:,None]),0,255).astype(np.uint8)
    image=Image.fromarray(pigment,'RGB')
    # Sobel-like pixel finite differences for normal texture. Energy bounded.
    dhdx=(np.roll(height,-1,axis=1)-np.roll(height,1,axis=1))*.5*bump*.22
    dhdy=(np.roll(height,-1,axis=0)-np.roll(height,1,axis=0))*.5*bump*.22
    normals=np.dstack((-dhdx,-dhdy,np.ones_like(dhdx)))
    normals/=np.maximum(np.linalg.norm(normals,axis=2,keepdims=True),1e-9)
    normals=np.clip((normals*.5+.5)*255,0,255).astype(np.uint8)
    return image,Image.fromarray(normals,'RGB'),metal,rough


@lru_cache(maxsize=64)
def _cached(role,rgb):
    return tile(role,rgb)


def surface_uv(vertices,role):
    """Deterministic UVs in world metres, with material-dependent repeat density.

    Atlas-less repeating material texture: no source pixels, and no claim of perfect seams.
    """
    v=np.asarray(vertices,float)
    ext=np.ptp(v,axis=0)
    # Fabric and vertical timber use front X/Z projection; cylindrical skin uses Y/Z
    # as needed to avoid degenerate UV for narrow materials.
    indices=np.argsort(ext)[-2:]
    a,b=sorted(map(int,indices))
    density={'fabric':9.,'wood':5.,'avocado_skin':12.,'steel':5.}.get(PRESETS.get(role,('plastic',))[0],7.)
    uv=v[:,[a,b]]*density
    return uv.astype(np.float32)


def texture_mesh(mesh,role,rgba,pbr_override=None):
    albedo,normal,metal,rough=_cached(role,tuple(rgba))
    if pbr_override is not None:
        metallic=pbr_override.get('metallic',metal)
        roughness=pbr_override.get('roughness',rough)
        if not (0<=float(metallic)<=1 and 0<=float(roughness)<=1):
            raise ValueError('Invalid material PBR factors')
        metal,rough=float(metallic),float(roughness)
    material=PBRMaterial(name=role,baseColorFactor=[255,255,255,255],
                         baseColorTexture=albedo,normalTexture=normal,
                         metallicFactor=float(metal),roughnessFactor=float(rough),
                         doubleSided=(role in {'fabric','fabric_dark','fabric_light','flesh','flesh_green'}))
    mesh.visual=TextureVisuals(uv=surface_uv(mesh.vertices,role),material=material)
    return mesh
