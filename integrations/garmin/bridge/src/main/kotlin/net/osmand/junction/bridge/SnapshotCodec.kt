package net.osmand.junction.bridge

import org.json.JSONArray
import org.json.JSONObject

/** Decode an API wrapper without fabricating freshness or forwarding unknown SDK values. */
object SnapshotCodec {
    private val required = listOf("version","session","generation","seq","state","geometryMode","reason","distanceM","roadName","maneuver","radiusDm","sourceAgeMs","fixAgeMs","anchors","paths")
    fun decode(json: String, wrapperVersion: Int, capturedAt: Long, exportAgeMs: Int, now: Long): Map<String, Any> {
        require(wrapperVersion == 1 && capturedAt >= 0 && now >= capturedAt && exportAgeMs in 0..60_000) { "unsupported or invalid API wrapper" }
        require(json.toByteArray(Charsets.UTF_8).size <= 65_536) { "API snapshot exceeds parse bound" }
        val raw = convert(JSONObject(json),0) as Map<*, *>
        validate(raw)
        val result = linkedMapOf<String, Any>()
        required.forEach { result[it] = checkNotNull(raw[it]) }
        val age = maxOf(exportAgeMs.toLong(),now-capturedAt).coerceAtMost(60_000).toInt()
        for (key in listOf("sourceAgeMs","fixAgeMs","progressAgeMs")) {
            if (raw.containsKey(key)) result[key] = ((raw[key] as Int).toLong()+age).coerceAtMost(60_000).toInt()
        }
        if (raw.containsKey("speedDmps")) result["speedDmps"] = raw["speedDmps"] as Int
        // Raw maps are freshly owned; normalize away future/unknown fields before SDK serialization.
        result["anchors"] = (raw["anchors"] as List<*>).map { a ->
            val item=a as Map<*, *>;mapOf("id" to item["id"]!!,"point" to item["point"]!!,"routeIndex" to item["routeIndex"]!!)
        }
        result["paths"] = (raw["paths"] as List<*>).map { p ->
            val item=p as Map<*, *>;linkedMapOf("id" to item["id"]!!,"role" to item["role"]!!,"points" to item["points"]!!,"anchorRefs" to item["anchorRefs"]!!).apply {
                if (raw["geometryMode"]=="layer_context") {
                    put("layer",item["layer"]!!)
                    if (item["role"]=="selected") put("segmentLayers",item["segmentLayers"]!!)
                }
            }
        }
        return result
    }
    private fun convert(value: Any?, depth: Int): Any? {
        require(depth <= 9) { "snapshot nesting bound" }
        return when(value) {
            is JSONObject -> {
                require(value.length() <= 32);val result=linkedMapOf<String,Any?>()
                value.keys().forEach { key -> result[key]=convert(value.get(key),depth+1) };result
            }
            is JSONArray -> { require(value.length()<=512);(0 until value.length()).map { convert(value.get(it),depth+1) } }
            is Long -> if (value in Int.MIN_VALUE..Int.MAX_VALUE) value.toInt() else value
            JSONObject.NULL -> null
            else -> value
        }
    }
    private fun number(value: Any?, low: Int, high: Int) = value is Int && value in low..high
    private fun text(value: Any?, low: Int=0, high: Int=80) = value is String && value.length in low..high
    private fun point(value: Any?, radius: Int): Boolean {
        val p=value as? List<*> ?: return false
        if (p.size!=2 || !number(p[0],-radius,radius) || !number(p[1],-radius,radius)) return false
        val x=p[0] as Int;val y=p[1] as Int;return x*x+y*y<=radius*radius
    }
    internal fun validate(raw: Map<*, *>) {
        require(required.all { raw.containsKey(it) })
        require(raw["version"]==1 && text(raw["session"],1,64) && number(raw["generation"],0,1_000_000) && number(raw["seq"],0,1_000_000))
        require(raw["state"] in listOf("active","idle","recalculating","unavailable"))
        val mode=raw["geometryMode"];require(mode in listOf("map_context","layer_context","routing_branches","route_only","unavailable"))
        require(listOf("reason","roadName","maneuver").all { text(raw[it]) })
        require(number(raw["distanceM"],0,1_000_000) && number(raw["radiusDm"],1,2000))
        require(listOf("sourceAgeMs","fixAgeMs").all { number(raw[it],0,60_000) })
        if (raw.containsKey("progressAgeMs") || raw.containsKey("speedDmps")) require(number(raw["progressAgeMs"],0,60_000) && number(raw["speedDmps"],0,700))
        val radius=raw["radiusDm"] as Int;val context=mode in listOf("map_context","layer_context")
        val anchors=raw["anchors"] as? List<*> ?: error("anchors")
        val paths=raw["paths"] as? List<*> ?: error("paths")
        require(anchors.size<=4 && paths.size<=(if(mode=="layer_context")40 else if(context)32 else 8))
        val byId=mutableMapOf<String,List<*>>()
        anchors.forEach { a ->
            val item=a as? Map<*, *> ?: error("anchor")
            require(text(item["id"],1,32) && point(item["point"],radius) && number(item["routeIndex"],0,1_000_000))
            val id=item["id"] as String;require(!byId.containsKey(id));byId[id]=item["point"] as List<*>
        }
        val ids=mutableSetOf<String>();var total=0;var selected=0
        paths.forEach { p ->
            val item=p as? Map<*, *> ?: error("path")
            require(text(item["id"],1,if(mode=="layer_context")24 else 32) && ids.add(item["id"] as String))
            val role=item["role"];require(role in listOf("selected","branch") || (context && role=="context"))
            if(role=="selected")selected++
            require(mode!="route_only" || role=="selected")
            val points=item["points"] as? List<*> ?: error("points")
            val links=item["anchorRefs"] as? List<*> ?: error("links")
            require(points.size in 2..(if(context)48 else 24) && points.all { point(it,radius) })
            if (mode=="layer_context") {
                require(number(item["layer"],-10,10))
                if (role=="selected") {
                    val layers=item["segmentLayers"] as? List<*> ?: error("segment layers")
                    require(layers.size==points.size-1 && layers.all { number(it,-10,10) })
                } else require(!item.containsKey("segmentLayers"))
            } else require(!item.containsKey("layer") && !item.containsKey("segmentLayers"))
            total+=points.size;require(total<=(if(context)512 else 96))
            require(links.size<=4 && if(role=="context") links.isEmpty() else links.isNotEmpty())
            val linked=mutableSetOf<String>()
            links.forEach { link ->
                val ref=link as? List<*> ?: error("ref")
                require(ref.size==2 && ref[0] is String && byId.containsKey(ref[0]) && number(ref[1],0,points.size-1))
                require(linked.add(ref[0] as String) && points[ref[1] as Int]==byId[ref[0]])
            }
            require(role!="selected" || linked==byId.keys)
        }
        if(raw["state"]=="active" && mode!="unavailable") require(selected==1 && anchors.isNotEmpty())
        else require(paths.isEmpty() && anchors.isEmpty())
    }
}
