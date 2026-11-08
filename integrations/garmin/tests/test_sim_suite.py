import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import sim_suite as suite


class FixedSuiteTests(unittest.TestCase):
    def points(self):
        return [{'id': 'A', 'lat': 1, 'lon': 2}, {'id': 'B', 'lat': 3, 'lon': 4},
                {'id': 'C', 'lat': 5, 'lon': 6}]

    def test_ordered_pairs_include_each_reverse_and_no_self_routes(self):
        s = suite.make_suite(self.points())
        self.assertEqual([(r['from'], r['to']) for r in s['scenarios']],
                         [('A', 'B'), ('A', 'C'), ('B', 'A'), ('B', 'C'), ('C', 'A'), ('C', 'B')])
        self.assertEqual([r['id'] for r in s['scenarios']], ['R001', 'R002', 'R003', 'R004', 'R005', 'R006'])
        self.assertEqual(suite.digest(s), suite.digest(suite.make_suite(self.points())))

    def test_five_points_produce_twenty_routes(self):
        points = [{'id': f'P{i}', 'lat': i, 'lon': i} for i in range(5)]
        self.assertEqual(len(suite.make_suite(points)['scenarios']), 20)

    def test_short_suite_is_explicit_pairs_not_all_combinations(self):
        routes=[{'id':'Q001','from':'A','to':'B','parent':'R007','focus':True}]
        s=suite.make_short_suite(self.points(),routes,{'windowM':600})
        self.assertEqual(s['scenarios'],routes)
        self.assertEqual(s['kind'],'short_native_routes')
        with self.assertRaisesRegex(ValueError,'scenario ID'):
            suite.make_short_suite(self.points(),[dict(routes[0],id='../unsafe')],{})
        with self.assertRaisesRegex(ValueError,'endpoints'):
            suite.make_short_suite(self.points(),[dict(routes[0],to='A')],{})

    def test_routine_policy_has_short_caps_and_never_repeats(self):
        self.assertEqual(suite.run_policy()['seconds'],1800)
        self.assertFalse(suite.run_policy()['repeat'])
        self.assertEqual(suite.run_policy('smoke')['seconds'],300)
        self.assertEqual(suite.run_policy('smoke')['maxRoutes'],1)
        with self.assertRaisesRegex(ValueError,'explicit'):suite.run_policy('endurance')
        with self.assertRaisesRegex(ValueError,'only applies'):suite.run_policy('regression',4)
        self.assertTrue(suite.run_policy('endurance',4)['repeat'])

    def test_smoke_prioritizes_saved_failure_focus_and_excludes_other_routes(self):
        s={'scenarios':[{'id':'Q001','focus':False},{'id':'Q002','focus':True}]}
        chosen=suite.profile_scenarios(s,{'active':['Q001','Q002']},suite.run_policy('smoke'))
        self.assertEqual([r['id'] for r in chosen],['Q002'])

    def test_duplicate_ids_coordinates_invalid_numbers_and_unsafe_ids_rejected(self):
        for change in ({'id': 'A'}, {'lat': 1, 'lon': 2}, {'lat': float('nan')},
                       {'lat': True}, {'lat': 81}, {'lon': 181}, {'id': '../bad'}):
            points = self.points(); points[1].update(change)
            with self.subTest(change=change), self.assertRaises(ValueError): suite.make_suite(points)

    def test_mutated_fixed_schedule_cannot_load(self):
        s = suite.make_suite(self.points()); s['scenarios'].reverse()
        with tempfile.TemporaryDirectory() as tmp, patch.object(suite, 'private_path', side_effect=lambda p: p):
            p = Path(tmp)/'suite.json'; p.write_text(json.dumps(s))
            with self.assertRaisesRegex(ValueError, 'fixed'): suite.load_suite(p)

    def test_coordinates_cannot_be_written_into_tracked_paths(self):
        with self.assertRaisesRegex(ValueError, 'ignored'): suite.private_path(Path('tasks/private-suite.json'))

    def test_other_target_forward_is_never_rebound(self):
        class Client:
            adb = ['adb', '-s', 'waydroid:5555']
            def command(self, *args):
                self.calls.append(args)
                return 'phone tcp:7381 tcp:7381\n'
        c = Client(); c.calls = []
        with self.assertRaisesRegex(RuntimeError, 'another'): suite.forward(c)
        self.assertEqual(c.calls, [('forward', '--list')])

    def test_estimates_distinguish_native_travel_and_fixed_simulation(self):
        s = suite.make_suite(self.points())
        plan = {'routes': {'R001': {'status': 'planned', 'distanceM': 12000,
                'nativeTimeSeconds': 600, 'simulationSeconds': 1200, 'maneuvers': 4, 'planningSeconds': 2}}}
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)/'routes.md'; suite.write_route_report(s, plan, p); text = p.read_text()
        self.assertIn('10.0 min | 20.0 min', text)
        self.assertIn('Calculated routes: 1/6', text)
        self.assertIn('not calculated', text)

    def test_selection_ranks_turn_density_instead_of_total_turns_or_length(self):
        s = suite.make_suite(self.points()); plan = {'routes': {}}
        for r, turns, distance in zip(s['scenarios'], [100, 20, 9, 8, 6, 1], [100000, 5000, 3000, 4000, 4000, 5000]):
            plan['routes'][r['id']] = {'status': 'planned', 'turns': turns, 'distanceM': distance}
        selected = suite.choose_routes(s, plan)
        self.assertEqual(selected['active'], ['R002', 'R003', 'R004', 'R005', 'R001'])
        self.assertEqual(selected['parked'], ['R006'])
        self.assertEqual(selected['planSha256'], suite.digest(plan))
        self.assertEqual(selected['simulation'], {'mode':'realistic','randomness':'native_unseeded'})

    def test_equal_density_prefers_shorter_route_then_stable_id(self):
        s = suite.make_suite(self.points()); plan = {'routes': {}}
        for i, r in enumerate(s['scenarios']):
            plan['routes'][r['id']] = {'status': 'planned', 'turns': 10 if i < 2 else 20, 'distanceM': 5000 if i < 2 else 10000}
        self.assertEqual(suite.choose_routes(s, plan)['active'], ['R001', 'R002', 'R003', 'R004', 'R005'])

    def test_density_requires_positive_distance(self):
        s = suite.make_suite(self.points())
        plan = {'routes': {r['id']: {'status': 'planned', 'turns': 1, 'distanceM': 0} for r in s['scenarios']}}
        with self.assertRaisesRegex(ValueError, 'positive'): suite.choose_routes(s, plan)

    def test_native_timing_accounts_for_dense_vertices_and_speed_has_a_floor(self):
        # Same physical straight, but native CONSTANT visits each route vertex.
        sparse = {'locationsLatLon': [[0, 0], [0, .001]]}
        dense = {'locationsLatLon': [[0, i*.0001] for i in range(11)]}
        self.assertGreater(suite.native_constant_seconds(dense,20),suite.native_constant_seconds(sparse,20))
        self.assertEqual(suite.native_constant_seconds(dense,20),suite.native_constant_seconds(dense,35))
        self.assertLess(suite.native_constant_seconds(sparse,20),suite.native_constant_seconds(sparse,10))


