import copy
import json
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from protocol.compact import encode,decode
from protocol.scene import validate

class CompactTests(unittest.TestCase):
    def fixtures(self):return json.loads((Path(__file__).resolve().parents[1]/'fixtures/wire/compact.json').read_text())
    def test_golden_round_trip_all_scene_values(self):
        for f in self.fixtures():
            wire=bytes.fromhex(f['hex']);self.assertEqual(encode(f['reply']),wire);self.assertEqual(decode(wire),f['reply'])
            self.assertEqual(validate(decode(wire)['scene']),[])
    def test_every_truncated_prefix_and_extra_bytes_rejected(self):
        for f in self.fixtures():
            wire=bytes.fromhex(f['hex'])
            for i in range(len(wire)):
                with self.assertRaises(ValueError):decode(wire[:i])
            with self.assertRaises(ValueError):decode(wire+b'\0')
    def test_unknown_version_and_noncanonical_varints_rejected(self):
        wire=bytearray.fromhex(self.fixtures()[0]['hex']);wire[2]=99
        with self.assertRaises(ValueError):decode(wire)
        with self.assertRaises(ValueError):decode(b'\xca\0'+wire[1:])
    def test_negative_reply_preserves_reason_and_request_identity(self):
        r={'version':1,'kind':'junction_unavailable','epoch':'epoch','requestId':52,'reason':'source_disconnected'}
        self.assertEqual(decode(encode(r)),r)

    def test_version_one_remains_readable(self):
        reply=self.fixtures()[0]['reply'];self.assertEqual(decode(encode(reply,version=1)),reply)

    def test_arrival_has_no_guidance_and_is_preserved(self):
        reply=copy.deepcopy(self.fixtures()[0]['reply']);s=reply['scene']
        s.update(state='arrived',geometryMode='unavailable',distanceM=0,anchors=[],paths=[],fixAgeMs=60000)
        self.assertEqual(validate(s),[]);self.assertEqual(decode(encode(reply)),reply)
        s['distanceM']=1;self.assertTrue(validate(s))

    def test_destination_must_match_actual_selected_endpoint(self):
        s=copy.deepcopy(self.fixtures()[0]['reply']['scene']);p=next(p for p in s['paths'] if p['role']=='selected')
        s['destination']=p['points'][-1].copy();self.assertEqual(validate(s),[])
        s['destination'][0]+=1;self.assertTrue(validate(s))
