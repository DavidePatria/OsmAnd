package net.osmand.shared.junction

import java.io.File
import kotlinx.serialization.json.*
import kotlin.test.*

/** Independently captured native decisions and OBF context, shared with the Java regressions. */
class JunctionRecordedTest {
    private fun recorded(name: String): JunctionGeometry.Scene {
        val relative = "OsmAnd-java/src/test/resources/junction/$name.json"
        val file = listOf(File("../$relative"), File(relative)).firstOrNull { it.isFile }
        assertNotNull(file, "Run from the shared module or repository root; native fixture must be present")
        val raw = Json.parseToJsonElement(file.readText()).jsonObject
        assertEquals("actual_osmand_capture", raw.getValue("provenance").jsonObject.getValue("kind").jsonPrimitive.content)
        val route = raw.getValue("route").jsonObject
        fun points(array: JsonArray) = array.map {
            val p = it.jsonObject
            JunctionGeometry.Geo(p.getValue("lat").jsonPrimitive.double, p.getValue("lon").jsonPrimitive.double,
                p["node"]?.jsonPrimitive?.contentOrNull)
        }
        val decisions = route.getValue("decisions").jsonArray.map {
            val d = it.jsonObject
            JunctionGeometry.Decision(d.getValue("routeIndex").jsonPrimitive.int, d.getValue("turn").jsonPrimitive.content,
                d.getValue("roadName").jsonPrimitive.content, d.getValue("roundaboutExit").jsonPrimitive.int)
        }
        val context = raw.getValue("context").jsonObject
        val roads = context.getValue("roads").jsonArray.map {
            val r = it.jsonObject
            JunctionGeometry.Road(points(r.getValue("points").jsonArray),
                r.getValue("tags").jsonObject.mapValues { entry -> entry.value.jsonPrimitive.contentOrNull })
        }
        val scene = JunctionGeometry.compile(
            JunctionGeometry.Route(points(route.getValue("points").jsonArray), decisions, route.getValue("indexBase").jsonPrimitive.int, -1),
            JunctionGeometry.Context(roads, context.getValue("available").jsonPrimitive.boolean, context.getValue("truncated").jsonPrimitive.boolean), false)
        assertEquals("map_context", scene.mode)
        assertTrue(scene.paths.size in 2..40)
        assertTrue(scene.paths.sumOf { it.points.size } <= 512)
        for (path in scene.paths) {
            assertTrue(path.points.size in 2..48)
            assertTrue(path.points.all { it.x * it.x + it.y * it.y <= scene.radius * scene.radius })
        }
        return scene
    }

    @Test fun nativeCloseRightTurnsKeepBothOriginalAnchors() {
        val scene = recorded("public-double-turn")
        assertEquals(listOf(75, 82), scene.anchors.map { it.index })
        val selected = scene.paths.first()
        assertTrue(selected.links[0] < selected.links[1])
        assertTrue(selected.points[selected.links[0] + 1].x > scene.anchors[0].point.x)
        val i = selected.links[1]
        val a = selected.points[i - 1]; val b = selected.points[i]; val c = selected.points[i + 1]
        assertTrue((b.x - a.x) * (c.y - b.y) - (b.y - a.y) * (c.x - b.x) < 0)
    }

    @Test fun nativeForkKeepsSelectedLeftArmAndGrayAlternatives() {
        val scene = recorded("public-fork")
        assertEquals(219, scene.anchors.first().index)
        assertTrue(scene.paths.first().points.last().x < scene.anchors.first().point.x)
        assertTrue(scene.paths.drop(1).all { it.role == "context" })
    }

    @Test fun accessOverridesAndOrdinaryServiceRoadsAreRetained() {
        assertTrue(JunctionGeometry.relevant(mapOf("highway" to "service"), false))
        assertTrue(JunctionGeometry.relevant(mapOf("highway" to "track"), false))
        assertTrue(JunctionGeometry.relevant(mapOf("highway" to "path", "motorcycle" to "yes", "access" to "no"), false))
        assertFalse(JunctionGeometry.relevant(mapOf("highway" to "residential", "motorcycle" to "no", "access" to "yes"), false))
        assertFalse(JunctionGeometry.relevant(mapOf("highway" to "footway"), false))
    }

    @Test fun mappedLevelsKeepBridgeTunnelAndPassageDistinctions() {
        assertEquals(1, JunctionGeometry.level(mapOf("bridge" to "yes")))
        assertEquals(-1, JunctionGeometry.level(mapOf("tunnel" to "yes")))
        assertEquals(0, JunctionGeometry.level(mapOf("tunnel" to "building_passage")))
        assertEquals(-2, JunctionGeometry.level(mapOf("layer" to "-2", "bridge" to "yes")))
        assertFailsWith<IllegalArgumentException> { JunctionGeometry.level(mapOf("layer" to "unknown")) }
    }
}
