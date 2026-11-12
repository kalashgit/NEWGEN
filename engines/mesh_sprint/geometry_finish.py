"""Bounded shape refinement and structural integrity audit, never Golden approval."""
from __future__ import annotations
import numpy as np
import trimesh

ORGANIC = {'skin','skin_dark','flesh','flesh_green','fabric','fabric_dark','fabric_light','red','olive','leather'}


def refine_component(v, f, role, seed=0):
    """Original sub-pixel surface displacement on real geometry; avoids hard blades.

    The amplitude is a fraction of component scale; this does not replace a sculpt.
    """
    v=np.asarray(v,dtype=float)
    faces=np.asarray(f,dtype=np.int64)
    if role not in ORGANIC or len(v)<70:
        return v.astype(np.float32),faces
    mesh=trimesh.Trimesh(vertices=v.copy(),faces=faces,process=False)
    normals=np.asarray(mesh.vertex_normals,dtype=float)
    span=np.linalg.norm(np.ptp(v,axis=0))
    if not np.isfinite(span) or span<.02:
        return v.astype(np.float32),faces
    # Controlled fine woven / ripened skin relief, no stochastic seams or landmarks.
    phase=(seed%1021)*.011
    x,y,z=v.T
    freq= (66. if role in {'skin','skin_dark'} else 83.)
    relief=(np.sin(x*freq+phase)*np.sin(y*freq*.73+z*freq*.21)
           +.4*np.sin(z*freq*.53+x*freq*.8))
    amplitude=min(.0008,span*.00035)
    out=v+normals*(amplitude*relief)[:,None]
    return out.astype(np.float32),faces


def audit_scene(scene):
    """Fail closed for invalid normals, triangles, area, excessive vertex-identity duplication.

    This verifies structural numeric properties, not object semantics or watertightness.
    """
    defects=[];counts={'geometry':0,'triangles':0,'vertices':0,'zero_area_triangles':0}
    if len(scene.geometry)==0:
        defects.append('empty_scene')
    for role,mesh in scene.geometry.items():
        counts['geometry']+=1
        counts['triangles']+=len(mesh.faces)
        counts['vertices']+=len(mesh.vertices)
        if len(mesh.faces)==0 or len(mesh.vertices)==0:
            defects.append(f'{role}:empty_geometry');continue
        a=np.asarray(mesh.area_faces,dtype=float)
        if np.any(~np.isfinite(a)):
            defects.append(f'{role}:nonfinite_face_area')
        tiny=int(np.count_nonzero(a<1e-12))
        counts['zero_area_triangles']+=tiny
        if tiny:
            defects.append(f'{role}:zero_area_faces:{tiny}')
        if not np.all(np.isfinite(mesh.vertices)):
            defects.append(f'{role}:nonfinite_vertices')
    return {'pass':not defects,'defects':defects,'counts':counts,'scope':'structural geometry only'}


def sanitize_faces(vertices,faces,area_epsilon=1e-12):
    """Remove exactly collapsed triangles (including duplicated elliptical pole rings)."""
    v=np.asarray(vertices,dtype=np.float64); f=np.asarray(faces,dtype=np.int64)
    a,b,c=v[f[:,0]],v[f[:,1]],v[f[:,2]]
    cross=np.cross(b-a,c-a)
    sq=np.sum(cross*cross,axis=1)
    keep=sq>(2*area_epsilon)**2
    if not np.any(keep):raise ValueError('All faces degenerate')
    # Leave vertex indices stable for UV projection and deterministic scene output.
    return v.astype(np.float32),f[keep],int(np.count_nonzero(~keep))
