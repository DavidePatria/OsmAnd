package net.osmand.junction.bridge

/** A data field cannot be launched through the watch-app prompt. */
internal object WatchTarget {
    fun appId(dataField: Boolean): String = if (dataField) NavigationService.DATA_FIELD_APP_ID else EchoActivity.WATCH_APP_ID
    fun shouldPrompt(dataField: Boolean, requested: Boolean): Boolean = requested && !dataField
}
