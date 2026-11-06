import Toybox.Lang;
import Toybox.StringUtil;

//! Lossless SDK transport adapter; decoded replies still pass the original gates.
module CompactWire {
    function words() as Array<String> {
        var values=["active","idle","recalculating","unavailable","map_context","layer_context","routing_branches","route_only","selected","branch","context","motorcycle road context; intersections do not imply connectivity","motorcycle road context with level ordering"];
        for(var i=0;i<4;i+=1) {values.add("j"+i);}
        for(var i=1;i<=40;i+=1) {values.add("c"+i);}
        return values;
    }
    function decode(value as Object?) as Object? {
        if (!(value instanceof ByteArray)) {return value;}
        if (value.size()>8192) {return null;}
        try {return new CompactReader(value).reply();} catch(error) {return null;}
    }
}
class CompactReader {
    private var _data as ByteArray;
    private var _at as Number=0;
    private var _words as Array<String>;
    function initialize(data as ByteArray) {_data=data;_words=CompactWire.words();}
    private function fail() as Void {throw new Lang.InvalidValueException("compact wire");}
    private function u() as Number {
        var n=0,shift=0;
        for(var i=0;i<3;i+=1) {
            if(_at>=_data.size()) {fail();}
            var b=_data[_at];_at+=1;n=n|((b&127)<<shift);
            if(b<128) {if((i>0 && b==0) || n>2000000) {fail();} return n;}
            shift+=7;
        }
        fail();return 0;
    }
    private function s() as Number {var n=u();return (n&1)==0?n/2:-(n+1)/2;}
    private function count(limit as Number) as Number {var n=u();if(n>limit) {fail();} return n;}
    private function text() as String {
        var token=count(_words.size());if(token>0) {return _words[token-1];}
        var size=count(320);if(_at+size>_data.size()) {fail();}
        var bytes=_data.slice(_at,_at+size);_at+=size;
        return StringUtil.convertEncodedString(bytes,{:fromRepresentation=>StringUtil.REPRESENTATION_BYTE_ARRAY,:toRepresentation=>StringUtil.REPRESENTATION_STRING_PLAIN_TEXT,:encoding=>StringUtil.CHAR_ENCODING_UTF8}) as String;
    }
    function reply() as Dictionary? {
        if(u()!=74 || u()!=67 || u()!=1) {return null;}
        var kind=count(1),epoch=text(),id=u();
        var result={"version"=>1,"kind"=>kind==0?"junction_snapshot":"junction_unavailable","epoch"=>epoch,"requestId"=>id};
        if(kind==1) {result["reason"]=text();} else {result["scene"]=scene();}
        if(_at!=_data.size()) {return null;}
        return result;
    }
    private function scene() as Dictionary {
        var value={"version"=>1,"session"=>text(),"generation"=>u(),"seq"=>u()};
        var keys=["state","geometryMode","reason","roadName","maneuver"];
        for(var i=0;i<keys.size();i+=1) {value[keys[i]]=text();}
        keys=["distanceM","sourceAgeMs","fixAgeMs","radiusDm"];
        for(var i=0;i<keys.size();i+=1) {value[keys[i]]=u();}
        if(count(1)==1) {value["progressAgeMs"]=u();value["speedDmps"]=u();}
        var anchors=[],n=count(4);
        for(var i=0;i<n;i+=1) {anchors.add({"id"=>text(),"routeIndex"=>u(),"point"=>[s(),s()]});}
        var paths=[],total=0;n=count(40);
        for(var i=0;i<n;i+=1) {
            var p={"id"=>text(),"role"=>text()},size=count(48),points=[],x=0,y=0;
            total+=size;if(size<2 || total>512) {fail();}
            for(var j=0;j<size;j+=1) {x+=s();y+=s();points.add([x,y]);}
            var refs=[],nr=count(4);
            for(var j=0;j<nr;j+=1) {var a=u(),idx=u();if(a>=anchors.size()) {fail();} refs.add([anchors[a]["id"],idx]);}
            p["points"]=points;p["anchorRefs"]=refs;
            if("layer_context".equals(value["geometryMode"])) {
                p["layer"]=s();
                if("selected".equals(p["role"])) {var levels=[];for(var j=1;j<size;j+=1) {levels.add(s());} p["segmentLayers"]=levels;}
            }
            paths.add(p);
        }
        value["anchors"]=anchors;value["paths"]=paths;return value;
    }
}
