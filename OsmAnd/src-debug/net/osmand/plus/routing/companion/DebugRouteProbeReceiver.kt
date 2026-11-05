package net.osmand.plus.routing.companion

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.os.SystemClock
import net.osmand.PlatformUtil
import net.osmand.plus.OsmandApplication
import net.osmand.plus.routing.RouteCalculationResult
import net.osmand.plus.settings.backend.ApplicationMode
import net.osmand.router.RouteSegmentResult
import org.json.JSONArray
import org.json.JSONObject
import java.util.IdentityHashMap
import java.util.concurrent.Executors
import java.util.concurrent.atomic.AtomicBoolean

/** Debug-source-only, shell/DUMP-protected inspection of an existing calculated route. */
class DebugRouteProbeReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action != ACTION && intent.action != PREPARE_MOTORCYCLE) return
        if (!busy.compareAndSet(false, true)) return
        val pending = goAsync()
        val app = context.applicationContext as OsmandApplication
        val request = intent.getStringExtra("request")?.takeIf { it.matches(Regex("[A-Za-z0-9_-]{1,64}")) } ?: "capture"
        if (intent.action == PREPARE_MOTORCYCLE) {
            try {
                if (app.isApplicationInitializing) {
                    write(app, request, JSONObject().put("request", request).put("status", "initializing"))
                } else {
                    ApplicationMode.changeProfileAvailability(ApplicationMode.MOTORCYCLE, true, app)
                    app.settings.APPLICATION_MODE.set(ApplicationMode.MOTORCYCLE)
                    app.routingHelper.setAppMode(ApplicationMode.MOTORCYCLE)
                    write(app, request, JSONObject().put("probeVersion", 1).put("request", request)
                        .put("status", "profile_prepared").put("applicationMode", "motorcycle"))
                }
            } finally {
                busy.set(false)
                pending.finish()
            }
            return
        }
        val helper = app.routingHelper
        // Never hold a routing lock while serializing or writing the capture.
        val route: RouteCalculationResult
        val progress: Int
        val calculating: Boolean
        synchronized(helper) {
            route = helper.route
            progress = route.currentRoute
            calculating = helper.isRouteBeingCalculated
        }
        worker.execute {
            try {
                val capture = if (app.isApplicationInitializing || calculating || !route.isCalculated) {
                    JSONObject().put("status", "unavailable").put("reason", "initializing_recalculating_or_no_route")
                        .put("initializing", app.isApplicationInitializing)
                        .put("recalculating", calculating).put("routeCalculated", route.isCalculated)
                } else {
                    Capture(route, progress).encode(app)
                }
                synchronized(helper) {
                    val coherent = helper.route === route && !helper.isRouteBeingCalculated && route.currentRoute == progress
                    capture.put("coherent", coherent)
                    if (!coherent) capture.put("status", "changed_during_capture")
                }
                capture.put("probeVersion", 1).put("request", request)
                    .put("capturedElapsedMs", SystemClock.elapsedRealtime())
                write(app, request, capture)
            } catch (error: Exception) {
                LOG.error("JUNCTION_PROBE capture failed", error)
                write(app, request, JSONObject().put("probeVersion", 1).put("request", request)
                    .put("status", "error").put("errorType", error.javaClass.simpleName))
            } finally {
                busy.set(false)
                pending.finish()
            }
        }
    }

    private fun write(app: OsmandApplication, request: String, capture: JSONObject) {
        val directory = app.filesDir.resolve("junction-probe").apply { mkdirs() }
        val temporary = directory.resolve("latest.tmp")
        temporary.writeText(capture.toString())
        check(temporary.renameTo(directory.resolve("latest.json")))
        LOG.info("JUNCTION_PROBE request=$request status=${capture.optString("status")}")
    }

    private class Capture(private val route: RouteCalculationResult, private val progress: Int) {
        private val ids = IdentityHashMap<RouteSegmentResult, String>()
        private val unique = ArrayList<RouteSegmentResult>()
        private var pointBudget = 50_000
        private var branchBudget = 2_048
        private var truncated = false

        private fun id(segment: RouteSegmentResult): String = ids[segment] ?: "s${unique.size}".also {
            ids[segment] = it
            unique.add(segment)
        }

        fun encode(app: OsmandApplication): JSONObject {
            val locations = route.immutableAllLocations
            val indexed = route.immutableAllSegments
            val points = JSONArray()
            for (point in locations.take(10_000)) {
                points.put(JSONArray().put(point.latitude).put(point.longitude))
            }
            if (locations.size > 10_000 || indexed.size > 10_000) truncated = true
            val references = JSONArray()
            for (segment in indexed.take(10_000)) references.put(id(segment))
            val segments = JSONArray()
            // Branch objects are recorded inline, without recursively traversing a road graph.
            for (segment in unique.toList()) {
                val encoded = segment(segment).put("id", ids[segment])
                val attachments = JSONArray()
                val first = segment.startPointIndex
                val last = segment.endPointIndex
                val step = if (last >= first) 1 else -1
                var node = first
                var count = 0
                while (count++ < 2_048) {
                    val entry = JSONObject().put("roadPointIndex", node)
                    val attached = try {
                        // Existing accessor dereferences cleared storage. Keep this limitation
                        // observable in this isolated probe, without changing the router.
                        segment.getAttachedRoutes(node)
                    } catch (_: NullPointerException) {
                        null
                    }
                    val preAttached = segment.getPreAttachedRoutes(node)
                    entry.put("attachedStorage", if (attached == null) "unavailable" else "available")
                    entry.put("attached", branches(attached))
                    entry.put("preAttachedStorage", if (preAttached == null) "unavailable" else "available")
                    entry.put("preAttached", branches(preAttached?.toList()))
                    attachments.put(entry)
                    if (node == last) break
                    node += step
                }
                if (node != last) truncated = true
                encoded.put("attachments", attachments)
                segments.put(encoded)
            }
            val directions = JSONArray()
            for ((index, direction) in route.immutableAllDirections.withIndex()) {
                if (index >= 2_000) { truncated = true; break }
                val turn = direction.turnType
                directions.put(JSONObject().put("index", index)
                    .put("routePointOffset", direction.routePointOffset)
                    .put("routeEndPointOffset", direction.routeEndPointOffset)
                    .put("turn", turn.toXmlString()).put("turnAngle", turn.turnAngle)
                    .put("roundaboutExit", turn.exitOut).put("distanceAfterM", direction.distance)
                    .put("streetName", direction.streetName ?: JSONObject.NULL)
                    .put("roadId", direction.routeDataObject?.id?.toString() ?: JSONObject.NULL))
            }
            val mode = route.appMode
            return JSONObject().put("status", if (truncated) "truncated" else "captured")
                .put("routeToken", System.identityHashCode(route).toString(16))
                .put("routeTokenScope", "process-local object identity; not a navigation generation")
                .put("currentRoutePoint", progress).put("locationCount", locations.size)
                .put("segmentReferenceCount", indexed.size).put("uniqueSegmentCount", unique.size)
                .put("applicationMode", mode?.stringKey ?: JSONObject.NULL)
                .put("routingProfile", mode?.routingProfile ?: JSONObject.NULL)
                .put("derivedProfile", mode?.let { app.settings.DERIVED_PROFILE.getModeValue(it) } ?: JSONObject.NULL)
                .put("routeService", route.routeService.toString()).put("distanceM", route.wholeDistance)
                .put("locationsLatLon", points).put("locationSegmentIds", references)
                .put("segments", segments).put("directions", directions)
                .put("limitations", JSONArray().put("routing attachments may omit filtered or cleared roads")
                    .put("shared coordinates alone do not establish connectivity")
                    .put("capture is diagnostic; lifecycle-safe production exporter is not implemented"))
        }

        private fun branches(list: List<RouteSegmentResult>?): JSONArray {
            val result = JSONArray()
            for (branch in list.orEmpty()) {
                if (branchBudget-- <= 0) { truncated = true; break }
                result.put(segment(branch))
            }
            return result
        }

        private fun segment(segment: RouteSegmentResult): JSONObject {
            val road = segment.`object`
            val count = road.pointsLength
            val points = JSONArray()
            val limit = minOf(count, 1_024, pointBudget)
            for (index in 0 until limit) {
                val point = segment.getPoint(index)
                points.put(JSONArray().put(index).put(road.getPoint31XTile(index)).put(road.getPoint31YTile(index))
                    .put(point.latitude).put(point.longitude))
            }
            pointBudget -= limit
            if (limit != count) truncated = true
            return JSONObject().put("roadId", road.id.toString())
                .put("startPointIndex", segment.startPointIndex).put("endPointIndex", segment.endPointIndex)
                .put("roadPointCount", count).put("points", points)
                .put("highway", road.highway ?: JSONObject.NULL).put("oneway", road.oneway)
                .put("name", road.name ?: JSONObject.NULL)
                .put("pointsTruncated", limit != count)
        }
    }

    companion object {
        const val ACTION = "net.osmand.junction.CAPTURE_ROUTE"
        const val PREPARE_MOTORCYCLE = "net.osmand.junction.PREPARE_MOTORCYCLE"
        private val LOG = PlatformUtil.getLog(DebugRouteProbeReceiver::class.java)
        private val busy = AtomicBoolean()
        private val worker = Executors.newSingleThreadExecutor()
    }
}
