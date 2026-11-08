package net.osmand.junction.bridge

import android.Manifest
import android.app.Activity
import android.app.AlertDialog
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.widget.Button
import android.widget.LinearLayout
import android.widget.TextView
import android.widget.EditText
import android.widget.ScrollView
import android.widget.Switch
import android.widget.Toast
import org.json.JSONArray

/** Explicit user start/stop. No automatic boot start or battery-setting changes. */
class NavigationActivity : Activity() {
    private val main=Handler(Looper.getMainLooper())
    private lateinit var status:TextView
    private lateinit var choices:LinearLayout
    private var lastDevices=""
    private var automatic=false
    private var diagnosticNote: EditText? = null
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
        val prefs=getSharedPreferences(NavigationService.PREFS,MODE_PRIVATE)
        layout.addView(Switch(this).apply {
            text=getString(R.string.navigation_data_field)
            isChecked=prefs.getBoolean("dataField",false)
            setOnCheckedChangeListener { _,checked ->
                prefs.edit().putBoolean("dataField",checked).apply()
                stopService(Intent(this@NavigationActivity,NavigationService::class.java))
                status.text=getString(R.string.navigation_restart_mode)
            }
        })
        layout.addView(Button(this).apply { text=getString(R.string.navigation_start);setOnClickListener { startBridge() } })
        layout.addView(Button(this).apply { text=getString(R.string.navigation_stop);setOnClickListener {
            stopService(Intent(this@NavigationActivity,NavigationService::class.java))
        } })
        choices=LinearLayout(this).apply { orientation=LinearLayout.VERTICAL };layout.addView(choices)
        if (BuildConfig.DEBUG) addDiagnostics(layout)
        setContentView(ScrollView(this).apply { addView(layout) })
        automatic=intent.getBooleanExtra("auto_start_from_osmand",false) && callingPackage==NavigationService.OSMAND
        if(automatic)android.util.Log.i("JunctionBridge","AUTO_START authenticated OsmAnd caller")
        if(automatic)startBridge()
    }
    private fun addDiagnostics(layout: LinearLayout) {
        val prefs=getSharedPreferences(NavigationService.PREFS,MODE_PRIVATE)
        layout.addView(TextView(this).apply { text=getString(R.string.diagnostics_explanation);setPadding(0,24,0,8) })
        val toggle=Switch(this).apply { text=getString(R.string.diagnostics_record);isChecked=prefs.getBoolean("diagnostics",false) }
        layout.addView(toggle)
        toggle.setOnClickListener {
            if (toggle.isChecked) {
                toggle.isChecked=false
                AlertDialog.Builder(this).setMessage(R.string.diagnostics_replace)
                    .setNegativeButton(android.R.string.cancel,null)
                    .setPositiveButton(R.string.diagnostics_start) { _, _ ->
                        DiagnosticLog.start(this)
                        prefs.edit().putBoolean("diagnostics",true).apply()
                        toggle.isChecked=true
                    }.show()
            } else {
                DiagnosticLog.record(this,"recording_stopped")
                prefs.edit().putBoolean("diagnostics",false).apply()
            }
        }
        diagnosticNote=EditText(this).apply { hint=getString(R.string.diagnostics_note);maxLines=3 }
        layout.addView(diagnosticNote)
        layout.addView(Button(this).apply { text=getString(R.string.diagnostics_export);setOnClickListener {
            val intent=Intent(Intent.ACTION_CREATE_DOCUMENT).addCategory(Intent.CATEGORY_OPENABLE)
                .setType("application/json").putExtra(Intent.EXTRA_TITLE,"junction-diagnostics.jsonl")
            startActivityForResult(intent,42)
        } })
    }
    @Deprecated("Activity result is used for compatibility with the existing Activity")
    override fun onActivityResult(requestCode:Int,resultCode:Int,data:Intent?) {
        super.onActivityResult(requestCode,resultCode,data)
        if(requestCode==42 && resultCode==RESULT_OK) data?.data?.let { uri ->
            DiagnosticLog.export(this,uri,diagnosticNote?.text?.toString().orEmpty()) { success ->
                Toast.makeText(this,if(success) R.string.diagnostics_saved else R.string.diagnostics_save_failed,Toast.LENGTH_LONG).show()
            }
        }
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
            .putExtra("request_watch_open",true)
        // Explicit test intent only; normal user starts always use Garmin Connect.
        if(BuildConfig.DEBUG && (this.intent.getStringExtra("transport")=="tethered" ||
            prefs.getBoolean("deskTethered",false))) intent.putExtra("transport","tethered")
        if(Build.VERSION.SDK_INT>=26) startForegroundService(intent) else startService(intent)
        if(automatic)finish()
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