class EvidenceTests(unittest.TestCase):
    def test_readiness_requires_live_current_process_tethered_sdk_state(self):
        value={'status':'ok','pid':42,'sdkStrategy':'ConnectIQAdbStrategy','deviceStatus':'CONNECTED'}
        self.assertTrue(suite.sdk_connected_state(value,'42'))
        for change in [{'status':'error'},{'pid':99},{'sdkStrategy':'ConnectIQDeviceStrategy'},
                       {'deviceStatus':'NOT_CONNECTED'},{'deviceStatus':'NO_DEVICE'}]:
            self.assertFalse(suite.sdk_connected_state(dict(value,**change),'42'))

    def test_native_stop_observations_deduplicate_fixes_and_separate_route_replacement(self):
        p = suite.NativeObservations()
        before = {'fixTimeMs':1,'fixSpeedMps':0,'nextRouteIndex':4,'routeToken':'a'}
        self.assertIsNone(p.sample(before));self.assertIsNone(p.sample(before))
        event = p.sample(dict(before,fixTimeMs=2,nextRouteIndex=8))
        self.assertTrue(event['stoppedOnBothObservedFixes'])
        self.assertEqual(p.summary['freshFixes'],2)
        self.assertEqual(p.summary['turnChangesWhileStopped'],1)
        self.assertIsNone(p.sample(dict(before,fixTimeMs=3,routeToken='b',nextRouteIndex=12)))
        self.assertEqual(p.summary['nativeTurnChanges'],1)

    def test_realistic_deadline_is_a_guard_without_constant_speed(self):
        route = {'remainingTimeSeconds':100,'locationsLatLon':[[0,0]]*1000}
        self.assertEqual(suite.native_route_timeout(route,{'mode':'realistic'}),4800)

    def test_execution_clock_starts_on_first_frame_and_never_moves_with_later_frames(self):
        p = suite.Progress(0)
        p.watch('JUNCTION_START build=test', 11)
        self.assertIsNone(p.first_draw)
        p.watch('JUNCTION_DRAW seq=1 state=idle', 12)
        p.watch('JUNCTION_DRAW seq=2 state=active', 15)
        self.assertEqual(p.first_draw, 12)
        self.assertEqual(p.last_draw, 15)

    def test_unrelated_android_crash_lines_are_not_recorded(self):
        self.assertFalse(suite.owned_android_line('11-08 10:00:00.123 999 999 E AndroidRuntime: private other app', {'123'}))
        self.assertTrue(suite.owned_android_line('11-08 10:00:00.123 123 124 E AndroidRuntime: own crash', {'123'}))
        self.assertTrue(suite.owned_android_line('11-08 10:00:00.123 100 100 I ActivityManager: net.osmand.plus.junction died', {'123'}))

    def test_ack_is_evidence_only_when_a_watch_draw_matches(self):
        p = suite.Progress(0)
        p.android('DRAW_ACK generation=3 seq=42 state=active', 1)
        self.assertEqual(p.confirmed['active'], 0)
        p.watch('JUNCTION_DRAW seq=41 state=active mode=map_context', 2)
        self.assertEqual(p.confirmed['active'], 0)
        p.watch('JUNCTION_DRAW seq=42 state=active mode=map_context', 3)
        self.assertEqual(p.confirmed['active'], 1)
        self.assertEqual(p.last_active, 3)
        self.assertEqual(p.confirmed_events[-1]['generation'], 3)
        self.assertEqual(p.confirmed_events[-1]['mode'], 'map_context')

    def test_dropped_old_events_do_not_grow_memory_forever(self):
        p = suite.Progress(0)
        for i in range(10000): p.watch(f'JUNCTION_DRAW seq={i} state=active', i)
        self.assertEqual(len(p.draws), 64)
        self.assertEqual(len(p.draw_modes), 64)
        self.assertEqual(p.confirmed['active'], 0)

    def test_watch_exception_is_not_successful_end_of_duration(self):
        p = suite.Progress(0)
        p.watch('Error: Out Of Memory', 1)
        self.assertEqual(p.failure, 'watch_runtime_error')
        self.assertFalse(p.expected_exit)
        p.watch('JUNCTION_SUITE_EXIT reason=duration', 2)
        self.assertEqual(p.failure, 'watch_runtime_error')

    def test_completed_observer_exit_is_distinct_from_time_cap(self):
        p=suite.Progress(0)
        p.watch('JUNCTION_SUITE_EXIT reason=completed',1)
        self.assertEqual(p.exit_reason,'completed')
        self.assertTrue(p.expected_exit)

    def test_tail_preserves_split_lines_and_reads_incrementally(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)/'watch.log'; p.write_text('first\npart')
            tail = suite.Tail(p)
            self.assertEqual(tail.read(), ['first'])
            with p.open('a') as f: f.write('ial\nlast\n')
            self.assertEqual(tail.read(), ['partial', 'last'])
            self.assertEqual(tail.read(), [])

    def test_connect_requires_visible_waydroid_before_adb_and_rejects_missing_serial(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(suite.subprocess, 'run') as run, patch.object(suite.desk, 'Desk') as desk:
            p = Path(tmp)/'cfg.json'; p.write_text('{}')
            with self.assertRaisesRegex(ValueError, 'explicit'): suite.connect(p)
            self.assertEqual(run.call_args.args[0], ['waydroid', 'show-full-ui'])
            desk.assert_not_called()


if __name__ == '__main__': unittest.main()
