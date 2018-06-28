#!/usr/bin/env python
# -*- coding: utf-8 -*-


from girder.constants import AccessType
from girder.models.model_base import AccessControlledModel
from girder.models.user import User
import datetime


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

    def initialize(self):
        self.name = 'spec'
        
        self.exposeFields(level=AccessType.READ, fields={
            '_id', 'name', 'created', 'content', 'description', 'creatorId'})

        
    def validate(self, spec):
        return spec


    def list(self, user=None, limit=0, offset=0,
             sort=None, currentUser=None):
        """
        List a page of model specs for a given user.

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
        self.remove(spec)

    def createSpec(self, spec=None, creator=None, save=True):
        now = datetime.datetime.utcnow()
        
        obj = {
            'name': spec['name'],
        #    'description': spec['description'],
        #    'icon': spec['icon'],
            'content': spec['content'],
            'created': now,
            'creatorId': creator['_id']
        }

        if creator is not None:
            self.setUserAccess(obj, user=creator, level=AccessType.ADMIN,
                               save=False)

        if save:
            obj = self.save(obj)

        return obj
   
    def updateSpec(self, spec):
        """
        Updates a spec.
        :param spec: The spec document to update.
        :type spec: dict
        :returns: The spec document that was edited.
        """
        spec['updated'] = datetime.datetime.utcnow()
        return self.save(spec)        
        
