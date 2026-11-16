package net.osmand.shared.junction

import kotlin.math.*

/** Portable counterpart of OsmAnd-java's bounded diagram compiler. Never chooses a route. */
internal object JunctionGeometry {
    data class Geo(val lat: Double, val lon: Double, val node: String? = null, val layer: Int = 0) {
        init { require(lat.isFinite() && lon.isFinite() && abs(lat) <= 80 && abs(lon) <= 180 && layer in -10..10) }
    }
    data class Decision(val index: Int, val turn: String, val name: String, val exit: Int, val end: Int = -1)
    data class Route(val points: List<Geo>, val decisions: List<Decision>, val base: Int, val destination: Int)
    data class Road(val points: List<Geo>, val tags: Map<String, String?>)
    data class Context(val roads: List<Road>, val available: Boolean, val truncated: Boolean = false)
    data class Point(val x: Int, val y: Int)
    data class Anchor(val id: String, val index: Int, val point: Point)
    data class Path(val id: String, val role: String, val points: List<Point>,
                    val links: List<Int> = emptyList(), val layer: Int = 0, val levels: List<Int> = emptyList())
    data class Scene(val mode: String, val reason: String, val radius: Int = 800,
                     val anchors: List<Anchor> = emptyList(), val paths: List<Path> = emptyList(),
                     val destination: Point? = null)
    private data class XY(val x: Double, val y: Double) {
        fun between(other: XY, t: Double) = XY(x + (other.x - x) * t, y + (other.y - y) * t)
        fun norm() = hypot(x, y)
    }
    private const val EARTH = 6371000.0
    private const val RADIUS = 75.0
    private val allowed = setOf("yes", "permissive", "designated", "destination", "delivery", "customers",
        "private", "permit", "agricultural", "forestry", "discouraged")
    private val excluded = setOf("footway", "cycleway", "path", "pedestrian", "steps", "bridleway", "corridor", "platform")
    private val excludedBicycle = setOf("motorway", "motorway_link", "footway", "pedestrian", "steps", "bridleway", "corridor", "platform")

    fun relevant(tags: Map<String, String?>, bicycle: Boolean): Boolean {
        if (bicycle) {
            val value = tags["bicycle"]
            if (value in setOf("no", "dismount", "use_sidepath")) return false
            if (value in allowed) return true
            for (key in listOf("vehicle", "access")) {
                if (tags[key] == "no") return false
                if (tags[key] in allowed) break
            }
            return tags["highway"] !in excludedBicycle
        }
        for (key in listOf("motorcycle", "motor_vehicle", "vehicle", "access")) {
            val value = tags[key]
            if (value in setOf("no", "dismount", "use_sidepath")) return false
            if (value in allowed) return true
        }
        return tags["highway"] !in excluded
    }

    fun level(tags: Map<String, String?>): Int {
        tags["layer"]?.let { return it.trim().toInt().also { n -> require(n in -10..10) } }
        fun present(key: String) = tags[key] != null && tags[key] !in setOf("no", "false", "0")
        return if (present("bridge")) 1 else if (present("tunnel") && tags["tunnel"] != "building_passage") -1 else 0
    }

    private fun radians(degrees: Double) = degrees * PI / 180
    private fun delta(degrees: Double) = atan2(sin(radians(degrees)), cos(radians(degrees)))
    fun distance(a: Geo, b: Geo) = EARTH * hypot(delta(b.lon - a.lon) * cos(radians((a.lat + b.lat) / 2)), radians(b.lat - a.lat))

    private class Frame(val origin: Geo, approach: Geo) {
        private fun eastNorth(p: Geo) = XY(delta(p.lon - origin.lon) * EARTH * cos(radians(origin.lat)), radians(p.lat - origin.lat) * EARTH)
        private val a = eastNorth(approach)
        private val bearing = atan2(-a.x, -a.y)
        fun project(p: Geo): XY {
            val v = eastNorth(p)
            return XY(v.x * cos(bearing) - v.y * sin(bearing), v.x * sin(bearing) + v.y * cos(bearing))
        }
    }

    fun compile(route: Route, context: Context, bicycle: Boolean): Scene {
        require(route.points.size in 2..10000 && route.decisions.size in 1..2000 && route.base in 0..1000000)
        require(route.base + route.points.lastIndex <= 1000000 && route.destination in -1..1000000)
        require(route.destination == -1 || route.destination >= route.base + route.points.lastIndex)
        require(route.decisions.zipWithNext().all { it.first.index <= it.second.index })
        require(route.decisions.all { it.index - route.base in route.points.indices })
        val scene = geometry(route, context, bicycle)
        if (scene.paths.isEmpty() || route.destination != route.base + route.points.lastIndex) return scene
        val d = route.decisions.first()
        val anchor = d.index - route.base
        val remaining = (anchor + 1..route.points.lastIndex).sumOf { distance(route.points[it - 1], route.points[it]) }
        val exit = d.end - route.base
        val exitDistance = if (exit > anchor && exit in route.points.indices)
            (anchor + 1..exit).sumOf { distance(route.points[it - 1], route.points[it]) } else 0.0
        return if (remaining <= max(RADIUS, if (exitDistance > 0) exitDistance + 20 else RADIUS))
            scene.copy(destination = scene.paths.first().points.last()) else scene
    }

