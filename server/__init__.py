from rest import spec, graph
from utils import ingest

def load(info):
    info['apiRoot'].spec = spec.Spec()
    info['apiRoot'].graph = graph.Graph()
    
    ingest()

    
