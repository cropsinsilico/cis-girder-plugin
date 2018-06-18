from girder.api.rest import Resource
from girder.api import access
from girder.api.docs import addModel
from girder.api.rest import Resource, filtermodel, RestException
from girder.api.describe import Description, autoDescribeRoute
from girder.constants import SortDir, AccessType
from ..models.spec import Spec as SpecModel


specDef = {
    "description": "Object representing a Crops in Silico model specification.",
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
            "description": ("Model specification"),
        },
        "description": {
            "type": "string"
        },
        "official": {
            "type": "boolean",
            "default": False,
            "description": "If set to true the spec is an official spec"
        },
        "created": {
            "type": "string",
            "format": "date-time",
            "description": "The time when the spec was created."
        },
        "creatorId": {
            "type": "string",
            "description": "A unique identifier of the user that created the spec."
        },
        "updated": {
            "type": "string",
            "format": "date-time",
            "description": "The last time when the spec was modified."
        }
    },
    'example': {
        '_accessLevel': 2,
        '_id': '5873dcdbaec030000144d233',
        '_modelType': 'spec',
        'name': 'canopy',
        'description': 'Canopy model for fake plant',
        'creatorId': '18312dcdbaec030000144d233',
        'created': '2017-01-09T18:56:27.262000+00:00',
        'official': True,
        'updated': '2017-01-10T16:15:17.313000+00:00'
    },
}
addModel('spec', specDef, resources='spec')

class Spec(Resource):
    def __init__(self):
        super(Spec, self).__init__()
        self.resourceName = 'spec'
        self._model = SpecModel()
        self.route('GET', (), self.listSpecs)
        self.route('GET', (':id',), self.getSpec)
        self.route('POST', (), self.createSpec)
        self.route('PUT', (':id',), self.updateSpec)
        self.route('DELETE', (':id',), self.deleteSpec)
        
    @access.public
    @filtermodel(model='spec', plugin='cis')
    @autoDescribeRoute(
        Description('Return all the specs accessible to the user')
        .param('userId', "The ID of the specs's creator.", required=False)
        .param('text', ('Perform a full text search for specs with matching '
                        'name or description.'), required=False)
        .pagingParams(defaultSort='lowerName',
                      defaultSortDir=SortDir.DESCENDING)
    )
    def listSpecs(self, userId, text, limit, offset, sort, params):
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
        Description('Create a new spec.')
        .jsonParam('spec', 'Name and attributes of the spec.', paramType='body')
        .responseClass('spec')
        .errorResponse('You are not authorized to create specs.', 403)
    )
    def createSpec(self, spec):
        user = self.getCurrentUser()

        return self.model('spec', 'cis').createSpec(spec, creator=user, 
            save=True)


    @access.public
    @filtermodel(model='spec', plugin='cis')
    @autoDescribeRoute(
        Description('Get a spec by ID.')
        .modelParam('id', model='spec', plugin='cis', force=True)
        .responseClass('spec')
        .errorResponse('ID was invalid.')
        .errorResponse('Read access was denied for the model', 403)
    )
    def getSpec(self, spec):
        return spec 
        
    @access.user
    @autoDescribeRoute(
        Description('Delete an existing spec.')
        .modelParam('id', 'The ID of the spec.',  model='spec', plugin='cis', level=AccessType.ADMIN)
        .errorResponse('ID was invalid.')
        .errorResponse('Delete access was denied for the spec.', 403)
    )
    def deleteSpec(self, spec):
        self.model('spec', 'cis').remove(spec)
        
    @access.user
    @autoDescribeRoute(
        Description('Update an existing spec.')
        .modelParam('id', model='spec', plugin='cis',
                    level=AccessType.WRITE, destName='specObj')
        .jsonParam('spec', 'Updated spec', paramType='body')
        .responseClass('spec')
        .errorResponse('ID was invalid.')
        .errorResponse('Access was denied for the spec.', 403)
    )
    def updateSpec(self, specObj, spec, params):
        return self.model('graph', 'cis').updateGraph(spec)        

        