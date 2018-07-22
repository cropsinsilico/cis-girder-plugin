import json
import yaml
from pprint import pprint

with open('fbp-light-files.json') as f:
    data = json.load(f)


    

inports = {}
outports = {}
models = {}
for key,process in data['processes'].items():
    component =  process['component'] 
    if component == 'inport' or component == 'outport':
        port = {}
        port['name'] = process['metadata']['name']
        port['type'] = process['metadata']['type']
        if component == 'inport':
           port['method']  = process['metadata']['read_meth']
           inports[key] = port  
        else:
           outports[key] = port  
    else: 
        models[key] = component

conns = []
for connection in data['connections']:
    srckey = connection['src']['process']
    srcport = connection['src']['port']
    tgtkey = connection['tgt']['process']
    tgtport = connection['tgt']['port']

    conn = {}
    if srckey in inports:
       conn['input'] = inports[srckey]['name']
       conn['filetype'] = inports[srckey]['method']
       conn['output'] = connection['tgt']['port']
    elif tgtkey in outports:
       conn['input'] = connection['src']['port']
       conn['output'] = outports[tgtkey]['name']
    conns.append(conn)
        
output = { "models": models, "connections": conns } 
print(yaml.safe_dump(output, default_flow_style=False))

"""
models:
  - name: LightModel
    language: c
    args:
      - example-fakeplant/src/light.c
      - -lm
    inputs:
      - ambient_light
      - canopy_structure
    outputs:
      - light_intensity
connections:
  - input: example-fakeplant/Input/ambient_light.txt
    output: ambient_light
    filetype: table
  - input: example-fakeplant/Input/canopy_structure.txt
    output: canopy_structure
    filetype: table_array
  - input: light_intensity
    output: output/light_intensity.txt
    filetype: table
    field_names: light_intensity
"""
