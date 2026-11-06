import Toybox.Lang;
import Toybox.Test;

function replyFor(request as Dictionary,scene as Dictionary) as Dictionary {
    return {"version"=>1,"kind"=>"junction_snapshot","epoch"=>request["epoch"],"requestId"=>request["requestId"],"scene"=>scene};
}
(:test)
function requestSlotDeadlineAndSupersededReply(logger as Test.Logger) as Boolean {
    var gate=new NavigationRequestGate(),state=new NavigationState();gate.reset("epoch");
    var first=gate.begin(0);
    if (gate.begin(100)!=null || gate.accept(replyFor(first,testScene()),3000,state)) { return false; }
    var second=gate.begin(3000);
    return second!=null && !gate.accept(replyFor(first,testScene()),3001,state) && gate.accept(replyFor(second,testScene()),3010,state);
}
(:test)
function reconnectEpochCannotRestorePreviousReply(logger as Test.Logger) as Boolean {
    var gate=new NavigationRequestGate(),state=new NavigationState();gate.reset("old");var old=gate.begin(0);
    gate.reset("new");var current=gate.begin(100);
    return !gate.accept(replyFor(old,testScene()),101,state) && gate.accept(replyFor(current,testScene()),102,state);
}
(:test)
function malformedReplyDoesNotConsumeRequestOrRefreshState(logger as Test.Logger) as Boolean {
    var gate=new NavigationRequestGate(),state=new NavigationState();gate.reset("epoch");var request=gate.begin(0);
    var bad=testScene();bad["version"]=2;
    if (gate.accept(replyFor(request,bad),50,state) || state.scene()!=null) { return false; }
    var wrongHeader=replyFor(request,testScene());wrongHeader["version"]=1.0;
    if (gate.accept(wrongHeader,60,state)) { return false; }
    return gate.accept(replyFor(request,testScene()),100,state) && !gate.accept(replyFor(request,testScene()),101,state);
}
(:test)
function roundTripAddsConservativeSourceAndFixAge(logger as Test.Logger) as Boolean {
    var gate=new NavigationRequestGate(),state=new NavigationState();gate.reset("epoch");var request=gate.begin(0);
    var scene=testScene();scene["fixAgeMs"]=4900;
    return gate.accept(replyFor(request,scene),200,state) && state.status(200).equals("stale_source") && state.scene()["fixAgeMs"]==5100;
}
(:test)
function invalidationKeepsOldGenerationRejection(logger as Test.Logger) as Boolean {
    var state=new NavigationState(),scene=testScene();scene["generation"]=5;state.accept(scene,0);state.invalidate();
    return state.scene()==null && !state.accept(testScene(),100);
}
(:test)
function unavailableReplyClearsGeometryWithoutResettingSourceOrder(logger as Test.Logger) as Boolean {
    var gate=new NavigationRequestGate(),state=new NavigationState();gate.reset("epoch");
    var first=gate.begin(0);gate.accept(replyFor(first,testScene()),10,state);
    var next=gate.begin(1000);
    var unavailable={"version"=>1,"kind"=>"junction_unavailable","epoch"=>next["epoch"],"requestId"=>next["requestId"],"reason"=>"source_busy"};
    if (!gate.accept(unavailable,1100,state) || state.scene()!=null) { return false; }
    var third=gate.begin(2000);
    return !gate.accept(replyFor(third,testScene()),2010,state);
}
