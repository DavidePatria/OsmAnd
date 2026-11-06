package net.osmand.plus.routing.companion

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.os.SystemClock
import android.os.Handler
import android.os.Looper
import net.osmand.aidl.AidlPermissionGroup
import net.osmand.Location
import net.osmand.plus.OsmandApplication
import net.osmand.plus.routing.NextDirectionInfo
import net.osmand.plus.settings.enums.SimulationMode
import org.json.JSONObject

/** Shell/DUMP-only controls of the CURRENT calculated route. Absent from release.
 * No arbitrary coordinates, file paths, package names or preference edits accepted.
 */
class DebugJunctionDeskReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action != ACTION) return
        val app = context.applicationContext as OsmandApplication
        val request = intent.getStringExtra("request")?.takeIf { it.matches(Regex("[A-Za-z0-9_-]{1,64}")) } ?: return
        val operation = intent.getStringExtra("operation") ?: "state"
        val result = JSONObject().put("request", request).put("operation", operation).put("deskVersion", 1)
        try {
            check(!app.isApplicationInitializing) { "initializing" }
            val helper = app.routingHelper
            val simulation = app.locationProvider.locationSimulation
            if (operation != "state") {
                require(intent.getStringExtra("scenario") == "current-route") { "named scenario required" }
            }
            when (operation) {
                "state" -> Unit
                "start" -> {
                    check(helper.isRouteCalculated && !helper.isRouteBeingCalculated) { "route not ready" }
                    simulation.stop()
                    restoreSettings(app)
                    oldMode = app.settings.simulateNavigationMode
                    oldSpeed = app.settings.simulateNavigationSpeed
                    app.settings.simulateNavigationMode = SimulationMode.CONSTANT.key
                    app.settings.simulateNavigationSpeed = 10f
                    val version = ++controlVersion
                    val route = helper.route
                    // The existing simulator's stop is cooperative. Let its old
                    // 1.5-second sleep finish before a new thread can start.
                    Handler(Looper.getMainLooper()).postDelayed({
                        if (controlVersion == version && helper.route === route && !helper.isRouteBeingCalculated) {
                            helper.resumeNavigation()
                            simulation.startStopRouteAnimation(null, false, null)
                        }
                    }, 2000)
                }
                "stop" -> {
                    controlVersion++
                    simulation.stop()
                    helper.pauseNavigation()
                    restoreSettings(app)
                }
                "freeze" -> { controlVersion++; simulation.stop() }
                "cancel" -> {
                    controlVersion++; simulation.stop(); restoreSettings(app); app.stopNavigation()
                }
                "detour" -> {
                    check(helper.isFollowingMode && helper.isRouteCalculated) { "active route required" }
                    val origin = Location(checkNotNull(helper.lastFixedLocation))
                    val route = helper.route.immutableAllLocations
                    val next = route[(helper.route.currentRoute + 1).coerceAtMost(route.lastIndex)]
                    val north = (next.latitude - origin.latitude) * 111_195
                    val east = (next.longitude - origin.longitude) * 111_195 * Math.cos(Math.toRadians(origin.latitude))
                    val length = Math.hypot(east, north)
                    check(length > 1) { "approach vector unavailable" }
                    simulation.stop()
                    val version = ++controlVersion
                    // Controlled synthetic traveled positions, perpendicular to the
                    // calculated route; the REAL engine decides deviation/recalculation.
                    for (i in 0..5) Handler(Looper.getMainLooper()).postDelayed({
                        if (version == controlVersion) {
                            val offset = 120.0 + i * 20
                            val fix = Location(origin)
                            fix.latitude += east / length * offset / 111_195
                            fix.longitude -= north / length * offset / (111_195 * Math.cos(Math.toRadians(origin.latitude)))
                            fix.time = System.currentTimeMillis(); fix.accuracy = 5f; fix.speed = 10f
                            app.locationProvider.setLocationFromSimulation(fix)
                        }
                    }, 2000L + i * 1500L)
                }
                "pause" -> helper.pauseNavigation()
                "resume" -> helper.resumeNavigation()
                "reload" -> app.aidlApi.reloadIndexes()
                "grant_bridge", "deny_bridge" -> {
                    val client = app.aidlApi.getOrCreateConnectedApp(BRIDGE)
                    app.aidlApi.setGroupGranted(client, AidlPermissionGroup.LOCATION, operation == "grant_bridge")
                    app.aidlApi.setAppEnabled(null, client, operation == "grant_bridge")
                }
                else -> error("unsupported operation")
            }
            result.put("status", "ok").put("elapsedMs", SystemClock.elapsedRealtime())
                .put("appDataDirectory", app.appPath.absolutePath)
                .put("routeCalculated", helper.isRouteCalculated).put("recalculating", helper.isRouteBeingCalculated)
                .put("following", helper.isFollowingMode).put("paused", helper.isPauseNavigation)
                .put("deviated", helper.isDeviatedFromRoute).put("simulating", simulation.isRouteAnimating)
                .put("routePoint", helper.route.currentRoute).put("routePoints", helper.route.immutableAllLocations.size)
                .put("routeToken", System.identityHashCode(helper.route).toString(16))
                .put("applicationMode", helper.appMode.stringKey)
                .put("mapFiles", app.resourceManager.routingMapFiles.size)
            val direction = helper.getNextRouteDirectionInfo(NextDirectionInfo(), false)?.directionInfo
            result.put("nextRouteIndex", direction?.routePointOffset ?: -1)
            helper.lastFixedLocation?.let {
                result.put("fixTimeMs", it.time).put("fixAgeMs", System.currentTimeMillis() - it.time)
                    .put("fixLatitude", it.latitude).put("fixLongitude", it.longitude)
                    .put("fixSpeedMps", if (it.hasSpeed()) it.speed else JSONObject.NULL)
            }
            helper.lastProjection?.let {
                result.put("projectionTimeMs", it.time).put("projectionProvider", it.provider)
            }
        } catch (error: Exception) {
            result.put("status", "error").put("errorType", error.javaClass.simpleName).put("reason", error.message)
        }
        val directory = checkNotNull(app.getExternalFilesDir("junction-desk")).apply { mkdirs() }
        val temporary = directory.resolve("latest.tmp")
        temporary.writeText(result.toString())
        check(temporary.renameTo(directory.resolve("latest.json")))
    }

    private fun restoreSettings(app: OsmandApplication) {
        oldMode?.let { app.settings.simulateNavigationMode = it }
        oldSpeed?.let { app.settings.simulateNavigationSpeed = it }
        oldMode = null; oldSpeed = null
    }

    companion object {
        private const val ACTION = "net.osmand.junction.DESK"
        private const val BRIDGE = "net.osmand.junction.bridge.debug"
        private var oldMode: String? = null
        private var oldSpeed: Float? = null
        private var controlVersion = 0L
    }
}
