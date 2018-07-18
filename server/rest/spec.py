# -*- coding: utf-8 -*
"""Defines the spec API."""
from girder.api import access
from girder.api.docs import addModel
from girder.api.rest import Resource, filtermodel, RestException
from girder.api.describe import Description, autoDescribeRoute
from girder.constants import SortDir, AccessType
from ..models.spec import Spec as SpecModel
from ..utils import ingest, fbpToCis
import pyaml
import yaml
from cis_interface.yamlfile import prep_yaml
from cis_interface.schema import get_schema
import os
import tempfile
import cherrypy

specDef = {
    "description": "Object representing a CiS model specification.",
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
        "public": {
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
            "description": "A unique identifier of user who created the spec."
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
    """Defines spec API."""

    def __init__(self):
        """Initialize spec API."""
        super(Spec, self).__init__()
        self.resourceName = 'spec'
        self._model = SpecModel()
        self.route('GET', (), self.listSpecs)
        self.route('GET', (':id',), self.getSpec)
        self.route('POST', (), self.createSpec)
        self.route('PUT', (':id',), self.updateSpec)
        self.route('DELETE', (':id',), self.deleteSpec)
        self.route('PUT', ('ingest',), self.ingestSpecs)
        self.route('POST', ('convert',), self.convertSpec)
        self.route('PUT', ('ingest',), self.ingestSpecs)
        self.route('POST', (':id', 'issue',), self.submitIssue)

    @access.admin
    @autoDescribeRoute(
        Description('Refresh specs from github')
        .errorResponse('Not authorized to ingest specs.', 403)
    )
    def ingestSpecs(self):
        """Ingest specs."""
        ingest()

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
        """List specs."""
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
        .jsonParam('spec', 'Name and attributes of the spec.',
                   paramType='body')
        .responseClass('spec')
        .errorResponse('Not authorized to create specs.', 403)
    )
    def createSpec(self, spec):
        """Create spec."""
        user = self.getCurrentUser()

        if 'public' in spec and spec['public'] and not user['admin']:
            raise RestException('Not authorized to create public specs', 403)

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
        """Get spec."""
        return spec

    @access.user
    @autoDescribeRoute(
        Description('Delete an existing spec.')
        .modelParam('id', 'The ID of the spec.',  model='spec', plugin='cis',
                    level=AccessType.ADMIN)
        .errorResponse('ID was invalid.')
        .errorResponse('Delete access was denied for the spec.', 403)
    )
    def deleteSpec(self, spec):
        """Delete spec."""
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
        """Update spec."""
        user = self.getCurrentUser()

        specObj['content'] = spec['content']

        if 'public' in spec and spec['public'] and not user['admin']:
            raise RestException('Not authorized to create public specs', 403)
        elif 'public' in spec:
            specObj['public'] = spec['public']

        return self.model('spec', 'cis').updateSpec(specObj)

    @access.user
    @autoDescribeRoute(
        Description('Convert a spec from FBP to cisrun format.')
        .jsonParam('spec', 'Name and attributes of the spec.',
                   paramType='body')
        .errorResponse()
        .errorResponse('Not authorized to convert specs.', 403)
    )
    def convertSpec(self, spec):
        """Convert spec."""
        cisspec = fbpToCis(spec['content'])

        # Write to temp file and validate
        tmpfile = tempfile.NamedTemporaryFile(suffix="yml", prefix="cis",
                                              delete=False)
        yaml.safe_dump(cisspec, tmpfile, default_flow_style=False)
        yml_prep = prep_yaml(tmpfile)
        os.remove(tmpfile.name)

        v = get_schema().validator
        yml_norm = v.normalized(yml_prep)
        if not v.validate(yml_norm):
            print(v.errors)
            raise RestException('Invalid model %s', 400, v.errors)

        self.setRawResponse()
        return pyaml.dump(cisspec)

    @access.user
    @autoDescribeRoute(
        Description('Submit this model to the official catalog')
        .modelParam('id', model='spec', plugin='cis', level=AccessType.WRITE)
        .responseClass('spec')
        .errorResponse('ID was invalid.')
        .errorResponse('Issue already exists', 303)
        .errorResponse('Not authorized to submit specs.', 403)
    )
    def submitIssue(self, spec):
        user = self.getCurrentUser()

        if  'issue_url' in spec:
            cherrypy.response.status = 303
            raise cherrypy.HTTPRedirect(spec['issue_url'])
	    
        cisspec = fbpToCis(spec['content'])

        specyaml = yaml.safe_dump(cisspec, default_flow_style=False)

        """Submit github issue (and eventually PR)."""
        return self.model('spec', 'cis').submitIssue(spec, specyaml, user)

