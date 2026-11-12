"""LAST LIGHT FOUNDRY: original procedural Blender model source factory V1.

Generates NEW editable .blend meshes, GLB exports and geometry manifests.
No copied third-party assets, no AI inference or Golden approval.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import random
import struct
import sys
from pathlib import Path

import bpy
from mathutils import Vector

MATS = {}
COUNT = 0

def mat(name, rgb, metallic=0.0, rough=0.6):
    key = (name, tuple(rgb), metallic, rough)
    if key in MATS: return MATS[key]
    m = bpy.data.materials.new(name)
    m.diffuse_color = (*rgb,1)
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (*rgb,1)
        bsdf.inputs["Roughness"].default_value = rough
        bsdf.inputs["Metallic"].default_value = metallic
    MATS[key] = m
    return m

def box(name, loc, dims, material, bevel=0.0):
    global COUNT
    if any(not math.isfinite(x) or x<=0 for x in dims):
        raise ValueError("invalid box dimensions")
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    obj = bpy.context.object
    obj.name = name
    obj.scale = dims
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(material)
    if bevel:
        mod=obj.modifiers.new("soft_machined_edges","BEVEL")
        mod.width = min(bevel, min(dims)*0.22)
        mod.segments=2
    COUNT += 1
    return obj

def cyl(name, loc, radius, depth, material, verts=16, rotation=(0,0,0)):
    global COUNT
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=radius, depth=depth, location=loc, rotation=rotation)
    obj=bpy.context.object
    obj.name=name
    obj.data.materials.append(material)
    COUNT += 1
    return obj

def seed_materials(rng, variant):
    hues=[
      (.30,.38,.38),(.44,.46,.41),(.41,.48,.51),(.47,.41,.36),
      (.36,.39,.48),(.46,.46,.34),(.42,.32,.30),(.39,.46,.40)
    ]
    rgb=hues[variant%len(hues)]
    return {
        "paint":mat("F11_candidate_painted_steel",rgb,0.42,0.56),
        "light":mat("F11_candidate_light_trim",tuple(min(.9,c+.20) for c in rgb),0.30,0.48),
        "dark":mat("F11_candidate_seam_and_rubber",(.12,.14,.14),.05,.82),
        "steel":mat("F11_candidate_brushed_metal",(.45,.48,.46),.77,.42),
        "rust":mat("F11_candidate_surface_oxidation",(.35,.19,.12),.08,.84),
        "wood":mat("F11_candidate_aged_wood",(.43,.31,.21),.0,.83),
        "soil":mat("F11_candidate_soil",(.20,.16,.12),.0,.96),
        "leaf":mat("F11_candidate_leaf",(.22,.36,.19),.0,.82),
        "glass":mat("F11_candidate_tinted_glass",(.16,.28,.30),.20,.27),
        "panel":mat("F11_candidate_cream_plastic",(.69,.65,.56),.02,.56)
    }

def screws(tag, x, face_y, z, width, m):
    for sx in (-1,1):
        cyl(f"{tag}_bolt_{sx}",(x+sx*width/2,face_y,z),.011,.008,m["steel"],verts=10,rotation=(math.pi/2,0,0))

def locker(v,r,m):
    bays=1+v%3; w=.42*bays+.12; h=1.65+v%4*.085; d=.48
    box("welded_frame",(0,0,h/2),(w,d,h),m["dark"],.018)
    box("top_cap",(0,0,h-.025),(w+.035,d+.025,.055),m["steel"],.012)
    for b in range(bays):
        x=-w/2+.06+(b+.5)*(w-.12)/bays
        dw=(w-.12)/bays-.022
        box(f"door_{b}",(x,-d/2-.013,h/2+.025),(dw,.030,h-.18),m["paint"],.008)
        box(f"door_seam_{b}",(x+dw/2-.025,-d/2-.034,h/2),(0.008,.005,h-.30),m["dark"])
        cyl(f"latch_{b}",(x+dw*.28,-d/2-.038,h*.51),.016,.025,m["steel"],verts=12,rotation=(math.pi/2,0,0))
        for i in range(3+v%3):
            box(f"air_vent_{b}_{i}",(x,-d/2-.033,h*.78+i*.036),(dw*.46,.005,.009),m["dark"])
        screws(f"door_{b}",x,-d/2-.033,h*.13,dw*.65,m)
    for x in (-w/2+.06,w/2-.06):
        box(f"ground_foot_{x:.2f}",(x,0,.028),(.075,d*.73,.056),m["steel"])
    # A believable pressed-metal rear panel and side ribs are necessary:
    # every 22.5-degree sprite must be recognizable, not a plain cuboid.
    box("rear_steel_inset",(0,d/2+.016,h*.53),(w*.82,.021,h*.79),m["paint"],.009)
    box("rear_maintenance_sticker",(0,d/2+.031,h*.76),(w*.42,.009,.13),m["light"],.005)
    box("rear_maintenance_barcode",(0,d/2+.038,h*.74),(w*.28,.006,.024),m["dark"])
    for side in (-1,1):
        xx=side*(w/2+.012)
        for level in (.20,.48,.75):
            box(f"side_pressed_rib_{side}_{level}",(xx,0,h*level),(.014,d*.69,.026),m["light"],.004)
        box(f"side_vertical_stiffener_{side}",(xx,d*.21,h*.5),(.019,.027,h*.66),m["steel"],.004)
    return (w,d,h)

def chest(v,r,m):
    w=.90+(v%3)*.10;d=.49; h=1.05
    box("formed_toolcabinet",(0,0,h/2+.08),(w,d,h-.16),m["paint"],.018)
    box("countertop",(0,0,h+.01),(w+.045,d+.025,.053),m["dark"],.016)
    count=3+v%4
    dz=(h-.32)/count
    for i in range(count):
        z=.20+(i+.5)*dz
        box(f"drawer_{i}",(0,-d/2-.020,z),(w-.09,.028,dz-.018),m["light"],.009)
        box(f"drawer_gap_{i}",(0,-d/2-.038,z+dz*.43),(w-.12,.005,.012),m["dark"])
        box(f"pullbar_{i}",(0,-d/2-.049,z),(.28,.035,.022),m["steel"],.007)
        for x in (-.13,.13):
            box(f"pull_mount_{i}_{x}",(x,-d/2-.043,z),(.03,.023,.05),m["dark"])
    for x in (-w*.4,w*.4):
        for y in (-d*.33,d*.33):
            cyl(f"caster_{x:.2f}_{y:.2f}",(x,y,.075),.072,.035,m["dark"],rotation=(math.pi/2,0,0))
    box("side_push_handle",(w/2+.065,0,h*.88),(.12,.045,.030),m["steel"])
    return (w+.16,d,h+.06)

def shelf(v,r,m):
    tiers=3+v%3;w=1.25+v%4*.12;d=.52;h=1.7+tiers*.08
    for x in (-w/2,w/2):
        for y in (-d/2,d/2):
            box(f"upright_{x:.2f}_{y:.2f}",(x,y,h/2),(.035,.035,h),m["steel"],.004)
    for i in range(tiers):
        z=.17+i*(h-.34)/(tiers-1)
        box(f"shelfplate_{i}",(0,0,z),(w+.025,d+.025,.04),m["paint"],.007)
        box(f"front_lip_{i}",(0,-d/2-.012,z+.018),(w+.02,.020,.063),m["light"],.005)
        for j in range(1+((v+i)%3)):
            nx=1+((v+i)%3)
            width=w/(nx+1)
            x= -w/2+(j+1)*(w/(nx+1))
            ht=.10+((v+i+j)%3)*.07
            box(f"stored_crate_{i}_{j}",(x,0,z+.02+ht/2),(width*.64,d*.6,ht),m["wood"] if (i+j)%2 else m["panel"],.006)
            box(f"crate_seam_{i}_{j}",(x,-d*.302,z+ht*.7),(width*.46,.007,.009),m["dark"])
    for x in (-w/2,w/2):
        box(f"back_bracing_{x:.2f}",(x,d*.28,h*.55),(.02,.02,h*.5),m["dark"])
    return (w+.04,d+.04,h)

def cabinet(v,r,m):
    w=.85+v%4*.13;d=.48;h=1.25+v%3*.16
    box("cabinet_carcase",(0,0,h/2+.085),(w,d,h-.17),m["wood"],.014)
    box("counter_top",(0,0,h-.02),(w+.05,d+.05,.065),m["panel"],.012)
    bays=1+v%2
    for i in range(bays):
        dw=(w-.09)/bays
        x=(i-(bays-1)/2)*dw
        box(f"recessed_panel_{i}",(x,-d/2-.018,h*.51),(dw-.035,.024,h*.68),m["paint"],.010)
        box(f"raised_door_border_{i}",(x,-d/2-.032,h*.51),(dw-.09,.013,h*.58),m["light"],.007)
        cyl(f"knob_{i}",(x+dw*.3,-d/2-.046,h*.49),.022,.040,m["steel"],verts=12,rotation=(math.pi/2,0,0))
    for x in (-w*.40,w*.40):
        for y in (-d*.35,d*.35):
            box(f"leg_{x:.2f}_{y:.2f}",(x,y,.07),(.07,.065,.14),m["wood"],.003)
    box("cabinet_rear_panel",(0,d/2+.021,h*.55),(w*.87,.031,h*.72),m["wood"],.009)
    box("cabinet_base_kickplate",(0,-d/2-.017,.18),(w*.83,.024,.09),m["dark"],.004)
    for side in (-1,1):
        box(f"door_visible_hinge_{side}",(side*w*.41,-d/2-.047,h*.70),(.028,.027,.083),m["steel"],.005)
    return (w+.05,d+.06,h+.05)

def generator(v,r,m):
    w=.93+v%3*.08;d=.59;h=.82
    box("engine_cradle",(0,0,.19),(w,d,.09),m["steel"],.011)
    box("generator_main_body",(0,0,.49),(w*.77,d*.82,.53),m["paint"],.042)
    box("top_fuel_tank",(0,0,.78),(w*.55,d*.66,.17),m["light"],.022)
    box("fuel_cap",(w*.16,0,.89),(.09,.09,.045),m["dark"],.008)
    for i in range(5+v%4):
        box(f"cooling_fin_{i}",(-w*.22+i*.058,-d*.425,.42),(.027,.020,.30),m["dark"],.005)
    box("control_plate",(w*.22,-d*.425,.56),(.24,.015,.19),m["dark"],.004)
    for i in range(3):
        cyl(f"control_led_{i}",(w*.12+i*.055,-d*.437,.57),.012,.013,m["panel"],verts=12,rotation=(math.pi/2,0,0))
    for x in (-w*.38,w*.38):
        cyl(f"rubber_wheel_{x:.2f}",(x,d*.38,.13),.124,.069,m["dark"],rotation=(math.pi/2,0,0))
        cyl(f"steel_hub_{x:.2f}",(x,d*.43,.13),.047,.072,m["steel"],rotation=(math.pi/2,0,0))
    box("carry_handle",(0,0,.99),(.44,.045,.031),m["steel"])
    for x in (-.21,.21):
        box(f"handle_upright_{x}",(x,0,.91),(.025,.040,.18),m["steel"])
    cyl("exhaust",(w*.32,d*.16,.96),.043,.21,m["dark"],verts=16)
    return (w,d,.99)

def vending(v,r,m):
    w=.82+v%3*.09;d=.64;h=1.88
    box("machine_body",(0,0,h/2),(w,d,h),m["paint"],.033)
    box("front_door_frame",(-w*.12,-d/2-.025,h*.53),(w*.70,.040,h*.74),m["dark"],.015)
    box("display_glazing",(-w*.12,-d/2-.052,h*.55),(w*.62,.015,h*.63),m["glass"],.009)
    for row in range(4):
        for col in range(3):
            x=-w*.37+col*w*.24
            z=h*.32+row*h*.13
            box(f"stock_item_{row}_{col}",(x,-d/2-.043,z),(.065,.020,.11),m["panel"] if (row+col+v)%2 else m["light"],.009)
    box("keypad",(w*.37,-d/2-.04,h*.57),(.12,.030,.22),m["dark"],.007)
    for n in range(6):
        box(f"button_{n}",(w*.33+(n%2)*.044,-d/2-.060,h*.62-(n//2)*.057),(.021,.009,.025),m["panel"])
    box("pickup_chute",(0,-d/2-.042,h*.145),(w*.57,.02,.16),m["dark"],.012)
    box("top_advertise",(0,-d/2-.044,h*.935),(w*.80,.017,h*.077),m["light"],.005)
    return (w,d,h)

def dumpster(v,r,m):
    w=1.50+v%4*.10;d=1.05;h=1.25
    box("pressed_steel_bin",(0,0,h*.49),(w,d,h*.90),m["paint"],.04)
    box("top_rim",(0,0,h*.96),(w+.06,d+.06,.075),m["dark"],.012)
    for x in (-w*.30,0,w*.30):
        box(f"front_stiffener_{x:.2f}",(x,-d/2-.018,h*.46),(.07,.034,h*.72),m["light"],.006)
    for side in (-1,1):
        x=side*(w/2+.025)
        box(f"side_lift_socket_{side}",(x,0,h*.42),(.09,.33,.18),m["steel"],.018)
    for half in (-1,1):
        x=half*w*.26
        box(f"hinged_lid_{half}",(x,0,h+.055),(w*.49,d*.98,.045),m["dark"],.012)
        for y in (-d*.30,d*.30):
            box(f"lid_rib_{half}_{y:.2f}",(x,y,h+.08),(w*.45,.035,.014),m["steel"],.005)
    for x in (-w*.40,w*.40):
        for y in (-d*.35,d*.35):
            cyl(f"wheel_{x:.2f}_{y:.2f}",(x,y,.065),.064,.04,m["dark"],rotation=(math.pi/2,0,0))
    return (w+.13,d+.06,h+.11)

def planter(v,r,m):
    w=1.15+v%4*.13;d=.68;h=.45
    box("moist_soil",(0,0,.30),(w*.90,d*.84,.20),m["soil"],.006)
    for x in (-w/2,w/2):
        box(f"oak_end_plank_{x:.2f}",(x,0,.28),(.085,d,.43),m["wood"],.006)
    for y in (-d/2,d/2):
        box(f"oak_side_plank_{y:.2f}",(0,y,.28),(w,.08,.43),m["wood"],.006)
    for x in (-w*.43,w*.43):
        for y in (-d*.40,d*.40):
            box(f"corner_post_{x:.2f}_{y:.2f}",(x,y,.26),(.07,.075,.52),m["steel"],.005)
    count=4+v%4
    for i in range(count):
        x=(i-(count-1)/2)*w*.78/max(count-1,1)
        y=(i%2-.5)*d*.24
        ht=.27+.08*((v+i)%3)
        cyl(f"plant_stem_{i}",(x,y,.40+ht/2),.014,ht,m["leaf"],verts=8)
        for a in range(3+v%2):
            phi=2*math.pi*a/(3+v%2)
            z=.46+ht*.55+a*.025
            leaf=cyl(f"leaf_cluster_{i}_{a}",(x+math.cos(phi)*.075,y+math.sin(phi)*.075,z),.062,.025,m["leaf"],verts=8,
                     rotation=(r.uniform(-.8,.8),r.uniform(-.8,.8),0))
    return (w+.13,d+.09,1.04)

GENERATORS={
    "industrial_locker":locker,"tool_chest":chest,"warehouse_shelf":shelf,
    "utility_cabinet":cabinet,"portable_generator":generator,
    "vending_machine":vending,"street_dumpster":dumpster,"raised_planter":planter
}

def rust_chips(r,m,bounds,variant):
    w,d,h=bounds
    for i in range(4+variant%7):
        # Small surface marks, intentionally geometric and non-overlapping on front face.
        x=r.uniform(-w*.39,w*.39)
        z=r.uniform(max(.11,h*.12),h*.91)
        box(f"front_paint_scuff_{i}",(x,-d/2-.071,z),(r.uniform(.013,.041),.006,.007),m["rust"])

def export_one(spec,output):
    global MATS,COUNT
    bpy.ops.wm.read_factory_settings(use_empty=True)
    MATS={}
    COUNT=0
    rng=random.Random(spec["seed"])
    mats=seed_materials(rng,spec["variant"])
    bounds=GENERATORS[spec["archetype"]](spec["variant"],rng,mats)
    # Rust is deliberately sparse rather than uniform noise; reviewer must calibrate.
    rust_chips(rng,mats,bounds,spec["variant"])
    obj=[o for o in bpy.data.objects if o.type=="MESH"]
    if not 15<=len(obj)<=250:
        raise ValueError("Unapproved geometry object count")
    bpy.context.view_layer.update()
    xyz=[o.matrix_world@Vector(c) for o in obj for c in o.bound_box]
    lo=[min(v[i] for v in xyz) for i in range(3)]
    hi=[max(v[i] for v in xyz) for i in range(3)]
    dims=[hi[i]-lo[i] for i in range(3)]
    if any(not .1<=d<=5 for d in dims):
        raise ValueError(f"Out of scale geometry {dims}")
    if lo[2]<-.06:
        raise ValueError("Asset goes below z=0 ground plane")
    folder=output/spec["asset_id"]
    folder.mkdir(parents=True,exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str((folder/"model.blend").resolve()))
    bpy.ops.export_scene.gltf(filepath=str((folder/"model.glb").resolve()),export_format="GLB",export_apply=True)
    glb=(folder/"model.glb").read_bytes()
    blend=(folder/"model.blend").read_bytes()
    if (len(glb)<1000 or glb[:4]!=b"glTF" or struct.unpack_from("<I",glb,8)[0]!=len(glb)
        or len(blend)<1000 or (blend[:7]!=b"BLENDER" and blend[:4]!=bytes.fromhex("28b52ffd"))):
        raise ValueError("Source export missing or has invalid signature")
    manifest={
        **spec,"source_kind":"NEW_ORIGINAL_PROCEDURAL_BLENDER_MESH",
        "geometry_object_count":len(obj),"material_count":len(bpy.data.materials),
        "dimensions_m":dims, "base_z_m":lo[2],
        "blender_version":bpy.app.version_string,
        "blend_sha256":hashlib.sha256(blend).hexdigest(),
        "glb_sha256":hashlib.sha256(glb).hexdigest(),
        "source_editable":True, "material_contract":"F11_PRECALIBRATION",
        "f12_approved":False,"golden_approved":False,"gameplay_integrated":False
    }
    (folder/"source_manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")
    print("FOUNDRY_NEW_SOURCE",spec["asset_id"],len(obj),dims,flush=True)
    return {
        "asset_id":spec["asset_id"],"glb_path":str((folder/"model.glb").resolve()),
        "glb_sha256":manifest["glb_sha256"],"original_blend_size_bytes":len(blend),
        "source_manifest_path":str((folder/"source_manifest.json").resolve())
    }

def main():
    argv=sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []
    p=argparse.ArgumentParser()
    p.add_argument("--plan",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args(argv)
    plan=json.loads(a.plan.read_text())
    if (plan.get("schema_version")!=1 or plan.get("generator_kind")!="DETERMINISTIC_BLENDER_PROCEDURAL_SOURCE"
        or plan.get("golden_approved") is not False or len(plan.get("selected",[]))>4):
        raise ValueError("Invalid source construction plan")
    selected=[export_one(spec,a.output) for spec in plan["selected"]]
    render_plan={
        "schema_version":1,"status":plan["status"],
        "source_plan_sha256":plan["catalog_sha256"],
        "source_count":plan["total"], "completed_before":plan["completed_before"],
        "selected":selected,"golden_approved":False
    }
    (a.output/"render_plan.json").write_text(json.dumps(render_plan,indent=2)+"\n")

if __name__=="__main__":
    main()
