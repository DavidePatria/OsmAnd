import Toybox.Communications;
import Toybox.Lang;
import Toybox.System;
import Toybox.Time;
import Toybox.Timer;
import Toybox.WatchUi;
class NavigationInput extends InputAdapter {
    private var _state as NavigationState;
    private var _gate as NavigationRequestGate = new NavigationRequestGate();
    private var _timer as Timer.Timer = new Timer.Timer();
    private var _epoch as String = "";
    private var _epochCounter as Number = 0;
    private var _busy as Boolean = false;
    private var _sendingId as Number = 0;
    private var _connected as Boolean = false;
    private var _lastTick as Number = 0;
    private var _displayed as Dictionary? = null;
    private var _startupOnly as Boolean;
    function initialize(state as NavigationState,startupOnly as Boolean) { InputAdapter.initialize();_state=state;_startupOnly=startupOnly; }
    private function newEpoch() as Void {
        _epochCounter+=1;
        _epoch=Time.now().value().toString()+":"+System.getTimer()+":"+_epochCounter;
        _gate.reset(_epoch);_state.invalidate();_busy=false;_sendingId=0;_displayed=null;
    }
    function start() as Void {
        System.println("JUNCTION_NAV_START epoch");
        newEpoch();
        System.println("JUNCTION_NAV_START register");
        Communications.registerForPhoneAppMessages(method(:onPhone));
        System.println("JUNCTION_NAV_START timer");
        // Let the initial view draw before attempting an external SDK send.
        if (!_startupOnly) { _timer.start(method(:tick),1000,true); }
    }
    function stop() as Void {
        _timer.stop();Communications.registerForPhoneAppMessages(null);newEpoch();
    }
    function tick() as Void {
        var now=System.getTimer(), connected=System.getDeviceSettings().phoneConnected;
        if (connected!=_connected || now<_lastTick) { _connected=connected;newEpoch(); }
        _lastTick=now;
        if (connected && !_busy) {
            var request=_gate.begin(now);
            if (request!=null) {
                if (_displayed!=null) {
                    request["displayedSession"]=_displayed["session"];
                    request["displayedGeneration"]=_displayed["generation"];
                    request["displayedSeq"]=_displayed["seq"];
                    request["displayedState"]=_displayed["state"];
                }
                _busy=true;_sendingId=request["requestId"];
                System.println("JUNCTION_NAV_REQUEST id="+_sendingId);
                try { Communications.transmit(request,null,new NavigationSendListener(self,_epoch,_sendingId)); }
                catch (error) { sendFinished(_epoch,_sendingId,false); }
            }
        }
        WatchUi.requestUpdate();
    }
    function sendFinished(epoch as String,id as Number,success as Boolean) as Void {
        if (!epoch.equals(_epoch) || id!=_sendingId) { return; }
        _busy=false;
        if (!success) { _gate.abandon(id);_state.invalidate();WatchUi.requestUpdate(); }
    }
    function onPhone(message as Communications.PhoneAppMessage) as Void {
        if (_connected && _gate.accept(CompactWire.decode(message.data),System.getTimer(),_state)) { WatchUi.requestUpdate(); }
    }
    function didDraw(scene as Dictionary?,status as String) as Void {
        _displayed=scene==null?null:{"session"=>scene["session"],"generation"=>scene["generation"],"seq"=>scene["seq"],"state"=>status};
    }
    function afterFrame() as Void { if (_startupOnly) { System.exit(); } }
}
class NavigationSendListener extends Communications.ConnectionListener {
    private var _input as NavigationInput;
    private var _epoch as String;
    private var _id as Number;
    function initialize(input as NavigationInput,epoch as String,id as Number) { ConnectionListener.initialize();_input=input;_epoch=epoch;_id=id; }
    function onComplete() as Void { _input.sendFinished(_epoch,_id,true); }
    function onError() as Void { _input.sendFinished(_epoch,_id,false); }
}
