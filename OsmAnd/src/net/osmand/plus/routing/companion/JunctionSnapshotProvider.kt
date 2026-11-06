package net.osmand.plus.routing.companion

import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.os.SystemClock
import com.google.gson.Gson
import net.osmand.PlatformUtil
import net.osmand.plus.OsmandApplication
import net.osmand.plus.routing.NextDirectionInfo
import net.osmand.plus.routing.RouteCalculationResult
import net.osmand.router.junction.JunctionCompiler
import net.osmand.router.junction.JunctionFixClock
import net.osmand.router.junction.JunctionGeometry
import net.osmand.router.junction.JunctionRoadReader
import net.osmand.router.junction.JunctionSnapshotCache
import net.osmand.router.junction.JunctionSnapshotCache.State
import net.osmand.router.junction.JunctionWindow
import net.osmand.router.junction.JunctionLayers
import java.util.concurrent.Executors
import java.util.concurrent.FutureTask
import java.util.concurrent.TimeUnit
import java.util.concurrent.TimeoutException
import java.util.concurrent.atomic.AtomicReference

/** Optional read-only exporter. Routing observation is serialized with UI lifecycle;
 * map IO/geometry use one worker and worker-owned streams. No native router changes.
 */
class JunctionSnapshotProvider(private val app: OsmandApplication) {
    private val cache = JunctionSnapshotCache()
    private val fixClock = JunctionFixClock()
    private val main = Handler(Looper.getMainLooper())
    private val pending = AtomicReference<FutureTask<Bundle?>?>()
    private val worker = Executors.newSingleThreadExecutor { runnable ->
        Thread(runnable, "JunctionGeometry").apply { isDaemon = true }
    }
    private var copiedRoute: RouteCalculationResult? = null
    private var routeInput: JunctionGeometry.Route? = null
    private var copiedJunction = -1
    private var retryAfter = 0L
    private val gson = Gson()

    /** Never wait for map work. A busy UI returns absent data, never old guidance. */
    fun snapshot(): Bundle? {
        if (Looper.myLooper() == Looper.getMainLooper()) return try {
            capture()?.let { ageAdjusted(it) }
        } catch (error: Exception) {
            LOG.error("Junction snapshot observation failed", error)
            null
        }
        var task = pending.get()
        if (task == null) {
            val created = FutureTask<Bundle?> { capture() }
            if (pending.compareAndSet(null, created)) {
                task = created
                main.post {
                    try { created.run() } finally { pending.compareAndSet(created, null) }
                }
            } else task = pending.get()
        }
        return try {
            val result = task?.get(200, TimeUnit.MILLISECONDS) ?: return null
            ageAdjusted(result)
        } catch (_: TimeoutException) {
            null
        } catch (error: Exception) {
            if (error is InterruptedException) Thread.currentThread().interrupt()
            LOG.error("Junction snapshot observation failed", error)
            null
        }
    }

    private fun ageAdjusted(result: Bundle): Bundle {
        val elapsed = SystemClock.elapsedRealtime() - result.getLong("capturedElapsedMs")
        return Bundle(result).apply { putInt("exportAgeMs", if (elapsed < 0) 60_000 else elapsed.coerceAtMost(60_000).toInt()) }
    }

    private fun capture(): Bundle? {
        check(Looper.myLooper() == Looper.getMainLooper())
        val helper = app.routingHelper
        var capturedAt = 0L
        val scene = synchronized(helper) {
            val now = SystemClock.elapsedRealtime()
            capturedAt = now
            val route = helper.route
            val info = helper.getNextRouteDirectionInfo(NextDirectionInfo(), false)
            val direction = info?.directionInfo
            val index = direction?.let { selected -> route.immutableAllDirections.indexOfFirst { it === selected } } ?: -1
            val state = when {
                app.isApplicationInitializing -> State.UNAVAILABLE
                helper.isRouteBeingCalculated -> State.RECALCULATING
                helper.isRouteWasFinished -> State.ARRIVED
                helper.isPauseNavigation -> State.PAUSED
                !helper.isFollowingMode || !route.isCalculated -> State.IDLE
                helper.isDeviatedFromRoute -> State.OFF_ROUTE
                index < 0 || direction == null -> State.UNAVAILABLE
                else -> State.ACTIVE
            }
            cache.observe(route, index, state)
            if (state != State.ACTIVE) {
                copiedRoute = null
                routeInput = null
            }
            val fix = helper.lastFixedLocation
            val fixAge = if (fix == null) 60_000 else fixClock.age(fix.time, System.currentTimeMillis(), now)
            // This refers to the FIRST original scene anchor, including zero
            // while OsmAnd still retains a decision whose entry was passed.
            val distance = if (direction == null || route.currentRoute > direction.routePointOffset) 0
                else route.getDistanceToPoint(helper.lastProjection, direction.routePointOffset).coerceAtLeast(0)
            val ticket = if (now >= retryAfter) cache.requestBuild() else null
            if (ticket != null) {
                try {
                    if (copiedRoute !== route || copiedJunction != index) {
                        val points = route.immutableAllLocations
                        val directions = route.immutableAllDirections
                        routeInput = JunctionWindow.copy(points.size, directions.size, index,
                            { position -> points[position].let {
                                val road = route.immutableAllSegments.getOrNull(position)?.`object`
                                JunctionGeometry.Geo(it.latitude, it.longitude, null,
                                    JunctionLayers.level(road?.getValue("layer"), road?.getValue("bridge"), road?.getValue("tunnel")))
                            } },
                            { position -> directions[position].let { JunctionGeometry.Decision(it.routePointOffset,
                                it.turnType.toXmlString(), it.streetName, it.turnType.exitOut) } })
                        copiedRoute = route
                        copiedJunction = index
                    }
                    val input = checkNotNull(routeInput)
                    worker.execute {
                        var scene: JunctionGeometry.Scene? = null
                        try {
                            val maps = app.resourceManager.routingMapFiles.map { it.file }.distinct()
                            val context = JunctionRoadReader().read(maps, input.points[input.decisions[0].routeIndex-input.indexBase]) { !cache.isCurrent(ticket) }
                            if (cache.isCurrent(ticket)) scene = JunctionCompiler().compile(input, 0, context)
                        } catch (error: Exception) {
                            LOG.error("Junction geometry unavailable", error)
                        }
                        val result = scene
                        main.post {
                            // Re-observe route/lifecycle before publishing a completed
                            // worker result, even when no client polled meanwhile.
                            try { capture() } catch (error: Exception) {
                                cache.observe(null, -1, State.UNAVAILABLE)
                                LOG.error("Junction completion observation failed", error)
                            }
                            if (cache.complete(ticket, result) && result == null) retryAfter = SystemClock.elapsedRealtime() + 5000
                        }
                    }
                } catch (error: Exception) {
                    cache.complete(ticket, null)
                    retryAfter = now + 5000
                    LOG.error("Junction route input unavailable", error)
                }
            }
            // Anticipation remains OFF in live export until actual fix/projection
            // timestamps and update cadence are verified on the phone.
            cache.snapshot(distance, fixAge, fixAge, 0)
        }
        // Serialization is deliberately outside the routing lock.
        return Bundle().apply {
            putInt("version", 1)
            putString("sceneJson", gson.toJson(scene))
            putLong("capturedElapsedMs", capturedAt)
            putInt("exportAgeMs", 0)
        }
    }

    companion object { private val LOG = PlatformUtil.getLog(JunctionSnapshotProvider::class.java) }
}
