import Toybox.Lang;

//! Local request clock bounds reply age without synchronized phone/watch clocks.
class NavigationRequestGate {
    private var _epoch as String = "";
    private var _next as Number = 0;
    private var _pending as Number = 0;
    private var _sentAt as Number = 0;
    function initialize() {}
    function reset(epoch as String) as Void { _epoch=epoch;_next=0;_pending=0; }
    function begin(now as Number) as Dictionary? {
        if (_pending!=0 && now>=_sentAt && now-_sentAt<3000) { return null; }
        _pending=0;
        if (_next>=1000000 || _epoch.length()==0) { return null; }
        _next+=1;_pending=_next;_sentAt=now;
        return {"version"=>1,"kind"=>"junction_request","epoch"=>_epoch,"requestId"=>_pending};
    }
    function abandon(id as Number) as Void { if (id==_pending) { _pending=0; } }
    function accept(value as Object?, now as Number, state as NavigationState) as Boolean {
        if (!(value instanceof Dictionary) || !SceneDecoder.integer(value["version"],1,1) ||
            !(value["kind"] instanceof String) || !(value["kind"].equals("junction_snapshot") || value["kind"].equals("junction_unavailable")) ||
            !(value["epoch"] instanceof String) || !value["epoch"].equals(_epoch) ||
            _pending==0 || !SceneDecoder.integer(value["requestId"],1,1000000) || value["requestId"]!=_pending || now<_sentAt || now-_sentAt>=3000) { return false; }
        if (value["kind"].equals("junction_unavailable")) {
            if (!(value["reason"] instanceof String) || value["reason"].length()>80) { return false; }
            state.invalidate();_pending=0;return true;
        }
        var decoded=SceneDecoder.decode(value["scene"]);
        if (decoded==null) { return false; }
        var roundTrip=now-_sentAt;
        var ages=["sourceAgeMs","fixAgeMs","progressAgeMs"];
        for (var i=0;i<ages.size();i+=1) {
            var age=decoded[ages[i]]+roundTrip;decoded[ages[i]]=age>60000?60000:age;
        }
        if (!state.accept(decoded,now)) { return false; }
        _pending=0;return true;
    }
}
