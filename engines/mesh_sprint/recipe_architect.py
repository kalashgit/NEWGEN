"""NEWGEN original design-brief -> deterministic construction recipe.

A language model / sprite inspector can supply a verified original design brief later.
These built-in test contracts are independently authored from the stated object
identity. They are NOT representations of the 4,347 canonical sprite references.
"""
import copy
import hashlib
import json

CONTRACTS = {
 'avocado': {
  'asset_id':'NG-DEMO-AVOCADO-001', 'name':'Halved avocado', 'family':'avocado',
  'intent':'Single ripe pear-shaped avocado half, exposed green flesh and brown central pit, dimensional dark rind',
  'geometry_parts':['pear-shaped skin shell','exposed flesh','inset seed cavity','brown pit','rind edge','short stem'],
  'material_roles':['skin','flesh','pit','flesh_green'],
  'visual_targets':{'foreground_min':0.075,'landmark_green_min':0.10,'landmark_brown_min':0.006,'edge_density_min':0.060,'bbox_width_ratio_max':0.63},
  'correction_operations':['seed_visibility','rind_definition','skin_texture'],
  'gameplay':{'category':'food','pickable':True,'collision':'box','inventory_size':[1,1], 'sockets':['grip']}
 },
 'backpack':{
  'asset_id':'NG-DEMO-BACKPACK-001','name':'Field backpack','family':'backpack',
  'intent':'Soft olive field rucksack with shaped body, protruding front pocket, two rear straps, zipper, carry handle',
  'geometry_parts':['padded body','front pouch','side pouches','zipper and pulls','rear shoulder straps','top handle','stitched seams'],
  'material_roles':['fabric','fabric_light','fabric_dark','steel'],
  'visual_targets':{'foreground_min':0.10,'landmark_green_min':0.04,'edge_density_min':0.065},
  'correction_operations':['pocket_seams','compression_webbing','stitch_details'],
  'gameplay':{'category':'wearable_container','pickable':True,'collision':'box','inventory_size':[2,3], 'sockets':['back','grip']}
 },
 'axe':{
  'asset_id':'NG-DEMO-AXE-001','name':'Forged woodsman axe','family':'axe',
  'intent':'Original long curved wooden haft with broad flared forged steel head, thin bevel and distinct socket',
  'geometry_parts':['curved tapered haft','flared metal head','thin sharpened wedge','reinforced eye/socket','wood-grain grip'],
  'material_roles':['wood','steel','edge','steel_dark'],
  'visual_targets':{'foreground_min':0.035,'landmark_brown_min':0.009,'landmark_metal_min':0.008,'edge_density_min':0.095},
  'correction_operations':['blade_definition','haft_grip','metal_surface'],
  'gameplay':{'category':'tool','pickable':True,'collision':'box','inventory_size':[1,3], 'sockets':['right_hand','grip']}
 }
}


def architect(family, *, seed=51):
    if family not in CONTRACTS:raise ValueError('Uninspected family: original design brief required')
    out=copy.deepcopy(CONTRACTS[family]);out['seed']=seed
    out['recipe_version']='NG_CLOSED_LOOP_DEMO_V1'
    out['source_evidence']={'type':'ORIGINAL_TEXT_DESIGN_CONTRACT','sprite_available':False,
      'sprite_identity_verified':False,'scope':'three hand-authored examples, not the LAST LIGHT master catalog'}
    out['geometric_recipe']={'operation':'authored_procedural_family','family':family,
     'operator_registry':'newgen.mesh_sprint.quality_geometry',
     'correction_operations':out['correction_operations']}
    out['sha256']=hashlib.sha256(json.dumps(out,sort_keys=True).encode()).hexdigest()
    return out
