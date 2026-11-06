package net.osmand.junction.bridge

import android.content.*
import android.os.IBinder
import android.os.SystemClock
import android.os.Build
import net.osmand.aidlapi.IOsmAndAidlInterface
import org.json.JSONObject
import java.util.concurrent.CountDownLatch
import java.util.concurrent.Executors
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicBoolean
import java.util.concurrent.atomic.AtomicReference

/** Actual cross-process getAppInfo + production codec, without Garmin transport.
 * Explicit shell/DUMP-only debug receiver; one request/worker, no background loop.
 */
class DebugSnapshotReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action !in listOf("net.osmand.junction.bridge.SNAPSHOT", "net.osmand.junction.bridge.DESK")) return
        val request = intent.getStringExtra("request")?.takeIf { it.matches(Regex("[A-Za-z0-9_-]{1,64}")) } ?: return
        if (intent.action == "net.osmand.junction.bridge.DESK") {
            val result = JSONObject().put("request", request).put("probeVersion", 1)
            try {
                when (intent.getStringExtra("operation")) {
                    "start_tethered" -> {
                        val service = Intent(context, NavigationService::class.java).putExtra("transport", "tethered")
                        if (Build.VERSION.SDK_INT >= 26) context.startForegroundService(service) else context.startService(service)
                    }
                    "stop_tethered" -> context.stopService(Intent(context, NavigationService::class.java))
                    else -> error("unsupported fixed debug operation")
                }
                result.put("status", "ok")
            } catch (error: Exception) {
                result.put("status", "error").put("reason", error.javaClass.simpleName)
            }
            val directory = checkNotNull(context.getExternalFilesDir("junction-desk")).apply { mkdirs() }
            val file = directory.resolve("latest.tmp"); file.writeText(result.toString())
            check(file.renameTo(directory.resolve("latest.json")))
            return
        }
        if (!busy.compareAndSet(false, true)) return
        val pending = goAsync()
        val app = context.applicationContext
        val connected = CountDownLatch(1)
        val source = AtomicReference<IOsmAndAidlInterface?>()
        val connection = object : ServiceConnection {
            override fun onServiceConnected(name: ComponentName, binder: IBinder) {
                source.set(IOsmAndAidlInterface.Stub.asInterface(binder)); connected.countDown()
            }
            override fun onServiceDisconnected(name: ComponentName) { source.set(null) }
            override fun onNullBinding(name: ComponentName) { connected.countDown() }
        }
        val started = SystemClock.elapsedRealtime()
        val bound = try {
            app.bindService(Intent().setComponent(ComponentName(NavigationService.OSMAND,
                "net.osmand.aidl.OsmandAidlServiceV2")), connection, Context.BIND_AUTO_CREATE)
        } catch (_: Exception) { false }
        worker.execute {
            val result = JSONObject().put("request", request).put("probeVersion", 1)
            try {
                check(bound && connected.await(3, TimeUnit.SECONDS)) { "source connection timeout" }
                val info = checkNotNull(source.get()).appInfo
                val received = SystemClock.elapsedRealtime()
                result.put("apiRoundTripMs", received - started).put("receivedElapsedMs", received)
                if (info == null) result.put("status", "permission_or_source_error")
                else {
                    val wrapper = info.navigationSnapshot
                    if (wrapper == null) result.put("status", "unsupported")
                    else if (wrapper.getString("status") == "unavailable") result.put("status", "source_busy")
                    else {
                        val json = checkNotNull(wrapper.getString("sceneJson"))
                        val scene = SnapshotCodec.decode(json, wrapper.getInt("version"),
                            wrapper.getLong("capturedElapsedMs", -1), wrapper.getInt("exportAgeMs", -1), received)
                        result.put("status", "decoded").put("scene", JSONObject(scene))
                            .put("sourceBytes", json.toByteArray(Charsets.UTF_8).size)
                    }
                }
            } catch (error: Exception) {
                result.put("status", "error").put("errorType", error.javaClass.simpleName).put("reason", error.message)
            } finally {
                try {
                    val directory = checkNotNull(app.getExternalFilesDir("junction-desk")).apply { mkdirs() }
                    val file = directory.resolve("latest.tmp"); file.writeText(result.toString())
                    check(file.renameTo(directory.resolve("latest.json")))
                } finally {
                    if (bound) try { app.unbindService(connection) } catch (_: Exception) { }
                    busy.set(false); pending.finish()
                }
            }
        }
    }
    companion object {
        private val busy = AtomicBoolean()
        private val worker = Executors.newSingleThreadExecutor()
    }
}
