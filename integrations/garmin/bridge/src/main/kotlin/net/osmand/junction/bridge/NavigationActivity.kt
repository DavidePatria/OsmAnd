package net.osmand.junction.bridge

import android.Manifest
import android.app.Activity
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.widget.Button
import android.widget.LinearLayout
import android.widget.TextView
import org.json.JSONArray

/** Explicit user start/stop. No automatic boot start or battery-setting changes. */
class NavigationActivity : Activity() {
    private val main=Handler(Looper.getMainLooper())
    private lateinit var status:TextView
    private lateinit var choices:LinearLayout
    private var lastDevices=""
    private val refresh=object:Runnable {
        override fun run() {
            val prefs=getSharedPreferences(NavigationService.PREFS,MODE_PRIVATE)
            status.text=prefs.getString("status",getString(R.string.navigation_stopped))
            val devices=prefs.getString("devices","[]") ?: "[]"
            if(devices!=lastDevices) {
                lastDevices=devices;choices.removeAllViews()
                val list=JSONArray(devices)
                if(list.length()>1) for(i in 0 until list.length()) {
                    val device=list.getJSONObject(i)
                    choices.addView(Button(this@NavigationActivity).apply {
                        text=device.optString("name",getString(R.string.navigation_watch))
                        setOnClickListener {
                            prefs.edit().putLong("deviceId",device.getLong("id")).apply();startBridge()
                        }
                    })
                }
            }
            main.postDelayed(this,1000)
        }
    }
    override fun onCreate(state:Bundle?) {
        super.onCreate(state)
        val layout=LinearLayout(this).apply { orientation=LinearLayout.VERTICAL;setPadding(24,48,24,24) }
        layout.addView(TextView(this).apply { text=getString(R.string.navigation_explanation);textSize=18f })
        status=TextView(this).apply { textSize=18f;setPadding(0,24,0,24) };layout.addView(status)
        layout.addView(Button(this).apply { text=getString(R.string.navigation_start);setOnClickListener { startBridge() } })
        layout.addView(Button(this).apply { text=getString(R.string.navigation_stop);setOnClickListener {
            stopService(Intent(this@NavigationActivity,NavigationService::class.java))
        } })
        choices=LinearLayout(this).apply { orientation=LinearLayout.VERTICAL };layout.addView(choices)
        setContentView(layout)
    }
    private fun startBridge() {
        val permissions=mutableListOf<String>()
        if(Build.VERSION.SDK_INT>=31 && checkSelfPermission(Manifest.permission.BLUETOOTH_CONNECT)!=PackageManager.PERMISSION_GRANTED) permissions.add(Manifest.permission.BLUETOOTH_CONNECT)
        val prefs=getSharedPreferences(NavigationService.PREFS,MODE_PRIVATE)
        if(Build.VERSION.SDK_INT>=33 && !prefs.getBoolean("notificationAsked",false)) {
            prefs.edit().putBoolean("notificationAsked",true).apply();permissions.add(Manifest.permission.POST_NOTIFICATIONS)
        }
        if(permissions.isNotEmpty()) { requestPermissions(permissions.toTypedArray(),1);return }
        val intent=Intent(this,NavigationService::class.java)
        // Explicit test intent only; normal user starts always use Garmin Connect.
        if(this.intent.getStringExtra("transport")=="tethered") intent.putExtra("transport","tethered")
        if(Build.VERSION.SDK_INT>=26) startForegroundService(intent) else startService(intent)
    }
    override fun onRequestPermissionsResult(code:Int,permissions:Array<out String>,results:IntArray) {
        super.onRequestPermissionsResult(code,permissions,results)
        if(code==1) {
            if(Build.VERSION.SDK_INT<31 || checkSelfPermission(Manifest.permission.BLUETOOTH_CONNECT)==PackageManager.PERMISSION_GRANTED) startBridge()
            else status.text=getString(R.string.navigation_permission)
        }
    }
    override fun onResume() { super.onResume();main.post(refresh) }
    override fun onPause() { main.removeCallbacks(refresh);super.onPause() }
}
