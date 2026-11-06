import Toybox.Lang;
import Toybox.System;
const REPLAY_MODE = true;
const NAVIGATION_MODE = false;
function createInput(app as JunctionApp) as InputAdapter { return new CapacityInput(app.nav); }

//! Synthetic bounds test only, under the NORMAL application heap (not unit-test heap).
class CapacityInput extends InputAdapter {
    private var _state as NavigationState;
    function initialize(state as NavigationState) { InputAdapter.initialize();_state=state; }
    function start() as Void {
        var anchors=[],links=[],paths=[];
        for (var i=0;i<4;i+=1) { anchors.add({"id"=>"a"+i,"point"=>[i*10,0],"routeIndex"=>i});links.add(["a"+i,i]); }
        for (var i=0;i<40;i+=1) {
            var points=[];
            for (var j=0;j<(i<32?13:12);j+=1) { points.add([j*10,i]); }
            var path={"id"=>"p"+i,"role"=>(i==0?"selected":"context"),"points"=>points,"anchorRefs"=>(i==0?links:[]),"layer"=>i%2};
            if (i==0) { var levels=[];for (var j=0;j<12;j+=1) { levels.add(j%2); }path["segmentLayers"]=levels; }
            paths.add(path);
        }
        var scene={"version"=>1,"session"=>"synthetic-capacity","generation"=>1,"seq"=>1,
            "state"=>"active","geometryMode"=>"layer_context","reason"=>"Synthetic capacity test, not mapped roads",
            "roadName"=>"SYNTHETIC CAPACITY TEST","maneuver"=>"TR","distanceM"=>120,"radiusDm"=>800,
            "sourceAgeMs"=>0,"fixAgeMs"=>0,"progressAgeMs"=>0,"speedDmps"=>0,"anchors"=>anchors,"paths"=>paths};
        if (!_state.accept(scene,System.getTimer())) { throw new Lang.InvalidValueException("Maximum synthetic scene rejected"); }
    }
    function afterFrame() as Void {
        var scene=_state.scene(),points=0;
        for (var i=0;i<scene["paths"].size();i+=1) { points+=scene["paths"][i]["points"].size(); }
        System.println("JUNCTION_CAPACITY_RENDER paths="+scene["paths"].size()+" points="+points);
        System.exit();
    }
}
