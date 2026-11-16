import Toybox.Activity;
import Toybox.Application;
import Toybox.Attention;
import Toybox.Communications;
import Toybox.Graphics;
import Toybox.Lang;
import Toybox.System;
import Toybox.Time;
import Toybox.WatchUi;

const REPLAY_MODE = false;

//! Runs only within a Garmin activity; the activity owns page updates and lifecycle.
class JunctionFieldApp extends Application.AppBase {
    var nav as NavigationState = new NavigationState();
    var input as FieldInput;
    function initialize() { AppBase.initialize(); input=new FieldInput(nav); }
    function onStart(state as Dictionary?) as Void { input.start(); }
    function onStop(state as Dictionary?) as Void { input.stop(); }
    function getInitialView() as [Views] or [Views, InputDelegates] { return [new JunctionField()]; }
}
function getFieldApp() as JunctionFieldApp { return Application.getApp() as JunctionFieldApp; }

class JunctionField extends WatchUi.DataField {
    private var _renderer as JunctionRenderer = new JunctionRenderer();
    private var _loggedFrame as Boolean = false;
    function initialize() { DataField.initialize(); }
    function compute(info as Activity.Info) as Void { getFieldApp().input.tick(); }
    function onUpdate(dc as Dc) as Void {
        var app=getFieldApp(), now=System.getTimer();
        if(!_loggedFrame) {
            _loggedFrame=true;
            var memory=System.getSystemStats();
            System.println("JUNCTION_FIELD_FRAME width="+dc.getWidth()+" height="+dc.getHeight()+" used="+memory.usedMemory+" free="+memory.freeMemory);
        }
        // Small multi-field layouts show a legible distance instead of clipped roads.
        if(dc.getWidth()<300 || dc.getHeight()<300) {
            dc.setColor(Graphics.COLOR_BLACK,Graphics.COLOR_BLACK);dc.clear();
            dc.setColor(Graphics.COLOR_WHITE,Graphics.COLOR_BLACK);
            var state=app.nav.status(now),scene=app.nav.scene();
            var text=state.equals("active") && scene!=null && !scene["geometryMode"].equals("unavailable")
                ? app.nav.displayDistance(now)+" m" : (state.equals("arrived")?"ARRIVED":
                    (state.equals("recalculating")?"REROUTING":(state.equals("active")?"DETAIL LIMITED":"WAITING")));
            dc.drawText(dc.getWidth()/2,dc.getHeight()/2-15,Graphics.FONT_SMALL,text,Graphics.TEXT_JUSTIFY_CENTER);
        } else { _renderer.draw(dc,app.nav,now,false); }
        app.input.didDraw(app.nav.scene(),app.nav.status(now));
    }
}

//! Poll using the activity's once-per-second compute callback; no Timer in data fields.
class FieldInput {
    private var _state as NavigationState;
    private var _gate as NavigationRequestGate = new NavigationRequestGate();
    private var _alert as JunctionAlert = new JunctionAlert();
    private var _epoch as String = "";
    private var _epochCounter as Number = 0;
    private var _busy as Boolean = false;
    private var _sendingId as Number = 0;
    private var _connected as Boolean = false;
    private var _lastTick as Number = 0;
    private var _displayed as Dictionary? = null;
    function initialize(state as NavigationState) { _state=state; }
    private function newEpoch() as Void {
        _epochCounter+=1;_epoch=Time.now().value().toString()+":"+System.getTimer()+":"+_epochCounter;
        _gate.reset(_epoch);_state.invalidate();_busy=false;_sendingId=0;_displayed=null;
    }
    function start() as Void { newEpoch();Communications.registerForPhoneAppMessages(method(:onPhone)); }
    function stop() as Void { Communications.registerForPhoneAppMessages(null);newEpoch(); }
    function tick() as Void {
        var now=System.getTimer(),connected=System.getDeviceSettings().phoneConnected;
        if(connected!=_connected || now<_lastTick) { _connected=connected;newEpoch(); }
        _lastTick=now;
        if(connected && !_busy) {
            var request=_gate.begin(now);
            if(request!=null) {
                if(_displayed!=null) {
                    request["displayedSession"]=_displayed["session"];request["displayedGeneration"]=_displayed["generation"];
                    request["displayedSeq"]=_displayed["seq"];request["displayedState"]=_displayed["state"];
                }
                _busy=true;_sendingId=request["requestId"];
                try { Communications.transmit(request,null,new FieldSendListener(self,_epoch,_sendingId)); }
                catch(error) { sendFinished(_epoch,_sendingId,false); }
            }
        }
    }
    function sendFinished(epoch as String,id as Number,success as Boolean) as Void {
        if(!epoch.equals(_epoch) || id!=_sendingId) { return; }
        _busy=false;if(!success) { _gate.abandon(id);_state.invalidate(); }
    }
    function onPhone(message as Communications.PhoneAppMessage) as Void {
        // CompactWire allocates a fresh object graph; no caller keeps it after this callback.
        if(_connected) {
            var packet=CompactWire.bytes(message.data);
            if(packet!=null) {_gate.acceptCompactOwned(packet,System.getTimer(),_state);}
        }
    }
    function didDraw(scene as Dictionary?,status as String) as Void {
        _displayed=scene==null?null:{"session"=>scene["session"],"generation"=>scene["generation"],"seq"=>scene["seq"],"state"=>status};
        if(_alert.shouldAlert(scene,status) && Attention has :vibrate) {
            try { Attention.vibrate([new Attention.VibeProfile(50,300)]); } catch(error) { }
        }
    }
}
class FieldSendListener extends Communications.ConnectionListener {
    private var _input as FieldInput;private var _epoch as String;private var _id as Number;
    function initialize(input as FieldInput,epoch as String,id as Number) { ConnectionListener.initialize();_input=input;_epoch=epoch;_id=id; }
    function onComplete() as Void { _input.sendFinished(_epoch,_id,true); }
    function onError() as Void { _input.sendFinished(_epoch,_id,false); }
}
