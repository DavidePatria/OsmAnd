import copy
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from protocol.scene import validate
from preview import road_strokes


class LayerStyleTests(unittest.TestCase):
    def scene(self):
        scene=json.loads((Path(__file__).resolve().parents[1]/'fixtures/contract/snapshot.json').read_text())['scene']
        scene['geometryMode']='layer_context'
        for p in scene['paths']:
            p['layer']=1 if p['role']!='selected' else 0
            if p['role']=='selected':p['segmentLayers']=[0]*(len(p['points'])-1)
        return scene

    def test_levels_are_required_and_cannot_hide_in_ordinary_mode(self):
        s=self.scene();self.assertEqual(validate(s),[])
        s['geometryMode']='map_context';self.assertTrue(validate(s))
        s=self.scene();s['paths'][0]['segmentLayers']=[];self.assertTrue(validate(s))
        s=self.scene();s['paths'][0]['layer']=True;self.assertTrue(validate(s))

    def test_context_overpass_draws_after_yellow_route_and_keeps_all_roads(self):
        s=self.scene();strokes=list(road_strokes(s));yellow=max(i for i,x in enumerate(strokes) if x[1]=='#ffd166')
        gray=max(i for i,x in enumerate(strokes) if x[1]=='#8193a6')
        self.assertGreater(gray,yellow);self.assertTrue(any(c=='black' and w==10 for _,c,w in strokes))
        for p in s['paths']:
            if p['role']!='selected':self.assertIn((p['points'],'#8193a6',4),strokes)

    def test_yellow_bridge_draws_above_lower_context(self):
        s=self.scene()
        for p in s['paths']:
            p['layer']=0
            if p['role']=='selected':p['layer']=1;p['segmentLayers']=[1]*(len(p['points'])-1)
        strokes=list(road_strokes(s));self.assertEqual(strokes[-1][1],'#ffd166')

    def test_layered_path_budget_is_40_with_shorter_ids(self):
        s=self.scene();selected=next(p for p in s['paths'] if p['role']=='selected')
        s['paths']=[selected]+[{'id':'c'+str(i),'role':'context','points':[[0,i],[10,i]],'anchorRefs':[],'layer':1} for i in range(39)]
        self.assertEqual(validate(s),[])
        s['paths'].append({'id':'last','role':'context','points':[[0,40],[10,40]],'anchorRefs':[],'layer':1})
        self.assertTrue(validate(s));s['paths'].pop();s['paths'][1]['id']='x'*25;self.assertTrue(validate(s))


if __name__=='__main__':unittest.main()
