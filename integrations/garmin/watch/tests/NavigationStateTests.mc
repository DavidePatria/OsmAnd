import Toybox.Lang;
import Toybox.Test;

function testScene() as Dictionary {
    return {"version"=>1,"session"=>"test","generation"=>1,"seq"=>1,"state"=>"active","geometryMode"=>"routing_branches",
        "reason"=>"partial roads","distanceM"=>100,"roadName"=>"Test","maneuver"=>"TR","radiusDm"=>2000,"sourceAgeMs"=>0,"fixAgeMs"=>0,
        "anchors"=>[{"id"=>"a","point"=>[0,0],"routeIndex"=>1}],
        "paths"=>[{"id"=>"route","role"=>"selected","points"=>[[0,-100],[0,0],[100,0]],"anchorRefs"=>[["a",1]]}]};
}
(:test)
function decoderRejectsMalformedScene(logger as Test.Logger) as Boolean {
    var s=testScene();s["version"]=2;if (SceneDecoder.decode(s)!=null) { return false; }
    s=testScene();s["paths"][0]["anchorRefs"]=[["missing",1]];if (SceneDecoder.decode(s)!=null) { return false; }
    s=testScene();s["paths"][0]["points"][0]=[1500,1500];return SceneDecoder.decode(s)==null;
}
(:test)
function invalidPacketDoesNotRefreshAge(logger as Test.Logger) as Boolean {
    var state=new NavigationState();if (!state.accept(testScene(),0)) { return false; }
    var bad=testScene();bad["version"]=2;
    return !state.accept(bad,2900) && state.status(4000).equals("stale_transport");
}
(:test)
function staleSourceIsDistinctFromTransport(logger as Test.Logger) as Boolean {
    var state=new NavigationState();var s=testScene();s["fixAgeMs"]=6000;
    return state.accept(s,100) && state.status(100).equals("stale_source");
}
(:test)
function olderGenerationAndDuplicateAreRejected(logger as Test.Logger) as Boolean {
    var state=new NavigationState();var s=testScene();s["generation"]=2;
    if (!state.accept(s,0) || state.accept(s,100)) { return false; }
    var old=testScene();old["seq"]=50;
    return !state.accept(old,200) && state.sequence()==1;
}
(:test)
function stateOwnsDecodedGeometry(logger as Test.Logger) as Boolean {
    var state=new NavigationState();var s=testScene();state.accept(s,0);
    s["paths"][0]["points"][0][0]=999;
    return state.scene()["paths"][0]["points"][0][0]==0;
}
(:test)
function rerouteClearsGeometryAndClockWrapExpires(logger as Test.Logger) as Boolean {
    var state=new NavigationState();state.accept(testScene(),100);
    if (!state.status(50).equals("stale_transport")) { return false; }
    var s=testScene();s["seq"]=2;s["state"]="recalculating";s["geometryMode"]="unavailable";s["paths"]=[];s["anchors"]=[];
    return state.accept(s,200) && state.status(201).equals("recalculating") && state.scene()["paths"].size()==0;
}
(:test)
function distanceEstimateIsBoundedAndDoesNotMoveGeometry(logger as Test.Logger) as Boolean {
    var state=new NavigationState();var s=testScene();s["progressAgeMs"]=250;s["speedDmps"]=100;
    if (!state.accept(s,0) || state.displayDistance(0)!=98 || state.displayDistance(750)!=90 || state.displayDistance(2000)!=90) { return false; }
    return state.scene()["anchors"][0]["point"][0]==0 && state.scene()["paths"][0]["points"][0][1]==-100;
}
(:test)
function distanceStopsAtZeroWithoutAdvancingJunction(logger as Test.Logger) as Boolean {
    var state=new NavigationState();var s=testScene();s["distanceM"]=3;s["progressAgeMs"]=0;s["speedDmps"]=100;
    return state.accept(s,0) && state.displayDistance(1000)==0 && state.sequence()==1 && state.scene()["anchors"][0]["routeIndex"]==1;
}
(:test)
function stoppedAndLegacySamplesAreNotAnticipated(logger as Test.Logger) as Boolean {
    var state=new NavigationState();if (!state.accept(testScene(),0) || state.displayDistance(1000)!=100) { return false; }
    var s=testScene();s["seq"]=2;s["progressAgeMs"]=500;s["speedDmps"]=0;
    return state.accept(s,1000) && state.displayDistance(2000)==100 && state.displayDistance(5001)==null;
}
(:test)
function malformedProgressPairIsRejected(logger as Test.Logger) as Boolean {
    var s=testScene();s["progressAgeMs"]=0;
    if (SceneDecoder.decode(s)!=null) { return false; }
    s["speedDmps"]=701;return SceneDecoder.decode(s)==null;
}
(:test)
function contextBudgetAndNoInventedConnectivity(logger as Test.Logger) as Boolean {
    var s=testScene();s["geometryMode"]="map_context";
    for (var i=0;i<28;i+=1) {
        s["paths"].add({"id"=>"c"+i,"role"=>"context","points"=>[[10,i],[100,i]],"anchorRefs"=>[]});
    }
    if (SceneDecoder.decode(s)==null) { return false; }
    s["paths"][1]["anchorRefs"]=[["a",0]];
    if (SceneDecoder.decode(s)!=null) { return false; }
    s["paths"][1]["anchorRefs"]=[];s["geometryMode"]="routing_branches";
    return SceneDecoder.decode(s)==null;
}
