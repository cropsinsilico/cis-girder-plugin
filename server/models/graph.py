#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Graph model definition."""

from girder.constants import AccessType
from girder.models.model_base import AccessControlledModel
import datetime


class Graph(AccessControlledModel):
    """Graph model."""

    def initialize(self):
        """Initialize the graph."""
        self.name = 'graph'

        self.exposeFields(level=AccessType.READ, fields={
            '_id', 'name', 'created', 'description', 'content',
            'creatorId', 'public'})

    def validate(self, graph):
        """Validate the graph."""
        return graph

    def list(self, user=None, limit=0, offset=0,
             sort=None, currentUser=None):
        """List a page of model graph for a given user.

        :param user: The user who owns the graph.
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

    def removeGraph(self, graph, token):
        """Remove the graph."""
        self.remove(graph)

    def createGraph(self, graph=None, creator=None, save=True):
        """Create a graph."""
        now = datetime.datetime.utcnow()

        obj = {
            'name': graph['name'],
            'content': graph['content'],
            'created': now,
            'creatorId': creator['_id']
        }

        if 'public' in graph and creator.get('admin'):
            self.setPublic(doc=obj, public=graph['public'])
        else:
            self.setPublic(doc=obj, public=False)  

        if creator is not None:
            self.setUserAccess(obj, user=creator, level=AccessType.ADMIN,
                               save=False)
        if save:
            obj = self.save(obj)

        return obj

    def updateGraph(self, graph):
        """Update a graph.

        :param graph: The graph document to update.
        :type graph: dict
        :returns: The graph document that was edited.
        """
        graph['updated'] = datetime.datetime.utcnow()

        return self.save(graph)