    private fun geometry(route: Route, context: Context, bicycle: Boolean): Scene {
        val d = route.decisions.first()
        val offset = d.index - route.base
        val cumulative = DoubleArray(route.points.size)
        for (i in offset + 1..route.points.lastIndex) cumulative[i] = cumulative[i - 1] + distance(route.points[i - 1], route.points[i])
        for (i in offset - 1 downTo 0) cumulative[i] = cumulative[i + 1] - distance(route.points[i], route.points[i + 1])
        val exit = d.end - route.base
        if (d.end >= 0 && (exit <= offset || exit !in route.points.indices)) return Scene("unavailable", "roundabout exit outside route window")
        val departure = if (exit > offset) max(RADIUS, cumulative[exit] + 20) else RADIUS
        var approach = max(0, offset - 1)
        while (approach > 0 && -cumulative[approach] < 30) approach--
        if (-cumulative[approach] < .1) return Scene("unavailable", "approach tangent unavailable")
        val frame = Frame(route.points[offset], route.points[approach])
        val indexes = mutableListOf(offset)
        for (decision in route.decisions.drop(1)) {
            val next = decision.index - route.base
            if (cumulative[next] > departure) break
            if (next > indexes.last()) {
                if (indexes.size == 4) return Scene("unavailable", "decision anchor capacity exceeded")
                indexes.add(next)
            }
        }
        var first = offset
        var last = offset
        while (first > 0 && -cumulative[first - 1] <= RADIUS) first--
        while (last < route.points.lastIndex && cumulative[last + 1] <= departure) last++
        val selected = mutableListOf<XY>()
        val prefix = if (first > 0) 1 else 0
        if (prefix == 1) selected.add(frame.project(route.points[first - 1]).between(frame.project(route.points[first]),
            (-RADIUS - cumulative[first - 1]) / (cumulative[first] - cumulative[first - 1])))
        for (i in first..last) selected.add(frame.project(route.points[i]))
        if (last < route.points.lastIndex) selected.add(frame.project(route.points[last]).between(frame.project(route.points[last + 1]),
            (departure - cumulative[last]) / (cumulative[last + 1] - cumulative[last])))
        val contextRadius = if (exit > offset) max(RADIUS, selected.maxOf { it.norm() }) else RADIUS
        if (contextRadius > 195) return Scene("unavailable", "roundabout exceeds display radius")
        val radius = ceil((contextRadius + 5) * 10).toInt()
        val fixed = mutableSetOf<Int>()
        if (exit > offset) fixed.add(exit - first + prefix)
        val selectedLevels = mutableListOf<Int>()
        if (prefix == 1) selectedLevels.add(route.points[first - 1].layer)
        for (i in first until last) selectedLevels.add(route.points[i].layer)
        if (last < route.points.lastIndex) selectedLevels.add(route.points[last].layer)
        for (i in 1 until selectedLevels.size) if (selectedLevels[i - 1] != selectedLevels[i]) fixed.add(i)
        val anchors = indexes.mapIndexed { i, k ->
            fixed.add(k - first + prefix)
            Anchor("j$i", k + route.base, quantize(frame.project(route.points[k]), radius))
        }
        val kept = simplify(selected, fixed)
        val links = indexes.map { k -> kept.count { it < k - first + prefix } }
        val levels = kept.dropLast(1).map { selectedLevels[it] }
        if (levels.isEmpty()) return Scene("unavailable", "selected-route capacity exceeded")
        val chosen = Path("selected", "selected", kept.map { quantize(selected[it], radius) }, links, levels.first(), levels)
        if (chosen.points.size !in 2..48) return Scene("unavailable", "selected-route capacity exceeded")
        fun limited(reason: String) = if (chosen.points.size > 24) Scene("unavailable", (reason + "; selected-route limit").take(80))
            else Scene("route_only", reason.take(80), radius, anchors, listOf(chosen))
        if (!context.available || context.truncated) return limited(if (context.truncated) "road context truncated" else "road context unavailable")
        val shared = mutableMapOf<String, Int>()
        context.roads.forEach { r -> r.points.forEach { p -> p.node?.let { shared[it] = (shared[it] ?: 0) + 1 } } }
        val paths = mutableListOf(chosen)
        var total = chosen.points.size
        var layered = levels.any { it != 0 }
        for (road in context.roads) {
            if (!relevant(road.tags, bicycle)) continue
            val raw = road.points.map { frame.project(it) }
            val critical = road.points.indices.filter { (shared[road.points[it].node] ?: 0) > 1 }.map { raw[it] }
            val layer = try { level(road.tags) } catch (_: IllegalArgumentException) { return limited("unsupported road layer metadata") }
            for (piece in clip(raw, contextRadius)) {
                val preserve = piece.indices.filter { i -> critical.any { it === piece[i] } }.toSet()
                val points = simplify(piece, preserve).map { quantize(piece[it], radius) }
                if (points.all { it == points.first() }) continue
                total += points.size
                if (points.size > 48) return limited("road vertex capacity exceeded: ${points.size}")
                if (paths.size >= 128 || total > 512) return limited("context capacity exceeded: ${paths.size} paths / $total points")
                paths.add(Path("c${paths.size}", "context", points, layer = layer))
                if (layer != 0) layered = true
            }
        }
        compact(paths)
        if (paths.size > 40) return limited("map context path capacity exceeded: ${paths.size}")
        val kind = if (bicycle) "bicycle" else "motorcycle"
        return if (paths.size == 1) limited("no local $kind roads available") else
            Scene(if (layered) "layer_context" else "map_context",
                if (layered) "$kind road context with level ordering" else "$kind road context; intersections do not imply connectivity",
                radius, anchors, paths)
    }

