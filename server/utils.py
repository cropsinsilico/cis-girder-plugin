# -*- coding: utf-8 -*
"""Plugin utilities."""
from git import Repo
import os
import yaml
import shutil
from models.spec import Spec as SpecModel


def cloneRepo(url, path, branch='master'):
    """Use gitpython to clone the specified repo/branch."""
    if not os.path.isdir(path):
        repo = Repo.clone_from(url, path, branch=branch)
    else:
        repo = Repo(path)
    return repo


def cisToUI(cismodel):
    """Convert from cisrun to UI format."""
    uimodel = {}
    for key in cismodel.keys():
        if key == 'name':
            uimodel['label'] = cismodel['name']
            uimodel['name'] = cismodel['name'].lower()
        elif key == 'inputs':
            uimodel['inports'] = convertInputsToPorts(cismodel['inputs'])
        elif key == 'outputs':
            uimodel['outports'] = convertInputsToPorts(cismodel['outputs'])
        else:
            uimodel[key] = cismodel[key]
    return {"content": uimodel}


def uiToCis(uimodel):
    """Convert dict from ui format to cisrun format."""
    cismodel = {}
    for key in uimodel.keys():
        if key == 'name':
            cismodel['name'] = uimodel['label']
        elif key == 'label' or key == 'icon' or key == 'description':
            pass
        elif key == 'inports':
            cismodel['inputs'] = convertPortsToPuts(uimodel['inports'])
        elif key == 'outports':
            cismodel['outputs'] = convertPortsToPuts(uimodel['outports'])
        else:
            cismodel[key] = uimodel[key]
    return {"model": cismodel}


def convertPortsToPuts(ports):
    """Convert UI inports/outports to cisrun inputs/output."""
    puts = []
    for port in ports:
        puts.append(port['name'])
    return puts


def convertInputsToPorts(inputs):
    """Convert cisrun inputs/output to UI inports/outports."""
    ports = []
    for input in inputs:
        port = {}
        port['name'] = input
        port['label'] = input
        port['type'] = 'all'
        ports.append(port)
    return ports


def loadSpecs(repo, path):
    """Load model specs from the specified temporary path.

    Convert from the cisrun YAML to the flow-based-protocol format required
    for UI.  The "content" nested dict is a convention used for storing
    these objects as blobs in Girder.
    """
    specs = {}
    for dirName, subdirList, fileList in os.walk(path + "/models"):

        if dirName.endswith(".git"):
            pass

        for fname in fileList:
            relpath = os.path.relpath(dirName + "/" + fname, path)

            model = {}
            with open(dirName + "/" + fname, 'r') as stream:
                model = yaml.load(stream)

            # Convert to format expected by UI
            converted = cisToUI(model['model'])
            if repo is not None:
                converted['hash'] = str(repo.tree()[relpath])

            specs[converted['content']['name']] = converted
    return specs


def fbpToCis(data):
    """ Given a flow-based-protocol graph, return in CIS format."""
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
            spec = SpecModel().findOne({'content.name': component})
            models[key] = uiToCis(spec['content'])['model']
    
    conns = []
    for connection in data['connections']:
        srckey = connection['src']['process']
        tgtkey = connection['tgt']['process']
    
        conn = {}
        is_model = False
        if srckey in inports:
           conn['input'] = inports[srckey]['name']
           conn['filetype'] = inports[srckey]['method']
           conn['output'] = connection['tgt']['port']
        elif tgtkey in outports:
           conn['input'] = connection['src']['port']
           conn['filetype'] = outports[tgtkey]['method']
           conn['output'] = outports[tgtkey]['name']
        else:
           conn['input'] = connection['src']['port']
           conn['output'] = connection['tgt']['port']

        if 'metadata' in connection and 'field_names' in connection['metadata']:
           conn['field_names'] = connection['metadata']['field_names']
        elif srckey in models and tgtkey in models:
           conn['field_names'] = connection['src']['port']

        if 'filetype' in conn and conn['filetype'] == 'table_array':
           conn['filetype'] = 'table'
           conn['as_array'] = 'True'

        conns.append(conn)

    return { "models": models.values(), "connections": conns }


def ingest():
    """Given a repo of specs, clone the repo and ingest into Girder.

    Use the git object hash to determine whether the spec has changed.
    """
    # TODO: Parameterize these in the plugin configuration
    url = "https://github.com/cropsinsilico/cis-specs"
    path = "/tmp/cis-specs"
    branch = "master"

    repo = cloneRepo(url, path, branch)
    gitspecs = loadSpecs(repo, path)

    specs = {}
    # Delete specs that are not in github
    #for spec in SpecModel().find({}):
    #    if 'public' not in spec or not spec['public']:
    #        pass
    #    name = spec['content']['name']
    #    specs[name] = spec
    #    if name not in gitspecs:
    #        SpecModel().remove(spec)
    #        print("Spec %s removed from github, deleting" % name)

    for key, gitspec in gitspecs.items():
        name = gitspec['content']['name']

        gitspec = gitspecs[name]
        spec = SpecModel().findOne({'content.name': name})
        if spec is not None:
            if 'hash' in spec and spec['hash'] != gitspec['hash']:
                print("Hash changed for spec %s, updating" % name)
                spec['content'] = gitspec['content']
                spec['hash'] = gitspec['hash']
                SpecModel().setPublic(spec, True, save=False)
                SpecModel().save(spec)
            else:
                print("Hash identical, not updating spec %s" % name)

        else:
            print("New spec %s, creating" % name)
            spec = {}
            spec['content'] = gitspec['content']
            spec['hash'] = gitspec['hash']
            SpecModel().setPublic(spec, True, save=False)
            SpecModel().save(spec)

    # Remove the temporary path
    shutil.rmtree(path)
