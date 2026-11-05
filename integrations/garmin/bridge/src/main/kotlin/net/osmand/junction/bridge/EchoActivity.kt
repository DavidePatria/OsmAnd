package net.osmand.junction.bridge

import android.app.Activity
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.os.SystemClock
import android.util.Log
import android.widget.TextView
import com.garmin.android.connectiq.ConnectIQ
import com.garmin.android.connectiq.IQApp
import com.garmin.android.connectiq.IQDevice
import java.util.concurrent.Executors
import java.util.ArrayDeque
import org.json.JSONObject

/** T03 transport probe only. No navigation data, Binder access or background service yet. */
class EchoActivity : Activity() {
    private lateinit var sdk: ConnectIQ
    private lateinit var statusView: TextView
    private val main = Handler(Looper.getMainLooper())
    private val sender = Executors.newSingleThreadExecutor()
    private var active = true
    private var sendInFlight = false
    private var registeredDevice: IQDevice? = null
    private val audit = ArrayDeque<String>()
    private val watchApp = IQApp(WATCH_APP_ID)
    private val transport by lazy {
        if (intent.getStringExtra("transport") == "tethered") ConnectIQ.IQConnectType.TETHERED
        else ConnectIQ.IQConnectType.WIRELESS
    }

    override fun onCreate(state: Bundle?) {
        super.onCreate(state)
        statusView = TextView(this).apply { textSize = 20f; setPadding(32, 64, 32, 32) }
        setContentView(statusView)
        filesDir.resolve("echo-probe.jsonl").writeText("")
        trace("INITIALIZING")
        sdk = ConnectIQ.getInstance(this, transport)
        sdk.initialize(this, false, object : ConnectIQ.ConnectIQListener {
            override fun onSdkReady() = onMain {
                trace("SDK_READY")
                selectDevice()
            }
            override fun onInitializeError(status: ConnectIQ.IQSdkErrorStatus) = onMain {
                trace("INITIALIZE_ERROR status=$status")
            }
            override fun onSdkShutDown() = onMain { trace("SDK_SHUT_DOWN") }
        })
    }

    private fun selectDevice() {
        try {
            val devices = sdk.knownDevices.orEmpty()
            val requestedId = intent.getLongExtra("garminDeviceId", -1)
            val device = if (requestedId >= 0) devices.singleOrNull { it.deviceIdentifier == requestedId }
                         else devices.singleOrNull()
            if (device == null) {
                trace("DEVICE_SELECTION_REQUIRED count=${devices.size}")
                return
            }
            registeredDevice = device
            sdk.registerForDeviceEvents(device) { _, status -> onMain { trace("DEVICE_STATUS status=$status") } }
            val listener = ConnectIQ.IQApplicationEventListener { _, app, messages, status -> onMain {
                trace("RECEIVE app_id='${app.applicationId}' status=$status count=${messages?.size ?: 0}")
                if (status != ConnectIQ.IQMessageStatus.SUCCESS) trace("RECEIVE_ERROR status=$status")
                else messages.orEmpty().forEach { receive(device, it) }
            } }
            sdk.registerForAppEvents(device, watchApp, listener)
            if (transport == ConnectIQ.IQConnectType.TETHERED) {
                // Simulator versions can omit the application ID on outgoing packets.
                // Test-only compatibility listener; never register this in wireless mode.
                sdk.registerForAppEvents(device, IQApp(""), listener)
                trace("SIMULATOR_EMPTY_APP_ID_LISTENER")
            }
            trace("REGISTERED app=$WATCH_APP_ID")
        } catch (error: Exception) {
            trace("REGISTER_ERROR type=${error.javaClass.simpleName}")
        }
    }

    private fun receive(device: IQDevice, value: Any?) {
        val message = value as? Map<*, *> ?: return trace("REJECT non_dictionary")
        val epoch = message["epoch"] as? String ?: return trace("REJECT missing_epoch")
        val id = message["requestId"] as? Int ?: return trace("REJECT missing_integer_id")
        val displayed = message["displayedId"] as? Int ?: return trace("REJECT missing_integer_ack")
        if (message["kind"] != "echo_request" || epoch.length !in 1..64 || id !in 1..1_000_000 || displayed !in 0 until id) {
            return trace("REJECT invalid_request")
        }
        trace("REQUEST epoch=$epoch id=$id displayed=$displayed")
        if (sendInFlight) return trace("DROP busy id=$id")
        sendInFlight = true
        // The tethered SDK writes to its socket synchronously. Keep it off the UI
        // thread; the main-thread guard bounds this executor to one pending send.
        sender.execute {
            try {
                sdk.sendMessage(device, watchApp, mapOf("kind" to "echo_reply", "epoch" to epoch, "requestId" to id)) { _, _, status -> onMain {
                    sendInFlight = false
                    // Delivery is proved by a subsequent displayedId, not this callback.
                    trace("SEND_STATUS id=$id status=$status")
                } }
            } catch (error: Exception) {
                onMain {
                    sendInFlight = false
                    trace("SEND_ERROR id=$id type=${error.javaClass.simpleName}")
                }
            }
        }
    }

    private fun onMain(action: () -> Unit) {
        main.post { if (active) action() }
    }

    private fun trace(event: String) {
        val line = "JUNCTION_ECHO t=${SystemClock.elapsedRealtime()} transport=$transport $event"
        Log.i("JunctionEcho", line)
        // Bounded, app-private test evidence survives a noisy device log buffer.
        val record = JSONObject().put("elapsed_ms", SystemClock.elapsedRealtime())
            .put("pid", android.os.Process.myPid())
            .put("transport", transport.toString()).put("event", event)
        audit.addLast(record.toString())
        if (audit.size > 256) audit.removeFirst()
        val temporary = filesDir.resolve("echo-probe.jsonl.tmp")
        temporary.writeText(audit.joinToString("\n", postfix = "\n"))
        check(temporary.renameTo(filesDir.resolve("echo-probe.jsonl")))
        statusView.text = getString(R.string.echo_status, transport.toString(), event)
    }

    override fun onDestroy() {
        active = false
        main.removeCallbacksAndMessages(null)
        sender.shutdownNow()
        if (::sdk.isInitialized) {
            try {
                registeredDevice?.let { sdk.unregisterForEvents(it) }
                sdk.shutdown(this)
            } catch (_: Exception) {
                // SDK may already be shut down after a failed initialization.
            }
        }
        super.onDestroy()
    }

    companion object {
        // Same UUID as watch/manifest.xml; Garmin's Android representation has no hyphens.
        const val WATCH_APP_ID = "9d7c2b1a4f6e4b3a9c1d2e8f5a6b7c8d"
    }
}
