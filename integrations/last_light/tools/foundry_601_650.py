#!/usr/bin/env python3
"""Fail-closed, provisional semantic intake for eight founder reference sheets.

Sheet numbers are layout labels, NOT canonical Notion asset IDs. A label such as
601 can name a canned meal in one sheet and a metal tool in another. Only
explicit concept-to-sheet observations are reconciled; everything else waits.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

SCHEMA = "last-light.founder-multisheet-intake.v1"
SHEETS = (
    ("S01_SURVIVAL_KITCHEN", "BEF3741D-5B4B-44CE-ACFE-16BBF48A7154(1).jpeg", "c3ecf66fe7bc3eefc2d26ee93feee3dc3ff66f6077a58e93e15e3f4c814cdd3b", "numbered_10x5"),
    ("S02_PANTRY_TOBACCO", "AEAFFB0D-819F-4DA6-BA30-493B036BAB01(1).jpeg", "609a5f39616d2b0e7dc51695cf1b62746a45174acad52154c197bd71dd6e8295", "numbered_10x5"),
    ("S03_VEHICLE_PARTS", "E420D3A6-579C-4B21-A096-AF532576016C(1).jpeg", "5c060050f974ff0219ce1e8fd44b00a9e3a921c9cd3181cfe4f9cf1af8ca2f0f", "numbered_10x5"),
    ("S04_GENERAL_CAR", "CA6A6605-A6AF-4CF6-9554-DF6065FA1A37(1).jpeg", "32dfb8e0bae103b73c281162d0a54f8a2912d8c1e37e1c789ebf981039c0b715", "numbered_10x5"),
    ("S05_CAR_MAINTENANCE", "9848FE93-BBD4-425B-AB78-658970CDE0B9(1).jpeg", "098111b7d21cd4c2279d54fc8cb78ebf159e07a5bb4dc2259c4bd47ee28da5a6", "numbered_10x5"),
    ("S06_MIXED_PARTS", "C8D3321E-52A5-4B2D-A9CB-3C168926807C.jpeg", "d165ca590f932762560be683135b9057f9fb521824dcb94890917fb92e9f59c8", "numbered_10x5"),
    ("S07_DENSE_MISC", "87D0B615-DBE7-4267-8F34-6FE69076E658(1).jpeg", "4bacf61f9464c8082d1fe63e017572f54202121106937af0860174c9fb3e2227", "dense_unverified_grid"),
    ("S08_DENSE_PANTRY", "FE1211BB-E9B7-4628-9B36-71E1A8E98B52(1).jpeg", "69ee5e85f2a3d8a3d42771d604ca799084ea30a32fd524e5291e37fd55082a9c", "dense_unverified_grid"),
)

# Each entry is a provisional physical object concept and explicit positions
# observed by an engineer. A position can be used at most once. Never infer
# identity by the printed number alone. Variants do not create extra geometry.
CONCEPTS = (
    ("canned_chili", "sealed_tin_can", (("S01_SURVIVAL_KITCHEN",601),("S02_PANTRY_TOBACCO",601),("S03_VEHICLE_PARTS",601),("S04_GENERAL_CAR",601),("S05_CAR_MAINTENANCE",601))),
    ("canned_sweet_corn", "sealed_tin_can", (("S01_SURVIVAL_KITCHEN",602),("S02_PANTRY_TOBACCO",602),("S03_VEHICLE_PARTS",602),("S04_GENERAL_CAR",602),("S05_CAR_MAINTENANCE",602))),
    ("canned_tuna", "sealed_tin_can", (("S02_PANTRY_TOBACCO",604),("S03_VEHICLE_PARTS",609),("S04_GENERAL_CAR",609),("S05_CAR_MAINTENANCE",606))),
    ("metal_canteen", "canteen_metal", (("S01_SURVIVAL_KITCHEN",609),("S03_VEHICLE_PARTS",611),("S05_CAR_MAINTENANCE",607),("S06_MIXED_PARTS",602))),
    ("vehicle_battery", "battery_12v", (("S01_SURVIVAL_KITCHEN",614),("S03_VEHICLE_PARTS",615),("S04_GENERAL_CAR",616),("S05_CAR_MAINTENANCE",612),("S06_MIXED_PARTS",605))),
    ("scissor_jack", "mechanical_scissor_jack", (("S03_VEHICLE_PARTS",616),("S06_MIXED_PARTS",607))),
    ("hydraulic_floor_jack", "rolling_floor_jack", (("S04_GENERAL_CAR",618),("S05_CAR_MAINTENANCE",613))),
    ("automotive_tire", "bare_tire", (("S03_VEHICLE_PARTS",617),("S04_GENERAL_CAR",620),("S05_CAR_MAINTENANCE",615),("S06_MIXED_PARTS",613))),
    ("alloy_wheel", "alloy_wheel_rim", (("S03_VEHICLE_PARTS",619),("S04_GENERAL_CAR",622),("S05_CAR_MAINTENANCE",618),("S06_MIXED_PARTS",614))),
    ("vehicle_radiator", "radiator_core", (("S03_VEHICLE_PARTS",625),("S05_CAR_MAINTENANCE",641),("S06_MIXED_PARTS",610))),
    ("carburetor", "fuel_air_mixer", (("S01_SURVIVAL_KITCHEN",620),("S04_GENERAL_CAR",617),("S06_MIXED_PARTS",606))),
    ("vehicle_seat", "upholstered_car_seat", (("S03_VEHICLE_PARTS",631),("S03_VEHICLE_PARTS",632),("S05_CAR_MAINTENANCE",647),("S06_MIXED_PARTS",611),("S06_MIXED_PARTS",612))),
    ("cast_iron_skillet", "frying_pan", (("S01_SURVIVAL_KITCHEN",626),("S02_PANTRY_TOBACCO",626),("S06_MIXED_PARTS",627))),
    ("rolled_blanket", "rolled_textile", (("S01_SURVIVAL_KITCHEN",612),("S04_GENERAL_CAR",614),("S05_CAR_MAINTENANCE",611),("S06_MIXED_PARTS",621))),
    ("canned_cat_food", "sealed_tin_can", (("S01_SURVIVAL_KITCHEN",627),("S06_MIXED_PARTS",629))),
    ("cheese_wedge", "food_cheese_wedge", (("S01_SURVIVAL_KITCHEN",634),("S06_MIXED_PARTS",648),("S06_MIXED_PARTS",649))),
    ("chalk_sticks", "chalk_cylinder_bundle", (("S01_SURVIVAL_KITCHEN",631),("S04_GENERAL_CAR",644),("S06_MIXED_PARTS",643))),
    ("playing_card_deck", "card_paper_stack", (("S01_SURVIVAL_KITCHEN",616),("S04_GENERAL_CAR",625),("S06_MIXED_PARTS",617))),
    ("cardboard_shipping_box", "carton_box", (("S01_SURVIVAL_KITCHEN",618),("S01_SURVIVAL_KITCHEN",619),("S04_GENERAL_CAR",628),("S06_MIXED_PARTS",619))),
    ("fresh_carrots", "root_vegetable_bundle", (("S01_SURVIVAL_KITCHEN",621),("S04_GENERAL_CAR",631),("S06_MIXED_PARTS",623))),
    ("chainsaw", "motor_chain_saw", (("S04_GENERAL_CAR",640),("S06_MIXED_PARTS",641))),
    ("charcoal_lumps", "fuel_charcoal", (("S01_SURVIVAL_KITCHEN",633),("S04_GENERAL_CAR",649),("S06_MIXED_PARTS",647))),
    ("chef_hat", "toque_fabric", (("S01_SURVIVAL_KITCHEN",636),("S02_PANTRY_TOBACCO",624))),
)

ACTIVE_RECIPES = ("vehicle_battery", "scissor_jack", "automotive_tire", "alloy_wheel", "vehicle_radiator", "carburetor", "vehicle_seat", "cast_iron_skillet")

def sha256(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for part in iter(lambda:f.read(1024*1024), b""):
            h.update(part)
    return h.hexdigest()

def produce(source_dir: Path | None = None) -> dict:
    sources=[]; slots=[]
    for name,filename,digest,layout in SHEETS:
        if source_dir is not None:
            f=source_dir/filename
            if not f.is_file() or sha256(f)!=digest:
                raise ValueError(f"missing/tampered founder reference sheet: {name}")
            from PIL import Image
            with Image.open(f) as im:
                if im.size!=(1536,1024):
                    raise ValueError(f"wrong source dimensions: {name}")
        sources.append(dict(sheet_id=name,filename=filename,sha256=digest,dimensions=[1536,1024],layout=layout,bytes_in_git=False))
        if layout=="numbered_10x5":
            for n in range(601,651):
                slots.append(dict(source_sheet=name,visual_slot=n,grid_row=(n-601)//10,grid_column=(n-601)%10,canonical_notion_id=None,concept_id=None,review="AWAITING_SEMANTIC_RECONCILIATION"))
    seen=set();groups=[];by_slot={(s['source_sheet'],s['visual_slot']):s for s in slots}
    for concept,family,observations in CONCEPTS:
        if not observations or concept in seen:
            raise ValueError(f"invalid unique concept {concept}")
        seen.add(concept)
        refs=[]
        for sheet,num in observations:
            key=(sheet,num)
            if key not in by_slot:
                raise ValueError(f"unknown sheet/slot: {key}")
            if by_slot[key]['concept_id'] is not None:
                raise ValueError(f"one reference slot assigned twice: {key}")
            by_slot[key]['concept_id']=concept
            by_slot[key]['review']="MANUALLY_GROUPED_PROVISIONAL"
            refs.append(dict(sheet_id=sheet,visual_slot=num))
        groups.append(dict(concept_id=concept,geometry_family=family,observations=refs,notion_canonical_id=None,visual_golden_approved=False,requires_distinct_model=concept in ACTIVE_RECIPES))
    if not set(ACTIVE_RECIPES).issubset(seen):
        raise ValueError('active recipe lacks a concept group')
    if len(slots)!=300 or len(groups)!=len(CONCEPTS):
        raise ValueError('intake expansion inconsistent')
    return dict(schema=SCHEMA,status='PROVISIONAL_NOT_GOLDEN',founder_golden_approved=False,
                rights='REFERENCE_ONLY_NO_SOURCE_PIXELS_REUSED_AS_GAME_TEXTURES',
                sources=sources,numbered_visual_slots=slots,reconciled_concepts=groups,
                active_technical_recipe_concepts=list(ACTIVE_RECIPES),
                counts=dict(original_sheets=len(sources),numbered_visual_slots=len(slots),
                    dense_unsegmented_sheets=2,provisional_distinct_concepts=len(groups),
                    manually_grouped_positions=sum(s['concept_id'] is not None for s in slots),
                    unreconciled_numbered_positions=sum(s['concept_id'] is None for s in slots),
                    new_golden_approvals=0,new_models_automatically_approved=0))

def verify(data:dict) -> None:
    if data!=produce():
        raise ValueError('intake edited without source/semantic reconciliation')
    ids={(s['source_sheet'],s['visual_slot']) for s in data['numbered_visual_slots']}
    if len(ids)!=300 or data['founder_golden_approved'] or any(x['notion_canonical_id'] for x in data['reconciled_concepts']):
        raise ValueError('dedup/Golden/Notion invariants violated')
    # These MUST differ: label 601 describes food in one image and pliers in another.
    a=next(s for s in data['numbered_visual_slots'] if s['source_sheet']=='S01_SURVIVAL_KITCHEN' and s['visual_slot']==601)
    b=next(s for s in data['numbered_visual_slots'] if s['source_sheet']=='S06_MIXED_PARTS' and s['visual_slot']==601)
    if a['concept_id']!='canned_chili' or b['concept_id'] is not None:
        raise ValueError('numeric grid collision incorrectly merged')

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--source-dir',type=Path)
    p.add_argument('--output',required=True,type=Path)
    args=p.parse_args()
    data=produce(args.source_dir);verify(data)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(data,sort_keys=True,indent=2)+'\n',encoding='utf-8')
    print('LL_REFERENCE_601_650_INTAKE_PASS',json.dumps(data['counts'],sort_keys=True))
