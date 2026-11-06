import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import desk


class DeskTargetTests(unittest.TestCase):
    def config(self, directory, serial='waydroid-test:5555'):
        path=Path(directory)/'config.json'
        path.write_text(json.dumps({'android_sdk':'/sdk','adb_serial':serial}))
        return path

    def test_missing_target_never_auto_selects_a_phone(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(desk.route_probe,'command') as call:
            with self.assertRaisesRegex(ValueError,'explicit Waydroid'):
                desk.Desk(self.config(directory,''))
            call.assert_not_called()

    def test_non_waydroid_target_rejected_before_any_mutation(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(desk.route_probe,'command',return_value='physical-phone') as call:
            with self.assertRaisesRegex(ValueError,'non-Waydroid'):
                desk.Desk(self.config(directory))
            self.assertEqual(call.call_count,1)
            self.assertEqual(call.call_args.args[0][-3:],['shell','getprop','ro.product.device'])

    def test_all_commands_retain_explicit_target(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(desk.route_probe,'command',return_value='waydroid_x86_64') as call:
            client=desk.Desk(self.config(directory));client.command('shell','echo','test')
            for invocation in call.call_args_list:
                self.assertEqual(invocation.args[0][:3],['/sdk/platform-tools/adb','-s','waydroid-test:5555'])

    def test_unknown_control_rejected_without_broadcast(self):
        client=object.__new__(desk.Desk)
        with patch.object(client,'command') as call:
            with self.assertRaisesRegex(ValueError,'unknown operation'):client.probe('erase')
            call.assert_not_called()

    def test_old_evidence_is_not_accepted_for_a_new_request(self):
        client=object.__new__(desk.Desk)
        old=json.dumps({'request':'old','status':'decoded'})
        current=json.dumps({'request':'new','status':'decoded'})
        with patch.object(desk.uuid,'uuid4') as identity, patch.object(client,'command',side_effect=['broadcast',old,current]), patch.object(desk.time,'sleep'):
            identity.return_value.hex='new'
            self.assertEqual(client.probe(bridge=True)['request'],'new')

    def test_invalid_endpoints_rejected_before_device_access(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(desk.Desk,'command') as call:
            for point in ([float('nan'),1],[90,1],[1,181]):
                with self.assertRaisesRegex(ValueError,'latitude'):
                    desk.prepare_endpoints(object(),point,[1,2],Path(directory))
            call.assert_not_called()

    def test_active_route_capture_rejects_recalculation_identity_race(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(desk.route_probe,'sample',return_value={'routeToken':'old'}), patch.object(desk.route_probe,'validate',return_value=[]):
            client=type('Client',(),{'adb':[]})();known={}
            source={'routeCalculated':True,'routeToken':'new'}
            self.assertIsNone(desk.capture_active_route(client,source,Path(directory),known))
            self.assertEqual(known,{})
            self.assertFalse((Path(directory)/'routes').exists())

    def test_active_route_capture_is_saved_once_per_native_identity(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(desk.route_probe,'sample',return_value={'routeToken':'new'}) as sample, patch.object(desk.route_probe,'validate',return_value=[]):
            client=type('Client',(),{'adb':[]})();known={};source={'routeCalculated':True,'routeToken':'new'}
            for _ in range(2):self.assertEqual(desk.capture_active_route(client,source,Path(directory),known),'routes/route-0.json')
            self.assertEqual(sample.call_count,1)


if __name__=='__main__':unittest.main()
