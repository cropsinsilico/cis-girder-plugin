from girder.api.rest import Resource
from girder.api import access
from girder.api.docs import addModel
from girder.api.rest import Resource, filtermodel, RestException
from girder.api.describe import Description, autoDescribeRoute
from girder.constants import SortDir, AccessType
from ..models.graph import Graph as GraphModel

graphDef = {
    "description": "Object representing a Crops in Silico model graph.",
    "required": [
        "_id",
        "name",
        "content"
    ],
    "properties": {
        "_id": {
            "type": "string",
            "description": "internal unique identifier"
        },
        "name": {
            "type": "string",
            "description": "A user-friendly name"
        },
        "content": {
            "type": "string",
            "description": ("Graph specification"),
        },
        "description": {
            "type": "string"
        },
        "official": {
            "type": "boolean",
            "default": False,
            "description": "If set to true the spec is an official graph"
        },
        "created": {
            "type": "string",
            "format": "date-time",
            "description": "The time when the graph was created."
        },
        "creatorId": {
            "type": "string",
            "description": "A unique identifier of the user that created the graph."
        },
        "updated": {
            "type": "string",
            "format": "date-time",
            "description": "The last time when the graph was modified."
        }
    },
    'example': {
        '_accessLevel': 2,
        '_id': '5873dcdbaec030000144d233',
        '_modelType': 'graph',
        'name': 'Fake Plant',
        'description': 'Example fake plant model graph',
        'creatorId': '18312dcdbaec030000144d233',
        'created': '2017-01-09T18:56:27.262000+00:00',
        'official': True,
        'updated': '2017-01-10T16:15:17.313000+00:00'
    },
}
addModel('graph', graphDef, resources='graph')

class Graph(Resource):
    def __init__(self):
        super(Graph, self).__init__()
        self.resourceName = 'graph'
        self._model = GraphModel()
        self.route('GET', (), self.listGraphs)
        self.route('GET', (':id',), self.getGraph)
        self.route('POST', (), self.createGraph)
        self.route('PUT', (':id',), self.updateGraph)
        self.route('DELETE', (':id',), self.deleteGraph)
        
    @access.public
    @filtermodel(model='graph', plugin='cis')
    @autoDescribeRoute(
        Description('Return all the graphs accessible to the user')
        .param('userId', "The ID of the graph's creator.", required=False)
        .param('text', ('Perform a full text search for graphs with matching '
                        'name or description.'), required=False)
        .pagingParams(defaultSort='lowerName',
                      defaultSortDir=SortDir.DESCENDING)
    )
    def listGraphs(self, userId, text, limit, offset, sort, params):
        currentUser = self.getCurrentUser()
        if userId:
            user = self.model('user').load(userId, force=True, exc=True)
        else:
            user = None
            
        return list(self._model.list(
                user=user, currentUser=currentUser,
                offset=offset, limit=limit, sort=sort))
                
               

    @access.user
    @autoDescribeRoute(
        Description('Create a new graph.')
        .jsonParam('graph', 'Name and attributes of the graph.', paramType='body')
        .responseClass('graph')
        .errorResponse('You are not authorized to create graphs.', 403)
    )
    def createGraph(self, graph):
        user = self.getCurrentUser()

        return self.model('graph', 'cis').createGraph(graph, creator=user, 
            save=True)


    @access.public
    @filtermodel(model='graph', plugin='cis')
    @autoDescribeRoute(
        Description('Get a graph by ID.')
        .modelParam('id', model='graph', plugin='cis', force=True)
        .responseClass('graph')
        .errorResponse('ID was invalid.')
        .errorResponse('Read access was denied for the graph', 403)
    )
    def getGraph(self, graph):
        return graph 
        
    @access.user
    @autoDescribeRoute(
        Description('Delete an existing graph.')
        .modelParam('id', 'The ID of the graph.',  model='graph', plugin='cis', level=AccessType.ADMIN)
        .errorResponse('ID was invalid.')
        .errorResponse('Delete access was denied for the graph.', 403)
    )
    def deleteGraph(self, graph):
        self.model('graph', 'cis').remove(graph)
        
    @access.user
    @autoDescribeRoute(
        Description('Update an existing graph.')
        .modelParam('id', model='graph', plugin='cis',
                    level=AccessType.WRITE, destName='graphObj')
        .jsonParam('graph', 'Updated graph', paramType='body')
        .responseClass('graph')
        .errorResponse('ID was invalid.')
        .errorResponse('Access was denied for the graph.', 403)
    )
    def updateGraph(self, graphObj, graph, params):
        return self.model('graph', 'cis').updateGraph(graph)