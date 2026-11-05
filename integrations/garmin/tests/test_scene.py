"""Drawing-scene bounds and diagnostic source conversion, without an SDK dependency."""
import copy
import importlib.util
import json
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from protocol.scene import validate
from replay_scene import compile_scene, simplify, clip_circle, add_map_context, non_motor_reason


def scene():
    return {'version':1,'session':'test','generation':1,'seq':1,'state':'active','geometryMode':'routing_branches',
            'reason':'partial roads','distanceM':100,'roadName':'Test','maneuver':'TR','radiusDm':2000,'sourceAgeMs':0,'fixAgeMs':0,
            'anchors':[{'id':'a','point':[0,0],'routeIndex':1}],
            'paths':[{'id':'route','role':'selected','points':[[0,-100],[0,0],[100,0]],'anchorRefs':[['a',1]]}]}


class SceneValidationTests(unittest.TestCase):
    def test_sdk_result_requires_a_complete_consistent_passing_summary(self):
        from replay import watch_test_result
        self.assertEqual(watch_test_result('Ran 1 tests\nPASSED (passed=1, failed=0, errors=0)\n',1),(True,1))
        for text,code in [('Ran 1 tests\nFAILED (passed=0, failed=1, errors=0)',1),
                          ('PASS',0),('Ran 2 tests\nPASSED (passed=1, failed=0, errors=0)',1),
                          ('Ran 1 tests\nPASSED (passed=1, failed=0, errors=0)',134)]:
            self.assertFalse(watch_test_result(text,code)[0])

    def test_all_recorded_scenes_validate(self):
        for path in (ROOT/'fixtures/recorded').glob('*.json'):
            recorded=json.loads(path.read_text())
            self.assertEqual(recorded['provenance']['kind'],'actual_osmand_capture')
            self.assertEqual(validate(recorded['scene']),[],path.name)

    def test_bad_version_and_noninteger_age(self):
        for key,value in [('version',2),('sourceAgeMs',float('inf')),('fixAgeMs',-1),('seq',1_000_001)]:
            value_scene=scene();value_scene[key]=value
            self.assertTrue(validate(value_scene),key)

    def test_progress_sample_requires_bounded_pair(self):
        value=scene();value['progressAgeMs']=250
        self.assertTrue(validate(value))
        value['speedDmps']=100
        self.assertEqual(validate(value),[])
        value['speedDmps']=701
        self.assertTrue(validate(value))

    def test_context_does_not_claim_anchor_connectivity(self):
        value=scene();value['geometryMode']='map_context'
        value['paths'].append({'id':'c','role':'context','points':[[0,-10],[0,10]],'anchorRefs':[]})
        self.assertEqual(validate(value),[])
        value['paths'][1]['anchorRefs']=[['a',0]]
        self.assertTrue(validate(value))

    def test_replay_distance_changes_each_second_with_fixed_geometry(self):
        from replay import frames
        value=scene();first=frames({'scene':value})[:6]
        self.assertEqual([f['atMs'] for f in first],list(range(0,6000,1000)))
        self.assertEqual([f['scene']['distanceM'] for f in first],[120,110,100,90,80,70])
        for frame in first:
            self.assertEqual(frame['scene']['paths'],value['paths'])
            self.assertEqual(frame['scene']['anchors'],value['anchors'])

    def test_radial_bounds_and_anchor_references(self):
        value=scene();value['paths'][0]['points'][0]=[1500,1500]
        self.assertTrue(validate(value))
        value=scene();value['paths'][0]['anchorRefs']=[['missing',1]]
        self.assertTrue(validate(value))
        value=scene();value['anchors'][0]['point']=[1,0]
        self.assertTrue(validate(value))

    def test_old_geometry_must_be_absent_during_reroute(self):
        value=scene();value['state']='recalculating'
        self.assertTrue(validate(value))
        value.update(geometryMode='unavailable',anchors=[],paths=[])
        self.assertEqual(validate(value),[])

    def test_capacity_cannot_silently_drop_branches(self):
        value=scene()
        value['paths'] += [{'id':str(i),'role':'branch','points':[[0,0],[10,i]],'anchorRefs':[['a',0]]} for i in range(8)]
        self.assertTrue(validate(value))

    def test_distinct_anchor_ids_are_not_merged_by_screen_position(self):
        value=scene();value['anchors'].append({'id':'b','point':[0,0],'routeIndex':2})
        value['paths'][0]['anchorRefs'].append(['b',1])
        self.assertEqual(validate(value),[])

    def test_recorded_close_turn_indexes_remain_separate(self):
        value=json.loads((ROOT/'fixtures/recorded/double-turn.json').read_text())['scene']
        self.assertEqual([a['routeIndex'] for a in value['anchors']],[75,82])
        self.assertEqual(len(value['paths'][0]['anchorRefs']),2)


