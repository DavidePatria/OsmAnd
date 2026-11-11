import Toybox.Lang;
import Toybox.Test;
import Toybox.System;

function testScene() as Dictionary {
    return {"version"=>1,"session"=>"test","generation"=>1,"seq"=>1,"state"=>"active","geometryMode"=>"routing_branches",
        "reason"=>"partial roads","distanceM"=>100,"roadName"=>"Test","maneuver"=>"TR","radiusDm"=>2000,"sourceAgeMs"=>0,"fixAgeMs"=>0,
        "anchors"=>[{"id"=>"a","point"=>[0,0],"routeIndex"=>1}],
        "paths"=>[{"id"=>"route","role"=>"selected","points"=>[[0,-100],[0,0],[100,0]],"anchorRefs"=>[["a",1]]}]};
}
(:test) function junctionLabelsAvoidCollisionsAndRoundEdges(logger as Test.Logger) as Boolean {
    var placed=[];
    var positions=[[227,227],[231,230],[225,232],[235,225]];
    for (var i=0;i<positions.size();i+=1) {
        var p=positions[i],box=JunctionLabelLayout.choose(p[0],p[1],42,71,454,454,89,379,placed);
        if (box==null || !JunctionLabelLayout.fits(box[0],box[1],box[2],box[3],454,454,89,379,placed)) {return false;}
        placed.add(box);
    }
    var edge=JunctionLabelLayout.choose(425,220,42,71,454,454,89,379,[]);
    if (edge==null || !JunctionLabelLayout.fits(edge[0],edge[1],edge[2],edge[3],454,454,89,379,[])) {return false;}
    var left=JunctionLabelLayout.chooseAway(227,227,42,71,454,454,89,379,[],-1,0);
    var right=JunctionLabelLayout.chooseAway(243,227,42,71,454,454,89,379,[left],1,0);
    return left!=null && right!=null && left[0]+left[2]<227 && right[0]>243;
}
(:test)
function junctionAlertFiresOncePerDisplayedNativeDecision(logger as Test.Logger) as Boolean {
    var alert=new JunctionAlert(),scene=testScene();
    if (!alert.shouldAlert(scene,"active") || alert.shouldAlert(scene,"active")) { return false; }
    scene["seq"]=2;scene["generation"]=2;scene["distanceM"]=50;
    if (alert.shouldAlert(scene,"active")) { return false; }
    if (alert.shouldAlert(null,"unavailable") || alert.shouldAlert(scene,"stale_transport") || alert.shouldAlert(scene,"active")) { return false; }
    scene["anchors"][0]["routeIndex"]=2;
    if (!alert.shouldAlert(scene,"active") || alert.shouldAlert(scene,"active")) { return false; }
    scene["maneuver"]="TL";
    return alert.shouldAlert(scene,"active") && !alert.shouldAlert(scene,"active");
}
(:test)
function junctionAlertWaitsForGeometryAndResetsAfterRoute(logger as Test.Logger) as Boolean {
    var alert=new JunctionAlert(),scene=testScene();scene["geometryMode"]="unavailable";
    if (alert.shouldAlert(scene,"active")) { return false; }
    scene["geometryMode"]="routing_branches";
    if (!alert.shouldAlert(scene,"active")) { return false; }
    alert.shouldAlert(null,"arrived");
    if (!alert.shouldAlert(scene,"active")) { return false; }
    alert.shouldAlert(null,"idle");
    if (!alert.shouldAlert(scene,"active")) { return false; }
    scene["session"]="new-session";return alert.shouldAlert(scene,"active");
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
    if (SceneDecoder.decode(s)!=null) { return false; }
    s["geometryMode"]="map_context";
    for (var i=28;i<39;i+=1) { s["paths"].add({"id"=>"c"+i,"role"=>"context","points"=>[[10,i],[100,i]],"anchorRefs"=>[]}); }
    if (s["paths"].size()!=40 || SceneDecoder.decode(s)==null) { return false; }
    s["paths"].add({"id"=>"overflow","role"=>"context","points"=>[[0,0],[10,10]],"anchorRefs"=>[]});
    return SceneDecoder.decode(s)==null;
}

