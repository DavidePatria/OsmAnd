package net.osmand.plus.routing.companion

import android.content.Intent
import androidx.lifecycle.Lifecycle
import net.osmand.PlatformUtil
import net.osmand.plus.OsmandApplication
import net.osmand.plus.R

/** Optional UI launch only. The Garmin SDK stays in the separate companion APK. */
object JunctionCompanionStarter {
    private const val BRIDGE="net.osmand.junction.bridge.debug"
    @JvmStatic fun onNavigationStarted(app: OsmandApplication) {
        if (!app.settings.JUNCTION_AUTO_START.getModeValue(app.routingHelper.appMode)) return
        app.runInUIThread {
            val activity=app.osmandMap.mapView.mapActivity
            if (activity==null || !activity.lifecycle.currentState.isAtLeast(Lifecycle.State.RESUMED)) {
                LOG.info("Junction companion not started: map activity is not visible")
                app.showToastMessage(R.string.junction_companion_start_manually)
                return@runInUIThread
            }
            try {
                // For-result supplies Android's authenticated callingPackage to the bridge.
                activity.startActivityForResult(Intent().setClassName(BRIDGE,
                    "net.osmand.junction.bridge.NavigationActivity").putExtra("auto_start_from_osmand",true),61580)
            } catch (error: Exception) {
                LOG.warn("Junction companion could not start",error)
                app.showToastMessage(R.string.junction_companion_start_manually)
            }
        }
    }
    private val LOG=PlatformUtil.getLog(JunctionCompanionStarter::class.java)
}