    private fun compact(paths: MutableList<Path>) {
        while (paths.size > 40) {
            val counts = mutableMapOf<Triple<Int, Int, Int>, Int>()
            fun key(path: Path, p: Point) = Triple(path.layer, p.x, p.y)
            paths.drop(1).forEach { p -> listOf(p.points.first(), p.points.last()).forEach { counts[key(p, it)] = (counts[key(p, it)] ?: 0) + 1 } }
            var changed = false
            search@ for (i in 1 until paths.size) for (j in i + 1 until paths.size) {
                val a = paths[i]; val b = paths[j]
                if (a.layer != b.layer || a.points.size + b.points.size - 1 > 48) continue
                for (ai in 0..1) for (bi in 0..1) {
                    val aa = if (ai == 0) a.points.first() else a.points.last()
                    val bb = if (bi == 0) b.points.first() else b.points.last()
                    if (aa != bb || counts[key(a, aa)] != 2) continue
                    val left = if (ai == 0) a.points.reversed() else a.points
                    val right = if (bi == 1) b.points.reversed() else b.points
                    paths[i] = a.copy(points = left + right.drop(1))
                    paths.removeAt(j); changed = true; break@search
                }
            }
            if (!changed) break
        }
    }

    private fun quantize(p: XY, radius: Int): Point {
        val point = Point(round(p.x * 10).toInt(), round(p.y * 10).toInt())
        require(point.x.toLong() * point.x + point.y.toLong() * point.y <= radius.toLong() * radius)
        return point
    }

    private fun simplify(points: List<XY>, fixed: Set<Int>): List<Int> {
        require(points.size >= 2 && fixed.all { it in points.indices })
        val keep = (fixed + 0 + points.lastIndex).toMutableSet()
        val stack = ArrayDeque<Pair<Int, Int>>()
        keep.sorted().zipWithNext().forEach { stack.addLast(it) }
        while (stack.isNotEmpty()) {
            val (a, b) = stack.removeLast()
            val aa = points[a]; val bb = points[b]
            val dx = bb.x - aa.x; val dy = bb.y - aa.y; val length = dx * dx + dy * dy
            var greatest = 1.0; var split = -1
            for (i in a + 1 until b) {
                val q = points[i]
                val t = if (length == 0.0) 0.0 else (((q.x - aa.x) * dx + (q.y - aa.y) * dy) / length).coerceIn(0.0, 1.0)
                val error = hypot(q.x - aa.x - t * dx, q.y - aa.y - t * dy)
                if (error > greatest) { greatest = error; split = i }
            }
            if (split >= 0) { keep.add(split); stack.addLast(a to split); stack.addLast(split to b) }
        }
        return keep.sorted()
    }

    private fun clip(points: List<XY>, radius: Double): List<List<XY>> {
        val result = mutableListOf<List<XY>>()
        var current = mutableListOf<XY>()
        fun flush() { if (current.isNotEmpty()) result.add(current); current = mutableListOf() }
        for (i in 1 until points.size) {
            val a = points[i - 1]; val b = points[i]
            val dx = b.x - a.x; val dy = b.y - a.y; val length = dx * dx + dy * dy
            if (length == 0.0) continue
            val dot = a.x * dx + a.y * dy
            val disc = dot * dot - length * (a.x * a.x + a.y * a.y - radius * radius)
            var lo = 1.0; var hi = 0.0
            if (disc > 0) { val root = sqrt(disc); lo = max(0.0, (-dot - root) / length); hi = min(1.0, (-dot + root) / length) }
            if (lo >= hi) { flush(); continue }
            val start = if (lo == 0.0) a else a.between(b, lo)
            val end = if (hi == 1.0) b else a.between(b, hi)
            if (current.isNotEmpty() && hypot(current.last().x - start.x, current.last().y - start.y) > 1e-6) flush()
            if (current.isEmpty()) current.add(start)
            current.add(end)
            if (hi < 1) flush()
        }
        flush()
        return result
    }
}