class DiagnosticCompilerTests(unittest.TestCase):
    def test_non_motor_classes_are_omitted_unless_access_overrides(self):
        for kind in ('footway','cycleway','path','pedestrian','steps','bridleway'):
            self.assertIsNotNone(non_motor_reason({'highway':kind}),kind)
            self.assertIsNone(non_motor_reason({'highway':kind,'motor_vehicle':'yes'}),kind)
        self.assertIsNone(non_motor_reason({'highway':'cycleway','motor_vehicle':'no','motorcycle':'yes'}))

    def test_specific_access_and_motor_roads_are_preserved(self):
        for road in ({'highway':'track'},{'highway':'service','access':'private'},
                     {'highway':'residential','access':'destination'},
                     {'highway':'track','surface':'gravel','tracktype':'grade3'},
                     {'highway':'residential','access':'no','motorcycle':'yes'}):
            self.assertIsNone(non_motor_reason(road),road)
        for road in ({'highway':'residential','motor_vehicle':'no'},
                     {'highway':'cycleway','motor_vehicle':'yes','motorcycle':'no'},
                     {'highway':'service','access':'no'}):
            self.assertIsNotNone(non_motor_reason(road),road)

    def test_display_filter_keeps_selected_route_and_motor_road_arms(self):
        capture=self.capture();base=compile_scene(capture,0,'hash',75)
        points=[[1,1,0.,-.0003],[2,2,0.,0.],[3,3,0.,.0003]]
        result=add_map_context(base,capture,0,{'roads':[{'highway':'cycleway','points31LatLon':points},
                 {'highway':'service','points31LatLon':points}]})
        self.assertEqual(result['paths'][0],base['paths'][0])
        self.assertEqual(len(result['paths']),2)
        self.assertEqual(result['geometryMode'],'map_context')

    def capture(self, count=1):
        def point(i,lat,lon):return [i,100+i,200+i,lat,lon]
        branches=[{'roadId':str(30+n),'startPointIndex':0,'endPointIndex':1,'roadPointCount':2,
                   'points':[point(0,0.,0.),point(1,0.,.001)],'pointsTruncated':False} for n in range(count)]
        incoming={'id':'in','roadId':'10','startPointIndex':0,'endPointIndex':1,'roadPointCount':2,
                  'points':[point(0,-.001,0.),point(1,0.,0.)],
                  'attachments':[{'roadPointIndex':1,'attachedStorage':'available','attached':branches}]}
        outgoing={'id':'out','roadId':'20','startPointIndex':0,'endPointIndex':1,'roadPointCount':2,
                  'points':[point(0,0.,0.),point(1,.001,0.)],
                  'attachments':[{'roadPointIndex':0,'attachedStorage':'available','attached':[]}]}
        return {'probeVersion':1,'status':'captured','coherent':True,'locationCount':3,
                'locationsLatLon':[[-.001,0.],[0.,0.],[.001,0.]],'locationSegmentIds':['in','out','out'],
                'segments':[incoming,outgoing],'directions':[{'routePointOffset':1,'turn':'C','streetName':'Test'}]}

    def test_branch_on_incoming_segment_is_retained(self):
        value=compile_scene(self.capture(),0,'hash')
        self.assertEqual(value['geometryMode'],'routing_branches')
        self.assertEqual(len(value['paths']),2)
        self.assertGreater(value['paths'][1]['points'][1][0],0) # east is rider-right on a northbound approach
        self.assertEqual(value['paths'][1]['points'][0],value['anchors'][0]['point'])

    def test_different_road_ids_with_same_bearing_are_not_merged(self):
        value=compile_scene(self.capture(2),0,'hash')
        self.assertEqual(len(value['paths']),3)

    def test_overflow_returns_route_only(self):
        value=compile_scene(self.capture(9),0,'hash')
        self.assertEqual(value['geometryMode'],'route_only')
        self.assertEqual(len(value['paths']),1)
        self.assertIn('capacity',value['reason'])

    def test_missing_attachments_are_explicit(self):
        value=self.capture();value['segments'][0]['attachments'][0]['attachedStorage']='unavailable'
        result=compile_scene(value,0,'hash')
        self.assertEqual(result['geometryMode'],'route_only')
        self.assertIn('unavailable',result['reason'])

    def test_simplifier_keeps_decision_even_if_nearly_collinear(self):
        result,indexes=simplify([(0.,0.),(1.,.01),(2.,0.),(3.,0.)],{1})
        self.assertIn(1,indexes)
        self.assertIn((1.,.01),result)

    def test_circle_clip_keeps_crossing_with_both_vertices_outside(self):
        result=clip_circle([(-20,0),(20,0)],10)
        self.assertEqual(result,[[(-10.,0.),(10.,0.)]])
        self.assertEqual(clip_circle([(-20,11),(20,11)],10),[])

    def test_circle_clip_does_not_connect_across_outside_arc(self):
        result=clip_circle([(0,0),(20,0),(20,20),(0,0)],10)
        self.assertEqual(len(result),2)

    def test_context_keeps_unfiltered_road_and_shared_shape_vertex(self):
        capture=self.capture();base=compile_scene(capture,0,'hash',75)
        roads=[{'points31LatLon':[[1,1,0.,-.0003],[2,2,.000001,0.],[3,3,0.,.0003]],'oneway':-1},
               {'points31LatLon':[[2,2,.000001,0.],[4,4,.0003,0.]],'oneway':1}]
        result=add_map_context(base,capture,0,{'roads':roads})
        self.assertEqual(result['geometryMode'],'map_context')
        self.assertEqual(len(result['paths']),3)
        self.assertEqual(len(result['paths'][1]['points']),3)
        self.assertEqual(result['paths'][1]['anchorRefs'],[])
        roads[0]['bridge']='yes'
        limited=add_map_context(base,capture,0,{'roads':roads})
        self.assertEqual(limited['geometryMode'],'route_only')
        self.assertIn('grade-separated',limited['reason'])
