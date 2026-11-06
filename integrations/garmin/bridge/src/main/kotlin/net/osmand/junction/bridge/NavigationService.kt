package net.osmand.junction.bridge

import android.app.*
import android.Manifest
import android.content.*
import android.content.pm.PackageManager
import android.os.*
import android.util.Log
import com.garmin.android.connectiq.ConnectIQ
import com.garmin.android.connectiq.IQApp
import com.garmin.android.connectiq.IQDevice
import net.osmand.aidlapi.IOsmAndAidlInterface
import org.json.JSONArray
import org.json.JSONObject
import java.util.concurrent.Executors

/** User-started connection to the isolated OsmAnd build and one selected Garmin. */
class NavigationService:Service() {
    private val main=Handler(Looper.getMainLooper())
    private val worker=Executors.newSingleThreadExecutor()
    private val delivery=NavigationDelivery()
    private val launchGate=WatchLaunchGate()
    private var sdk:ConnectIQ?=null
    private var device:IQDevice?=null
    private val watch=IQApp(EchoActivity.WATCH_APP_ID)
    @Volatile private var source:IOsmAndAidlInterface?=null
    private var bound=false
    @Volatile private var active=true
    private var ready=false
    private var tethered=false
    private var foreground=false
    private val prefs by lazy { getSharedPreferences(PREFS,MODE_PRIVATE) }
    private val rebind=Runnable { if(active && !bound) bindSource() }
    private val sourceConnection=object:ServiceConnection {
        override fun onServiceConnected(name:ComponentName,binder:IBinder) {
            if(!active)return
            source=IOsmAndAidlInterface.Stub.asInterface(binder);delivery.connectionChanged()
            status(R.string.navigation_waiting_watch,"SOURCE_BOUND")
        }
        override fun onServiceDisconnected(name:ComponentName) {
            if(!active)return
            source=null;delivery.connectionChanged();status(R.string.navigation_waiting_osmand,"SOURCE_DISCONNECTED")
        }
        override fun onBindingDied(name:ComponentName) { if(active) { unbindSource();main.postDelayed(rebind,2000) } }
        override fun onNullBinding(name:ComponentName) { if(active) { unbindSource();main.postDelayed(rebind,2000) } }
    }
    override fun onCreate() {
        super.onCreate()
        if(Build.VERSION.SDK_INT>=31 && checkSelfPermission(Manifest.permission.BLUETOOTH_CONNECT)!=PackageManager.PERMISSION_GRANTED) {
            status(R.string.navigation_permission,"NEARBY_PERMISSION_REQUIRED");stopSelf();return
        }
        if(Build.VERSION.SDK_INT>=26) getSystemService(NotificationManager::class.java).createNotificationChannel(
            NotificationChannel(CHANNEL,getString(R.string.navigation_channel),NotificationManager.IMPORTANCE_LOW))
        try { startForeground(1,notification(getString(R.string.navigation_starting)));foreground=true }
        catch(error:Exception) { status(R.string.navigation_permission,"FOREGROUND_ERROR ${error.javaClass.simpleName}");stopSelf() }
    }
    override fun onStartCommand(intent:Intent?,flags:Int,startId:Int):Int {
        if(intent?.action==STOP) { stopSelf();return START_NOT_STICKY }
        if(!foreground)return START_NOT_STICKY
        if(intent?.getBooleanExtra("request_watch_open",false)==true)launchGate.request()
        if(sdk==null) {
            tethered=intent?.getStringExtra("transport")=="tethered"
            bindSource()
            try {
                val instance=ConnectIQ.getInstance(this,if(tethered)ConnectIQ.IQConnectType.TETHERED else ConnectIQ.IQConnectType.WIRELESS)
                sdk=instance
                instance.initialize(this,false,object:ConnectIQ.ConnectIQListener {
                    override fun onSdkReady()=onMain { ready=true;selectDevice() }
                    override fun onInitializeError(status:ConnectIQ.IQSdkErrorStatus)=onMain { this@NavigationService.status(R.string.navigation_garmin_unavailable,"SDK_ERROR $status") }
                    override fun onSdkShutDown()=onMain { delivery.connectionChanged();stopSelf() }
                })
            } catch(error:Exception) { status(R.string.navigation_garmin_unavailable,"SDK_ERROR ${error.javaClass.simpleName}") }
        } else if(ready)selectDevice()
        return START_NOT_STICKY
    }
    private fun bindSource() {
        if(bound || !active)return
        try {
            bound=bindService(Intent().setComponent(ComponentName(OSMAND,"net.osmand.aidl.OsmandAidlServiceV2")),sourceConnection,BIND_AUTO_CREATE)
            if(!bound) { status(R.string.navigation_waiting_osmand,"SOURCE_ABSENT");main.postDelayed(rebind,2000) }
        } catch(error:Exception) { status(R.string.navigation_waiting_osmand,"SOURCE_BIND_ERROR ${error.javaClass.simpleName}");main.postDelayed(rebind,2000) }
    }
    private fun unbindSource() {
        source=null;delivery.connectionChanged()
        if(bound) { try { unbindService(sourceConnection) } catch(_:IllegalArgumentException) { };bound=false }
    }
    private fun selectDevice() {
        val instance=sdk ?: return
        try {
            val devices=instance.knownDevices.orEmpty()
            val list=JSONArray();devices.forEach {
                list.put(JSONObject().put("id",it.deviceIdentifier).put("name",it.friendlyName.orEmpty().ifBlank { getString(R.string.navigation_watch) }))
            }
            prefs.edit().putString("devices",list.toString()).apply()
            val chosen=prefs.getLong("deviceId",-1)
            val selected=if(chosen>=0) devices.singleOrNull { it.deviceIdentifier==chosen } else devices.singleOrNull()
            if(selected==null) { status(R.string.navigation_choose_watch,"DEVICE_SELECTION_REQUIRED count=${devices.size}");return }
            if(device?.deviceIdentifier==selected.deviceIdentifier) {requestWatchOpen();return}
            device?.let { instance.unregisterForEvents(it) };delivery.connectionChanged();device=selected
            instance.registerForDeviceEvents(selected) { _,state -> onMain {
                delivery.connectionChanged();status(R.string.navigation_waiting_watch,"DEVICE_STATUS $state")
                if(state==IQDevice.IQDeviceStatus.CONNECTED)requestWatchOpen()
            } }
            val listener=ConnectIQ.IQApplicationEventListener { sender,_,messages,result -> onMain {
                if(sender.deviceIdentifier==device?.deviceIdentifier && result==ConnectIQ.IQMessageStatus.SUCCESS) messages.orEmpty().forEach { receive(selected,it) }
            } }
            instance.registerForAppEvents(selected,watch,listener)
            if(tethered)instance.registerForAppEvents(selected,IQApp(""),listener)
            status(R.string.navigation_waiting_watch,"WATCH_REGISTERED")
            requestWatchOpen()
        } catch(error:Exception) { status(R.string.navigation_garmin_unavailable,"REGISTER_ERROR ${error.javaClass.simpleName}") }
    }
    private fun requestWatchOpen() {
        val instance=sdk ?: return
        val target=device ?: return
        try {
            if(!launchGate.begin(SystemClock.elapsedRealtime(),instance.getDeviceStatus(target)==IQDevice.IQDeviceStatus.CONNECTED))return
            instance.openApplication(target,watch) { _,_,result -> onMain {
                val label=when(result) {
                    ConnectIQ.IQOpenApplicationStatus.PROMPT_SHOWN_ON_DEVICE -> R.string.navigation_watch_prompt
                    ConnectIQ.IQOpenApplicationStatus.APP_IS_NOT_INSTALLED -> R.string.navigation_watch_not_installed
                    ConnectIQ.IQOpenApplicationStatus.APP_IS_ALREADY_RUNNING -> R.string.navigation_waiting_watch
                    else -> R.string.navigation_watch_open_manually
                }
                status(label,"WATCH_OPEN_STATUS $result")
            } }
        } catch(error:Exception) {Log.w("JunctionBridge","WATCH_OPEN_ERROR ${error.javaClass.simpleName}")}
    }
    private fun receive(target:IQDevice,message:Any?) {
        val ticket=delivery.begin(message,SystemClock.elapsedRealtime()) ?: return
        val ack=message as? Map<*, *>
        val displayedSeq=ack?.get("displayedSeq") as? Int
        val displayedGeneration=ack?.get("displayedGeneration") as? Int
        val displayedState=ack?.get("displayedState") as? String
        if(displayedSeq!=null && displayedGeneration!=null && displayedSeq in 0..1_000_000 && displayedGeneration in 0..1_000_000 &&
            displayedState in listOf("active","idle","recalculating","unavailable","arrived","stale_source","stale_transport")) {
            Log.i("JunctionBridge","DRAW_ACK generation=$displayedGeneration seq=$displayedSeq state=$displayedState")
        }
        val api=source
        worker.execute {
            var sent=false
            var failure="source_error"
            try {
                var scene:Map<String,Any>?=null
                try {
                  if(api==null) failure="source_disconnected"
                  else {
                    val info=api.appInfo
                    if(info==null)failure="permission_or_source_error"
                    else {
                        val wrapper=info.navigationSnapshot
                        if(wrapper==null)failure="source_unsupported"
                        else if(wrapper.getInt("version")!=1)failure="source_unsupported"
                        else if(wrapper.getString("status")=="unavailable")failure="source_busy"
                        else {
                            scene=SnapshotCodec.decode(wrapper.getString("sceneJson") ?: error("missing scene"),wrapper.getInt("version"),
                                wrapper.getLong("capturedElapsedMs",-1),wrapper.getInt("exportAgeMs",-1),SystemClock.elapsedRealtime())
                            failure="ok"
                        }
                    }
                  }
                } catch(error:Exception) {
                    failure="source_invalid_or_error"
                    if(error is DeadObjectException)onMain {
                        if(source===api) { unbindSource();main.postDelayed(rebind,2000) }
                    }
                }
                val now=SystemClock.elapsedRealtime()
                val response=if(scene!=null)delivery.response(ticket,scene,now) else delivery.unavailable(ticket,failure,now)
                val instance=sdk
                if(response!=null && instance!=null && active) {
                    val wire=CompactWire.encode(response)
                    Log.i("JunctionBridge","WIRE_BYTES ${wire.size} request=${ticket.id}")
                    instance.sendMessage(target,watch,wire) { _,_,result -> onMain {
                        delivery.finish(ticket)
                        val label=if(result!=ConnectIQ.IQMessageStatus.SUCCESS)R.string.navigation_waiting_watch
                            else if(scene==null)R.string.navigation_waiting_osmand else R.string.navigation_running
                        status(label,"SEND_STATUS $result request=${ticket.id} source=$failure")
                    } }
                    sent=true
                }
            } catch(error:Exception) {
                Log.w("JunctionBridge","Source/send failure ${error.javaClass.simpleName}")
                onMain { status(R.string.navigation_waiting_osmand,"SOURCE_OR_SEND_ERROR ${error.javaClass.simpleName}") }
            } finally { if(!sent)delivery.finish(ticket) }
        }
    }
    private fun onMain(action:()->Unit) { main.post { if(active)action() } }
    private fun status(text:Int,event:String) {
        Log.i("JunctionBridge",event)
        val label=getString(text)
        if(prefs.getString("status",null)==label)return
        prefs.edit().putString("status",label).apply()
        if(foreground && (Build.VERSION.SDK_INT<33 || checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS)==PackageManager.PERMISSION_GRANTED)) {
            getSystemService(NotificationManager::class.java).notify(1,notification(label))
        }
    }
    private fun notification(text:String):Notification {
        val flags=PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        val stop=PendingIntent.getService(this,1,Intent(this,NavigationService::class.java).setAction(STOP),flags)
        val open=PendingIntent.getActivity(this,0,Intent(this,NavigationActivity::class.java),flags)
        val builder=if(Build.VERSION.SDK_INT>=26)Notification.Builder(this,CHANNEL) else Notification.Builder(this)
        return builder.setSmallIcon(android.R.drawable.ic_menu_directions).setContentTitle(getString(R.string.app_name))
            .setContentText(text).setOngoing(true).setContentIntent(open).addAction(android.R.drawable.ic_menu_close_clear_cancel,getString(R.string.navigation_stop),stop).build()
    }
    override fun onBind(intent:Intent?):IBinder?=null
    override fun onDestroy() {
        active=false;foreground=false;main.removeCallbacksAndMessages(null);unbindSource();worker.shutdownNow()
        try { device?.let { sdk?.unregisterForEvents(it) };sdk?.shutdown(this) } catch(_:Exception) { }
        prefs.edit().putString("status",getString(R.string.navigation_stopped)).apply()
        stopForeground(STOP_FOREGROUND_REMOVE);super.onDestroy()
    }
    companion object {
        const val PREFS="navigation"
        const val OSMAND="net.osmand.plus.junction"
        private const val CHANNEL="watch-navigation"
        private const val STOP="net.osmand.junction.bridge.STOP"
    }
}
