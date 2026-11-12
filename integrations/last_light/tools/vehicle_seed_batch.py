#!/usr/bin/env python3
"""Eight original reference-informed F11/F12 GLB technical candidates.

No source image pixels, logos, or proprietary 3D meshes are used. This is a
bounded, deterministic candidate batch; it does not consume paid Copilot.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from seed_3d_factory import Maker, render
from foundry_601_650 import ACTIVE_RECIPES, produce, SCHEMA


def build(key: str) -> Maker:
    m=Maker(key)
    if key=='vehicle_battery':
        m.box('insulated_12v_case',(0,0,.31),(.69,.43,.53),'black')
        m.box('molded_case_rim',(0,0,.59),(.71,.45,.07),'darkmetal')
        m.box('lid_plate',(0,0,.62),(.65,.40,.06),'navy')
        for x in (-.22,0,.22):
            m.box('removable_cell_cover',(x,0,.66),(.18,.30,.025),'black')
        for x,c in ((-.26,'red'),(.26,'steel')):
            m.cyl('raised_terminal_post',(x,.10,.715),.065,.10,c,sections=16)
            m.cyl('terminal_collar',(x,.10,.675),.092,.022,'darkmetal')
        m.line('recessed_lift_handle',[(-.17,-.01,.67),(-.17,-.01,.75),(.17,-.01,.75),(.17,-.01,.67)],.025,'black')
        for x in (-.30,.30):m.box('side_case_reinforcing_rib',(x,-.216,.31),(.025,.012,.46),'metal')
    elif key=='scissor_jack':
        m.box('foot_plate',(0,0,.035),(.94,.38,.07),'darkmetal')
        m.box('saddle',(0,0,.87),(.38,.32,.09),'steel')
        for y in (-.12,.12):
            for a,b in (((-.42,y,.11),(.0,y,.80)),((.42,y,.11),(.0,y,.80)),((-.32,y,.80),(.0,y,.12)),((.32,y,.80),(.0,y,.12))):
                m.rod('hinged_lifting_arm',a,b,.057,'rust')
            for x,z in ((-.28,.20),(.28,.20),(0,.50)):
                m.cyl('bearing_pivot',(x,y,z),.067,.04,'steel',axis='y')
        m.rod('threaded_drive_screw',(-.42,0,.48),(.49,0,.48),.034,'steel')
        for x in np.linspace(-.35,.42,12):m.torus('fine_drive_thread',(float(x),0,.48),.036,.008,'darkmetal',axis='x')
        m.rod('turning_crank',(.48,0,.48),(.68,0,.48),.042,'steel')
        m.rod('crank_handle',(.68,0,.48),(.68,-.24,.48),.035,'black')
    elif key=='automotive_tire':
        m.torus('continuous_black_rubber_carcass',(0,0,.43),.31,.15,'rubber',axis='y')
        m.torus('outer_sidewall_shoulder',(0,-.12,.43),.31,.055,'black',axis='y')
        m.torus('rear_sidewall_shoulder',(0,.12,.43),.31,.055,'black',axis='y')
        for i in range(24):
            angle=i*2*math.pi/24
            x=.42*math.cos(angle);z=.43+.42*math.sin(angle)
            m.box('separate_tread_block',(x,0,z),(.105,.29,.042),'darkmetal',rot=(angle,[0,1,0]))
        m.torus('recessed_inner_bead',(0,-.03,.43),.21,.026,'darkmetal',axis='y')
    elif key=='alloy_wheel':
        m.torus('machined_outer_rim',(0,0,.45),.36,.068,'steel',axis='y')
        m.torus('inner_bead_lock',(0,0,.45),.26,.032,'metal',axis='y')
        m.cyl('center_hub',(0,0,.45),.13,.12,'steel',axis='y')
        for i in range(5):
            a=2*math.pi*i/5
            m.rod('five_spoke_alloy_structure',(.09*math.cos(a),0,.45+.09*math.sin(a)),(.32*math.cos(a),0,.45+.32*math.sin(a)),.06,'steel')
            m.cyl('wheel_lug_bore',(.096*math.cos(a),-.07,.45+.096*math.sin(a)),.028,.018,'darkmetal',axis='y')
        m.cyl('separate_center_cap',(0,-.074,.45),.056,.023,'darkmetal',axis='y')
    elif key=='vehicle_radiator':
        m.box('rectangular_core',(0,0,.54),(.92,.16,.87),'darkmetal')
        for i in range(18):
            z=.17+i*.043
            m.box('heat_exchanger_fin',(0,-.091,z),(.83,.015,.018),'metal')
        for x in (-.48,.48):m.box('side_water_tank',(x,0,.54),(.12,.24,.95),'steel')
        m.box('top_structural_crossmember',(0,0,1.04),(.98,.23,.07),'rust')
        m.box('lower_structural_crossmember',(0,0,.045),(.98,.23,.07),'rust')
        for x in (-.42,.42):
            m.box('mounting_tab',(x,0,1.115),(.11,.23,.08),'metal')
            m.cyl('mounting_bolt',(x,-.13,1.118),.032,.035,'black',axis='y')
        m.cyl('upper_hose_port',(.55,0,.86),.11,.28,'steel',axis='x')
        m.cyl('lower_hose_port',(-.55,0,.24),.11,.28,'steel',axis='x')
        m.cyl('radiator_pressure_neck',(.26,0,1.115),.08,.11,'steel')
        m.cyl('pressure_cap',(.26,0,1.18),.105,.035,'black')
    elif key=='carburetor':
        m.box('cast_lower_fuel_bowl',(0,0,.20),(.68,.49,.36),'metal')
        m.box('gasket_flange',(0,0,.41),(.71,.53,.075),'darkmetal')
        for x in (-.17,.17):
            m.cyl('dual_vertical_venturi',(x,0,.74),.17,.56,'steel')
            m.cyl('open_intake_throat',(x,0,1.025),.122,.018,'darkmetal')
            m.torus('upper_throttle_rim',(x,0,1.02),.165,.025,'rust')
        m.box('float_chamber_cover',(0,-.277,.22),(.53,.083,.25),'rust')
        for x in (-.27,.27):m.cyl('chamber_fastener',(x,-.33,.19),.024,.045,'steel',axis='y')
        m.rod('throttle_linkage',(.27,0,.55),(.48,0,.77),.028,'darkmetal')
        m.rod('fuel_inlet_tube',(-.30,0,.28),(-.53,0,.37),.055,'steel')
        m.cyl('air_fuel_mixture_screw',(.34,-.23,.34),.036,.20,'steel',axis='x')
    elif key=='vehicle_seat':
        m.box('steel_mounting_rails',(0,0,.06),(.64,.62,.09),'darkmetal')
        for x in (-.25,.25):m.box('sliding_floor_channel',(x,0,.035),(.09,.78,.07),'steel')
        m.box('seat_cushion',(0,-.10,.34),(.77,.66,.27),'fabric',rot=(.08,[1,0,0]))
        m.box('rounded_front_edge',(0,-.40,.29),(.74,.12,.23),'khaki')
        m.box('backrest_frame',(0,.24,.78),(.78,.27,1.03),'darkmetal',rot=(-.13,[1,0,0]))
        m.box('backrest_upholstery',(0,.08,.80),(.72,.29,.97),'fabric',rot=(-.13,[1,0,0]))
        m.box('lumbar_relief',(0,-.081,.57),(.57,.039,.22),'khaki')
        m.box('backrest_center_ventilation',(0,-.075,1.01),(.45,.041,.32),'khaki')
        for x in (-.22,.22):m.rod('headrest_mount_rod',(x,.16,1.32),(x,.16,1.57),.025,'steel')
        m.box('detachable_headrest',(0,.14,1.60),(.54,.25,.25),'fabric')
        m.box('side_recline_knob',(.42,.21,.42),(.085,.10,.085),'black')
    elif key=='cast_iron_skillet':
        m.cyl('iron_cooking_base',(0,0,.10),.37,.10,'darkmetal')
        m.torus('flared_cast_rim',(0,0,.17),.385,.048,'metal')
        m.cyl('empty_inner_cooking_surface',(0,0,.159),.33,.012,'black')
        m.rod('integral_long_handle',(.35,0,.13),(.96,0,.13),.081,'darkmetal')
        m.torus('handle_hanging_eye',(1.00,0,.13),.064,.020,'metal')
        m.box('short_pour_spout',(-.35,0,.16),(.14,.15,.04),'metal')
        m.box('opposite_iron_helper_grip',(-.35,0,.12),(.20,.14,.065),'darkmetal')
    else:
        raise KeyError(key)
    return m


def run(output:Path)->dict:
    input_catalog=produce()
    if input_catalog['schema']!=SCHEMA or input_catalog['founder_golden_approved']:
        raise ValueError('invalid source admission')
    output.mkdir(parents=True,exist_ok=True)
    for folder in ('models','sprites_64','world_atlas_8','preview_144'):(output/folder).mkdir(exist_ok=True)
    manifest=dict(schema='last-light.vehicle-seed-3d.v1',status='TECHNICAL_CANDIDATE_NOT_GOLDEN',
                  founder_golden_approved=False,notion_canonical_ids='UNRESOLVED',
                  source_intake_schema=SCHEMA,
                  rights='original procedural geometry; no supplied image pixels or logos used',assets=[])
    atlas=Image.new('RGBA',(64*4,64*2),(0,0,0,0))
    for idx,key in enumerate(ACTIVE_RECIPES):
        m=build(key)
        glb=output/'models'/f'{key}.glb'
        m.scene.export(file_obj=str(glb),file_type='glb')
        preview=output/'preview_144'/f'{key}.png'
        render(m.scene,preview)
        img=Image.open(preview).convert('RGBA').resize((64,64),Image.Resampling.LANCZOS)
        img.save(output/'sprites_64'/f'{key}.png')
        # Preserve exact RGBA cell bytes; alpha_composite rewrites antialias pixels.
        atlas.paste(img,((idx%4)*64,(idx//4)*64))
        world=Image.new('RGBA',(64,64*8),(0,0,0,0))
        for heading in range(8):
            frame=output/'world_atlas_8'/f'__temporary_{idx}_{heading}.png'
            render(m.scene,frame,64,heading*45)
            with Image.open(frame) as fr:world.alpha_composite(fr,(0,heading*64))
            frame.unlink()
        world.save(output/'world_atlas_8'/f'{key}.png')
        ntri=sum(x['triangles'] for x in m.parts)
        manifest['assets'].append(dict(candidate_id=f'll_vehicle_ref_{idx+1:03}',recipe_key=key,
              source_concept_id=key,glb=f'models/{key}.glb',sha256=hashlib.sha256(glb.read_bytes()).hexdigest(),
              sprite_64=f'sprites_64/{key}.png',atlas_8=f'world_atlas_8/{key}.png',
              component_count=len(m.parts),triangles=ntri,component_names=[x['component'] for x in m.parts],
              golden_approved=False,notion_id=None,artistic_review='PENDING',collision='UNTESTED',
              actual_mobile_performance='UNTESTED'))
        print('LL_VEHICLE_MODEL_CANDIDATE',key,len(m.parts),ntri,flush=True)
    atlas.save(output/'inventory_8_items_64px.png')
    manifest['inventory_atlas']={'file':'inventory_8_items_64px.png','rows':2,'columns':4,'cell_px':[64,64]}
    (output/'candidate_manifest.json').write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n')
    print('LL_VEHICLE_ORIGINAL_MODELS_PASS',len(manifest['assets']),flush=True)
    return manifest

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,required=True);a=ap.parse_args()
    run(a.output)
