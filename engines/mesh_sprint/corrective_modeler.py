"""Bounded component-focused corrective modeling, creating REAL geometry.

Original family builders are preserved as the baseline. Corrections are geometry,
not image editing. All new geometry remains unapproved and must be re-rendered.
"""
from pathlib import Path
import importlib.util
import numpy as np


def sibling(filename):
    s=importlib.util.spec_from_file_location('newgen_'+filename,Path(__file__).with_name(filename+'.py'))
    m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m


def construct(contract, iteration=0):
    f=sibling('factory');q=f._quality_geometry()
    fam=contract['family'];b=f.MeshBuilder(preserve_parts=True)
    if fam not in q.BUILDERS:raise ValueError('Missing family construction recipe')
    q.BUILDERS[fam](b,seed=contract['seed'],variant=0)
    if iteration>0:
        # Shape-specific construction is deterministic and bounded: never silently
        # replace detailed parts with a box or infer an unsupported object.
        if fam=='avocado':
            # Inner flesh/cavity rings are anchored to the *front cut surface*.
            # Earlier free-floating back-skin guides were explicitly removed after
            # inspecting the render: they made a black wire outside the avocado.
            t=np.linspace(0,2*np.pi,49)
            q._ring_loop(b,[[.061*np.cos(a),-.023,.165+.074*np.sin(a)] for a in t],.0034,'flesh_green')
            q._ring_loop(b,[[.073*np.cos(a),-.027,.165+.083*np.sin(a)] for a in t],.0022,'pit_shadow')
            # Seed-facing surface details: attached small ellipsoid, no extraneous props.
            b.ellipsoid([-.015,-.074,.183],[.009,.004,.012],'pit_light',16,9)
        elif fam=='backpack':
            # Front-pocket retention tabs, sewn webbing and edge stitching.
            for x in (-.16,.16):
                q.ribbon(b,'fabric_dark',[[x,-.265,.28],[x,-.286,.255],[x,-.271,.186]],
                         [.031,.032,.027],thickness=.007)
                b.box([x,-.29,.256],[.036,.013,.028],'steel_dark')
            for z in (.181,.315):
                q._ring_loop(b,[[x,-.267+0.014*(x/.2)**2,z] for x in np.linspace(-.19,.19,26)],.0025,'stitch')
            # Wearable load-bearing attachment: side straps with real width.
            for side in (-1,1):
                x=side*.29
                q.ribbon(b,'fabric_dark',[[x,-.06,.56],[x*1.08,-.10,.48],[x,-.15,.39]],
                         [.029,.038,.031],.009)
        elif fam=='axe':
            # Lower haft wrapped in a distinct grip ribbon, non-slip raised ridge.
            q.ribbon(b,'leather',[[.007,-.032,.06],[.018,-.035,.12],[.021,-.035,.19],[.020,-.032,.26]],
                     [.047,.048,.043,.038],thickness=.007)
            # Forged shoulder fillets and pronounced partial taper wear, not a disk.
            for yy in (-.033,.033):
                # Engraving follows the actual metal cheek, beneath its top contour.
                q._ring_loop(b,[[-.07,yy,.898],[-.16,yy*.92,.909],[-.27,yy*.67,.918]],.002,'edge')
            # Low-profile leather grip binding that wraps the actual handle diameter.
            # This makes fine-scale surface detail visible without floating elements.
            for z in (.095,.135,.175,.215):
                center_x=.022 if z<.20 else .020
                t=np.linspace(0,2*np.pi,33)
                q._ring_loop(b,[[center_x+.033*np.cos(a),.029*np.sin(a),z] for a in t],.0031,'leather')
            # Two stamped forge tracks follow the cheeks, not the air above the edge.
            for yy in (-.039,.039):
                q._ring_loop(b,[[-.11,yy,.858],[-.19,yy*.9,.865],[-.26,yy*.7,.877]],.0025,'steel_dark')
            # Additional hardware quality is checked from exported geometry afterward.
    return b


def export(builder,root,asset_id):
    """Re-use the same real GLB export and PBR/material pipeline as NEWGEN."""
    import hashlib,json
    root=Path(root);(root/'models').mkdir(parents=True,exist_ok=True)
    raw,stats=builder.export()
    dest=root/'models'/f'{asset_id}.glb';dest.write_bytes(raw)
    stats['sha256']=hashlib.sha256(raw).hexdigest()
    return dest,stats
