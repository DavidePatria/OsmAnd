import Toybox.System;
import Toybox.Lang;

//! Replaceable input only; scene decoder/state/renderer stay shared.
class InputAdapter {
    function initialize() {}
    function start() as Void {}
    function stop() as Void {}
    function now() as Number { return System.getTimer(); }
    function advance(delta as Number) as Void {}
    function togglePause() as Void {}
    function paused() as Boolean { return false; }
    function didDraw(scene as Dictionary?,status as String) as Void {}
    function afterFrame() as Void {}
}
