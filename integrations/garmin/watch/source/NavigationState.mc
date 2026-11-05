import Toybox.Lang;

//! Scene validation and freshness; delivery request/epoch checks belong to the input adapter.
module SceneDecoder {
    function integer(value as Object?, low as Number, high as Number) as Boolean {
        return value instanceof Number && value >= low && value <= high;
    }
    function text(value as Object?, limit as Number) as Boolean {
        return value instanceof String && value.length() <= limit;
    }
    function point(value as Object?, radius as Number) as Boolean {
        if (!(value instanceof Array) || value.size() != 2) { return false; }
        return integer(value[0], -radius, radius) && integer(value[1], -radius, radius) &&
            value[0]*value[0] + value[1]*value[1] <= radius*radius;
    }
    function decode(value as Object?) as Dictionary? {
        if (!(value instanceof Dictionary)) { return null; }
        var required = ["version","session","generation","seq","state","geometryMode","reason","distanceM","roadName","maneuver","radiusDm","sourceAgeMs","fixAgeMs","anchors","paths"];
        for (var i=0; i<required.size(); i+=1) { if (!value.hasKey(required[i])) { return null; } }
        if (!integer(value["version"],1,1) || !text(value["session"],64) || value["session"].length()==0 ||
            !integer(value["generation"],0,1000000) || !integer(value["seq"],0,1000000) ||
            !integer(value["sourceAgeMs"],0,60000) || !integer(value["fixAgeMs"],0,60000) ||
            !integer(value["distanceM"],0,1000000) || !integer(value["radiusDm"],1,2000) ||
            !text(value["roadName"],80) || !text(value["maneuver"],80) || !text(value["reason"],80) ||
            !text(value["state"],32) || !text(value["geometryMode"],32)) { return null; }
        var progressAge=0, speed=0;
        if (value.hasKey("progressAgeMs") || value.hasKey("speedDmps")) {
            if (!integer(value["progressAgeMs"],0,60000) || !integer(value["speedDmps"],0,700)) { return null; }
            progressAge=value["progressAgeMs"];speed=value["speedDmps"];
        }
        var status=value["state"], mode=value["geometryMode"], radius=value["radiusDm"];
        if (!(status.equals("active") || status.equals("idle") || status.equals("recalculating") || status.equals("unavailable"))) { return null; }
        if (!(mode.equals("routing_branches") || mode.equals("map_context") || mode.equals("route_only") || mode.equals("unavailable"))) { return null; }
        var context=mode.equals("map_context");
        var anchors=value["anchors"], paths=value["paths"];
        if (!(anchors instanceof Array) || anchors.size()>4 || !(paths instanceof Array) || paths.size()>(context?32:8)) { return null; }
        var byId={}, normalizedAnchors=[];
        for (var i=0; i<anchors.size(); i+=1) {
            var a=anchors[i];
            if (!(a instanceof Dictionary) || !text(a["id"],32) || a["id"].length()==0 || byId.hasKey(a["id"]) ||
                !point(a["point"],radius) || !integer(a["routeIndex"],0,1000000)) { return null; }
            var p=a["point"];
            var normalized={"id"=>a["id"],"point"=>[p[0],p[1]],"routeIndex"=>a["routeIndex"]};
            byId[a["id"]]=normalized; normalizedAnchors.add(normalized);
        }
        var ids={}, total=0, selected=0, normalizedPaths=[];
        for (var i=0; i<paths.size(); i+=1) {
            var p=paths[i];
            if (!(p instanceof Dictionary) || !text(p["id"],32) || p["id"].length()==0 || ids.hasKey(p["id"]) || !text(p["role"],16)) { return null; }
            ids[p["id"]]=true;
            var role=p["role"], points=p["points"], links=p["anchorRefs"];
            if (!(role.equals("selected") || role.equals("branch") || (context && role.equals("context"))) ||
                !(points instanceof Array) || points.size()<2 || points.size()>(context?48:24) ||
                !(links instanceof Array) || (links.size()==0 && !role.equals("context")) || links.size()>4 ||
                (role.equals("context") && links.size()!=0)) { return null; }
            if (role.equals("selected")) { selected+=1; }
            if (mode.equals("route_only") && !role.equals("selected")) { return null; }
            total+=points.size(); if (total>(context?512:96)) { return null; }
            var normalizedPoints=[], normalizedLinks=[], linked={};
            for (var j=0; j<points.size(); j+=1) {
                if (!point(points[j],radius)) { return null; }
                normalizedPoints.add([points[j][0],points[j][1]]);
            }
            for (var j=0; j<links.size(); j+=1) {
                var ref=links[j];
                if (!(ref instanceof Array) || ref.size()!=2 || !text(ref[0],32) || !byId.hasKey(ref[0]) ||
                    linked.hasKey(ref[0]) || !integer(ref[1],0,points.size()-1)) { return null; }
                var expected=byId[ref[0]]["point"], actual=points[ref[1]];
                if (expected[0]!=actual[0] || expected[1]!=actual[1]) { return null; }
                linked[ref[0]]=true;normalizedLinks.add([ref[0],ref[1]]);
            }
            if (role.equals("selected") && linked.size()!=anchors.size()) { return null; }
            normalizedPaths.add({"id"=>p["id"],"role"=>role,"points"=>normalizedPoints,"anchorRefs"=>normalizedLinks});
        }
        var activeGeometry=status.equals("active") && !mode.equals("unavailable");
        if (activeGeometry && (selected!=1 || anchors.size()==0)) { return null; }
        if (!activeGeometry && (paths.size()!=0 || anchors.size()!=0)) { return null; }
        return {"version"=>1,"session"=>value["session"],"generation"=>value["generation"],"seq"=>value["seq"],
            "state"=>status,"geometryMode"=>mode,"reason"=>value["reason"],"distanceM"=>value["distanceM"],
            "roadName"=>value["roadName"],"maneuver"=>value["maneuver"],"radiusDm"=>radius,
            "sourceAgeMs"=>value["sourceAgeMs"],"fixAgeMs"=>value["fixAgeMs"],
            "progressAgeMs"=>progressAge,"speedDmps"=>speed,"anchors"=>normalizedAnchors,"paths"=>normalizedPaths};
    }
}