(:test)
function maximumFullContextBudgetOwns512PointsAndRejects513(logger as Test.Logger) as Boolean {
    // Synthetic capacity input only; never presented as an extracted junction.
    var s=testScene();s["geometryMode"]="map_context";s["paths"]=[];
    for (var i=0;i<32;i+=1) {
        var points=[];
        for (var j=0;j<16;j+=1) { points.add([j*10,i]); }
        s["paths"].add({"id"=>"p"+i,"role"=>(i==0?"selected":"context"),
            "points"=>points,"anchorRefs"=>(i==0?[["a",0]]:[])});
    }
    var state=new NavigationState();
    if (!state.accept(s,0) || state.scene()["paths"].size()!=32) { return false; }
    s["paths"][0]["points"][0][0]=777;
    if (state.scene()["paths"][0]["points"][0][0]!=0) { return false; }
    s["paths"][0]["points"][0][0]=0;
    var memory=System.getSystemStats();
    System.println("JUNCTION_CAPACITY points=512 used="+memory.usedMemory+" free="+memory.freeMemory);
    s["paths"][31]["points"].add([160,31]);
    return SceneDecoder.decode(s)==null;
}

(:test)
function layeredContextOwnsItsDrawingLevels(logger as Test.Logger) as Boolean {
    var s=testScene();s["geometryMode"]="layer_context";
    s["paths"][0]["layer"]=0;s["paths"][0]["segmentLayers"]=[0,1];
    var state=new NavigationState();
    if (!state.accept(s,0)) { return false; }
    s["paths"][0]["segmentLayers"][0]=9;
    return state.scene()["paths"][0]["segmentLayers"][0]==0;
}
(:test)
function incompleteOrLegacyLayerMetadataIsRejected(logger as Test.Logger) as Boolean {
    var s=testScene();s["paths"][0]["layer"]=0;
    if (SceneDecoder.decode(s)!=null) { return false; }
    s["geometryMode"]="layer_context";s["paths"][0]["segmentLayers"]=[0];
    if (SceneDecoder.decode(s)!=null) { return false; }
    s["paths"][0]["segmentLayers"]=[0,1.0];
    return SceneDecoder.decode(s)==null;
}

(:test) function nativeArrivalIgnoresOldFixButExpiresWithoutFreshSource(logger as Test.Logger) as Boolean {
    var scene=testScene();scene["state"]="arrived";scene["distanceM"]=0;scene["geometryMode"]="unavailable";scene["anchors"]=[];scene["paths"]=[];
    scene["fixAgeMs"]=60000;scene["progressAgeMs"]=60000;scene["speedDmps"]=0;
    var state=new NavigationState();
    if(!state.accept(scene,0) || !state.status(1000).equals("arrived") || !state.status(3001).equals("stale_transport")) {return false;}
    scene["seq"]+=1;scene["sourceAgeMs"]=5001;
    return state.accept(scene,4000) && state.status(4000).equals("stale_source");
}
(:test) function cancelAndNewNavigationAreNotArrival(logger as Test.Logger) as Boolean {
    var state=new NavigationState(),scene=testScene();scene["state"]="idle";scene["geometryMode"]="unavailable";scene["anchors"]=[];scene["paths"]=[];
    if(!state.accept(scene,0) || !state.status(0).equals("idle")) {return false;}
    var next=testScene();next["generation"]+=1;return state.accept(next,10) && state.status(10).equals("active");
}
(:test) function destinationMustBeTheSelectedEndpointAndIsOwned(logger as Test.Logger) as Boolean {
    var scene=testScene(),points=scene["paths"][0]["points"],end=points[points.size()-1];scene["destination"]=[end[0],end[1]];
    var decoded=SceneDecoder.decode(scene);if(decoded==null) {return false;}
    scene["destination"][0]+=1;
    return decoded["destination"][0]==end[0] && SceneDecoder.decode(scene)==null;
}

(:test)
function ownedCompactSceneStillValidatesAndRejectsStaleUpdates(logger as Test.Logger) as Boolean {
    var state=new NavigationState(),s=testScene();
    if(!state.acceptOwned(s,100) || state.scene()["distanceM"]!=100) { return false; }
    var stale=testScene();stale["distanceM"]=9;
    if(state.acceptOwned(stale,200) || state.scene()["distanceM"]!=100) { return false; }
    var bad=testScene();bad["seq"]=2;bad["paths"][0]["points"][0]=[3000,3000];
    if(state.acceptOwned(bad,300) || state.scene()["distanceM"]!=100) { return false; }
    var newer=testScene();newer["seq"]=2;newer["distanceM"]=55;
    return state.acceptOwned(newer,400) && state.scene()["distanceM"]==55;
}
