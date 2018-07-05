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


def cisToFBP(cismodel):
    """Convert from cisrun to flow-based-protocol (FBP)."""
    fbpmodel = {}
    for key in cismodel.keys():
        if key == 'name':
            fbpmodel['label'] = cismodel['name']
            fbpmodel['name'] = cismodel['name'].lower()
        elif key == 'inputs':
            fbpmodel['inports'] = convertInputsToPorts(cismodel['inputs'])
        elif key == 'outputs':
            fbpmodel['outports'] = convertInputsToPorts(cismodel['outputs'])
        else:
            fbpmodel[key] = cismodel[key]
    return {"content": fbpmodel}


def fbpToCis(fbpmodel):
    """Convert dict from fbp format to cisrun format."""
    cismodel = {}
    for key in fbpmodel.keys():
        if key == 'name':
            cismodel['name'] = fbpmodel['label']
        elif key == 'label' or key == 'icon' or key == 'description':
            pass
        elif key == 'inports':
            cismodel['inputs'] = convertPortsToPuts(fbpmodel['inports'])
        elif key == 'outports':
            cismodel['outputs'] = convertPortsToPuts(fbpmodel['outports'])
        else:
            cismodel[key] = fbpmodel[key]
    return {"model": cismodel}


def convertPortsToPuts(ports):
    """Convert FBP inports/outports to cisrun inputs/output."""
    puts = []
    for port in ports:
        puts.append(port['name'])
    return puts


def convertInputsToPorts(inputs):
    """Convert cisrun inputs/output to FBP inports/outports."""
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
            converted = cisToFBP(model['model'])
            converted['hash'] = str(repo.tree()[relpath])

            specs[converted['content']['name']] = converted
    return specs


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
    for spec in SpecModel().find({}):
        name = spec['content']['name']
        specs[name] = spec
        if name not in gitspecs:
            SpecModel().remove(spec)
            print("Spec %s removed from github, deleting" % name)

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
