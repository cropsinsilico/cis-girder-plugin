from rest import spec, graph
from utils import ingest
from girder import events
from girder.utility.model_importer import ModelImporter
from girder.plugins.oauth.providers.github import GitHub


def storeToken(event):
    user, token = event.info['user'], event.info['token']

    user['_oauthToken'] = token
    ModelImporter.model('user').save(user, validate=False)

def load(info):
    info['apiRoot'].spec = spec.Spec()
    info['apiRoot'].graph = graph.Graph()    
    ingest()
    GitHub.addScopes(['user:email', 'public_repo'])
    events.bind('oauth.auth_callback.after', 'cis', storeToken) 
