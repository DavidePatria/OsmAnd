package net.osmand.shared.junction

import kotlinx.serialization.json.*
import net.osmand.shared.binary.BinaryMapIndexReader
import net.osmand.shared.binary.ResultMatcher
import net.osmand.shared.binary.SearchRequest
import net.osmand.shared.routing.RouteDataObject
import net.osmand.shared.util.KMapUtils
import kotlin.math.*
import kotlin.time.TimeSource

/** JSON boundary keeps Apple callers independent of Kotlin collection/number bridging. */
class JunctionPort {
    fun layer(road: RouteDataObject): Int = try {
        JunctionGeometry.level(listOf("layer", "bridge", "tunnel").associateWith { road.getValue(it) })
    } catch (_: Exception) { -99 }

    fun compile(inputJson: String, mapFiles: List<String>): String = try {
        require(inputJson.encodeToByteArray().size <= 2_000_000)
        val input = Json.parseToJsonElement(inputJson).jsonObject
        val rawPoints = input.getValue("points").jsonArray
        require(rawPoints.size in 2..10000)
        val points = rawPoints.map { raw ->
            val p = raw.jsonArray
            require(p.size == 4)
            JunctionGeometry.Geo(p[0].jsonPrimitive.double, p[1].jsonPrimitive.double,
                p[2].jsonPrimitive.contentOrNull, p[3].jsonPrimitive.int)
        }
        val rawDecisions = input.getValue("decisions").jsonArray
        require(rawDecisions.size in 1..2000)
        val decisions = rawDecisions.map { raw ->
            val d = raw.jsonArray
            require(d.size == 5)
            JunctionGeometry.Decision(d[0].jsonPrimitive.int, d[1].jsonPrimitive.content.take(80),
                d[2].jsonPrimitive.content.take(80), d[3].jsonPrimitive.int, d[4].jsonPrimitive.int)
        }
        val route = JunctionGeometry.Route(points, decisions, input.getValue("indexBase").jsonPrimitive.int,
            input.getValue("destinationIndex").jsonPrimitive.int)
        val center = points[decisions.first().index - route.base]
        encode(JunctionGeometry.compile(route, readRoads(mapFiles, center), input["profile"]?.jsonPrimitive?.content == "bicycle"), decisions.first())
    } catch (_: Exception) {
        buildJsonObject {
            put("geometryMode", "unavailable"); put("reason", "invalid or unavailable native geometry")
            put("roadName", ""); put("maneuver", ""); put("radiusDm", 800)
            put("anchors", JsonArray(emptyList())); put("paths", JsonArray(emptyList()))
        }.toString()
    }

    private fun readRoads(files: List<String>, center: JunctionGeometry.Geo): JunctionGeometry.Context {
        if (files.isEmpty()) return JunctionGeometry.Context(emptyList(), false)
        if (files.size > 32) return JunctionGeometry.Context(emptyList(), false, true)
        val dy = 200.0 / 111000
        val dx = dy / cos(center.lat * PI / 180)
        if (center.lon - dx < -180 || center.lon + dx > 180) return JunctionGeometry.Context(emptyList(), false)
        val left = KMapUtils.get31TileNumberX(center.lon - dx)
        val right = KMapUtils.get31TileNumberX(center.lon + dx)
        val top = KMapUtils.get31TileNumberY(center.lat + dy)
        val bottom = KMapUtils.get31TileNumberY(center.lat - dy)
        val roads = mutableListOf<JunctionGeometry.Road>()
        val identities = mutableSetOf<String>()
        var total = 0
        var truncated = false
        val started = TimeSource.Monotonic.markNow()
        val matcher = object : ResultMatcher<RouteDataObject> {
            override fun isCancelled(): Boolean = truncated || started.elapsedNow().inWholeMilliseconds > 2000
            override fun publish(obj: RouteDataObject): Boolean {
                if (isCancelled()) { truncated = true; return false }
                if (obj.getHighway() == null || obj.getPointsLength() < 2) return false
                val intersects = (1 until obj.getPointsLength()).any { i ->
                    max(obj.getPoint31XTile(i - 1), obj.getPoint31XTile(i)) >= left &&
                    min(obj.getPoint31XTile(i - 1), obj.getPoint31XTile(i)) <= right &&
                    max(obj.getPoint31YTile(i - 1), obj.getPoint31YTile(i)) >= top &&
                    min(obj.getPoint31YTile(i - 1), obj.getPoint31YTile(i)) <= bottom
                }
                if (!intersects) return false
                if (roads.size >= 512 || total + obj.getPointsLength() > 50000) { truncated = true; return false }
                val identity = buildString {
                    append(obj.getId())
                    for (i in 0 until obj.getPointsLength()) append(":${obj.getPoint31XTile(i)},${obj.getPoint31YTile(i)}")
                }
                if (!identities.add(identity)) return false
                val tags = (listOf("highway", "layer", "bridge", "tunnel", "access", "vehicle", "motor_vehicle", "motorcycle", "bicycle", "junction"))
                    .associateWith { obj.getValue(it) }
                val points = (0 until obj.getPointsLength()).map { i ->
                    val x = obj.getPoint31XTile(i); val y = obj.getPoint31YTile(i)
                    JunctionGeometry.Geo(KMapUtils.get31LatitudeY(y), KMapUtils.get31LongitudeX(x), "$x:$y")
                }
                total += points.size
                roads.add(JunctionGeometry.Road(points, tags))
                return false
            }
        }
        for (file in files) {
            if (matcher.isCancelled()) { truncated = true; break }
            val reader = BinaryMapIndexReader(file)
            try {
                for (region in reader.getRoutingIndexes()) {
                    val request = SearchRequest.buildSearchRouteRequest(left, right, top, bottom)
                    reader.loadRouteIndexData(reader.searchRouteIndexTree(request, region.getSubregions()).toMutableList(), matcher)
                    if (matcher.isCancelled()) { truncated = true; break }
                }
            } finally { reader.close() }
        }
        return JunctionGeometry.Context(roads, true, truncated)
    }

    internal fun encode(scene: JunctionGeometry.Scene, decision: JunctionGeometry.Decision): String {
        fun pair(point: JunctionGeometry.Point) = JsonArray(listOf(JsonPrimitive(point.x), JsonPrimitive(point.y)))
        return buildJsonObject {
            put("geometryMode", scene.mode); put("reason", scene.reason.take(80)); put("radiusDm", scene.radius)
            put("roadName", decision.name.take(80)); put("maneuver", decision.turn.take(80)); put("roundaboutExit", decision.exit)
            putJsonArray("anchors") {
                for (a in scene.anchors) add(buildJsonObject { put("id", a.id); put("routeIndex", a.index); put("point", pair(a.point)) })
            }
            putJsonArray("paths") {
                for (p in scene.paths) add(buildJsonObject {
                    put("id", p.id); put("role", p.role)
                    put("points", JsonArray(p.points.map { pair(it) }))
                    put("anchorRefs", JsonArray(p.links.mapIndexed { i, link -> JsonArray(listOf(JsonPrimitive(scene.anchors[i].id), JsonPrimitive(link))) }))
                    if (scene.mode == "layer_context") {
                        put("layer", p.layer)
                        if (p.role == "selected") put("segmentLayers", JsonArray(p.levels.map { JsonPrimitive(it) }))
                    }
                })
            }
            scene.destination?.let { put("destination", pair(it)) }
        }.toString()
    }
}
