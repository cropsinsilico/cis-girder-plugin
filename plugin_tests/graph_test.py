#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import six
import os
import yaml
import pyaml
from pprint import pprint
from tests import base
import girder
from girder.constants import ROOT_DIR


def setUpModule():
    base.enabledPlugins.append('cis')
    base.startServer()


def tearDownModule():
    base.stopServer()


class GraphTestCase(base.TestCase):

    def setUp(self):
        super(GraphTestCase, self).setUp()
        users = ({
            'email': 'root@dev.null',
            'login': 'admin',
            'firstName': 'Root',
            'lastName': 'van Klompf',
            'password': 'secret'
        }, {
            'email': 'joe@dev.null',
            'login': 'joeregular',
            'firstName': 'Joe',
            'lastName': 'Regular',
            'password': 'secret'
        })
        self.admin, self.user = [self.model('user').createUser(**user)
                                 for user in users]

        resp = self.request('/spec/ingest', user=self.admin, method='PUT')
                            

    def testGraph(self):
        fbp_graph_file = os.path.join(ROOT_DIR, 'plugins', 'cis', 
                                      'plugin_tests',
                                      'light_files_fbp.json')
        with open(fbp_graph_file, 'r') as fp:
            data = json.load(fp)
            
        graph = { 
                  "name": "test",
                  "content": data 
                }

        resp = self.request('/graph', user=self.user, method='POST',
                            type='application/json', body=json.dumps(graph))
        self.assertStatus(resp, 200)
        self.assertEquals(resp.json['name'], 'test')
        graphId = resp.json['_id']

        graph['name'] = 'renamed'
        resp = self.request('/graph/%s' % graphId,  user=self.user,
                            method='PUT', type='application/json',
                            body=json.dumps(graph))
        self.assertStatus(resp, 200)

        resp = self.request('/graph/%s' % graphId,  user=self.user,
                            method='GET')
        self.assertStatus(resp, 200)
        self.assertEquals(resp.json['name'], 'renamed')

        resp = self.request(path='/graph', method='GET', user=self.user)
        self.assertStatusOk(resp)
        self.assertEqual(len(resp.json), 1)

        resp = self.request('/graph/%s' % graphId, user=self.admin,
                            method='DELETE')
        self.assertStatus(resp, 200)

    def testConvert(self):
        fakeplant_yml = os.path.join(ROOT_DIR, 'plugins', 'cis', 
                                     'plugin_tests',
                                     'fakeplant.yaml')

        fakeplant_fbp = os.path.join(ROOT_DIR, 'plugins', 'cis', 
                                     'plugin_tests',
                                     'fakeplant_fbp.json')
        with open(fakeplant_fbp, 'r') as fp:
            data = json.load(fp)

        with open(fakeplant_yml, 'r') as fp:
            goldyml = yaml.load(fp)

        goldyml['connections'] = sorted(goldyml['connections'], key=lambda x: x['output'])
        goldyml['models'] = sorted(goldyml['models'], key=lambda x: x['name'])

        graph = { 
                  "name": "test",
                  "content": data 
                }

        resp = self.request('/graph/convert', user=self.user, method='POST',
                            isJson=False, type='application/json', body=json.dumps(graph))
        self.assertStatus(resp, 200)
        respyml = yaml.load(resp.body[0])
        respyml['connections'] = sorted(respyml['connections'], key=lambda x: x['output'])
        respyml['models'] = sorted(respyml['models'], key=lambda x: x['name'])

        self.assertEquals(goldyml, respyml)

    def tearDown(self):
        self.model('user').remove(self.user)
        self.model('user').remove(self.admin)
