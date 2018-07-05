#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import six
from tests import base
import girder


def setUpModule():
    base.enabledPlugins.append('cis')
    base.startServer()


def tearDownModule():
    base.stopServer()


class SpecTestCase(base.TestCase):

    def setUp(self):
        super(SpecTestCase, self).setUp()
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

        model = ({
            'content': {
              'name': 'GrowthModelPy',
              'description': 'Growth Model (Python)',
              'args': 'example-fakeplant/src/growth.py',
              'driver': 'PythonModelDriver',
              'icon': 'pagelines',
              'inputs': [ 'photosynthesis_rate' ],
              'outputs': [ 'growth_rate' ]
            }
        })

        self.model_spec = self.model('spec', 'cis').createSpec(spec=model,
            creator=self.user)

    def testListing(self):
        user = self.user

        resp = self.request( path='/spec', method='GET', user=self.user )
        self.assertStatusOk(resp)
        self.assertEqual(len(resp.json), 1)

    def testCreatePublic(self):
        model = ({ 
            "content": {
               "args": "test/test/test.cpp",
               "description": "Test Model",
               "driver": "TestModelDriver",
               "icon": "test",
               "inports": [
                 {
                   "label": "test_in",
                   "name": "test_in",
                   "type": "all"
                 }
               ],
               "label": "TestModel",
               "name": "test",
               "outports": [
                 {
                   "label": "test_out",
                   "name": "test_out",
                   "type": "all"
                 }
               ]
             },
             "public": True
        })

        resp = self.request('/spec', user=self.user, method='POST',
                            type='application/json', body=json.dumps(model))
        self.assertStatus(resp, 403)

        resp = self.request('/spec', user=self.admin, method='POST',
                            type='application/json', body=json.dumps(model))
        self.assertStatus(resp, 200)
        self.assertTrue(resp.json['public'])

        model['public'] = False
        resp = self.request('/spec/%s' % resp.json["_id"],  user=self.admin,
                            method='PUT', type='application/json',
                            body=json.dumps(model))
        self.assertStatus(resp, 200)
        self.assertFalse(resp.json['public'])

        resp = self.request('/spec/%s' % resp.json["_id"],  user=self.admin, 
                            method='GET')
        self.assertStatus(resp, 200)
        self.assertEquals(resp.json['content']['name'], 'test')

        resp = self.request('/spec/%s' % resp.json["_id"], user=self.admin, 
                            method='DELETE')
        self.assertStatus(resp, 200)

        

        #test_spec = self.model('spec', 'cis').findOne({})


        #resp = self.request('/spec', user=self.admin, method='POST',
        #                             params=model})
        #self.assertStatusOk(resp)

    def testIngest(self):

        resp = self.request('/spec/ingest', user=self.user, method='PUT')
        self.assertStatus(resp, 403)

        resp = self.request('/spec/ingest', user=self.admin, method='PUT')
        self.assertStatus(resp, 200)

        resp = self.request( path='/spec', method='GET', user=self.user )
        self.assertStatusOk(resp)
        self.assertEqual(len(resp.json), 5)

    def testOauth(self):
        event = { 
                 "user": self.user,
                 "token" : "test" 
                }
        girder.events.trigger('oauth.auth_callback.after', event)

    def testConvert(self):
        model = ({ 
            "content": {
               "args": "test/test/test.cpp",
               "description": "Test Model",
               "driver": "TestModelDriver",
               "icon": "test",
               "inports": [
                 {
                   "label": "test_in",
                   "name": "test_in",
                   "type": "all"
                 }
               ],
               "label": "TestModel",
               "name": "test",
               "outports": [
                 {
                   "label": "test_out",
                   "name": "test_out",
                   "type": "all"
                 }
               ]
             }
        })

        resp = self.request('/spec/convert', user=self.user, method='POST',
                            isJson=False, type='application/json', body=json.dumps(model))
        self.assertStatus(resp, 200)
        self.assertEquals(resp.body, ["model:\n  args: test/test/test.cpp\n  driver: TestModelDriver\n  inputs:\n    - test_in\n  name: TestModel\n  outputs:\n    - test_out\n"])

#model:
#  args: test/test/test.cpp
#  driver: TestModelDriver
#  inputs:
#    - test_in
#  name: TestModel
#  outputs:
#    - test_out

    def tearDown(self):
        self.model('spec', 'cis').remove(self.model_spec)
        self.model('user').remove(self.user)
        self.model('user').remove(self.admin)
