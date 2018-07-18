#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Spec object definition."""

from girder.constants import AccessType
from girder.models.model_base import AccessControlledModel
#from girder.utility import JsonEncoder
import json
import datetime
import requests
import yaml


# Example Spec object:
# {
#     "name": "inport",
#     "label": "InPort",
#     "description": "An input port for the graph",
#     "icon": "signin",
#     "driver": "GCCModelDriver",
#     "args": "unused",
#     "inports": [],
#     "outports": [
#         {"name": "value", "type": "all"}
#     ]
# }


class Spec(AccessControlledModel):
    """Defines the spec model."""

    def initialize(self):
        """Initialize the model."""
        self.name = 'spec'

        self.exposeFields(level=AccessType.READ, fields={
            '_id', 'name', 'created', 'content', 'description',
            'creatorId', 'issue_url', 'public'})

    def validate(self, spec):
        """Validate the model."""
        return spec

    def list(self, user=None, limit=0, offset=0,
             sort=None, currentUser=None):
        """List a page of model specs for a given user.

        :param user: The user who owns the model spec.
        :type user: dict or None
        :param limit: The page limit.
        :param offset: The page offset
        :param sort: The sort field.
        :param currentUser: User for access filtering.
        """
        cursor_def = {}
        if user is not None:
            cursor_def['creatorId'] = user['_id']

        cursor = self.find(cursor_def, sort=sort)
        for r in self.filterResultsByPermission(
                cursor=cursor, user=currentUser, level=AccessType.READ,
                limit=limit, offset=offset):
            yield r

    def removeSpec(self, spec, token):
        """Remove a spec."""
        self.remove(spec)

    def createSpec(self, spec=None, creator=None, save=True):
        """Create a spec."""
        now = datetime.datetime.utcnow()

        obj = {
            'content': spec['content'],
            'hash': spec.get('hash', ''),
            'created': now,
            'creatorId': creator['_id']
        }

        if 'public' in spec and creator.get('admin'):
            self.setPublic(doc=obj, public=spec['public'])
        else:
            self.setPublic(doc=obj, public=False)

        self.setUserAccess(obj, user=creator, level=AccessType.ADMIN, save=False)

        if save:
            obj = self.save(obj)

        return obj

    def updateSpec(self, spec):
        """Update a spec.

        :param spec: The spec document to update.
        :type spec: dict
        :returns: The spec document that was edited.
        """
        spec['updated'] = datetime.datetime.utcnow()
        return self.save(spec)


    def submitIssue(self, spec, yaml, user=None):
        """Submit issue to github cis-specs repo for this model."""
        #issuesUrl = 'https://api.github.com/repos/cropsinsilico/cis-specs/issues'
        issuesUrl = 'https://api.github.com/repos/craig-willis/cis-specs/issues'

        # Authorization: token OAUTH-TOKEN
	#"_oauthToken": {
	#	"access_token": "377e64390aca1d1e13334893db43159c495f2bda",
        authHeader = 'token %s' % user['_oauthToken']['access_token']
        print(authHeader)

        # Create our issue
        issue = {'title': 'New model request: %s' % spec['content']['name'],
                 'body': '```%s```' % yaml }
        print(json.dumps(issue))
        #json=json.dumps(issue, cls=JsonEncoder)
        r = requests.post(issuesUrl, json=issue, headers={'Authorization': authHeader})
        if r.status_code == requests.codes.created:
            body = r.json()
            print(body)
            spec['issue_url'] = body['url']
            return self.save(spec)
        else:
            r.raise_for_status()

