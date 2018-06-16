from rest import spec, graph


def load(info):
    info['apiRoot'].spec = spec.Spec()
    info['apiRoot'].graph = graph.Graph()
    
    