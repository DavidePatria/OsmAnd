import Toybox.Lang;

//! A displayed native decision is identified independently of packet sequence
//! and navigation-state generations, which can change on pause/reconnection.
class JunctionAlert {
    private var _session as String = "";
    private var _index as Number = -1;
    private var _maneuver as String = "";
    function shouldAlert(scene as Dictionary?,status as String) as Boolean {
        if (status.equals("idle") || status.equals("arrived")) {
            _session="";_index=-1;_maneuver="";return false;
        }
        if (!status.equals("active") || scene==null || scene["geometryMode"].equals("unavailable") || scene["anchors"].size()==0) { return false; }
        var session=scene["session"],index=scene["anchors"][0]["routeIndex"],maneuver=scene["maneuver"];
        if (_session.equals(session) && _index==index && _maneuver.equals(maneuver)) { return false; }
        _session=session;_index=index;_maneuver=maneuver;return true;
    }
}
