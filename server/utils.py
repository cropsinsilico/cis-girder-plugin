# -*- coding: utf-8 -*
"""Plugin utilities."""
from git import Repo
import os
import yaml
import urllib
import shutil
from models.spec import Spec as SpecModel
from girder.plugins.jobs.models.job import Job as JobModel

import datetime
import sys

from kubernetes_executor import KubernetesJob

def jupyterUserEncode(username):
    return urllib.quote_plus(username).replace('.', '%2e').replace('-', '%2d').replace('%', '-')
    
def execGraph(yaml_graph, username):
    # Write YAML graph to a file
    #yaml_path = "graph.yaml";f = open(yaml_path,"w");f.write(yaml_graph);f.close()
    
    # TODO: How do we cache/lookup this execution again later? Hash the command?
    
    # Give our job a unique name
    job_name = username + "-" + str(datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
    job_type = 'k8s.io/cis_interface'
    
    # Specify the Docker image and command(s) to run
    docker_image = "bodom0015/cis_interface:0.6.1"
    init_command = "mkdir -p /pvc/" + job_name + " && ls -al && cp -R /pvc/models/* /pvc/" + job_name
    command = "echo '" + str(yaml_graph) + "' > graph.yml && echo Running in $(pwd): && ls -al && cisrun graph.yml"
    
    # Encode our username with Jupyter's special homebrew recipe
    username = jupyterUserEncode(username)
    
    # Job must run in same namespace as the PVC
    namespace = "hub"
    
    # Specify some arbitrary limits
    timeout = 120
    num_cpus = 1
    max_ram_mb = 512
        
    # Create a record in the Job database
    jobModel = JobModel()
    job_model = jobModel.createJob(job_name, job_type, async=True, kwargs={
        'name': job_name,
        'type': job_type,
        'namespace': namespace,
        'username': username,
        'init_command': init_command,
        'command': command,
        'image': docker_image,
        'timeout': timeout,
        'num_cpus': num_cpus,
        'max_ram_mb': max_ram_mb,
    })
    
    jobModel.save(job_model)
    
    # Create and run the job
    k8s_job = KubernetesJob(username, job_name, namespace, timeout, init_command, command, docker_image, num_cpus, max_ram_mb)
    if not k8s_job.is_running():
        jobModel.scheduleJob(job_model)
        k8s_job.submit()
    
    return job_name
    
def getLogs(job_name, job_type, username): 
    # Create and run the job
    timeout = 120
    num_cpus = 1
    max_ram_mb = 512
    job = KubernetesJob(username, job_name, "hub", timeout, None, None, None, num_cpus, max_ram_mb)
    #if not job.is_running():
        #return 'Job is not running'
    #elif not job.is_done():
        #return 'Job is still running'
    #elif job.is_failed():
        #return 'Job is failed'
    #else:
        #return job.get_error_message() 
    return job.get_error_message()

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

def get_label_or_name(metadata):
    return metadata.get('label', metadata.get('name', None))
    
def get_process_by_name(processes, name):
    ret = None
    for key,process in processes.items():
        if process['metadata']['name'] == name:
            ret = process
            break
    return ret

def fbpToCis(data):
    """ Given a flow-based-protocol graph, return in CIS format."""
    inports = {}
    outports = {}
    models = {}
    for key,process in data['processes'].items():
        component =  process['component']
        if component == 'inport' or component == 'outport':
            port = {}
            port['name'] = get_label_or_name(process['metadata'])
            port['type'] = process['metadata']['type']
            if component == 'inport':
               port['method']  = process['metadata']['read_meth']
               inports[key] = port
            else:
               port['method']  = process['metadata']['write_meth']
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
           in_port = get_process_by_name(data['processes'], srckey)
           conn['input'] = get_label_or_name(in_port['metadata'])
           conn['filetype'] = inports[srckey]['method']
           conn['output'] = connection['tgt']['port']
        elif tgtkey in outports:
           conn['input'] = connection['src']['port']
           conn['filetype'] = outports[tgtkey]['method']
           out_port = get_process_by_name(data['processes'], tgtkey)
           conn['output'] = get_label_or_name(in_port['metadata'])
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
