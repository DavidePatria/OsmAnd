package net.osmand.junction.bridge

import java.io.ByteArrayOutputStream

/** Lossless SDK-boundary encoding. The logical envelope/scene validators stay unchanged.
 * SDK 2.4.0 tethered sends sleep floor(bytes/600) seconds: nested point arrays were
 * larger than our 3-second deadline. Version, bounds and coordinates are preserved.
 */
object CompactWire {
    val words = listOf("active","idle","recalculating","unavailable","map_context","layer_context",
        "routing_branches","route_only","selected","branch","context",
        "motorcycle road context; intersections do not imply connectivity","motorcycle road context with level ordering") +
        (0..3).map { "j$it" } + (1..40).map { "c$it" } + listOf("arrived")
    fun encode(reply: Map<String,Any>): ByteArray {
        require(reply["version"]==1 && reply["kind"] in listOf("junction_snapshot","junction_unavailable"))
        val w=Writer();w.u(74);w.u(67);w.u(2)
        val unavailable=reply["kind"]=="junction_unavailable";w.u(if(unavailable)1 else 0)
        w.text(reply["epoch"] as String);w.u(reply["requestId"] as Int)
        if(unavailable)w.text(reply["reason"] as String) else {
            val s=reply["scene"] as Map<*,*>;SnapshotCodec.validate(s)
            for(k in listOf("session"))w.text(s[k] as String)
            for(k in listOf("generation","seq"))w.u(s[k] as Int)
            for(k in listOf("state","geometryMode","reason","roadName","maneuver"))w.text(s[k] as String)
            for(k in listOf("distanceM","sourceAgeMs","fixAgeMs","radiusDm"))w.u(s[k] as Int)
            w.u(if(s.containsKey("progressAgeMs"))1 else 0)
            if(s.containsKey("progressAgeMs")) {w.u(s["progressAgeMs"] as Int);w.u(s["speedDmps"] as Int)}
            val anchors=s["anchors"] as List<*>;w.u(anchors.size)
            anchors.forEach { a -> val v=a as Map<*,*>;w.text(v["id"] as String);w.u(v["routeIndex"] as Int);w.point(v["point"] as List<*>) }
            val paths=s["paths"] as List<*>;w.u(paths.size)
            paths.forEach { p ->
                val v=p as Map<*,*>;w.text(v["id"] as String);w.text(v["role"] as String)
                val points=v["points"] as List<*>;w.u(points.size);var x=0;var y=0
                points.forEach { item -> val xy=item as List<*>;val nx=xy[0] as Int;val ny=xy[1] as Int;w.s(nx-x);w.s(ny-y);x=nx;y=ny }
                val refs=v["anchorRefs"] as List<*>;w.u(refs.size)
                refs.forEach { r -> val ref=r as List<*>;w.u(anchors.indexOfFirst { (it as Map<*,*>)["id"]==ref[0] });w.u(ref[1] as Int) }
                if(s["geometryMode"]=="layer_context") {
                    w.s(v["layer"] as Int)
                    if(v["role"]=="selected") (v["segmentLayers"] as List<*>).forEach { w.s(it as Int) }
                }
            }
            w.u(if(s.containsKey("destination"))1 else 0)
            if(s.containsKey("destination"))w.point(s["destination"] as List<*>)
        }
        return w.bytes.toByteArray().also { require(it.size<=8192) }
    }
    private class Writer {
        val bytes=ByteArrayOutputStream()
        fun u(input:Int) { require(input in 0..2_000_000);var n=input;while(n>=128) {bytes.write((n and 127) or 128);n=n ushr 7};bytes.write(n) }
        fun s(n:Int)=u(if(n<0)-2*n-1 else 2*n)
        fun text(value:String) {
            require(Charsets.UTF_8.newEncoder().canEncode(value)) { "invalid Unicode" }
            val token=words.indexOf(value)+1;u(token)
            if(token==0) { val data=value.toByteArray(Charsets.UTF_8);require(data.size<=320);u(data.size);bytes.write(data) }
        }
        fun point(xy:List<*>) {s(xy[0] as Int);s(xy[1] as Int)}
    }
}
