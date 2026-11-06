import json
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from protocol.envelope import validate_request,validate_reply


class EnvelopeTests(unittest.TestCase):
    def request(self):return {'version':1,'kind':'junction_request','epoch':'test','requestId':1}
    def test_valid_request_reply_and_unavailable(self):
        request=self.request();self.assertEqual(validate_request(request),[])
        scene=json.loads((ROOT/'fixtures/recorded/fork.json').read_text())['scene']
        self.assertEqual(validate_reply(dict(request,kind='junction_snapshot',scene=scene)),[])
        self.assertEqual(validate_reply(dict(request,kind='junction_unavailable',reason='source_busy')),[])
    def test_numbers_and_ack_are_strict(self):
        for key,value in [('version',True),('requestId',1.0),('epoch',''),('requestId',0)]:
            request=self.request();request[key]=value;self.assertTrue(validate_request(request))
        request=dict(self.request(),displayedSeq=1);self.assertTrue(validate_request(request))
        request.update(displayedGeneration=1,displayedSession='source',displayedState='active')
        self.assertEqual(validate_request(request),[])
    def test_unavailable_does_not_carry_old_geometry(self):
        self.assertTrue(validate_reply(dict(self.request(),kind='junction_unavailable',reason='error',scene={})))
        self.assertTrue(validate_reply(dict(self.request(),kind='junction_snapshot',scene={})))
    def test_machine_readable_schema_and_named_examples_exist(self):
        for name in ('scene','envelope'):
            value=json.loads((ROOT/'protocol'/f'{name}.schema.json').read_text())
            self.assertIn('properties',value);self.assertIn('$schema',value)
        examples=sorted((ROOT/'fixtures/contract').glob('*.json'))
        self.assertEqual(len(examples),3)
        for path in examples:
            value=json.loads(path.read_text())
            self.assertEqual(validate_request(value) if value['kind']=='junction_request' else validate_reply(value),[],path.name)
    def test_malformed_container_types_are_rejected(self):
        self.assertTrue(validate_request(dict(self.request(),kind=[])))
        value=json.loads((ROOT/'fixtures/recorded/fork.json').read_text())['scene'];value['state']={}
        self.assertTrue(validate_reply(dict(self.request(),kind='junction_snapshot',scene=value)))
        value.update(geometryMode='route_only',state='active',paths=[None])
        self.assertTrue(validate_reply(dict(self.request(),kind='junction_snapshot',scene=value)))


if __name__=='__main__':unittest.main()
