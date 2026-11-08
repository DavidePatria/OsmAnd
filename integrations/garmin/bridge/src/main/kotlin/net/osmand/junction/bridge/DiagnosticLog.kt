package net.osmand.junction.bridge

import android.content.Context
import android.os.SystemClock
import org.json.JSONObject
import java.io.File
import java.util.concurrent.ArrayBlockingQueue
import java.util.concurrent.ThreadPoolExecutor
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicInteger

/** Two bounded private files retain recent events even if the process is killed. */
internal class RollingDiagnosticFiles(private val directory: File, private val limit: Long = 4L * 1024 * 1024) {
    private val current get() = File(directory, "current.jsonl")
    private val previous get() = File(directory, "previous.jsonl")
    @Synchronized fun clear() { directory.mkdirs(); current.delete(); previous.delete() }
    @Synchronized fun append(line: String) {
        directory.mkdirs()
        val bytes = (line + "\n").toByteArray(Charsets.UTF_8)
        if (bytes.size > limit) return
        if (current.length() + bytes.size > limit) {
            previous.delete()
            if (current.exists() && !current.renameTo(previous)) throw java.io.IOException("Cannot rotate diagnostic log")
        }
        current.appendBytes(bytes)
    }
    @Synchronized fun export(out: java.io.OutputStream, note: String) {
        val header = JSONObject().put("type", "export").put("exportedAtMs", System.currentTimeMillis())
            .put("note", note.take(1000)).toString() + "\n"
        out.write(header.toByteArray(Charsets.UTF_8))
        for (file in listOf(previous, current)) if (file.isFile) file.inputStream().use { it.copyTo(out) }
    }
    @Synchronized fun exists() = current.isFile || previous.isFile
}

internal object DiagnosticLog {
    private val dropped = AtomicInteger()
    private var lastGeometry = ""
    private var geometryRecordedAt = 0L
    private val executor = ThreadPoolExecutor(1, 1, 0, TimeUnit.SECONDS, ArrayBlockingQueue(256),
        { task -> Thread(task, "junction-diagnostics").apply { isDaemon = true } },
        { _, _ -> dropped.incrementAndGet() })
    private fun files(context: Context) = RollingDiagnosticFiles(File(context.filesDir, "diagnostics"))
    private fun enabled(context: Context) = BuildConfig.DEBUG && context.getSharedPreferences(NavigationService.PREFS, Context.MODE_PRIVATE).getBoolean("diagnostics", false)
    @Synchronized fun scene(context: Context, requestId: Int, scene: Map<String, Any>) {
        if (!enabled(context)) return
        try {
            val safe = scene.filterKeys { it != "roadName" && it != "session" }
            val geometry = JSONObject(safe.filterKeys { it in setOf("geometryMode", "radiusDm", "anchors", "paths", "destination") }).toString()
            val now = SystemClock.elapsedRealtime()
            val includeGeometry = geometry != lastGeometry || now - geometryRecordedAt >= 30_000
            val details = if (!includeGeometry) safe.filterKeys { it !in setOf("anchors", "paths", "destination") } else safe
            lastGeometry = geometry
            if (includeGeometry) geometryRecordedAt = now
            record(context, "source_scene", JSONObject().put("requestId", requestId).put("geometryIncluded", includeGeometry)
                .put("scene", JSONObject(details)))
        } catch (_: Exception) { dropped.incrementAndGet() }
    }
    fun record(context: Context, type: String, fields: JSONObject = JSONObject()) {
        if (!enabled(context)) return
        val app = context.applicationContext
        val line = try { fields.put("type", type).put("wallTimeMs", System.currentTimeMillis())
            .put("elapsedMs", SystemClock.elapsedRealtime()).put("droppedEvents", dropped.get()).toString() } catch (_: Exception) { return }
        executor.execute { try { files(app).append(line) } catch (_: Exception) { dropped.incrementAndGet() } }
    }
    fun start(context: Context) {
        val app = context.applicationContext
        synchronized(this) { lastGeometry = ""; geometryRecordedAt = 0 }
        executor.execute {
            try {
                files(app).clear(); dropped.set(0)
                files(app).append(JSONObject().put("type", "recording_started").put("wallTimeMs", System.currentTimeMillis())
                    .put("elapsedMs", SystemClock.elapsedRealtime()).put("bridgeVersion", BuildConfig.VERSION_NAME).toString())
            } catch (_: Exception) { dropped.incrementAndGet() }
        }
    }
    fun export(context: Context, uri: android.net.Uri, note: String, callback: (Boolean) -> Unit) {
        val app = context.applicationContext
        executor.execute {
            val success = try {
                val log = files(app)
                if (!log.exists()) false else app.contentResolver.openOutputStream(uri)?.use { log.export(it, note); true } ?: false
            } catch (_: Exception) { false }
            android.os.Handler(android.os.Looper.getMainLooper()).post { callback(success) }
        }
    }
}
