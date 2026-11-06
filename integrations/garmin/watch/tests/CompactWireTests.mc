import Toybox.Lang;
import Toybox.StringUtil;
import Toybox.Test;

//! Public golden vectors shared with independent Python and Kotlin/SDK tests.
function compactBytes(hex as String) as ByteArray { return StringUtil.convertEncodedString(hex,{:fromRepresentation=>StringUtil.REPRESENTATION_STRING_HEX,:toRepresentation=>StringUtil.REPRESENTATION_BYTE_ARRAY}) as ByteArray; }
function compactEqual(a as Object?,b as Object?) as Boolean {
 if(a instanceof Dictionary && b instanceof Dictionary) {if(a.size()!=b.size()) {return false;} var keys=a.keys();for(var i=0;i<keys.size();i+=1) {if(!b.hasKey(keys[i]) || !compactEqual(a[keys[i]],b[keys[i]])) {return false;}} return true;}
 if(a instanceof Array && b instanceof Array) {if(a.size()!=b.size()) {return false;} for(var i=0;i<a.size();i+=1) {if(!compactEqual(a[i],b[i])) {return false;}} return true;}
 if(a instanceof String && b instanceof String) {return a.equals(b);} return a==b;
}
function compactGolden0() as ByteArray {return compactBytes("4a430200000c636f6d706163742d746573740100177265706c61792d3061353863663164623463626563313501010107001b726f7574696e672064617461206d6179206f6d697420726f61647300165669612064656c6ce28099556e6974c3a020f09f8f8d000454534c4c780000d00f00010edb010000020909129202e915bd03c6066d880225d2011ca201f001be0138560394083d86015d68b90160af049205e7028a02d7014ae90234910316f9061d9d012a010007000262300a0200004dce0401000000");}
(:test) function compactLosslessGolden0(logger as Test.Logger) as Boolean {var actual=CompactWire.decode(compactGolden0());return compactEqual(actual,{"version"=>1,"kind"=>"junction_snapshot","epoch"=>"compact-test","requestId"=>1,"scene"=>{"version"=>1,"session"=>"replay-0a58cf1db4cbec15","generation"=>1,"seq"=>1,"state"=>"active","geometryMode"=>"routing_branches","reason"=>"routing data may omit roads","distanceM"=>120,"roadName"=>"Via dell\u2019Unit\u00e0 \ud83c\udfcd","maneuver"=>"TSLL","radiusDm"=>2000,"sourceAgeMs"=>0,"fixAgeMs"=>0,"anchors"=>[{"id"=>"j0","point"=>[0,0],"routeIndex"=>219}],"paths"=>[{"id"=>"selected","role"=>"selected","points"=>[[137,-1397],[-86,-978],[-141,-846],[-160,-741],[-146,-660],[-26,-565],[2,-522],[0,0],[-31,67],[-78,119],[-171,167],[-451,496],[-631,629],[-739,666],[-920,692],[-1121,703],[-1566,688],[-1645,709]],"anchorRefs"=>[["j0",7]]},{"id"=>"b0","role"=>"branch","points"=>[[0,0],[-39,295]],"anchorRefs"=>[["j0",0]]}]}}) && SceneDecoder.decode(actual["scene"])!=null;}
function compactGolden1() as ByteArray {return compactBytes("4a430200000c636f6d706163742d746573740100177265706c61792d3061353863663164623463626563313501010106001b726f7574696e672064617461206d6179206f6d697420726f61647300165669612064656c6ce28099556e6974c3a020f09f8f8d000454534c4c780000d00f00010edb010000020909129202e915bd03c6066d880225d2011ca201f001be0138560394083d86015d68b90160af049205e7028a02d7014ae90234910316f9061d9d012a010007010101010101010101010101010101010101000262300a0200004dce040100000201d9198a0b");}
(:test) function compactLosslessGolden1(logger as Test.Logger) as Boolean {var actual=CompactWire.decode(compactGolden1());return compactEqual(actual,{"version"=>1,"kind"=>"junction_snapshot","epoch"=>"compact-test","requestId"=>1,"scene"=>{"version"=>1,"session"=>"replay-0a58cf1db4cbec15","generation"=>1,"seq"=>1,"state"=>"active","geometryMode"=>"layer_context","reason"=>"routing data may omit roads","distanceM"=>120,"roadName"=>"Via dell\u2019Unit\u00e0 \ud83c\udfcd","maneuver"=>"TSLL","radiusDm"=>2000,"sourceAgeMs"=>0,"fixAgeMs"=>0,"anchors"=>[{"id"=>"j0","point"=>[0,0],"routeIndex"=>219}],"paths"=>[{"id"=>"selected","role"=>"selected","points"=>[[137,-1397],[-86,-978],[-141,-846],[-160,-741],[-146,-660],[-26,-565],[2,-522],[0,0],[-31,67],[-78,119],[-171,167],[-451,496],[-631,629],[-739,666],[-920,692],[-1121,703],[-1566,688],[-1645,709]],"anchorRefs"=>[["j0",7]],"layer"=>-1,"segmentLayers"=>[-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1]},{"id"=>"b0","role"=>"branch","points"=>[[0,0],[-39,295]],"anchorRefs"=>[["j0",0]],"layer"=>1}],"destination"=>[-1645,709]}}) && SceneDecoder.decode(actual["scene"])!=null;}
(:test) function compactRejectsMalformedAndKeepsDeadline(logger as Test.Logger) as Boolean {
 var bytes=compactGolden0();for(var i=0;i<bytes.size();i+=1) {if(CompactWire.decode(bytes.slice(0,i))!=null) {return false;}}
 bytes.add(0);if(CompactWire.decode(bytes)!=null) {return false;} bytes=compactGolden0();bytes[2]=99;if(CompactWire.decode(bytes)!=null) {return false;}
 var gate=new NavigationRequestGate(),state=new NavigationState();gate.reset("compact-test");gate.begin(0);var reply=CompactWire.decode(compactGolden0());reply["requestId"]=1;return !gate.accept(reply,3000,state) && state.scene()==null;
}

(:test) function compactVersionOneStillDecodes(logger as Test.Logger) as Boolean {
    var current=compactGolden0(),old=current.slice(0,current.size()-1);old[2]=1;
    return compactEqual(CompactWire.decode(current),CompactWire.decode(old));
}
