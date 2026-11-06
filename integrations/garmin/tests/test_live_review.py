import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import replay
import review_live


class LiveEvidenceTests(unittest.TestCase):
    def scene(self):
        return json.loads((Path(__file__).resolve().parents[1]/'fixtures/contract/snapshot.json').read_text())['scene']

    def row(self,number,scene):
        return {'sample':number,'hostSeconds':number,'api':{'status':'decoded','apiRoundTripMs':5,'sourceBytes':1000,'scene':scene},'source':{'fixTimeMs':100000+1500*number,'fixAgeMs':100}}

    def test_no_samples_cannot_pass(self):
        self.assertEqual(review_live.analyze([])['status'],'fail')

    def test_distance_changes_do_not_change_fixed_geometry(self):
        a=self.scene();b=copy.deepcopy(a);b['seq']+=1;b['distanceM']=max(0,a['distanceM']-10)
        report=review_live.analyze([self.row(0,a),self.row(1,b)])
        self.assertEqual(report['status'],'pass');self.assertEqual(report['generationsWithDecreasingDistance'],1)
        self.assertEqual(report['fixIntervalMs']['median'],1500)

    def test_geometry_cannot_change_inside_a_generation(self):
        a=self.scene();b=copy.deepcopy(a);b['seq']+=1;b['roadName']='changed'
        report=review_live.analyze([self.row(0,a),self.row(1,b)])
        self.assertIn('geometry changed within a generation',report['failures'])

    def test_old_source_order_cannot_pass(self):
        a=self.scene();report=review_live.analyze([self.row(0,a),self.row(1,a)])
        self.assertIn('source order regressed',report['failures'])

    def test_actual_trace_preserves_distance_and_age_values(self):
        scene=self.scene();scene['distanceM']=417;scene['fixAgeMs']=321
        value={'provenance':{'kind':'actual_osmand_capture','captureSha256':'a'*64},'frames':[{'atMs':0,'scene':scene}]}
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory)/'trace.json';p.write_text(json.dumps(value));recorded,frames=replay.load_trace(p)
            self.assertEqual(frames[0]['scene'],scene)
            replay.generate(recorded,Path(directory)/'generated',Path('/watch'),1,'actual',trace_frames=frames)
            generated=json.loads((Path(directory)/'generated/frames.json').read_text())
            self.assertEqual(generated,frames)

    def test_trace_bounds_and_order_are_required(self):
        frame={'atMs':0,'scene':self.scene()}
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory)/'trace.json'
            for frames in [[],[frame]*65,[frame,frame],[dict(frame,atMs=-1)]]:
                p.write_text(json.dumps({'provenance':{'kind':'actual_osmand_capture','captureSha256':'a'*64},'frames':frames}))
                with self.assertRaises(ValueError):replay.load_trace(p)

    def test_trace_export_preserves_actual_values_and_rejects_undecoded_gaps(self):
        a=self.row(0,self.scene());a['api']['receivedElapsedMs']=1000
        b=copy.deepcopy(a);b['api']['receivedElapsedMs']=2500;b['api']['scene']['seq']+=1
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'samples.jsonl';out=Path(directory)/'out'
            path.write_text(json.dumps(a)+'\n'+json.dumps(b)+'\n')
            review_live.write_trace(path,out)
            _,frames=replay.load_trace(out/'actual-trace.json')
            self.assertEqual([f['atMs'] for f in frames],[0,1500]);self.assertEqual(frames[1]['scene'],b['api']['scene'])
            b['api']['status']='source_busy';path.write_text(json.dumps(b)+'\n')
            with self.assertRaisesRegex(ValueError,'unavailable'):review_live.write_trace(path,out)
            self.assertFalse((out/'actual-trace.json').exists())

    def test_review_numbers_survive_native_index_changes_and_missing_examples(self):
        # Synthetic coordinates test review bookkeeping only, never road geometry.
        scene=self.scene();index=scene['anchors'][0]['routeIndex']
        capture={'routeToken':'new','directions':[{'routePointOffset':index,'index':1,'turn':'TR'}],
                 'locationsLatLon':[[0,0]]*(index+1)}
        capture['locationsLatLon'][index]=[1,2]
        row=self.row(0,scene);row['source'].update(routeToken='new',nextRouteIndex=index)
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory);out=p/'review';out.mkdir()
            (out/'manifest.json').write_text(json.dumps({'examples':[
                {'example':2,'nativeIndex':index-1,'coordinates':[{'latitude':3,'longitude':4}]},
                {'example':7,'nativeIndex':index-1,'coordinates':[{'latitude':1,'longitude':2}]}]}))
            (p/'capture.json').write_text(json.dumps(capture))
            (p/'samples.jsonl').write_text(json.dumps(row)+'\n')
            review_live.build_review(p/'samples.jsonl',p/'capture.json',out)
            manifest=json.loads((out/'manifest.json').read_text())
            self.assertEqual([m['example'] for m in manifest['examples']],[7])
            self.assertTrue((out/'held-7.json').exists())


if __name__=='__main__':unittest.main()
