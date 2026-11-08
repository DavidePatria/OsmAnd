package net.osmand.plus.routing.companion

import android.content.Intent
import android.widget.CheckBox
import androidx.appcompat.app.AlertDialog
import androidx.lifecycle.Lifecycle
import net.osmand.PlatformUtil
import net.osmand.plus.BuildConfig
import net.osmand.plus.OsmandApplication
import net.osmand.plus.R

/** Optional UI launch only. The Garmin SDK stays in the separate companion APK. */
object JunctionCompanionStarter {
    private const val BRIDGE = "net.osmand.junction.bridge.debug"
    private const val TEST_BRIDGE = "net.osmand.junction.bridge.physicaltest"
    private const val ACTIVITY = "net.osmand.junction.bridge.NavigationActivity"
    private val LOG = PlatformUtil.getLog(JunctionCompanionStarter::class.java)

    @JvmStatic fun onNavigationStarted(app: OsmandApplication) {
        // The bridge authenticates this isolated development identity only.
        if (app.packageName != "net.osmand.plus.junction") return
        val mode = app.routingHelper.appMode
        val automatic = app.settings.JUNCTION_AUTO_START.getModeValue(mode)
        app.runInUIThread {
            val activity = app.osmandMap.mapView.mapActivity
            if (activity == null || !activity.lifecycle.currentState.isAtLeast(Lifecycle.State.RESUMED)) {
                if (automatic) {
                    LOG.info("Junction companion not started: map activity is not visible")
                    app.showToastMessage(R.string.junction_companion_start_manually)
                }
                return@runInUIThread
            }
            val bridge = listOfNotNull(if (BuildConfig.DEBUG) TEST_BRIDGE else null, BRIDGE)
                .firstOrNull { Intent().setClassName(it, ACTIVITY).resolveActivity(app.packageManager) != null }
            if (bridge == null) {
                if (automatic) app.showToastMessage(R.string.junction_companion_start_manually)
                return@runInUIThread
            }
            fun launch() {
                if (!app.routingHelper.isFollowingMode ||
                    !activity.lifecycle.currentState.isAtLeast(Lifecycle.State.RESUMED)) return
                try {
                    // For-result supplies Android's authenticated callingPackage to the bridge.
                    activity.startActivityForResult(Intent().setClassName(bridge, ACTIVITY)
                        .putExtra("auto_start_from_osmand", true), 61580)
                } catch (error: Exception) {
                    LOG.warn("Junction companion could not start", error)
                    app.showToastMessage(R.string.junction_companion_start_manually)
                }
            }
            if (automatic) {
                launch()
            } else {
                val remember = CheckBox(activity).apply {
                    setText(R.string.junction_companion_remember)
                }
                AlertDialog.Builder(activity)
                    .setTitle(R.string.junction_companion_prompt_title)
                    .setMessage(R.string.junction_companion_prompt_message)
                    .setView(remember)
                    .setPositiveButton(R.string.shared_string_open) { _, _ ->
                        if (app.routingHelper.isFollowingMode) {
                            if (remember.isChecked) app.settings.JUNCTION_AUTO_START.setModeValue(mode, true)
                            launch()
                        }
                    }
                    .setNegativeButton(R.string.shared_string_cancel, null)
                    .show()
            }
        }
    }
}
