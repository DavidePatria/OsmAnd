import Toybox.Lang;
import Toybox.System;
import Toybox.Timer;
import Toybox.WatchUi;
const REPLAY_MODE = true;
function createInput(app as JunctionApp) as InputAdapter { return new ReplayInput(app.nav); }

class ReplayInput extends InputAdapter {
    private var _state as NavigationState;
    private var _timer as Timer.Timer = new Timer.Timer();
    private var _frames as Array<Dictionary>;
    private var _started as Number = 0;
    private var _offset as Number = 0;
    private var _frozen as Number = 0;
    private var _paused as Boolean = false;
    private var _index as Number = -1;
    private var _sequence as Number = 0;

    function initialize(state as NavigationState) {
        InputAdapter.initialize();_state=state;_frames=ReplayFixtures.frames();
        _paused=ReplayFixtures.hold();
    }
    function now() as Number {
        if (_paused) { return _frozen; }
        return _offset+((System.getTimer()-_started)*ReplayFixtures.speed()).toNumber();
    }
    function start() as Void {
        _started=System.getTimer();
        System.println("JUNCTION_REPLAY source=captured scenario="+ReplayFixtures.scenario()+" sha256="+ReplayFixtures.sourceHash());
        // One display update per second at normal speed. Faster replay scales
        // the timer too, so it does not skip the distance samples under test.
        tick();_timer.start(method(:tick),(1000/ReplayFixtures.speed()).toNumber(),true);
    }
    function stop() as Void { _timer.stop(); }
    function tick() as Void {
        var elapsed=now();
        if (elapsed>=26000) {
            _offset=0;_started=System.getTimer();_index=-1;elapsed=0;
        }
        while (_index+1<_frames.size() && _frames[_index+1]["atMs"]<=elapsed) {
            _index+=1;applyFrame(elapsed);
        }
        WatchUi.requestUpdate();
    }
    private function applyFrame(elapsed as Number) as Void {
        var packet=_frames[_index]["scene"];
        if (packet!=null) {
            _sequence+=1;packet["seq"]=_sequence;
            if (!_state.accept(packet,elapsed)) { System.println("JUNCTION_REPLAY_REJECT frame="+_index); }
        }
    }
    function paused() as Boolean { return _paused; }
    function togglePause() as Void {
        if (_paused) { _offset=_frozen;_started=System.getTimer();_paused=false; }
        else { _frozen=now();_paused=true; }
        WatchUi.requestUpdate();
    }
    function advance(delta as Number) as Void {
        var next=_index+delta;
        if (next<0) { next=0; }
        if (next>=_frames.size()) { next=0; }
        _index=next;_frozen=_frames[_index]["atMs"];_offset=_frozen;_started=System.getTimer();_paused=true;
        applyFrame(_frozen);WatchUi.requestUpdate();
    }
}