class NavigationState {
    private var _scene as Dictionary? = null;
    private var _receivedAt as Number = 0;
    private var _session as String = "";
    private var _generation as Number = -1;
    private var _seq as Number = -1;

    function accept(value as Object?, now as Number) as Boolean {
        var scene=SceneDecoder.decode(value);
        if (scene==null) { return false; }
        if (_scene!=null && _session.equals(scene["session"])) {
            if (scene["generation"]<_generation || (scene["generation"]==_generation && scene["seq"]<=_seq)) { return false; }
        }
        _scene=scene;_receivedAt=now;_session=scene["session"];
        _generation=scene["generation"];_seq=scene["seq"];
        return true;
    }
    function scene() as Dictionary? { return _scene; }
    function sequence() as Number { return _seq; }
    //! Hold the junction scene fixed. Estimate distance only, at most one second
    //! beyond the matched progress sample. Never advance the junction locally.
    function displayDistance(now as Number) as Number? {
        if (!status(now).equals("active")) { return null; }
        var age=_scene["progressAgeMs"]+now-_receivedAt;
        if (age>1000) { age=1000; }
        var correction=(_scene["speedDmps"]*age/10000.0).toNumber();
        var distance=_scene["distanceM"]-correction;
        return distance<0?0:distance;
    }
    function status(now as Number) as String {
        if (_scene==null) { return "unavailable"; }
        var status=_scene["state"];
        if (!status.equals("active")) { return status; }
        var age=now-_receivedAt;
        if (age<0) { return "stale_transport"; }
        if (_scene["sourceAgeMs"]+age>5000 || _scene["fixAgeMs"]+age>5000 || _scene["progressAgeMs"]+age>5000) { return "stale_source"; }
        if (age>3000) { return "stale_transport"; }
        return "active";
    }
}
